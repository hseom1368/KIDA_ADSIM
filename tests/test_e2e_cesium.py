"""E2E 통합 테스트: Python 시뮬레이션 → CZML/JSON 내보내기 파이프라인 검증"""

import json
import os
import tempfile
import pytest

from modules.model import AirDefenseModel
from modules.exporters import CZMLExporter, CesiumConfigExporter
from tests.conftest import EXPERIMENT_SCENARIOS, ARCHITECTURES


@pytest.fixture(scope="module")
def e2e_killweb_result():
    """S1 Kill Web 전체 파이프라인 결과."""
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


class TestE2ECesiumIntegration:
    """전체 파이프라인: 시뮬레이션 → CZML → JSON 검증."""

    def test_full_pipeline_czml(self, e2e_killweb_result):
        """S1 Kill Web: CZML 생성 → 패킷 수 검증."""
        r = e2e_killweb_result
        exporter = CZMLExporter(
            r["snapshots"], r["config"],
            topology_edges=r["topology_edges"], architecture="killweb",
        )
        czml = exporter.build_czml()

        # document + threats + engagements + effects + sensors + shooters + c2 + topo + target
        assert len(czml) > 10
        assert czml[0]["id"] == "document"

        # 패킷 유형별 존재 확인
        ids = [p["id"] for p in czml]
        assert any(i.startswith("threat_") for i in ids)
        assert any(i.startswith("sensor_") for i in ids)
        assert any(i.startswith("shooter_") for i in ids)
        assert any(i.startswith("engagement_") for i in ids)
        assert any(i.startswith("effect_") for i in ids)
        assert any(i.startswith("topo_") for i in ids)
        assert "defense_target" in ids

    def test_full_pipeline_config(self, e2e_killweb_result):
        """S1 Kill Web: viewer_config.json 생성 + 7키 검증."""
        r = e2e_killweb_result
        exporter = CesiumConfigExporter(
            r["snapshots"], r["config"], "killweb", "scenario_1_saturation",
        )
        config = exporter.build_config()

        assert "radar_volumes" in config
        assert len(config["radar_volumes"]) == len(r["snapshots"][0]["sensors"])
        assert len(config["batteries"]) == len(r["snapshots"][0]["shooters"])
        assert config["metadata"]["architecture"] == "killweb"

    def test_czml_entity_count_matches_simulation(self, e2e_killweb_result):
        """CZML 위협 패킷 수 = 시뮬레이션 고유 위협 수."""
        r = e2e_killweb_result
        exporter = CZMLExporter(r["snapshots"], r["config"])
        czml = exporter.build_czml()

        threat_packets = [p for p in czml if p["id"].startswith("threat_")]
        # 시뮬레이션의 고유 위협 ID
        threat_ids = set()
        for snap in r["snapshots"]:
            for t in snap["threats"]:
                threat_ids.add(t["id"])
        assert len(threat_packets) == len(threat_ids)

    def test_czml_json_serializable(self, e2e_killweb_result):
        """CZML이 JSON 직렬화 가능한지 확인."""
        r = e2e_killweb_result
        exporter = CZMLExporter(
            r["snapshots"], r["config"],
            topology_edges=r["topology_edges"], architecture="killweb",
        )
        json_str = exporter.to_json()
        data = json.loads(json_str)
        assert isinstance(data, list)

    def test_file_export_roundtrip(self, e2e_killweb_result):
        """CZML + JSON 파일 내보내기 → 재로드 검증."""
        r = e2e_killweb_result
        with tempfile.TemporaryDirectory() as tmpdir:
            czml_path = os.path.join(tmpdir, "test.czml")
            config_path = os.path.join(tmpdir, "config.json")

            CZMLExporter(
                r["snapshots"], r["config"],
                topology_edges=r["topology_edges"], architecture="killweb",
            ).export(czml_path)

            CesiumConfigExporter(
                r["snapshots"], r["config"], "killweb", "scenario_1_saturation",
            ).export(config_path)

            # 파일 존재 확인
            assert os.path.exists(czml_path)
            assert os.path.exists(config_path)

            # 파일 내용 유효 JSON 확인
            with open(czml_path) as f:
                czml = json.load(f)
            with open(config_path) as f:
                config = json.load(f)

            assert czml[0]["id"] == "document"
            assert "metadata" in config

    def test_all_scenarios_export_no_crash(self):
        """7시나리오 × 2아키텍처 = 14개 CZML + JSON 에러 없음."""
        for scenario in EXPERIMENT_SCENARIOS:
            for arch in ARCHITECTURES:
                m = AirDefenseModel(
                    architecture=arch, scenario=scenario,
                    seed=42, record_snapshots=True,
                )
                r = m.run_full()
                edges = [
                    {"source": u, "target": v, "link_type": d.get("link_type", "")}
                    for u, v, d in m.topology.edges(data=True)
                ]

                czml_exp = CZMLExporter(
                    r["snapshots"], r["config"],
                    topology_edges=edges, architecture=arch,
                )
                czml = czml_exp.build_czml()
                assert czml[0]["id"] == "document", f"Failed: {scenario}/{arch}"

                cfg_exp = CesiumConfigExporter(
                    r["snapshots"], r["config"], arch, scenario,
                )
                config = cfg_exp.build_config()
                assert "metadata" in config, f"Failed: {scenario}/{arch}"

    def test_baseline_unchanged(self):
        """시뮬레이션 기준선 불변 (exporters 변경이 model에 영향 없음)."""
        for arch, expected_leaker in [("linear", 35.6), ("killweb", 22.2)]:
            m = AirDefenseModel(
                architecture=arch, scenario="scenario_1_saturation", seed=42,
            )
            r = m.run_full()
            leaker = r["metrics"]["leaker_rate"]
            assert abs(leaker - expected_leaker) < 0.5, (
                f"{arch}: leaker={leaker:.1f}% != expected {expected_leaker}%"
            )
