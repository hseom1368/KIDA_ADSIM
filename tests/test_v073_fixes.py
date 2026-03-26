"""v0.7.3 고가자산 소모율 + 중복교전 해결 테스트"""

import pytest
from modules.model import AirDefenseModel
from modules.config import REALISTIC_DEPLOYMENT


class TestExpensiveAssetWaste:
    """가설 3: 고가자산(PAC-3/THAAD)이 저가 위협(MLRS)에 소모"""

    def test_killweb_mlrs_waste_nonzero(self):
        """Kill Web이 MLRS를 정확 식별해도 BMD 사수가 교전 → 고가자산 소모"""
        m = AirDefenseModel(
            architecture="killweb", scenario="scenario_7_mlrs_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        r = m.run_full()
        # MLRS_GUIDED에 대한 Pk가 있는 BMD 사수가 교전 → waste 기록
        assert r["metrics"]["expensive_asset_waste_rate"] > 0

    def test_default_deployment_no_waste(self):
        """DEFAULT_DEPLOYMENT에서는 MLRS 없으므로 waste=0"""
        m = AirDefenseModel(
            architecture="linear", scenario="scenario_1_saturation", seed=42,
        )
        r = m.run_full()
        assert r["metrics"]["expensive_asset_waste_rate"] == 0.0

    def test_can_engage_uses_identified_type(self):
        """ShooterAgent.can_engage가 identified_type 기준 Pk 조회"""
        m = AirDefenseModel(
            architecture="linear", scenario="scenario_7_mlrs_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        # 시뮬레이션 전 — 위협 직접 생성하여 테스트
        from modules.agents import ThreatAgent
        threat = ThreatAgent(m, "MLRS_GUIDED", (100, 0), (100, 50))
        threat.identified_type = "SRBM"  # 오인식

        pac3 = [s for s in m.shooter_agents if s.weapon_type == "PATRIOT_PAC3"][0]
        # MLRS로 식별 시 Pk(MLRS_GUIDED)=0.90 > 0 → 교전 가능
        assert pac3.can_engage(threat)
        pk = pac3.compute_pk(threat)
        assert pk > 0


class TestDuplicateEngagement:
    """가설 2: C2 축 간 교전상태 미공유 → 중복교전"""

    def test_linear_duplicate_nonzero(self):
        """Linear 3축에서 중복교전 발생"""
        m = AirDefenseModel(
            architecture="linear", scenario="scenario_6_tot_mixed",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        r = m.run_full()
        assert r["metrics"]["duplicate_engagement_rate"] > 0

    def test_killweb_no_duplicate(self):
        """Kill Web COP 공유로 중복교전 방지"""
        m = AirDefenseModel(
            architecture="killweb", scenario="scenario_6_tot_mixed",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        r = m.run_full()
        assert r["metrics"]["duplicate_engagement_rate"] == 0.0

    def test_default_deployment_no_duplicate(self):
        """DEFAULT_DEPLOYMENT (3축 C2 없음) → 중복교전 없음"""
        m = AirDefenseModel(
            architecture="linear", scenario="scenario_1_saturation", seed=42,
        )
        r = m.run_full()
        assert r["metrics"]["duplicate_engagement_rate"] == 0.0

    def test_multi_axis_detection(self):
        """REALISTIC_DEPLOYMENT Linear에서 다축 탐지 발생"""
        m = AirDefenseModel(
            architecture="linear", scenario="scenario_6_tot_mixed",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        m.run_full()
        multi_axis = sum(1 for axes in m._threat_detected_axes.values()
                         if len(axes) >= 2)
        assert multi_axis > 0
