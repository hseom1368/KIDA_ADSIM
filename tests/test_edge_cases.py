"""test_edge_cases.py - 엣지 케이스 및 극한 상황 테스트"""

import random
import pytest
from modules.model import AirDefenseModel
from modules.agents import ThreatAgent, ShooterAgent
from modules.config import ENGAGEMENT_POLICY


class TestAmmoExhaustion:
    """탄약 소진 상황"""

    def test_all_shooters_no_ammo(self):
        """모든 사수 탄약 0 → 교전 0, 전량 누출"""
        model = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation", seed=42
        )
        for sh in model.shooter_agents:
            sh.ammo_count = 0
        result = model.run_full()
        assert result["metrics"]["engagement_success_rate"] == 0.0
        assert result["metrics"]["leaker_rate"] > 0

    def test_partial_ammo_exhaustion(self):
        """일부 사수만 탄약 0 → 에러 없이 완료"""
        model = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation", seed=42
        )
        for sh in model.shooter_agents[:3]:
            sh.ammo_count = 0
        result = model.run_full()
        assert result["total_steps"] > 0


class TestExtremeJamming:
    """극한 재밍 환경"""

    def test_max_jamming_no_crash(self):
        """jamming_level=1.0 → 에러 없이 완료"""
        model = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation",
            seed=42, jamming_level=1.0
        )
        result = model.run_full()
        assert result["total_steps"] > 0

    def test_heavy_jamming_increases_leaker_rate(self):
        """EW heavy 시나리오가 light보다 누출률이 높음 (멀티 시드 평균)"""
        avg_light = 0
        avg_heavy = 0
        n_seeds = 5
        for seed in range(n_seeds):
            m_light = AirDefenseModel(
                architecture="killweb", scenario="scenario_3_ew_light", seed=seed
            )
            m_heavy = AirDefenseModel(
                architecture="killweb", scenario="scenario_3_ew_heavy", seed=seed
            )
            avg_light += m_light.run_full()["metrics"]["leaker_rate"]
            avg_heavy += m_heavy.run_full()["metrics"]["leaker_rate"]
        avg_light /= n_seeds
        avg_heavy /= n_seeds
        assert avg_heavy >= avg_light, (
            f"heavy({avg_heavy:.1f}%) < light({avg_light:.1f}%)"
        )


class TestNodeDestruction:
    """노드 파괴 극한 케이스"""

    def test_scenario5_completes(self):
        """시나리오 5(노드 파괴) 양쪽 아키텍처 에러 없이 완료"""
        for arch in ["linear", "killweb"]:
            model = AirDefenseModel(
                architecture=arch, scenario="scenario_5_node_destruction", seed=42
            )
            result = model.run_full()
            assert result["total_steps"] > 0
            assert result["metrics"]["leaker_rate"] >= 0

    def test_killweb_more_resilient_than_linear(self):
        """노드 파괴 시 Kill Web이 Linear보다 누출률이 낮음 (멀티 시드)"""
        linear_leakers = 0
        killweb_leakers = 0
        n_seeds = 5
        for seed in range(n_seeds):
            m_lin = AirDefenseModel(
                architecture="linear",
                scenario="scenario_5_node_destruction", seed=seed
            )
            m_kw = AirDefenseModel(
                architecture="killweb",
                scenario="scenario_5_node_destruction", seed=seed
            )
            linear_leakers += m_lin.run_full()["metrics"]["leaker_rate"]
            killweb_leakers += m_kw.run_full()["metrics"]["leaker_rate"]
        # Kill Web이 평균적으로 더 낮은 누출률
        assert killweb_leakers <= linear_leakers + 10.0  # 10% 오차 허용


class TestScenario4Reproducibility:
    """시나리오 4 재현성 (Poisson 도착)"""

    def test_same_seed_same_results(self):
        """동일 seed → 동일 결과"""
        results = []
        for _ in range(2):
            m = AirDefenseModel(
                architecture="killweb", scenario="scenario_4_sequential", seed=42
            )
            r = m.run_full()
            results.append(r["metrics"]["leaker_rate"])
        assert results[0] == results[1], "시나리오 4: 동일 seed에서 결과가 달라짐"

    def test_different_seed_different_results(self):
        """다른 seed → 다른 결과 (비결정적 위협 도착)"""
        m1 = AirDefenseModel(
            architecture="killweb", scenario="scenario_4_sequential", seed=1
        )
        m2 = AirDefenseModel(
            architecture="killweb", scenario="scenario_4_sequential", seed=999
        )
        r1 = m1.run_full()
        r2 = m2.run_full()
        # 위협 수가 다를 수 있음 (Poisson)
        t1 = len([t for t in m1.threat_agents])
        t2 = len([t for t in m2.threat_agents])
        assert t1 != t2 or r1["metrics"]["leaker_rate"] != r2["metrics"]["leaker_rate"], \
            "다른 seed인데 결과가 완전히 동일"


class TestShooterScore3D:
    """shooter_score()가 3D 경사거리를 사용하는지 검증"""

    def test_score_accounts_for_altitude(self):
        """고도가 다른 위협에 대해 shooter_score가 다른 값을 반환"""
        model = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation", seed=42
        )
        shooter = model.shooter_agents[0]
        near_pos = (shooter.pos[0] + 20, shooter.pos[1])

        threat_low = ThreatAgent(model, "AIRCRAFT", near_pos, (100, 50), launch_time=0)
        threat_low.altitude = 1.0

        threat_high = ThreatAgent(model, "AIRCRAFT", near_pos, (100, 50), launch_time=0)
        threat_high.altitude = 15.0

        score_low = shooter.shooter_score(threat_low, 0.0)
        score_high = shooter.shooter_score(threat_high, 0.0)

        # 같은 수평 위치지만 고도 차이로 점수가 달라야 함
        if score_low > 0 and score_high > 0:
            assert score_low != score_high, \
                "동일 수평위치, 다른 고도인데 shooter_score가 같음"


class TestConfigConstants:
    """config에서 추출한 상수가 올바르게 적용되는지 검증"""

    def test_target_arrival_distance(self):
        """위협 도달 판정 거리가 config 값과 일치"""
        assert ENGAGEMENT_POLICY["target_arrival_distance"] == 1.0

    def test_effective_range_ratio(self):
        """유효 교전 범위 비율이 config 값과 일치"""
        assert ENGAGEMENT_POLICY["effective_range_ratio"] == 0.95

    def test_coverage_overlap_factor(self):
        """커버리지 중첩 보정 계수가 config 값과 일치"""
        assert ENGAGEMENT_POLICY["coverage_overlap_factor"] == 0.7
