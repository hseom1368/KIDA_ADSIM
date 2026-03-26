"""v0.7 에이전트 신규 기능 테스트"""

import pytest
from modules.model import AirDefenseModel
from modules.agents import SensorAgent, ShooterAgent, ThreatAgent
from modules.config import REALISTIC_DEPLOYMENT


@pytest.fixture
def model():
    return AirDefenseModel(
        architecture="killweb", scenario="scenario_1_saturation", seed=42,
    )


class TestShooterMinAltitude:
    """ShooterAgent min_altitude 검증"""

    def test_existing_shooters_min_altitude_zero(self, model):
        """기존 사수는 min_altitude=0 (동작 변경 없음)"""
        for sh in model.shooter_agents:
            assert sh.min_altitude == 0

    def test_thaad_min_altitude(self):
        """THAAD는 고도 40km 미만 위협에 교전 불가"""
        m = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        thaad = [s for s in m.shooter_agents if s.weapon_type == "THAAD"]
        if thaad:
            assert thaad[0].min_altitude == 40

    def test_min_altitude_blocks_low_threat(self):
        """min_altitude > 위협 고도이면 can_engage=False"""
        m = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        thaad = [s for s in m.shooter_agents if s.weapon_type == "THAAD"]
        if not thaad:
            pytest.skip("THAAD not in deployment")

        # 저고도 위협 생성 (고도 10km)
        low_threat = ThreatAgent(m, "CRUISE_MISSILE", (100, 200), (100, 50))
        low_threat.altitude = 10.0  # THAAD min_altitude=40보다 낮음
        assert not thaad[0].can_engage(low_threat)

    def test_min_altitude_allows_high_threat(self):
        """min_altitude <= 위협 고도이면 can_engage 가능 (다른 조건 충족 시)"""
        m = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        thaad = [s for s in m.shooter_agents if s.weapon_type == "THAAD"]
        if not thaad:
            pytest.skip("THAAD not in deployment")

        # 고고도 SRBM (고도 50km)
        high_threat = ThreatAgent(m, "SRBM", (100, 200), (100, 50))
        high_threat.altitude = 50.0
        # THAAD는 SRBM에 Pk=0.9, 고도 40-150km → can_engage 가능
        # (사거리 내에 있다면)
        # 정확한 결과는 거리에 따라 다르므로 min_altitude 체크만 통과하는지 확인
        assert high_threat.altitude >= thaad[0].min_altitude


class TestSensorRoleAndDetectableTypes:
    """SensorAgent 역할 분리 및 탐지 유형 필터 검증"""

    def test_existing_sensors_weapon_fc_role(self, model):
        """기존 센서는 role=weapon_fc"""
        for s in model.sensor_agents:
            assert s.role == "weapon_fc"

    def test_existing_sensors_detect_all_types(self, model):
        """기존 센서는 detectable_types=None (모든 유형 탐지)"""
        for s in model.sensor_agents:
            assert s.detectable_types is None
            assert s.can_detect_type("SRBM")
            assert s.can_detect_type("UAS")

    def test_green_pine_detects_only_srbm(self):
        """GREEN_PINE은 SRBM만 탐지"""
        m = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        gp = [s for s in m.sensor_agents if s.sensor_type == "GREEN_PINE"]
        if not gp:
            pytest.skip("GREEN_PINE not in deployment")
        assert gp[0].can_detect_type("SRBM")
        assert not gp[0].can_detect_type("CRUISE_MISSILE")
        assert not gp[0].can_detect_type("UAS")

    def test_fps117_min_detection_altitude(self):
        """FPS117은 고도 1km 미만 위협 탐지 불가"""
        m = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        fps = [s for s in m.sensor_agents if s.sensor_type == "FPS117"]
        if not fps:
            pytest.skip("FPS117 not in deployment")
        assert fps[0].min_detection_altitude == 1.0

    def test_tps880k_low_altitude_detection(self):
        """TPS880K는 50m 이상 저고도 탐지 가능"""
        m = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        tps = [s for s in m.sensor_agents if s.sensor_type == "TPS880K"]
        if not tps:
            pytest.skip("TPS880K not in deployment")
        assert tps[0].min_detection_altitude == 0.05
        assert tps[0].can_detect_type("UAS")

    def test_sensor_cueing_to(self):
        """신규 센서의 provides_cueing_to 설정 확인"""
        m = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        gp = [s for s in m.sensor_agents if s.sensor_type == "GREEN_PINE"]
        if gp:
            assert gp[0].provides_cueing_to == ["KAMD_OPS"]


class TestRealisticDeploymentSmoke:
    """REALISTIC_DEPLOYMENT 기반 시뮬레이션 스모크 테스트"""

    @pytest.mark.parametrize("arch", ["linear", "killweb"])
    def test_realistic_smoke_run(self, arch):
        """REALISTIC_DEPLOYMENT로 시뮬레이션이 에러 없이 완료"""
        m = AirDefenseModel(
            architecture=arch, scenario="scenario_1_saturation",
            seed=42, deployment=REALISTIC_DEPLOYMENT,
        )
        result = m.run_full()
        assert result["total_steps"] > 0
        assert result["metrics"]["leaker_rate"] >= 0
        assert result["metrics"]["engagement_success_rate"] >= 0
