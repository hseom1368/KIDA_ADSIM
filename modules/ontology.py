"""
ontology.py - 방공체계 도메인 온톨로지 (Pydantic 기반)
Domain ontology for air defense system entity types and capabilities.

4-카테고리 타입 체계: SensorType, C2Type, ShooterType, ThreatType
각 타입은 능력(Capability) + 토폴로지 관계 필드로 구성.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# =============================================================================
# 능력(Capability) 모델
# =============================================================================

class DetectionCapability(BaseModel):
    """센서 탐지 능력"""
    detection_range: float = Field(gt=0, description="탐지 거리 (km)")
    tracking_capacity: int = Field(gt=0, description="동시 추적 용량")
    scan_rate: float = Field(gt=0, description="스캔 빈도 (초당)")
    # v0.7 신규 필드 (기본값 → 하위 호환)
    role: str = Field(default="weapon_fc", description="센서 역할 (early_warning/surveillance/local_surveillance/weapon_fc)")
    detectable_types: Optional[List[str]] = Field(default=None, description="탐지 가능 위협 유형 (None=모든 유형)")
    min_detection_altitude: float = Field(default=0, ge=0, description="최소 탐지 고도 (km)")
    provides_cueing_to: Optional[List[str]] = Field(default=None, description="큐잉 제공 대상 C2 노드 타입")


class C2Capability(BaseModel):
    """C2 노드 처리 능력"""
    processing_capacity: int = Field(gt=0, description="동시 처리 용량")
    auth_delay_linear: Optional[tuple] = Field(
        default=None, description="선형 C2 승인 지연 (min, max) 초"
    )
    auth_delay_killweb: Optional[tuple] = Field(
        default=None, description="Kill Web 승인 지연 (min, max) 초"
    )


class EngagementCapability(BaseModel):
    """사격체 교전 능력"""
    max_range: float = Field(gt=0, description="최대 사거리 (km)")
    min_range: float = Field(ge=0, description="최소 사거리 (km)")
    max_altitude: float = Field(gt=0, description="최대 교전 고도 (km)")
    min_altitude: float = Field(default=0, ge=0, description="최소 교전 고도 (km)")
    pk_table: dict = Field(description="위협 유형별 Pk {threat_type: pk}")
    ammo_count: int = Field(gt=0, description="탄약 수")
    reload_time: float = Field(ge=0, description="재장전 시간 (초)")
    engagement_time: float = Field(gt=0, description="교전 소요 시간 (초)")
    # v0.7 신규 필드
    intercept_method: Optional[str] = Field(default=None, description="요격 방식 (hit_to_kill/proximity_fuse/command_guidance)")


class ThreatCapability(BaseModel):
    """위협체 비행 능력"""
    speed: float = Field(gt=0, description="비행 속도 (km/s)")
    altitude: float = Field(ge=0, description="비행 고도 (km)")
    rcs: float = Field(gt=0, description="레이더 반사 면적 (m²)")
    maneuvering: bool = Field(default=False, description="기동 여부")
    # v0.7.1 신규 필드
    radar_signature: Optional[str] = Field(default=None, description="레이더 시그니처 (ballistic 등)")
    cost_ratio: float = Field(default=1.0, ge=0, description="비용 비율 (SRBM 대비)")


# =============================================================================
# 비행 프로파일 모델
# =============================================================================

class FlightPhase(BaseModel):
    """비행 프로파일 단계"""
    name: str
    duration_ratio: float = Field(ge=0, le=1)
    altitude_start: float = Field(ge=0)
    altitude_end: float = Field(ge=0)
    speed_start: float = Field(ge=0)
    speed_end: float = Field(ge=0)
    maneuvering: bool = False


class FlightProfile(BaseModel):
    """위협체 비행 프로파일"""
    profile_type: str
    phases: List[FlightPhase]


# =============================================================================
# 엔티티 타입 기본 클래스
# =============================================================================

EntityCategory = Literal["sensor", "c2", "shooter", "threat"]


class EntityType(BaseModel):
    """엔티티 타입 기본 클래스"""
    type_id: str = Field(description="고유 타입 식별자 (e.g., 'EWR', 'PATRIOT_PAC3')")
    category: EntityCategory
    label: str = Field(description="표시명")


# =============================================================================
# 구체 엔티티 타입
# =============================================================================

class SensorType(EntityType):
    """센서 타입 정의"""
    category: Literal["sensor"] = "sensor"
    capability: DetectionCapability
    reporting_c2_type: Optional[str] = Field(
        default=None, description="선형 C2에서 보고할 상위 C2 노드 타입"
    )


class C2Type(EntityType):
    """C2 노드 타입 정의"""
    category: Literal["c2"] = "c2"
    capability: C2Capability
    parent_c2_type: Optional[str] = Field(
        default=None, description="상위 C2 노드 타입 (선형 계층 구조)"
    )


class ShooterType(EntityType):
    """사격체 타입 정의"""
    category: Literal["shooter"] = "shooter"
    capability: EngagementCapability
    controlling_c2_type: Optional[str] = Field(
        default=None, description="선형 C2에서 통제받는 C2 노드 타입"
    )


class ThreatType(EntityType):
    """위협체 타입 정의"""
    category: Literal["threat"] = "threat"
    capability: ThreatCapability
    flight_profile: Optional[FlightProfile] = None


# =============================================================================
# 시나리오 스키마
# =============================================================================

class WaveSpec(BaseModel):
    """파상 공격 사양"""
    time: float = Field(ge=0, description="파상 발사 시각 (초)")
    threats: dict = Field(description="위협 유형별 수량 {type: count}")


class ScenarioSchema(BaseModel):
    """시나리오 정형 스키마"""
    name: str
    description: str
    approach_azimuth: tuple = (240, 360)
    approach_distance: float = 200
    jamming_level: float = Field(default=0.0, ge=0, le=1)
    detection_factor: float = Field(default=1.0, ge=0, le=1)
    latency_factor: float = Field(default=1.0, ge=1)
    node_destruction: list = Field(default_factory=list)

    # 파상 공격 시나리오
    waves: Optional[List[WaveSpec]] = None

    # 포아송 시나리오
    poisson_lambda: Optional[float] = None
    duration: Optional[float] = None
    threat_mix: Optional[dict] = None
