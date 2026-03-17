"""v0.6a BIHO gun/missile 분리 검증 테스트"""

import pytest
from modules.config import SHOOTER_PARAMS
from modules.model import AirDefenseModel
from modules.agents import ShooterAgent, ThreatAgent


# =========================================================================
# BIHO config 분리 검증
# =========================================================================
class TestBihoConfig:
    def test_biho_gun_range_3km(self):
        """BIHO 기관포 유효 사거리 3km"""
        assert SHOOTER_PARAMS["BIHO"]["gun_range"] == 3

    def test_biho_missile_range_7km(self):
        """BIHO 신궁 미사일 사거리 7km"""
        assert SHOOTER_PARAMS["BIHO"]["missile_range"] == 7

    def test_biho_gun_ammo_600(self):
        """BIHO 기관포 600발"""
        assert SHOOTER_PARAMS["BIHO"]["gun_ammo"] == 600

    def test_biho_missile_ammo_2(self):
        """BIHO 신궁 미사일 2발"""
        assert SHOOTER_PARAMS["BIHO"]["missile_ammo"] == 2

    def test_biho_total_ammo_602(self):
        """BIHO 총 탄약 602발 (600 + 2)"""
        assert SHOOTER_PARAMS["BIHO"]["ammo_count"] == 602

    def test_biho_pk_tables_exist(self):
        """BIHO gun/missile 별도 Pk 테이블 존재"""
        assert "pk_table_gun" in SHOOTER_PARAMS["BIHO"]
        assert "pk_table_missile" in SHOOTER_PARAMS["BIHO"]


# =========================================================================
# BIHO 에이전트 모드 분기 검증
# =========================================================================
class TestBihoEngagement:
    @pytest.fixture
    def setup(self):
        """BIHO 테스트 환경 설정"""
        m = AirDefenseModel(architecture="killweb",
                            scenario="scenario_1_saturation", seed=42)
        biho = [s for s in m.shooter_agents if s.weapon_type == "BIHO"][0]
        return m, biho

    def test_biho_has_dual_mode(self, setup):
        """BIHO 에이전트에 이중 모드 플래그 설정"""
        _, biho = setup
        assert biho._has_dual_mode is True

    def test_biho_initial_gun_ammo(self, setup):
        """BIHO 초기 기관포 탄약 600"""
        _, biho = setup
        assert biho.gun_ammo == 600

    def test_biho_initial_missile_ammo(self, setup):
        """BIHO 초기 미사일 탄약 2"""
        _, biho = setup
        assert biho.missile_ammo == 2

    def test_gun_mode_at_2km(self, setup):
        """2km 거리 UAS → gun 모드 선택"""
        m, biho = setup
        uas = ThreatAgent(m, "UAS", (biho.pos[0], biho.pos[1] + 2), (100, 50))
        uas.altitude = 0.3
        mode = biho._get_biho_mode(uas)
        assert mode == "gun"

    def test_missile_mode_at_5km(self, setup):
        """5km 거리 CM → missile 모드 선택"""
        m, biho = setup
        cm = ThreatAgent(m, "CRUISE_MISSILE",
                         (biho.pos[0], biho.pos[1] + 5), (100, 50))
        cm.altitude = 0.03
        mode = biho._get_biho_mode(cm)
        assert mode == "missile"

    def test_no_mode_at_8km(self, setup):
        """8km 거리 → 교전 불가 (양 모드 사거리 초과)"""
        m, biho = setup
        far = ThreatAgent(m, "CRUISE_MISSILE",
                          (biho.pos[0], biho.pos[1] + 8), (100, 50))
        far.altitude = 0.5
        mode = biho._get_biho_mode(far)
        assert mode is None

    def test_gun_engage_decrements_gun_ammo(self, setup):
        """gun 모드 교전 시 gun_ammo 감소"""
        m, biho = setup
        uas = ThreatAgent(m, "UAS", (biho.pos[0], biho.pos[1] + 2), (100, 50))
        uas.altitude = 0.3
        initial_gun = biho.gun_ammo
        initial_missile = biho.missile_ammo
        biho.engage(uas)
        assert biho.gun_ammo == initial_gun - 1
        assert biho.missile_ammo == initial_missile  # 미사일 변동 없음

    def test_missile_engage_decrements_missile_ammo(self, setup):
        """missile 모드 교전 시 missile_ammo 감소"""
        m, biho = setup
        cm = ThreatAgent(m, "CRUISE_MISSILE",
                         (biho.pos[0], biho.pos[1] + 5), (100, 50))
        cm.altitude = 0.03
        initial_gun = biho.gun_ammo
        initial_missile = biho.missile_ammo
        biho.engage(cm)
        assert biho.missile_ammo == initial_missile - 1
        assert biho.gun_ammo == initial_gun  # 기관포 변동 없음

    def test_missile_exhausted_falls_back_to_gun(self, setup):
        """미사일 소진 후 gun 사거리 내 타겟은 gun으로 교전"""
        m, biho = setup
        biho.missile_ammo = 0
        biho.ammo_count = biho.gun_ammo
        uas = ThreatAgent(m, "UAS", (biho.pos[0], biho.pos[1] + 2), (100, 50))
        uas.altitude = 0.3
        mode = biho._get_biho_mode(uas)
        assert mode == "gun"

    def test_non_biho_has_no_dual_mode(self, setup):
        """PAC-3 등 비-BIHO 사수는 이중 모드 없음"""
        m, _ = setup
        pac3 = [s for s in m.shooter_agents if s.weapon_type == "PATRIOT_PAC3"][0]
        assert pac3._has_dual_mode is False
