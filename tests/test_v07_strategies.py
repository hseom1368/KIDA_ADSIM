"""v0.7.1 전략 패턴 확장 테스트 — 3축 분리, 위협 식별, 다층 교전"""

import pytest
from modules.model import AirDefenseModel
from modules.config import REALISTIC_DEPLOYMENT


class TestLinear3AxisRouting:
    """Linear C2 3축 분리 라우팅 검증"""

    def test_default_deployment_no_axis_filter(self):
        """DEFAULT_DEPLOYMENT에서는 축별 필터 적용 안 됨 (하위 호환)"""
        m = AirDefenseModel(architecture="linear", scenario="scenario_1_saturation", seed=42)
        r = m.run_full()
        # 기존과 동일하게 교전이 발생해야 함
        assert m.metrics.threats_engaged > 0
        assert r["metrics"]["leaker_rate"] < 100

    def test_realistic_deployment_srbm_uses_kamd_axis(self):
        """REALISTIC_DEPLOYMENT에서 SRBM은 KAMD_OPS 축 사수 사용"""
        m = AirDefenseModel(
            architecture="linear", scenario="scenario_1_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        r = m.run_full()
        # PAC-3, CHEONGUNG2는 KAMD_OPS 축이므로 SRBM에 교전
        kamd_shooters = [s for s in m.shooter_agents
                         if s.weapon_type in ("PATRIOT_PAC3", "CHEONGUNG2", "THAAD", "LSAM_ABM")]
        kamd_shots = sum(s.shots_fired for s in kamd_shooters)
        assert kamd_shots > 0

    def test_realistic_deployment_completes(self):
        """REALISTIC_DEPLOYMENT + 모든 시나리오 에러 없이 완료"""
        for sc in ["scenario_1_saturation", "scenario_2_complex"]:
            for arch in ["linear", "killweb"]:
                m = AirDefenseModel(
                    architecture=arch, scenario=sc, seed=42,
                    deployment=REALISTIC_DEPLOYMENT,
                )
                r = m.run_full()
                assert r["total_steps"] > 0


class TestThreatIdentification:
    """위협 식별 모델 검증"""

    def test_linear_misidentifies_mlrs(self):
        """Linear: MLRS_GUIDED를 SRBM으로 오인식 (70% 확률)"""
        m = AirDefenseModel(
            architecture="linear", scenario="scenario_7_mlrs_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        m.run_full()
        misid = sum(1 for _, i, a in m.metrics.threat_identifications
                    if i != a and a == "MLRS_GUIDED")
        total_mlrs = sum(1 for _, _, a in m.metrics.threat_identifications
                         if a == "MLRS_GUIDED")
        # 50건 중 상당수가 오인식되어야 함 (확률적이므로 넉넉한 범위)
        if total_mlrs > 0:
            misid_rate = misid / total_mlrs
            assert misid_rate > 0.3, f"MLRS 오인식률 {misid_rate:.1%}가 너무 낮음"

    def test_killweb_correctly_identifies_mlrs(self):
        """Kill Web: MLRS_GUIDED를 정확히 식별 (다중 센서 융합)"""
        m = AirDefenseModel(
            architecture="killweb", scenario="scenario_7_mlrs_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        m.run_full()
        accuracy = m.metrics.metric_15_threat_id_accuracy()
        assert accuracy >= 90.0, f"Kill Web 식별 정확도 {accuracy:.1f}%가 너무 낮음"

    def test_existing_threats_always_correct(self):
        """기존 위협(SRBM, CM 등)은 항상 정확히 식별"""
        for arch in ["linear", "killweb"]:
            m = AirDefenseModel(
                architecture=arch, scenario="scenario_1_saturation", seed=42,
            )
            m.run_full()
            accuracy = m.metrics.metric_15_threat_id_accuracy()
            assert accuracy == 100.0


class TestNewScenarios:
    """v0.7.1 신규 시나리오 검증"""

    @pytest.mark.parametrize("arch", ["linear", "killweb"])
    def test_scenario6_tot_mixed(self, arch):
        """TOT 섞어쏘기 시나리오 실행"""
        m = AirDefenseModel(
            architecture=arch, scenario="scenario_6_tot_mixed",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        r = m.run_full()
        assert r["total_steps"] > 0
        assert r["metrics"]["leaker_rate"] >= 0

    @pytest.mark.parametrize("arch", ["linear", "killweb"])
    def test_scenario7_mlrs_saturation(self, arch):
        """MLRS 포화 시나리오 실행"""
        m = AirDefenseModel(
            architecture=arch, scenario="scenario_7_mlrs_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        r = m.run_full()
        assert r["total_steps"] > 0

    def test_killweb_better_leaker_in_tot(self):
        """TOT 시나리오에서 Kill Web이 Linear보다 누출률 낮음"""
        results = {}
        for arch in ["linear", "killweb"]:
            m = AirDefenseModel(
                architecture=arch, scenario="scenario_6_tot_mixed",
                seed=42, deployment=REALISTIC_DEPLOYMENT,
            )
            r = m.run_full()
            results[arch] = r["metrics"]["leaker_rate"]
        assert results["killweb"] <= results["linear"]


class TestNewMetrics:
    """v0.7.1 신규 메트릭 검증"""

    def test_metrics_keys_present(self):
        """compute_all_metrics에 신규 키가 존재"""
        m = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
        r = m.run_full()
        met = r["metrics"]
        assert "duplicate_engagement_rate" in met
        assert "expensive_asset_waste_rate" in met
        assert "threat_id_accuracy" in met
        assert "multi_layer_intercept_opportunities" in met
        assert "inter_c2_info_delay" in met

    def test_threat_id_accuracy_default_100(self):
        """기존 시나리오에서 위협 식별 정확도 100%"""
        m = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
        r = m.run_full()
        assert r["metrics"]["threat_id_accuracy"] == 100.0
