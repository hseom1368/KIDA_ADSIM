"""
registry.py - 엔티티 레지스트리
Entity registry: loads config.py parameters into Pydantic ontology types.
Provides typed lookups, Pk-based prioritization, and topology relation queries.

Lifecycle: Created once in AirDefenseModel.__init__(), immutable thereafter.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .config import (
    SENSOR_PARAMS, C2_PARAMS, SHOOTER_PARAMS, THREAT_PARAMS,
    TOPOLOGY_RELATIONS,
)
from .ontology import (
    SensorType, C2Type, ShooterType, ThreatType,
    DetectionCapability, C2Capability, EngagementCapability, ThreatCapability,
    FlightProfile, FlightPhase,
)


class EntityRegistry:
    """방공체계 엔티티 타입 레지스트리.

    config.py 딕셔너리를 Pydantic 온톨로지 모델로 변환하여 관리.
    토폴로지 관계, Pk 기반 사수 우선순위, 역조회를 제공.
    """

    def __init__(self):
        self._sensors: Dict[str, SensorType] = {}
        self._c2_types: Dict[str, C2Type] = {}
        self._shooters: Dict[str, ShooterType] = {}
        self._threats: Dict[str, ThreatType] = {}
        self._loaded = False

    def load_from_config(self):
        """config.py 파라미터를 온톨로지 타입으로 변환하여 로드"""
        self._load_sensors()
        self._load_c2_types()
        self._load_shooters()
        self._load_threats()
        self._loaded = True

    # ── 로드 헬퍼 ──

    def _load_sensors(self):
        sensor_to_c2 = TOPOLOGY_RELATIONS.get("sensor_to_c2", {})
        for type_id, params in SENSOR_PARAMS.items():
            self._sensors[type_id] = SensorType(
                type_id=type_id,
                label=params["label"],
                capability=DetectionCapability(
                    detection_range=params["detection_range"],
                    tracking_capacity=params["tracking_capacity"],
                    scan_rate=params["scan_rate"],
                    # v0.7 신규 필드 (.get 기본값 → 하위 호환)
                    role=params.get("role", "weapon_fc"),
                    detectable_types=params.get("detectable_types"),
                    min_detection_altitude=params.get("min_detection_altitude", 0),
                    provides_cueing_to=params.get("provides_cueing_to"),
                ),
                reporting_c2_type=sensor_to_c2.get(type_id),
            )

    def _load_c2_types(self):
        c2_hierarchy = TOPOLOGY_RELATIONS.get("c2_hierarchy", {})
        for type_id, params in C2_PARAMS.items():
            self._c2_types[type_id] = C2Type(
                type_id=type_id,
                label=params["label"],
                capability=C2Capability(
                    processing_capacity=params["processing_capacity"],
                    auth_delay_linear=params["auth_delay_linear"],
                    auth_delay_killweb=params["auth_delay_killweb"],
                ),
                parent_c2_type=c2_hierarchy.get(type_id),
            )

    def _load_shooters(self):
        shooter_to_c2 = TOPOLOGY_RELATIONS.get("shooter_to_c2", {})
        for type_id, params in SHOOTER_PARAMS.items():
            self._shooters[type_id] = ShooterType(
                type_id=type_id,
                label=params["label"],
                capability=EngagementCapability(
                    max_range=params["max_range"],
                    min_range=params["min_range"],
                    max_altitude=params["max_altitude"],
                    min_altitude=params.get("min_altitude", 0),
                    pk_table=dict(params["pk_table"]),
                    ammo_count=params["ammo_count"],
                    reload_time=params["reload_time"],
                    engagement_time=params["engagement_time"],
                    intercept_method=params.get("intercept_method"),
                ),
                controlling_c2_type=shooter_to_c2.get(type_id),
            )

    def _load_threats(self):
        for type_id, params in THREAT_PARAMS.items():
            flight_profile = None
            if "flight_profile" in params:
                fp = params["flight_profile"]
                flight_profile = FlightProfile(
                    profile_type=fp["type"],
                    phases=[FlightPhase(**p) for p in fp["phases"]],
                )
            self._threats[type_id] = ThreatType(
                type_id=type_id,
                label=params["label"],
                capability=ThreatCapability(
                    speed=params["speed"],
                    altitude=params["altitude"],
                    rcs=params["rcs"],
                    maneuvering=params["maneuvering"],
                ),
                flight_profile=flight_profile,
            )

    # ── 타입 조회 ──

    def get_sensor_type(self, type_id: str) -> SensorType:
        return self._sensors[type_id]

    def get_c2_type(self, type_id: str) -> C2Type:
        return self._c2_types[type_id]

    def get_shooter_type(self, type_id: str) -> ShooterType:
        return self._shooters[type_id]

    def get_threat_type(self, type_id: str) -> ThreatType:
        return self._threats[type_id]

    # ── 전체 목록 ──

    def all_sensor_types(self) -> List[SensorType]:
        return list(self._sensors.values())

    def all_c2_types(self) -> List[C2Type]:
        return list(self._c2_types.values())

    def all_shooter_types(self) -> List[ShooterType]:
        return list(self._shooters.values())

    def all_threat_types(self) -> List[ThreatType]:
        return list(self._threats.values())

    # ── Pk 기반 쿼리 (Gemini #6) ──

    def get_compatible_shooters(self, threat_type_id: str) -> List[ShooterType]:
        """해당 위협 유형에 Pk > 0인 사수 타입 반환"""
        return [
            st for st in self._shooters.values()
            if st.capability.pk_table.get(threat_type_id, 0) > 0
        ]

    def get_prioritized_shooters(self, threat_type_id: str) -> List[ShooterType]:
        """해당 위협 유형에 대해 Pk 내림차순 정렬된 사수 타입 반환"""
        compatible = self.get_compatible_shooters(threat_type_id)
        return sorted(
            compatible,
            key=lambda st: st.capability.pk_table.get(threat_type_id, 0),
            reverse=True,
        )

    # ── 토폴로지 관계 역조회 (Gemini #5) ──

    def get_sensors_for_c2(self, c2_type_id: str) -> List[SensorType]:
        """해당 C2 타입에 보고하는 센서 타입 역조회"""
        return [
            st for st in self._sensors.values()
            if st.reporting_c2_type == c2_type_id
        ]

    def get_shooters_for_c2(self, c2_type_id: str) -> List[ShooterType]:
        """해당 C2 타입이 통제하는 사수 타입 역조회"""
        return [
            st for st in self._shooters.values()
            if st.controlling_c2_type == c2_type_id
        ]

    def get_child_c2_types(self, c2_type_id: str) -> List[C2Type]:
        """해당 C2 타입을 상위로 갖는 하위 C2 타입 역조회"""
        return [
            ct for ct in self._c2_types.values()
            if ct.parent_c2_type == c2_type_id
        ]

    # ── v0.7 신규 쿼리 ──

    def get_sensors_by_role(self, role: str) -> List[SensorType]:
        """특정 역할의 센서 타입 반환"""
        return [
            st for st in self._sensors.values()
            if st.capability.role == role
        ]

    def get_shooters_by_altitude_range(
        self, min_alt: float, max_alt: float
    ) -> List[ShooterType]:
        """교전 고도 범위가 겹치는 사수 타입 반환"""
        return [
            st for st in self._shooters.values()
            if st.capability.min_altitude <= max_alt
            and st.capability.max_altitude >= min_alt
        ]
