"""엔티티 레지스트리 테스트"""

import pytest
from modules.registry import EntityRegistry
from modules.ontology import SensorType, ShooterType, C2Type, ThreatType


@pytest.fixture
def registry():
    reg = EntityRegistry()
    reg.load_from_config()
    return reg


class TestRegistryLoad:
    def test_load_sensors(self, registry):
        st = registry.get_sensor_type("EWR")
        assert isinstance(st, SensorType)
        assert st.capability.detection_range == 500
        assert st.label == "EWR (그린파인급)"

    def test_load_all_sensors(self, registry):
        all_sensors = registry.all_sensor_types()
        assert len(all_sensors) == 4  # EWR, PATRIOT_RADAR, MSAM_MFR, SHORAD_RADAR

    def test_load_c2_types(self, registry):
        ct = registry.get_c2_type("MCRC")
        assert isinstance(ct, C2Type)
        assert ct.capability.processing_capacity == 5

    def test_load_shooters(self, registry):
        st = registry.get_shooter_type("PATRIOT_PAC3")
        assert isinstance(st, ShooterType)
        assert st.capability.max_range == 120
        assert st.capability.pk_table["SRBM"] == 0.85

    def test_load_threats(self, registry):
        tt = registry.get_threat_type("SRBM")
        assert isinstance(tt, ThreatType)
        assert tt.capability.speed == 2.0
        assert tt.flight_profile is not None

    def test_load_all_threat_types(self, registry):
        all_threats = registry.all_threat_types()
        assert len(all_threats) == 4

    def test_missing_type_raises(self, registry):
        with pytest.raises(KeyError):
            registry.get_sensor_type("NONEXISTENT")


class TestTopologyRelations:
    def test_sensor_reporting_c2(self, registry):
        ewr = registry.get_sensor_type("EWR")
        assert ewr.reporting_c2_type == "MCRC"

    def test_shooter_controlling_c2(self, registry):
        pac3 = registry.get_shooter_type("PATRIOT_PAC3")
        assert pac3.controlling_c2_type == "TOC_PAT"

    def test_c2_hierarchy(self, registry):
        toc = registry.get_c2_type("BATTALION_TOC")
        assert toc.parent_c2_type == "MCRC"

    def test_sensors_for_c2(self, registry):
        sensors = registry.get_sensors_for_c2("MCRC")
        assert any(s.type_id == "EWR" for s in sensors)

    def test_shooters_for_c2(self, registry):
        shooters = registry.get_shooters_for_c2("TOC_PAT")
        assert any(s.type_id == "PATRIOT_PAC3" for s in shooters)

    def test_child_c2_types(self, registry):
        children = registry.get_child_c2_types("MCRC")
        assert any(c.type_id == "BATTALION_TOC" for c in children)


class TestPkQueries:
    def test_compatible_shooters_srbm(self, registry):
        compatible = registry.get_compatible_shooters("SRBM")
        types = [s.type_id for s in compatible]
        assert "PATRIOT_PAC3" in types
        assert "CHEONGUNG2" in types
        # BIHO has Pk=0 for SRBM
        assert "BIHO" not in types

    def test_prioritized_shooters_srbm(self, registry):
        prioritized = registry.get_prioritized_shooters("SRBM")
        # PATRIOT_PAC3 (0.85) > CHEONGUNG2 (0.75)
        assert prioritized[0].type_id == "PATRIOT_PAC3"
        assert prioritized[1].type_id == "CHEONGUNG2"

    def test_prioritized_shooters_uas(self, registry):
        prioritized = registry.get_prioritized_shooters("UAS")
        types = [s.type_id for s in prioritized]
        assert "PATRIOT_PAC3" in types  # Pk=0.70
        assert "BIHO" in types          # Pk=0.60

    def test_compatible_empty_for_unknown(self, registry):
        assert registry.get_compatible_shooters("UNKNOWN") == []
