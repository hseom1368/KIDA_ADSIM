"""v0.7 레지스트리 신규 쿼리 및 필드 테스트"""

import pytest
from modules.registry import EntityRegistry


@pytest.fixture
def registry():
    reg = EntityRegistry()
    reg.load_from_config()
    return reg


class TestV07OntologyFields:
    """v0.7 신규 온톨로지 필드 검증"""

    def test_shooter_min_altitude_field(self, registry):
        thaad = registry.get_shooter_type("THAAD")
        assert thaad.capability.min_altitude == 40

    def test_shooter_min_altitude_default(self, registry):
        biho = registry.get_shooter_type("BIHO")
        assert biho.capability.min_altitude == 0

    def test_shooter_intercept_method(self, registry):
        thaad = registry.get_shooter_type("THAAD")
        assert thaad.capability.intercept_method == "hit_to_kill"

    def test_sensor_role_field(self, registry):
        gp = registry.get_sensor_type("GREEN_PINE")
        assert gp.capability.role == "early_warning"

    def test_sensor_detectable_types(self, registry):
        gp = registry.get_sensor_type("GREEN_PINE")
        assert gp.capability.detectable_types == ["SRBM"]

    def test_sensor_min_detection_altitude(self, registry):
        fps = registry.get_sensor_type("FPS117")
        assert fps.capability.min_detection_altitude == 1.0

    def test_sensor_provides_cueing_to(self, registry):
        gp = registry.get_sensor_type("GREEN_PINE")
        assert gp.capability.provides_cueing_to == ["KAMD_OPS"]

    def test_existing_sensor_defaults(self, registry):
        ewr = registry.get_sensor_type("EWR")
        assert ewr.capability.role == "weapon_fc"
        assert ewr.capability.detectable_types is None
        assert ewr.capability.min_detection_altitude == 0


class TestV07NewQueries:
    """v0.7 신규 쿼리 함수 검증"""

    def test_sensors_by_role_early_warning(self, registry):
        ew_sensors = registry.get_sensors_by_role("early_warning")
        assert len(ew_sensors) == 1
        assert ew_sensors[0].type_id == "GREEN_PINE"

    def test_sensors_by_role_surveillance(self, registry):
        surv = registry.get_sensors_by_role("surveillance")
        assert len(surv) == 1
        assert surv[0].type_id == "FPS117"

    def test_sensors_by_role_weapon_fc(self, registry):
        wfc = registry.get_sensors_by_role("weapon_fc")
        # 기존 4개 센서
        assert len(wfc) == 4

    def test_shooters_by_altitude_range_high(self, registry):
        """고고도 (40-150km) 사수 조회"""
        high = registry.get_shooters_by_altitude_range(40, 150)
        type_ids = [s.type_id for s in high]
        assert "THAAD" in type_ids
        assert "LSAM_ABM" in type_ids
        # PAC-3 MSE도 max_altitude=40이므로 포함
        assert "PATRIOT_PAC3" in type_ids

    def test_shooters_by_altitude_range_low(self, registry):
        """저고도 (0-5km) 사수 조회"""
        low = registry.get_shooters_by_altitude_range(0, 5)
        type_ids = [s.type_id for s in low]
        assert "CHUNMA" in type_ids
        assert "BIHO" in type_ids
        # THAAD는 min_altitude=40이므로 제외
        assert "THAAD" not in type_ids
        # LSAM_ABM도 min_altitude=40이므로 제외
        assert "LSAM_ABM" not in type_ids


class TestV07NewC2Types:
    """v0.7 신규 C2 타입 검증"""

    def test_kamd_ops_loaded(self, registry):
        kamd = registry.get_c2_type("KAMD_OPS")
        assert kamd.capability.processing_capacity == 8

    def test_army_local_ad_loaded(self, registry):
        army = registry.get_c2_type("ARMY_LOCAL_AD")
        assert army.capability.processing_capacity == 3

    def test_iaoc_loaded(self, registry):
        iaoc = registry.get_c2_type("IAOC")
        assert iaoc.capability.processing_capacity == 10
        assert iaoc.capability.auth_delay_linear is None

    def test_all_c2_count(self, registry):
        all_c2 = registry.all_c2_types()
        assert len(all_c2) == 6  # 기존 3 + 신규 3

    def test_all_shooter_count(self, registry):
        all_shooters = registry.all_shooter_types()
        assert len(all_shooters) == 9  # 기존 4 + 신규 5
