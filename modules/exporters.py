"""
exporters.py - 시뮬레이션 결과 내보내기
CZML exporter for Cesium 3D visualization of simulation snapshots.
"""

from __future__ import annotations

import json
import re
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

    # 위협 유형별 궤적 보간 설정 (Cesium interpolation)
    INTERPOLATION_CONFIG = {
        "SRBM": {"algorithm": "LAGRANGE", "degree": 5},
        "CRUISE_MISSILE": {"algorithm": "LINEAR", "degree": 1},
        "AIRCRAFT": {"algorithm": "LAGRANGE", "degree": 3},
        "UAS": {"algorithm": "LINEAR", "degree": 1},
    }

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

    # 교전 결과 색상
    ENGAGEMENT_COLORS = {
        "hit": [255, 200, 0, 255],       # 주황 (명중)
        "miss": [128, 128, 128, 200],    # 회색 (실패)
    }

    # 토폴로지 스타일 (아키텍처별)
    TOPOLOGY_STYLES = {
        "linear": {"color": [255, 255, 255, 150], "dash": False, "width": 1.5},
        "killweb": {"color": [0, 128, 255, 150], "dash": True, "width": 1.5},
    }

    # 시뮬레이션 좌표 → 경위도 변환 기준점 (가상)
    # 기본: 한반도 중부 (127.0°E, 37.0°N) 기준, 1km ≈ 0.009° 위도, 0.011° 경도
    BASE_LON = 127.0
    BASE_LAT = 37.0
    KM_TO_LAT = 0.009
    KM_TO_LON = 0.011

    def __init__(self, snapshots: list, config: dict,
                 base_lon: float = 127.0, base_lat: float = 37.0,
                 topology_edges: Optional[list] = None,
                 architecture: Optional[str] = None):
        """
        Args:
            snapshots: model.run_full()["snapshots"] 리스트
            config: {"area_size": ..., "defense_target": ...}
            base_lon: 경도 기준점
            base_lat: 위도 기준점
            topology_edges: [{"source": str, "target": str, "link_type": str}, ...]
            architecture: "linear" 또는 "killweb" (토폴로지 스타일 결정)
        """
        self.snapshots = snapshots
        self.config = config
        self.BASE_LON = base_lon
        self.BASE_LAT = base_lat
        self.topology_edges = topology_edges
        self.architecture = architecture

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

        # 교전 이벤트 (polyline + 효과 마커)
        czml.extend(self._build_engagement_packets())

        # 센서 (고정 위치 + 탐지 범위 원)
        czml.extend(self._build_sensor_packets())

        # 사수 (고정 위치 + 사거리 원)
        czml.extend(self._build_shooter_packets())

        # C2 노드 (고정 위치)
        czml.extend(self._build_c2_packets())

        # C2 토폴로지 연결선
        czml.extend(self._build_topology_packets())

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
        """위협체 궤적 CZML 패킷 (보간 알고리즘 + 상태 properties 포함)"""
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
                        "last_alive": th["alive"],
                    }
                if th["alive"]:
                    threat_data[tid]["alive_until"] = t
                threat_data[tid]["last_alive"] = th["alive"]
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

            # 보간 설정
            interp = self.INTERPOLATION_CONFIG.get(
                data["type"], {"algorithm": "LINEAR", "degree": 1}
            )

            # 상태 판정
            status = "active" if data["last_alive"] else "destroyed"

            packets.append({
                "id": f"threat_{tid}",
                "name": f"{data['type']}_{tid}",
                "availability": f"{start}/{end}",
                "position": {
                    "epoch": "2024-01-01T00:00:00Z",
                    "cartographicDegrees": cartographic_degrees,
                    "interpolationAlgorithm": interp["algorithm"],
                    "interpolationDegree": interp["degree"],
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
                "properties": {
                    "type": data["type"],
                    "status": status,
                },
            })
        return packets

    def _build_engagement_packets(self) -> list:
        """교전 이벤트 CZML 패킷 (polyline + 효과 마커)"""
        if not self.snapshots:
            return []

        # 사수 위치 룩업 (고정)
        shooter_pos = {}
        for sh in self.snapshots[0].get("shooters", []):
            shooter_pos[sh["id"]] = sh["pos"]

        # 위협 위치를 시간별로 인덱싱
        threat_pos_by_time = {}
        for snap in self.snapshots:
            t = snap["time"]
            for th in snap["threats"]:
                threat_pos_by_time[(th["id"], t)] = (
                    th["pos"], th.get("altitude", 0)
                )

        # 스냅샷 시간 목록 (가장 가까운 시간 탐색용)
        snap_times = [s["time"] for s in self.snapshots]

        # 교전 이벤트 수집
        _engagement_re = re.compile(
            r"shooter=(\S+),\s*hit=(True|False),\s*Pk=([\d.]+)"
        )
        engagements = []
        for snap in self.snapshots:
            for evt in snap.get("events", []):
                if evt.get("event") != "engagement":
                    continue
                m = _engagement_re.search(evt.get("detail", ""))
                if not m:
                    continue
                engagements.append({
                    "time": evt["time"],
                    "threat_id": evt["threat_id"],
                    "shooter_id": m.group(1),
                    "hit": m.group(2) == "True",
                    "pk": float(m.group(3)),
                })

        packets = []
        for idx, eng in enumerate(engagements):
            sid = eng["shooter_id"]
            tid = eng["threat_id"]
            t = eng["time"]
            hit = eng["hit"]

            # 사수 위치
            s_pos = shooter_pos.get(sid)
            if s_pos is None:
                continue

            # 교전 시점의 위협 위치 (가장 가까운 스냅샷)
            closest_t = min(snap_times, key=lambda st: abs(st - t))
            t_entry = threat_pos_by_time.get((tid, closest_t))
            if t_entry is None:
                continue
            t_pos, t_alt = t_entry

            # 좌표 변환
            shooter_geo = self._sim_to_geo(s_pos, 0)
            threat_geo = self._sim_to_geo(t_pos, t_alt)

            color_key = "hit" if hit else "miss"
            color = self.ENGAGEMENT_COLORS[color_key]
            iso_start = self._iso_time(max(0, t - 5))
            iso_end = self._iso_time(t + 5)

            # 교전 polyline 패킷
            packets.append({
                "id": f"engagement_{idx}",
                "name": f"Engagement {sid}\u2192{tid}",
                "availability": f"{iso_start}/{iso_end}",
                "polyline": {
                    "positions": {
                        "cartographicDegrees": [*shooter_geo, *threat_geo],
                    },
                    "width": 2,
                    "material": {
                        "solidColor": {"color": {"rgba": color}},
                    },
                },
                "properties": {
                    "type": "engagement",
                    "result": "hit" if hit else "miss",
                    "shooter_id": sid,
                    "threat_id": tid,
                },
            })

            # 효과 마커 패킷
            iso_effect_end = self._iso_time(t + 10)
            packets.append({
                "id": f"effect_{idx}",
                "name": f"{'Hit' if hit else 'Miss'} {tid}",
                "availability": f"{self._iso_time(t)}/{iso_effect_end}",
                "position": {"cartographicDegrees": threat_geo},
                "point": {
                    "color": {"rgba": color},
                    "pixelSize": 20 if hit else 12,
                    "outlineColor": {"rgba": [255, 100, 0, 255] if hit
                                     else [100, 100, 100, 255]},
                    "outlineWidth": 3,
                },
                "properties": {
                    "type": "effect",
                    "result": "hit" if hit else "miss",
                    "shooter_id": sid,
                    "threat_id": tid,
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

    def _build_topology_packets(self) -> list:
        """C2 네트워크 토폴로지 연결선 CZML 패킷"""
        if not self.topology_edges or not self.snapshots:
            return []

        # 노드 위치 룩업 (첫 스냅샷에서 모든 엔티티 위치 수집)
        node_pos = {}
        first = self.snapshots[0]
        for s in first.get("sensors", []):
            node_pos[s["id"]] = s["pos"]
        for sh in first.get("shooters", []):
            node_pos[sh["id"]] = sh["pos"]
        for c in first.get("c2_nodes", []):
            node_pos[c["id"]] = c["pos"]

        # 아키텍처 스타일
        style = self.TOPOLOGY_STYLES.get(
            self.architecture or "linear",
            self.TOPOLOGY_STYLES["linear"],
        )

        packets = []
        for edge in self.topology_edges:
            src = edge["source"]
            tgt = edge["target"]
            src_pos = node_pos.get(src)
            tgt_pos = node_pos.get(tgt)
            if src_pos is None or tgt_pos is None:
                continue

            # 연결선 고도: 지상 500m
            src_geo = self._sim_to_geo(src_pos, 0.5)
            tgt_geo = self._sim_to_geo(tgt_pos, 0.5)

            # 재질: 점선(killweb) 또는 실선(linear)
            if style["dash"]:
                material = {
                    "polylineDash": {
                        "color": {"rgba": style["color"]},
                        "dashLength": 16.0,
                    },
                }
            else:
                material = {
                    "solidColor": {"color": {"rgba": style["color"]}},
                }

            packets.append({
                "id": f"topo_{src}_{tgt}",
                "name": f"{src}\u2192{tgt}",
                "polyline": {
                    "positions": {
                        "cartographicDegrees": [*src_geo, *tgt_geo],
                    },
                    "width": style["width"],
                    "material": material,
                },
                "properties": {
                    "link_type": edge.get("link_type", ""),
                    "architecture": self.architecture or "",
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


class CesiumConfigExporter:
    """Cesium 3D 뷰어 설정 파일(viewer_config.json) 생성기.

    시뮬레이션 결과 메타데이터, 카메라 프리셋, 레이더 볼륨,
    포대 정보 등을 프론트엔드가 소비할 수 있는 JSON으로 내보냄.

    Usage:
        exporter = CesiumConfigExporter(result["snapshots"], result["config"],
                                         "killweb", "scenario_1_saturation")
        exporter.export("viewer_config.json")
    """

    VERSION = "0.6.1"

    # 좌표 변환 상수 (CZMLExporter와 동일)
    BASE_LON = 127.0
    BASE_LAT = 37.0
    KM_TO_LAT = 0.009
    KM_TO_LON = 0.011

    # 카메라 프리셋 (한반도 중부 기준)
    CAMERA_PRESETS = {
        "overview": {
            "lon": 127.0, "lat": 37.0, "alt": 300000,
            "heading": 0, "pitch": -55, "roll": 0,
        },
        "tactical": {
            "lon": 127.03, "lat": 36.8, "alt": 130000,
            "heading": 0, "pitch": -30, "roll": 0,
        },
        "horizontal": {
            "lon": 126.65, "lat": 37.82, "alt": 60000,
            "heading": 90, "pitch": -4, "roll": 0,
        },
        "battery": {
            "lon": 127.03, "lat": 37.77, "alt": 20000,
            "heading": 0, "pitch": -38, "roll": 0,
        },
    }

    # HUD 기본 설정
    DEFAULT_HUD_CONFIG = {
        "show_radar_fov": True,
        "show_engagement_range": True,
        "show_ammo_bars": True,
        "show_engagement_log": True,
        "show_topology_links": True,
        "log_max_entries": 14,
    }

    def __init__(self, snapshots: list, config: dict,
                 architecture: str, scenario: str):
        """
        Args:
            snapshots: model.run_full()["snapshots"] 리스트
            config: {"area_size": ..., "defense_target": ...}
            architecture: "linear" 또는 "killweb"
            scenario: 시나리오 이름
        """
        self.snapshots = snapshots
        self.config = config
        self.architecture = architecture
        self.scenario = scenario

    def _sim_to_geo(self, pos: tuple) -> dict:
        """시뮬레이션 좌표 → {"lon": float, "lat": float, "alt": 0}"""
        return {
            "lon": self.BASE_LON + pos[0] * self.KM_TO_LON,
            "lat": self.BASE_LAT + pos[1] * self.KM_TO_LAT,
            "alt": 0,
        }

    def build_config(self) -> dict:
        """viewer_config.json 딕셔너리 생성 (7개 top-level 키)"""
        from datetime import datetime, timezone

        first = self.snapshots[0] if self.snapshots else {}

        # 시뮬레이션 시간 및 위협 수
        sim_time = self.snapshots[-1]["time"] if self.snapshots else 0.0
        total_threats = len(first.get("threats", []))

        # metadata
        metadata = {
            "architecture": self.architecture,
            "scenario": self.scenario,
            "sim_time_total": sim_time,
            "total_threats": total_threats,
            "version": self.VERSION,
            "generated_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }

        # radar_volumes (센서 데이터)
        radar_volumes = []
        for s in first.get("sensors", []):
            geo = self._sim_to_geo(s["pos"])
            radar_volumes.append({
                "sensor_id": s["id"],
                "position": geo,
                "detection_range_m": s["detection_range"] * 1000,
            })

        # batteries (사수 데이터)
        batteries = []
        for sh in first.get("shooters", []):
            geo = self._sim_to_geo(sh["pos"])
            batteries.append({
                "battery_id": sh["id"],
                "position": geo,
                "max_range_m": sh["max_range"] * 1000,
                "weapon_type": sh["weapon_type"],
                "initial_ammo": sh["max_ammo"],
            })

        # engagement_policy (config.py에서 가져오기)
        from modules.config import ENGAGEMENT_POLICY
        engagement_policy = {
            "optimal_pk_threshold": ENGAGEMENT_POLICY["optimal_pk_threshold"],
            "emergency_pk_threshold": ENGAGEMENT_POLICY["emergency_pk_threshold"],
            "must_engage_distance_km": ENGAGEMENT_POLICY["must_engage_distance"],
        }

        # coordinate_reference
        coordinate_reference = {
            "base_lon": self.BASE_LON,
            "base_lat": self.BASE_LAT,
            "km_to_lat": self.KM_TO_LAT,
            "km_to_lon": self.KM_TO_LON,
        }

        return {
            "metadata": metadata,
            "camera_presets": self.CAMERA_PRESETS,
            "radar_volumes": radar_volumes,
            "batteries": batteries,
            "engagement_policy": engagement_policy,
            "hud_config": self.DEFAULT_HUD_CONFIG.copy(),
            "coordinate_reference": coordinate_reference,
        }

    def export(self, filepath: str) -> None:
        """viewer_config.json 파일로 내보내기"""
        config = self.build_config()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def to_json(self) -> str:
        """JSON 문자열 반환"""
        return json.dumps(self.build_config(), indent=2, ensure_ascii=False)
