"""CZML 스키마 준수 검증 테스트 (v0.6.1 P1-T0).

TDD 진입점: CZML/JSON 출력이 Cesium 스펙 + 프로젝트 스키마를 준수하는지 검증.
미구현 기능은 @pytest.mark.xfail 로 표시 → 해당 Task 완료 후 제거.
"""

import pytest

from modules.model import AirDefenseModel
from modules.exporters import CZMLExporter


# ── 스키마 상수 ──────────────────────────────────────────────────

REQUIRED_THREAT_KEYS = {"id", "position", "point", "path", "properties"}
REQUIRED_THREAT_POSITION_KEYS = {
    "epoch", "cartographicDegrees", "interpolationAlgorithm", "interpolationDegree",
}
REQUIRED_THREAT_PROPERTIES = {"type", "status"}

REQUIRED_ENGAGEMENT_PROPERTIES = {"type", "result", "shooter_id", "threat_id"}

REQUIRED_CONFIG_TOP_KEYS = {
    "metadata", "camera_presets", "radar_volumes", "batteries",
    "engagement_policy", "hud_config", "coordinate_reference",
}


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sim_result():
    """시나리오 1 killweb, seed=42, 스냅샷 기록."""
    m = AirDefenseModel(
        architecture="killweb",
        scenario="scenario_1_saturation",
        seed=42,
        record_snapshots=True,
    )
    return m.run_full()


@pytest.fixture(scope="module")
def czml_packets(sim_result):
    """CZMLExporter 로 생성한 전체 패킷 리스트."""
    exporter = CZMLExporter(sim_result["snapshots"], sim_result["config"])
    return exporter.build_czml()


@pytest.fixture(scope="module")
def threat_packets(czml_packets):
    return [p for p in czml_packets if p.get("id", "").startswith("threat_")]


@pytest.fixture(scope="module")
def engagement_packets(czml_packets):
    return [p for p in czml_packets if p.get("id", "").startswith("engagement_")]


# ── TestCZMLDocumentPacket ───────────────────────────────────────

class TestCZMLDocumentPacket:
    """Document 패킷 기본 구조 검증 (기존 구현으로 즉시 PASS)."""

    def test_first_packet_is_document(self, czml_packets):
        assert czml_packets[0]["id"] == "document"

    def test_document_has_clock(self, czml_packets):
        doc = czml_packets[0]
        assert "clock" in doc
        assert "interval" in doc["clock"]
        assert "currentTime" in doc["clock"]

    def test_document_has_name(self, czml_packets):
        assert czml_packets[0]["name"] == "KIDA_ADSIM"

    def test_document_has_version(self, czml_packets):
        assert czml_packets[0]["version"] == "1.0"


# ── TestThreatPacketSchema ───────────────────────────────────────

class TestThreatPacketSchema:
    """위협 패킷 스키마: properties + interpolation 필드 검증."""

    def test_threat_packets_exist(self, threat_packets):
        assert len(threat_packets) > 0

    def test_threat_has_required_keys(self, threat_packets):
        for pkt in threat_packets:
            assert REQUIRED_THREAT_KEYS.issubset(pkt.keys()), (
                f"Missing keys in {pkt['id']}: "
                f"{REQUIRED_THREAT_KEYS - pkt.keys()}"
            )

    def test_threat_position_has_interpolation(self, threat_packets):
        for pkt in threat_packets:
            pos = pkt["position"]
            assert REQUIRED_THREAT_POSITION_KEYS.issubset(pos.keys()), (
                f"Missing position keys in {pkt['id']}: "
                f"{REQUIRED_THREAT_POSITION_KEYS - pos.keys()}"
            )

    def test_threat_properties_fields(self, threat_packets):
        for pkt in threat_packets:
            props = pkt["properties"]
            assert REQUIRED_THREAT_PROPERTIES.issubset(props.keys())

    def test_interpolation_algorithm_valid(self, threat_packets):
        valid_algorithms = {"LINEAR", "LAGRANGE", "HERMITE"}
        for pkt in threat_packets:
            algo = pkt["position"]["interpolationAlgorithm"]
            assert algo in valid_algorithms, f"Invalid algorithm: {algo}"

    def test_interpolation_degree_positive(self, threat_packets):
        for pkt in threat_packets:
            degree = pkt["position"]["interpolationDegree"]
            assert isinstance(degree, int) and degree >= 1


# ── TestEngagementPacketSchema ───────────────────────────────────

class TestEngagementPacketSchema:
    """교전 이벤트 패킷 스키마 검증."""

    def test_engagement_packets_exist(self, engagement_packets):
        assert len(engagement_packets) > 0, "교전 이벤트가 있으면 패킷이 생성되어야 함"

    def test_engagement_has_polyline(self, engagement_packets):
        assert len(engagement_packets) > 0, "engagement 패킷이 있어야 검증 가능"
        for pkt in engagement_packets:
            assert "polyline" in pkt, f"{pkt['id']} missing polyline"

    def test_engagement_has_properties(self, engagement_packets):
        assert len(engagement_packets) > 0, "engagement 패킷이 있어야 검증 가능"
        for pkt in engagement_packets:
            props = pkt.get("properties", {})
            assert REQUIRED_ENGAGEMENT_PROPERTIES.issubset(props.keys()), (
                f"Missing engagement properties in {pkt['id']}"
            )

    def test_effect_markers_exist(self, czml_packets):
        effects = [p for p in czml_packets if p.get("id", "").startswith("effect_")]
        assert len(effects) > 0, "교전 결과 효과 마커가 생성되어야 함"


# ── TestTopologyPacketSchema ─────────────────────────────────────

class TestTopologyPacketSchema:
    """C2 토폴로지 polyline 패킷 스키마 검증."""

    def test_topology_packets_exist(self, sim_result):
        edges = [
            {"source": "EWR_1", "target": "MCRC", "link_type": "sensor_to_c2"}
        ]
        exporter = CZMLExporter(
            sim_result["snapshots"], sim_result["config"],
            topology_edges=edges, architecture="killweb",
        )
        czml = exporter.build_czml()
        topo = [p for p in czml if p.get("id", "").startswith("topo_")]
        assert len(topo) > 0

    def test_topology_has_polyline(self, sim_result):
        edges = [
            {"source": "EWR_1", "target": "MCRC", "link_type": "sensor_to_c2"}
        ]
        exporter = CZMLExporter(
            sim_result["snapshots"], sim_result["config"],
            topology_edges=edges, architecture="killweb",
        )
        czml = exporter.build_czml()
        topo = [p for p in czml if p.get("id", "").startswith("topo_")]
        for pkt in topo:
            assert "polyline" in pkt


# ── TestCesiumConfigSchema ───────────────────────────────────────

class TestCesiumConfigSchema:
    """CesiumConfigExporter viewer_config.json 스키마 검증."""

    def test_config_has_required_keys(self, sim_result):
        from modules.exporters import CesiumConfigExporter
        exporter = CesiumConfigExporter(
            sim_result["snapshots"], sim_result["config"],
            "killweb", "scenario_1_saturation",
        )
        config = exporter.build_config()
        assert REQUIRED_CONFIG_TOP_KEYS.issubset(config.keys()), (
            f"Missing config keys: {REQUIRED_CONFIG_TOP_KEYS - config.keys()}"
        )

    def test_config_metadata_fields(self, sim_result):
        from modules.exporters import CesiumConfigExporter
        exporter = CesiumConfigExporter(
            sim_result["snapshots"], sim_result["config"],
            "killweb", "scenario_1_saturation",
        )
        config = exporter.build_config()
        meta = config["metadata"]
        assert meta["architecture"] == "killweb"
        assert meta["scenario"] == "scenario_1_saturation"
        assert "version" in meta

    def test_radar_volumes_count_matches_sensors(self, sim_result):
        from modules.exporters import CesiumConfigExporter
        exporter = CesiumConfigExporter(
            sim_result["snapshots"], sim_result["config"],
            "killweb", "scenario_1_saturation",
        )
        config = exporter.build_config()
        sensor_count = len(sim_result["snapshots"][0]["sensors"])
        assert len(config["radar_volumes"]) == sensor_count
