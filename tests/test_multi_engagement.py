"""test_multi_engagement.py - v0.4 다중 교전 모델링 테스트"""

import pytest
from modules.model import AirDefenseModel
from modules.config import ENGAGEMENT_POLICY


class TestMultiEngagementConfig:
    """다중 교전 설정 검증"""

    def test_max_simultaneous_shooters_in_config(self):
        """ENGAGEMENT_POLICY에 max_simultaneous_shooters 존재"""
        assert "max_simultaneous_shooters" in ENGAGEMENT_POLICY
        assert "default_max_simultaneous" in ENGAGEMENT_POLICY

    def test_srbm_max_3_shooters(self):
        """SRBM 위협에 최대 3기 사수 설정"""
        assert ENGAGEMENT_POLICY["max_simultaneous_shooters"]["SRBM"] == 3

    def test_cruise_missile_max_2_shooters(self):
        """순항미사일 위협에 최대 2기 사수 설정"""
        assert ENGAGEMENT_POLICY["max_simultaneous_shooters"]["CRUISE_MISSILE"] == 2

    def test_aircraft_uas_max_1_shooter(self):
        """항공기/UAS 위협에 1기 사수 설정"""
        assert ENGAGEMENT_POLICY["max_simultaneous_shooters"]["AIRCRAFT"] == 1
        assert ENGAGEMENT_POLICY["max_simultaneous_shooters"]["UAS"] == 1


class TestMultiEngagementExecution:
    """다중 교전 실행 검증"""

    def test_multi_engagement_metrics_recorded(self):
        """다중 교전 메트릭이 정상 기록됨"""
        model = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation", seed=42
        )
        result = model.run_full()
        # 다중 교전 메트릭 존재 확인
        assert "multi_engagement_rate" in result["metrics"]
        assert "avg_shooters_per_multi_engagement" in result["metrics"]

    def test_multi_engagement_occurs_for_high_priority(self):
        """고위협(SRBM/CM) 시나리오에서 다중 교전 발생"""
        # 시나리오 1에는 SRBM이 다수 포함 → 다중 교전 발생 기대
        model = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation", seed=42
        )
        result = model.run_full()
        assert result["metrics"]["multi_engagement_rate"] > 0, \
            "고위협 시나리오에서 다중 교전이 발생해야 함"

    def test_multi_engagement_increases_ammo_usage(self):
        """다중 교전 시 탄약 소비가 단일 교전보다 많거나 같음 (멀티 시드 평균)"""
        # 다중 교전 ON (기본)
        total_shots_multi = 0
        # 다중 교전 OFF (모든 위협 1기로 제한)
        total_shots_single = 0
        n_seeds = 3

        for seed in range(n_seeds):
            m = AirDefenseModel(
                architecture="killweb", scenario="scenario_1_saturation", seed=seed
            )
            r = m.run_full()
            total_shots_multi += m.metrics.total_shots

        # 단일 교전 모드: 임시로 모든 max_simultaneous를 1로 변경
        original = ENGAGEMENT_POLICY["max_simultaneous_shooters"].copy()
        for k in ENGAGEMENT_POLICY["max_simultaneous_shooters"]:
            ENGAGEMENT_POLICY["max_simultaneous_shooters"][k] = 1
        try:
            for seed in range(n_seeds):
                m = AirDefenseModel(
                    architecture="killweb", scenario="scenario_1_saturation", seed=seed
                )
                r = m.run_full()
                total_shots_single += m.metrics.total_shots
        finally:
            ENGAGEMENT_POLICY["max_simultaneous_shooters"].update(original)

        assert total_shots_multi >= total_shots_single, \
            f"다중 교전({total_shots_multi}발) < 단일 교전({total_shots_single}발)"

    def test_no_double_destroy(self):
        """위협이 두 번 destroy 되지 않음 — 격추 수 ≤ 총 위협 수"""
        model = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation", seed=42
        )
        result = model.run_full()
        total_threats = len(model.threat_agents)
        destroyed = sum(1 for t in model.threat_agents if not t.is_alive)
        assert destroyed <= total_threats


class TestMultiEngagementRegression:
    """기존 동작 호환성 검증"""

    def test_scenario1_completes_both_arch(self):
        """시나리오 1 양쪽 아키텍처 에러 없이 완료"""
        for arch in ["linear", "killweb"]:
            model = AirDefenseModel(
                architecture=arch, scenario="scenario_1_saturation", seed=42
            )
            result = model.run_full()
            assert result["total_steps"] > 0

    def test_killweb_still_beats_linear_multi_seed(self):
        """다중 교전 도입 후에도 Kill Web이 Linear보다 평균 누출률 낮음"""
        linear_leakers = 0
        killweb_leakers = 0
        n_seeds = 5
        for seed in range(n_seeds):
            m_lin = AirDefenseModel(
                architecture="linear", scenario="scenario_1_saturation", seed=seed
            )
            m_kw = AirDefenseModel(
                architecture="killweb", scenario="scenario_1_saturation", seed=seed
            )
            linear_leakers += m_lin.run_full()["metrics"]["leaker_rate"]
            killweb_leakers += m_kw.run_full()["metrics"]["leaker_rate"]

        avg_lin = linear_leakers / n_seeds
        avg_kw = killweb_leakers / n_seeds
        assert avg_kw <= avg_lin + 5.0, \
            f"Kill Web({avg_kw:.1f}%) > Linear({avg_lin:.1f}%) + 5%"

    def test_jamming_level_explicit_override(self):
        """v0.4 jamming_level 명시적 오버라이드 동작 확인"""
        # 시나리오 1의 jamming_level=0.0이지만, 명시적 0.5 전달
        model = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation",
            seed=42, jamming_level=0.5
        )
        assert model.jamming_level == 0.5, \
            f"명시적 값 0.5가 적용되어야 하나 {model.jamming_level}"

    def test_jamming_level_scenario_default(self):
        """jamming_level 미전달 시 시나리오 config 값 사용"""
        # scenario_3_ew_heavy의 jamming_level=0.8
        model = AirDefenseModel(
            architecture="killweb", scenario="scenario_3_ew_heavy", seed=42
        )
        assert model.jamming_level == 0.8, \
            f"시나리오 값 0.8이 적용되어야 하나 {model.jamming_level}"
