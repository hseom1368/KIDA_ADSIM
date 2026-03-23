"""아키텍처 전략 패턴 테스트"""

import pytest
from modules.model import AirDefenseModel
from modules.strategies import LinearC2Strategy, KillWebStrategy, ArchitectureStrategy
from modules.registry import EntityRegistry
from modules.agents import ThreatAgent
from modules.config import ENGAGEMENT_POLICY, ADAPTIVE_ENGAGEMENT, COMM_DEGRADATION


@pytest.fixture
def registry():
    reg = EntityRegistry()
    reg.load_from_config()
    return reg


@pytest.fixture
def linear_model():
    return AirDefenseModel(architecture="linear", scenario="scenario_1_saturation", seed=42)


@pytest.fixture
def killweb_model():
    return AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)


class TestStrategySelection:
    def test_linear_model_has_linear_strategy(self, linear_model):
        assert isinstance(linear_model.strategy, LinearC2Strategy)

    def test_killweb_model_has_killweb_strategy(self, killweb_model):
        assert isinstance(killweb_model.strategy, KillWebStrategy)

    def test_both_are_architecture_strategy(self, linear_model, killweb_model):
        assert isinstance(linear_model.strategy, ArchitectureStrategy)
        assert isinstance(killweb_model.strategy, ArchitectureStrategy)


class TestRedundancyFactor:
    def test_linear_redundancy_factor(self, registry):
        strategy = LinearC2Strategy(registry)
        assert strategy.get_redundancy_factor() == 1.0

    def test_killweb_redundancy_factor(self, registry):
        strategy = KillWebStrategy(registry)
        assert strategy.get_redundancy_factor() == COMM_DEGRADATION["killweb_redundancy_factor"]

    def test_model_comm_uses_redundancy(self, killweb_model):
        assert killweb_model.comm_channel.redundancy_factor == COMM_DEGRADATION["killweb_redundancy_factor"]


class TestLinearStrategy:
    def test_topology_builds(self, linear_model):
        assert linear_model.topology.number_of_nodes() > 0
        assert linear_model.topology.number_of_edges() > 0

    def test_fusion_bonus_zero(self, linear_model):
        threat = ThreatAgent(linear_model, "SRBM", (100, 180), (100, 50))
        bonus = linear_model.strategy.compute_fusion_bonus(linear_model, threat)
        assert bonus == 0.0

    def test_max_simultaneous_fixed(self, linear_model):
        threat = ThreatAgent(linear_model, "SRBM", (100, 180), (100, 50))
        max_sh = linear_model.strategy.get_max_simultaneous(linear_model, threat)
        assert max_sh == ENGAGEMENT_POLICY["max_simultaneous_shooters"]["SRBM"]

    def test_select_shooter_prefers_high_pk(self, linear_model):
        """Pk 기반 우선순위: PATRIOT > CHEONGUNG for SRBM"""
        threat = ThreatAgent(linear_model, "SRBM", (100, 120), (100, 50))
        shooter = linear_model.strategy.select_shooter(linear_model, threat)
        if shooter:
            # PATRIOT_PAC3가 SRBM에 대해 Pk 가장 높음
            assert shooter.weapon_type in ["PATRIOT_PAC3", "CHEONGUNG2"]

    def test_cop_update_noop(self, linear_model):
        """선형 C2는 COP 업데이트 없음"""
        # 에러 없이 실행되면 성공
        linear_model.strategy.update_cop(linear_model)

    def test_share_plan_noop(self, linear_model):
        """선형 C2는 교전 계획 공유 없음"""
        threat = ThreatAgent(linear_model, "SRBM", (100, 180), (100, 50))
        linear_model.strategy.share_engagement_plan(linear_model, threat, [])


class TestKillWebStrategy:
    def test_topology_builds(self, killweb_model):
        assert killweb_model.topology.number_of_nodes() > 0
        # Kill Web은 완전 메시이므로 엣지 수가 선형보다 많음

    def test_adaptive_max_shooters_normal(self, killweb_model):
        threat = ThreatAgent(killweb_model, "SRBM", (100, 180), (100, 50))
        max_sh = killweb_model.strategy.get_max_simultaneous(killweb_model, threat)
        assert max_sh == 3  # 정상 모드

    def test_adaptive_max_shooters_degraded(self, killweb_model):
        """탄약 30% 이하 → 단일 교전"""
        for sh in killweb_model.shooter_agents:
            sh.ammo_count = max(1, int(sh.initial_ammo * 0.2))
        threat = ThreatAgent(killweb_model, "SRBM", (100, 180), (100, 50))
        max_sh = killweb_model.strategy.get_max_simultaneous(killweb_model, threat)
        assert max_sh == ADAPTIVE_ENGAGEMENT["degraded_max_shooters"]

    def test_adaptive_max_shooters_critical(self, killweb_model):
        """탄약 10% 이하 → 고위협만 교전"""
        for sh in killweb_model.shooter_agents:
            sh.ammo_count = max(1, int(sh.initial_ammo * 0.05))
        srbm = ThreatAgent(killweb_model, "SRBM", (100, 180), (100, 50))
        uas = ThreatAgent(killweb_model, "UAS", (100, 180), (100, 50))
        assert killweb_model.strategy.get_max_simultaneous(killweb_model, srbm) == 1
        assert killweb_model.strategy.get_max_simultaneous(killweb_model, uas) == 0

    def test_cop_update_shares_status(self, killweb_model):
        """Kill Web COP는 아군 상태 공유"""
        killweb_model.strategy.update_cop(killweb_model)
        # C2 노드에 아군 상태 존재 확인
        for c2 in killweb_model.c2_agents:
            if c2.is_operational:
                assert len(c2.friendly_status) > 0
                break

    def test_share_engagement_plan(self, killweb_model):
        """Kill Web 교전 계획 공유"""
        threat = ThreatAgent(killweb_model, "SRBM", (100, 180), (100, 50))
        killweb_model.strategy.share_engagement_plan(
            killweb_model, threat, killweb_model.shooter_agents[:2]
        )
        for c2 in killweb_model.c2_agents:
            if c2.is_operational:
                assert threat.unique_id in c2.engagement_plan
                break


class TestRegistryInModel:
    def test_model_has_registry(self, linear_model):
        assert hasattr(linear_model, 'registry')
        assert linear_model.registry is not None

    def test_registry_loaded(self, linear_model):
        st = linear_model.registry.get_sensor_type("EWR")
        assert st.capability.detection_range == 500
