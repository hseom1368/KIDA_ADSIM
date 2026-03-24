"""온톨로지 도메인 모델 테스트"""

import pytest
from pydantic import ValidationError

from modules.ontology import (
    DetectionCapability, C2Capability, EngagementCapability, ThreatCapability,
    SensorType, C2Type, ShooterType, ThreatType, EntityType,
    FlightPhase, FlightProfile, ScenarioSchema, WaveSpec,
)


class TestCapabilities:
    def test_detection_capability_valid(self):
        cap = DetectionCapability(detection_range=500, tracking_capacity=100, scan_rate=1.0)
        assert cap.detection_range == 500
        assert cap.tracking_capacity == 100

    def test_detection_capability_invalid_range(self):
        with pytest.raises(ValidationError):
            DetectionCapability(detection_range=-1, tracking_capacity=100, scan_rate=1.0)

    def test_engagement_capability(self):
        cap = EngagementCapability(
            max_range=120, min_range=3, max_altitude=30,
            pk_table={"SRBM": 0.85}, ammo_count=16,
            reload_time=1800, engagement_time=5,
        )
        assert cap.pk_table["SRBM"] == 0.85

    def test_c2_capability(self):
        cap = C2Capability(
            processing_capacity=5,
            auth_delay_linear=(15, 120),
            auth_delay_killweb=(2, 5),
        )
        assert cap.processing_capacity == 5

    def test_threat_capability(self):
        cap = ThreatCapability(speed=2.0, altitude=50.0, rcs=0.5, maneuvering=True)
        assert cap.maneuvering is True


class TestEntityTypes:
    def test_sensor_type(self):
        st = SensorType(
            type_id="EWR", label="EWR (그린파인급)",
            capability=DetectionCapability(
                detection_range=500, tracking_capacity=100, scan_rate=1.0,
            ),
            reporting_c2_type="MCRC",
        )
        assert st.category == "sensor"
        assert st.reporting_c2_type == "MCRC"

    def test_c2_type(self):
        ct = C2Type(
            type_id="BATTALION_TOC", label="대대 TOC",
            capability=C2Capability(
                processing_capacity=3,
                auth_delay_linear=(3, 10),
                auth_delay_killweb=(1, 3),
            ),
            parent_c2_type="MCRC",
        )
        assert ct.category == "c2"
        assert ct.parent_c2_type == "MCRC"

    def test_shooter_type(self):
        st = ShooterType(
            type_id="PATRIOT_PAC3", label="PATRIOT PAC-3 MSE",
            capability=EngagementCapability(
                max_range=120, min_range=3, max_altitude=30,
                pk_table={"SRBM": 0.85}, ammo_count=16,
                reload_time=1800, engagement_time=5,
            ),
            controlling_c2_type="TOC_PAT",
        )
        assert st.category == "shooter"
        assert st.controlling_c2_type == "TOC_PAT"

    def test_threat_type(self):
        tt = ThreatType(
            type_id="SRBM", label="SRBM (KN-23형)",
            capability=ThreatCapability(
                speed=2.0, altitude=50.0, rcs=0.5, maneuvering=True,
            ),
        )
        assert tt.category == "threat"
        assert tt.flight_profile is None

    def test_sensor_type_no_reporting(self):
        """reporting_c2_type 없는 센서"""
        st = SensorType(
            type_id="TEST", label="Test",
            capability=DetectionCapability(
                detection_range=100, tracking_capacity=10, scan_rate=1.0,
            ),
        )
        assert st.reporting_c2_type is None

    def test_entity_type_missing_field(self):
        """필수 필드 누락 시 에러"""
        with pytest.raises(ValidationError):
            SensorType(type_id="X", label="X")  # capability 누락


class TestFlightProfile:
    def test_flight_phase(self):
        phase = FlightPhase(
            name="boost", duration_ratio=0.15,
            altitude_start=0, altitude_end=50,
            speed_start=0.5, speed_end=2.5,
            maneuvering=False,
        )
        assert phase.name == "boost"

    def test_flight_profile(self):
        fp = FlightProfile(
            profile_type="ballistic",
            phases=[
                FlightPhase(name="boost", duration_ratio=0.15,
                           altitude_start=0, altitude_end=50,
                           speed_start=0.5, speed_end=2.5),
                FlightPhase(name="midcourse", duration_ratio=0.85,
                           altitude_start=50, altitude_end=0,
                           speed_start=2.5, speed_end=3.0),
            ],
        )
        assert len(fp.phases) == 2


class TestScenarioSchema:
    def test_wave_spec(self):
        wave = WaveSpec(time=0, threats={"SRBM": 10, "CRUISE_MISSILE": 5})
        assert wave.threats["SRBM"] == 10

    def test_scenario_schema(self):
        schema = ScenarioSchema(
            name="테스트", description="테스트 시나리오",
            waves=[WaveSpec(time=0, threats={"SRBM": 5})],
        )
        assert schema.jamming_level == 0.0
        assert len(schema.waves) == 1
