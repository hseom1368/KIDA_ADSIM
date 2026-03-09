"""test_agents.py - 에이전트 비행 프로파일, 탐지, 교전 테스트"""

import math
import random
import pytest
from modules.model import AirDefenseModel
from modules.agents import SensorAgent, ShooterAgent, ThreatAgent
from modules.config import THREAT_PARAMS


class TestThreatFlightProfile:
    """위협체 비행 프로파일 테스트"""

    def test_srbm_terminal_descent(self):
        """SRBM 종말단계에서 고도가 30km 이하로 하강"""
        model = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
        srbm_threats = [t for t in model.threat_agents if t.threat_type == "SRBM"]
        assert len(srbm_threats) > 0

        threat = srbm_threats[0]
        # 비행 시간의 90% 경과 시 (종말단계) 고도 확인
        if threat.phase_timeline:
            last_phase = threat.phase_timeline[-1]
            # 종말단계 종료 시 고도 ≈ 0km
            assert last_phase["altitude_end"] <= 1.0, "SRBM 종말단계 종료 고도가 1km 이하여야 함"
            # 종말단계 시작 고도 ≈ 30km
            assert last_phase["altitude_start"] >= 20.0, "SRBM 종말단계 시작 고도가 20km 이상이어야 함"

    def test_cruise_missile_low_altitude(self):
        """순항미사일 순항 단계에서 저고도 유지"""
        params = THREAT_PARAMS["CRUISE_MISSILE"]
        phases = params["flight_profile"]["phases"]
        # 순항 단계 (cruise) 찾기
        cruise_phase = [p for p in phases if p["name"] == "cruise"][0]
        # 순항 단계 고도 ≤ 0.5km
        assert cruise_phase["altitude_end"] <= 0.5, "순항미사일 순항 고도가 0.5km 이하여야 함"


class TestSensorDetection:
    """센서 탐지 테스트"""

    def test_detect_out_of_range(self):
        """사거리 밖 위협 미탐지"""
        model = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
        sensor = model.sensor_agents[0]
        # 매우 먼 위협 생성
        far_threat = ThreatAgent(model, "SRBM", (9999, 9999), (100, 50), launch_time=0)
        random.seed(42)
        assert sensor.detect(far_threat, 0.0) is False

    def test_detection_factor_reduces_probability(self):
        """detection_factor=0.5 적용 시 탐지 확률 감소 확인 (통계적)"""
        model = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
        sensor = model.sensor_agents[0]
        # 센서 근처 위협 생성 (탐지 가능 거리)
        near_pos = (sensor.pos[0] + 20, sensor.pos[1] + 20)
        threat = ThreatAgent(model, "AIRCRAFT", near_pos, (100, 50), launch_time=0)

        n_trials = 500
        detections_full = 0
        detections_half = 0
        for i in range(n_trials):
            random.seed(i)
            if sensor.detect(threat, 0.0, 1.0):
                detections_full += 1
            random.seed(i)
            if sensor.detect(threat, 0.0, 0.5):
                detections_half += 1

        # detection_factor=0.5 → 탐지 수가 절반 이하 (약간의 허용 오차)
        assert detections_half < detections_full, "detection_factor=0.5가 탐지 확률을 줄여야 함"


class TestShooterEngagement:
    """사격체 교전 테스트"""

    def test_cannot_engage_out_of_range(self):
        """사거리 밖 위협 교전 불가"""
        model = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
        shooter = model.shooter_agents[0]
        far_threat = ThreatAgent(model, "SRBM", (9999, 9999), (100, 50), launch_time=0)
        assert shooter.can_engage(far_threat) is False

    def test_cannot_engage_no_ammo(self):
        """탄약 소진 시 교전 불가"""
        model = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
        shooter = model.shooter_agents[0]
        shooter.ammo_count = 0
        near_pos = (shooter.pos[0] + 10, shooter.pos[1])
        threat = ThreatAgent(model, "AIRCRAFT", near_pos, (100, 50), launch_time=0)
        threat.altitude = 5.0  # 교전 가능 고도
        assert shooter.can_engage(threat) is False

    def test_pk_decreases_with_jamming(self):
        """재밍 증가 시 Pk 감소"""
        model = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
        shooter = model.shooter_agents[0]
        near_pos = (shooter.pos[0] + 20, shooter.pos[1])
        threat = ThreatAgent(model, "AIRCRAFT", near_pos, (100, 50), launch_time=0)
        threat.altitude = 5.0

        pk_no_jam = shooter.compute_pk(threat, 0.0)
        pk_with_jam = shooter.compute_pk(threat, 0.5)

        if pk_no_jam > 0:
            assert pk_with_jam < pk_no_jam, "재밍 시 Pk가 감소해야 함"
