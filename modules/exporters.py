"""
exporters.py - 시뮬레이션 결과 내보내기
CZML exporter for Cesium 3D visualization of simulation snapshots.
"""

from __future__ import annotations

import json
from typing import List, Optional


class CZMLExporter:
    """스냅샷 데이터를 CZML 형식으로 내보내기 (Cesium 3D 시각화용).

    CZML은 Cesium.js에서 사용하는 JSON 기반 시계열 지리 데이터 포맷.
    시뮬레이션의 위협 궤적, 센서 범위, 사수 위치 등을 3D로 시각화할 수 있다.

    Usage:
        model = AirDefenseModel(record_snapshots=True, ...)
        result = model.run_full()
        exporter = CZMLExporter(result["snapshots"], result["config"])
        exporter.export("output.czml")
    """

    # 색상 상수 (RGBA 0-255)
    COLORS = {
        "SRBM": [255, 0, 0, 255],           # 빨강
        "CRUISE_MISSILE": [255, 165, 0, 255], # 주황
        "AIRCRAFT": [255, 255, 0, 255],       # 노랑
        "UAS": [128, 0, 128, 255],            # 보라
        "sensor": [0, 128, 255, 180],         # 파랑 반투명
        "shooter": [0, 200, 0, 255],          # 초록
        "c2": [255, 255, 255, 255],           # 흰색
        "destroyed": [128, 128, 128, 100],    # 회색 반투명
    }

    # 시뮬레이션 좌표 → 경위도 변환 기준점 (가상)
    # 기본: 한반도 중부 (127.0°E, 37.0°N) 기준, 1km ≈ 0.009° 위도, 0.011° 경도
    BASE_LON = 127.0
    BASE_LAT = 37.0
    KM_TO_LAT = 0.009
    KM_TO_LON = 0.011

    def __init__(self, snapshots: list, config: dict,
                 base_lon: float = 127.0, base_lat: float = 37.0):
        """
        Args:
            snapshots: model.run_full()["snapshots"] 리스트
            config: {"area_size": ..., "defense_target": ...}
            base_lon: 경도 기준점
            base_lat: 위도 기준점
        """
        self.snapshots = snapshots
        self.config = config
        self.BASE_LON = base_lon
        self.BASE_LAT = base_lat

    def _sim_to_geo(self, pos: tuple, altitude_km: float = 0.0) -> list:
        """시뮬레이션 좌표 (x, y) → [경도, 위도, 고도(m)]"""
        lon = self.BASE_LON + pos[0] * self.KM_TO_LON
        lat = self.BASE_LAT + pos[1] * self.KM_TO_LAT
        alt = altitude_km * 1000  # km → m
        return [lon, lat, alt]

    def _iso_time(self, sim_time: float) -> str:
        """시뮬레이션 시간(초) → ISO 8601 문자열"""
        # 가상 시작 시각: 2024-01-01T00:00:00Z
        hours = int(sim_time // 3600)
        minutes = int((sim_time % 3600) // 60)
        seconds = int(sim_time % 60)
        return f"2024-01-01T{hours:02d}:{minutes:02d}:{seconds:02d}Z"

    def build_czml(self) -> list:
        """CZML 문서 생성"""
        if not self.snapshots:
            return [self._document_packet()]

        czml = [self._document_packet()]

        # 위협 궤적
        czml.extend(self._build_threat_packets())

        # 센서 (고정 위치 + 탐지 범위 원)
        czml.extend(self._build_sensor_packets())

        # 사수 (고정 위치 + 사거리 원)
        czml.extend(self._build_shooter_packets())

        # C2 노드 (고정 위치)
        czml.extend(self._build_c2_packets())

        # 방어 대상
        czml.append(self._build_defense_target_packet())

        return czml

    def _document_packet(self) -> dict:
        """CZML 문서 헤더 패킷"""
        if not self.snapshots:
            return {"id": "document", "name": "KIDA_ADSIM", "version": "1.0"}

        start = self._iso_time(self.snapshots[0]["time"])
        end = self._iso_time(self.snapshots[-1]["time"])
        return {
            "id": "document",
            "name": "KIDA_ADSIM",
            "version": "1.0",
            "clock": {
                "interval": f"{start}/{end}",
                "currentTime": start,
                "multiplier": 10,
            },
        }

    def _build_threat_packets(self) -> list:
        """위협체 궤적 CZML 패킷"""
        # 위협별 시계열 위치 수집
        threat_data = {}
        for snap in self.snapshots:
            t = snap["time"]
            for th in snap["threats"]:
                tid = th["id"]
                if tid not in threat_data:
                    threat_data[tid] = {
                        "type": th["type"],
                        "positions": [],
                        "alive_until": t,
                    }
                if th["alive"]:
                    threat_data[tid]["alive_until"] = t
                geo = self._sim_to_geo(th["pos"], th.get("altitude", 0))
                threat_data[tid]["positions"].append((t, geo))

        packets = []
        for tid, data in threat_data.items():
            if not data["positions"]:
                continue
            # 카르토그래픽 위치 시계열: [time, lon, lat, alt, time, ...]
            cartographic_degrees = []
            for t, geo in data["positions"]:
                cartographic_degrees.extend([t, *geo])

            start = self._iso_time(data["positions"][0][0])
            end = self._iso_time(data["alive_until"])

            packets.append({
                "id": f"threat_{tid}",
                "name": f"{data['type']}_{tid}",
                "availability": f"{start}/{end}",
                "position": {
                    "epoch": "2024-01-01T00:00:00Z",
                    "cartographicDegrees": cartographic_degrees,
                },
                "point": {
                    "color": {"rgba": self.COLORS.get(data["type"],
                                                       [255, 0, 0, 255])},
                    "pixelSize": 8,
                },
                "path": {
                    "material": {
                        "solidColor": {
                            "color": {"rgba": self.COLORS.get(data["type"],
                                                               [255, 0, 0, 255])},
                        },
                    },
                    "width": 2,
                    "leadTime": 0,
                    "trailTime": 300,
                },
            })
        return packets

    def _build_sensor_packets(self) -> list:
        """센서 CZML 패킷 (고정 위치 + 탐지 범위)"""
        if not self.snapshots:
            return []
        first = self.snapshots[0]
        packets = []
        for s in first.get("sensors", []):
            geo = self._sim_to_geo(s["pos"])
            packets.append({
                "id": f"sensor_{s['id']}",
                "name": s["id"],
                "position": {"cartographicDegrees": geo},
                "point": {
                    "color": {"rgba": self.COLORS["sensor"]},
                    "pixelSize": 10,
                },
                "ellipse": {
                    "semiMajorAxis": s["detection_range"] * 1000,
                    "semiMinorAxis": s["detection_range"] * 1000,
                    "material": {
                        "solidColor": {
                            "color": {"rgba": [0, 128, 255, 30]},
                        },
                    },
                },
            })
        return packets

    def _build_shooter_packets(self) -> list:
        """사수 CZML 패킷"""
        if not self.snapshots:
            return []
        first = self.snapshots[0]
        packets = []
        for sh in first.get("shooters", []):
            geo = self._sim_to_geo(sh["pos"])
            packets.append({
                "id": f"shooter_{sh['id']}",
                "name": f"{sh['weapon_type']}_{sh['id']}",
                "position": {"cartographicDegrees": geo},
                "point": {
                    "color": {"rgba": self.COLORS["shooter"]},
                    "pixelSize": 10,
                },
                "ellipse": {
                    "semiMajorAxis": sh["max_range"] * 1000,
                    "semiMinorAxis": sh["max_range"] * 1000,
                    "material": {
                        "solidColor": {
                            "color": {"rgba": [0, 200, 0, 20]},
                        },
                    },
                },
            })
        return packets

    def _build_c2_packets(self) -> list:
        """C2 노드 CZML 패킷"""
        if not self.snapshots:
            return []
        first = self.snapshots[0]
        packets = []
        for c in first.get("c2_nodes", []):
            geo = self._sim_to_geo(c["pos"])
            packets.append({
                "id": f"c2_{c['id']}",
                "name": c["id"],
                "position": {"cartographicDegrees": geo},
                "point": {
                    "color": {"rgba": self.COLORS["c2"]},
                    "pixelSize": 12,
                },
            })
        return packets

    def _build_defense_target_packet(self) -> dict:
        """방어 대상 CZML 패킷"""
        target = self.config.get("defense_target", (100, 50))
        geo = self._sim_to_geo(target)
        return {
            "id": "defense_target",
            "name": "Defense Target",
            "position": {"cartographicDegrees": geo},
            "point": {
                "color": {"rgba": [255, 215, 0, 255]},
                "pixelSize": 15,
            },
        }

    def export(self, filepath: str) -> None:
        """CZML 파일로 내보내기"""
        czml = self.build_czml()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(czml, f, indent=2, ensure_ascii=False)

    def to_json(self) -> str:
        """CZML JSON 문자열 반환"""
        return json.dumps(self.build_czml(), indent=2, ensure_ascii=False)
