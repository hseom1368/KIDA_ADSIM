"""CZML 내보내기 테스트"""

import json
import os
import tempfile
import pytest

from modules.model import AirDefenseModel
from modules.exporters import CZMLExporter, CesiumConfigExporter


@pytest.fixture
def snapshot_result():
    m = AirDefenseModel(
        architecture="killweb", scenario="scenario_1_saturation",
        seed=42, record_snapshots=True,
    )
    return m.run_full()


class TestCZMLExporter:
    def test_build_czml_nonempty(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        czml = exporter.build_czml()
        assert len(czml) > 1  # 최소 document + entities

    def test_document_packet(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        czml = exporter.build_czml()
        doc = czml[0]
        assert doc["id"] == "document"
        assert "clock" in doc

    def test_threat_packets_exist(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        czml = exporter.build_czml()
        threat_packets = [p for p in czml if p["id"].startswith("threat_")]
        assert len(threat_packets) > 0

    def test_sensor_packets_exist(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        czml = exporter.build_czml()
        sensor_packets = [p for p in czml if p["id"].startswith("sensor_")]
        assert len(sensor_packets) > 0

    def test_export_file(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        with tempfile.NamedTemporaryFile(suffix=".czml", delete=False) as f:
            filepath = f.name

        try:
            exporter.export(filepath)
            assert os.path.exists(filepath)
            with open(filepath) as f:
                data = json.load(f)
            assert isinstance(data, list)
            assert data[0]["id"] == "document"
        finally:
            os.unlink(filepath)

    def test_to_json(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        json_str = exporter.to_json()
        data = json.loads(json_str)
        assert isinstance(data, list)

    def test_empty_snapshots(self):
        exporter = CZMLExporter([], {"defense_target": (100, 50)})
        czml = exporter.build_czml()
        assert len(czml) == 1  # document only

    def test_defense_target_packet(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        czml = exporter.build_czml()
        target_packets = [p for p in czml if p["id"] == "defense_target"]
        assert len(target_packets) == 1


# ── v0.6.1 통합 테스트 ──────────────────────────────────────────

@pytest.fixture(scope="module")
def full_result_with_topology():
    """시나리오 1 killweb, 스냅샷 + 토폴로지 엣지 포함."""
    m = AirDefenseModel(
        architecture="killweb", scenario="scenario_1_saturation",
        seed=42, record_snapshots=True,
    )
    result = m.run_full()
    edges = [
        {"source": u, "target": v, "link_type": d.get("link_type", "")}
        for u, v, d in m.topology.edges(data=True)
    ]
    result["topology_edges"] = edges
    return result


class TestCZMLv2Integration:
    """v0.6.1 CZML Exporter 통합 테스트."""

    def test_full_export_valid_json(self, full_result_with_topology):
        r = full_result_with_topology
        exporter = CZMLExporter(
            r["snapshots"], r["config"],
            topology_edges=r["topology_edges"], architecture="killweb",
        )
        czml = exporter.build_czml()
        # JSON 직렬화 가능 확인
        json_str = json.dumps(czml)
        data = json.loads(json_str)
        assert data[0]["id"] == "document"

    def test_engagement_packets_exist(self, full_result_with_topology):
        r = full_result_with_topology
        exporter = CZMLExporter(r["snapshots"], r["config"])
        czml = exporter.build_czml()
        eng = [p for p in czml if p["id"].startswith("engagement_")]
        assert len(eng) > 0

    def test_effect_packets_match_engagements(self, full_result_with_topology):
        r = full_result_with_topology
        exporter = CZMLExporter(r["snapshots"], r["config"])
        czml = exporter.build_czml()
        eng = [p for p in czml if p["id"].startswith("engagement_")]
        eff = [p for p in czml if p["id"].startswith("effect_")]
        # 각 교전에 대해 효과 마커 1개씩
        assert len(eff) == len(eng)

    def test_topology_packets_count(self, full_result_with_topology):
        r = full_result_with_topology
        exporter = CZMLExporter(
            r["snapshots"], r["config"],
            topology_edges=r["topology_edges"], architecture="killweb",
        )
        czml = exporter.build_czml()
        topo = [p for p in czml if p["id"].startswith("topo_")]
        # 모든 엣지의 양쪽 노드가 스냅샷에 존재하면 패킷 수 == 엣지 수
        assert len(topo) > 0
        assert len(topo) <= len(r["topology_edges"])

    def test_backward_compatible_no_topology(self, snapshot_result):
        """topology_edges 없이도 기존대로 동작."""
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        czml = exporter.build_czml()
        topo = [p for p in czml if p["id"].startswith("topo_")]
        assert len(topo) == 0

    def test_all_scenarios_no_crash(self):
        """7시나리오 × 2아키텍처 CZML export 에러 없음."""
        from tests.conftest import EXPERIMENT_SCENARIOS, ARCHITECTURES
        for scenario in EXPERIMENT_SCENARIOS:
            for arch in ARCHITECTURES:
                m = AirDefenseModel(
                    architecture=arch, scenario=scenario,
                    seed=42, record_snapshots=True,
                )
                r = m.run_full()
                exporter = CZMLExporter(r["snapshots"], r["config"])
                czml = exporter.build_czml()
                assert czml[0]["id"] == "document"


class TestCesiumConfigExporter:
    """CesiumConfigExporter 통합 테스트."""

    def test_config_has_required_keys(self, full_result_with_topology):
        r = full_result_with_topology
        exporter = CesiumConfigExporter(
            r["snapshots"], r["config"], "killweb", "scenario_1_saturation",
        )
        config = exporter.build_config()
        required = {"metadata", "camera_presets", "radar_volumes", "batteries",
                     "engagement_policy", "hud_config", "coordinate_reference"}
        assert required.issubset(config.keys())

    def test_radar_volumes_count(self, full_result_with_topology):
        r = full_result_with_topology
        exporter = CesiumConfigExporter(
            r["snapshots"], r["config"], "killweb", "scenario_1_saturation",
        )
        config = exporter.build_config()
        sensor_count = len(r["snapshots"][0]["sensors"])
        assert len(config["radar_volumes"]) == sensor_count

    def test_batteries_count(self, full_result_with_topology):
        r = full_result_with_topology
        exporter = CesiumConfigExporter(
            r["snapshots"], r["config"], "killweb", "scenario_1_saturation",
        )
        config = exporter.build_config()
        shooter_count = len(r["snapshots"][0]["shooters"])
        assert len(config["batteries"]) == shooter_count

    def test_export_creates_valid_json(self, full_result_with_topology):
        r = full_result_with_topology
        exporter = CesiumConfigExporter(
            r["snapshots"], r["config"], "killweb", "scenario_1_saturation",
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            exporter.export(filepath)
            with open(filepath) as f:
                data = json.load(f)
            assert "metadata" in data
        finally:
            os.unlink(filepath)
