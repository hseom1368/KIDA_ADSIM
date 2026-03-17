"""v0.6a 파라미터 교정 검증 테스트"""

import pytest
from modules.config import (
    SHOOTER_PARAMS, SCENARIO_PARAMS, DEFAULT_DEPLOYMENT, ENGAGEMENT_POLICY
)
from modules.model import AirDefenseModel


# =========================================================================
# PAC-3 MSE 파라미터 교정
# =========================================================================
class TestPAC3Corrections:
    def test_pac3_max_range_60km(self):
        """PAC-3 MSE 교전 사거리 60km (120→60)"""
        assert SHOOTER_PARAMS["PATRIOT_PAC3"]["max_range"] == 60

    def test_pac3_max_altitude_40km(self):
        """PAC-3 MSE 최대 고도 40km (30→40)"""
        assert SHOOTER_PARAMS["PATRIOT_PAC3"]["max_altitude"] == 40

    def test_pac3_ammo_12(self):
        """PAC-3 MSE 탄약 12발 (16→12, M903 MSE 캐니스터)"""
        assert SHOOTER_PARAMS["PATRIOT_PAC3"]["ammo_count"] == 12

    def test_pac3_engagement_time_9s(self):
        """PAC-3 MSE 교전 시간 9초 (5→9, hit-to-kill 사이클)"""
        assert SHOOTER_PARAMS["PATRIOT_PAC3"]["engagement_time"] == 9

    def test_pac3_cannot_engage_at_65km(self):
        """PAC-3 MSE는 65km에서 교전 불가"""
        m = AirDefenseModel(architecture="killweb",
                            scenario="scenario_1_saturation", seed=42)
        pac3 = [s for s in m.shooter_agents if s.weapon_type == "PATRIOT_PAC3"][0]
        from modules.agents import ThreatAgent
        # SRBM at 65km from PAC-3
        far_threat = ThreatAgent(m, "SRBM", (pac3.pos[0], pac3.pos[1] + 65),
                                 (100, 50))
        far_threat.altitude = 20.0
        assert not pac3.can_engage(far_threat)

    def test_pac3_can_engage_at_40km(self):
        """PAC-3 MSE는 수평 40km (경사거리 ~45km)에서 교전 가능"""
        m = AirDefenseModel(architecture="killweb",
                            scenario="scenario_1_saturation", seed=42)
        pac3 = [s for s in m.shooter_agents if s.weapon_type == "PATRIOT_PAC3"][0]
        from modules.agents import ThreatAgent
        close_threat = ThreatAgent(m, "SRBM", (pac3.pos[0], pac3.pos[1] + 40),
                                   (100, 50))
        close_threat.altitude = 20.0
        assert pac3.can_engage(close_threat)


# =========================================================================
# 천궁-II 파라미터 교정
# =========================================================================
class TestCheongung2Corrections:
    def test_cheongung2_max_range_45km(self):
        """천궁-II 최대 사거리 45km (40→45)"""
        assert SHOOTER_PARAMS["CHEONGUNG2"]["max_range"] == 45


# =========================================================================
# MCRC 재배치 검증
# =========================================================================
class TestMCRCRepositioning:
    def test_mcrc_linear_behind_shooters(self):
        """선형 C2 MCRC가 사수 후방 (100, 50)에 배치"""
        linear_nodes = DEFAULT_DEPLOYMENT["c2_nodes"]["linear"]
        mcrc = [n for n in linear_nodes if n["type"] == "MCRC"][0]
        assert mcrc["pos"] == (100, 50)

    def test_mcrc_killweb_behind_shooters(self):
        """Kill Web MCRC가 사수 후방 (100, 50)에 배치"""
        kw_nodes = DEFAULT_DEPLOYMENT["c2_nodes"]["killweb"]
        mcrc = [n for n in kw_nodes if n["type"] == "MCRC"][0]
        assert mcrc["pos"] == (100, 50)

    def test_mcrc_position_in_model(self):
        """모델 초기화 후 MCRC 위치 확인"""
        m = AirDefenseModel(architecture="linear",
                            scenario="scenario_1_saturation", seed=42)
        mcrc_agents = [c for c in m.c2_agents if c.node_type == "MCRC"]
        assert len(mcrc_agents) == 1
        assert mcrc_agents[0].pos == (100, 50)


# =========================================================================
# 시나리오 1 파상 순서 검증
# =========================================================================
class TestScenario1WaveSequencing:
    def test_wave_1_uas_first(self):
        """시나리오 1: 1파 UAS 선행"""
        waves = SCENARIO_PARAMS["scenario_1_saturation"]["waves"]
        assert waves[0]["time"] == 0
        assert "UAS" in waves[0]["threats"]
        assert "SRBM" not in waves[0]["threats"]

    def test_wave_2_cm_mid(self):
        """시나리오 1: 2파 순항미사일"""
        waves = SCENARIO_PARAMS["scenario_1_saturation"]["waves"]
        assert waves[1]["time"] == 20
        assert "CRUISE_MISSILE" in waves[1]["threats"]

    def test_wave_3_srbm_last(self):
        """시나리오 1: 3파 SRBM 최후"""
        waves = SCENARIO_PARAMS["scenario_1_saturation"]["waves"]
        assert waves[2]["time"] == 40
        assert "SRBM" in waves[2]["threats"]

    def test_total_threat_count(self):
        """시나리오 1: 총 위협 45기 (UAS 20 + CM 10 + SRBM 15)"""
        waves = SCENARIO_PARAMS["scenario_1_saturation"]["waves"]
        total = sum(
            count for wave in waves for count in wave["threats"].values()
        )
        assert total == 45
