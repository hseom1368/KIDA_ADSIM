# KIDA_ADSIM 온톨로지 기반 리팩토링 분석 및 권장안

## Context

현재 KIDA_ADSIM v0.5는 Linear C2 vs Kill Web 비교에 최적화된 파라미터 연구 도구로, **파라미터 수준의 유연성은 우수**하지만 **구조적 유연성이 부족**하다. 구체적으로:

1. **아키텍처 확장 불가**: `model.py`에 9개의 `if architecture == "killweb"/"linear"` 분기가 산재 — 3번째 아키텍처(예: Hybrid C2) 추가 시 전면 재작성 필요
2. **엔티티 타입 추가 어려움**: 새 센서/사수/위협 타입 추가 시 config.py + agents.py + network.py + model.py 4개 파일 수정 필요
3. **시나리오 스키마 불일치**: wave 기반 시나리오와 Poisson 시나리오가 서로 다른 딕셔너리 구조 사용
4. **시각화 잠금**: matplotlib 2D 전용, Cesium.js 연동을 위한 지리 표준 포맷(CZML/GeoJSON) 미지원
5. **교전 정책 하드코딩**: 전략 교체 불가, 단일 정책만 지원

사용자는 (a) 시나리오/상황 자유 수정, (b) Cesium.js 3D 시각화 연동, (c) 의도한 대로 동작하지 않는 구현 개선을 목표로 한다.

---

## 분석 결론: 온톨로지 적용은 적절하나, "경량 도메인 온톨로지" 방식을 권장

### Full OWL 온톨로지 (owlready2/rdflib) — 권장하지 않음

| 장점 | 단점 |
|------|------|
| NATO 표준(C2SIM, JC3IEDM) 호환 | 학습 곡선이 가파름 |
| 자동 추론(reasoner) 가능 | 런타임 성능 오버헤드 |
| 시맨틱 검증 가능 | 1-2인 연구팀에 과도한 복잡도 |
| 장기 상호운용성 | Python M&S 생태계와 괴리 |

**판단**: 현재 프로젝트는 단일 조직 연구용 M&S이며, NATO 연합작전 상호운용성이 목표가 아님. Full OWL은 **과도(overkill)**.

### 경량 도메인 온톨로지 (Pydantic + Strategy + Registry) — 권장

온톨로지의 **핵심 개념**만 차용하여 Python-native로 구현:

| 온톨로지 개념 | Python 구현 | 효과 |
|--------------|-------------|------|
| **Class Hierarchy** (개념 계층) | Pydantic 모델 상속 체계 | 엔티티 타입 정형화 + 검증 |
| **Properties** (속성 관계) | 타입 힌트 + capability 컴포지션 | 능력 기반 매칭 가능 |
| **Relationships** (관계) | Registry + NetworkX 메타데이터 | 명시적 관계 모델링 |
| **Instances** (개체) | 데이터 기반 팩토리 패턴 | config만으로 새 타입 추가 |
| **Constraints** (제약) | Pydantic validator | 스키마 검증 자동화 |
| **Reasoning** (추론) | Strategy pattern dispatch | 아키텍처별 행동 분리 |

---

## 권장 리팩토링 설계

### Phase 1: 도메인 모델 계층 (modules/ontology.py 신규)

```python
# 핵심 개념: 엔티티 타입 계층 + 능력(Capability) 컴포지션

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from enum import Enum

# --- 능력(Capability) 정의 ---
class DetectionCapability(BaseModel):
    """탐지 능력 온톨로지"""
    detection_range: float          # km
    tracking_capacity: int
    scan_rate: float                # Hz
    rcs_reference: float = 1.0      # m²

class EngagementCapability(BaseModel):
    """교전 능력 온톨로지"""
    max_range: float                # km
    min_range: float
    max_altitude: float             # km
    pk_table: Dict[str, float]      # threat_type → Pk
    ammo_capacity: int
    reload_time: float              # seconds
    engagement_time: float          # seconds

class C2Capability(BaseModel):
    """C2 처리 능력"""
    processing_capacity: int
    auth_delay: Dict[str, tuple]    # architecture → (min, max)

class FlightProfile(BaseModel):
    """위협 비행 프로파일"""
    profile_type: str
    phases: List[dict]              # phase 목록

class ThreatCapability(BaseModel):
    """위협 특성"""
    speed: float                    # km/s
    altitude: float                 # km
    rcs: float                      # m²
    maneuvering: bool
    flight_profile: Optional[FlightProfile] = None

# --- 엔티티 타입 정의 (온톨로지 클래스) ---
class EntityType(BaseModel):
    """모든 엔티티의 기본 타입 (온톨로지 최상위 클래스)"""
    type_id: str
    label: str
    category: Literal["sensor", "c2", "shooter", "threat"]

class SensorType(EntityType):
    category: Literal["sensor"] = "sensor"
    capability: DetectionCapability

class ShooterType(EntityType):
    category: Literal["shooter"] = "shooter"
    capability: EngagementCapability

class C2Type(EntityType):
    category: Literal["c2"] = "c2"
    capability: C2Capability

class ThreatType(EntityType):
    category: Literal["threat"] = "threat"
    capability: ThreatCapability
```

### Phase 2: 엔티티 레지스트리 (modules/registry.py 신규)

```python
class EntityRegistry:
    """엔티티 타입 레지스트리 — config.py 딕셔너리를 온톨로지 모델로 변환"""

    def __init__(self):
        self._sensor_types: Dict[str, SensorType] = {}
        self._shooter_types: Dict[str, ShooterType] = {}
        self._c2_types: Dict[str, C2Type] = {}
        self._threat_types: Dict[str, ThreatType] = {}

    def load_from_config(self, config_module):
        """기존 config.py 딕셔너리에서 자동 로드 — 역호환성 보장"""
        for key, params in config_module.SENSOR_PARAMS.items():
            self._sensor_types[key] = SensorType.from_config(key, params)
        # ... 동일 패턴으로 shooter, c2, threat

    def get_compatible_shooters(self, threat_type_id: str) -> List[ShooterType]:
        """온톨로지 추론: 특정 위협에 교전 가능한 사수 타입 조회"""
        results = []
        for st in self._shooter_types.values():
            if threat_type_id in st.capability.pk_table and st.capability.pk_table[threat_type_id] > 0:
                results.append(st)
        return results
```

### Phase 3: 아키텍처 전략 패턴 (modules/strategies.py 신규)

`model.py`의 9개 if/else 분기를 전략 객체로 분리:

```python
from abc import ABC, abstractmethod

class ArchitectureStrategy(ABC):
    """아키텍처별 행동 전략 (온톨로지의 Reasoning 역할)"""

    @abstractmethod
    def build_topology(self, sensors, c2_nodes, shooters) -> nx.DiGraph: ...

    @abstractmethod
    def process_killchain(self, env, sensor, threat, comm, topology) -> Generator: ...

    @abstractmethod
    def select_shooter(self, threat, available_shooters, cop_data) -> Optional[Shooter]: ...

    @abstractmethod
    def fuse_tracks(self, tracks, c2_node) -> dict: ...

    @abstractmethod
    def update_cop(self, c2_nodes, shooters, threats) -> None: ...

    @abstractmethod
    def get_max_simultaneous(self, threat, shooter) -> int: ...

class LinearC2Strategy(ArchitectureStrategy):
    """선형 C2 전략 구현"""
    # model.py의 linear 분기 로직을 여기로 이동

class KillWebStrategy(ArchitectureStrategy):
    """Kill Web 전략 구현"""
    # model.py의 killweb 분기 로직을 여기로 이동
```

**효과**: 새 아키텍처 추가 시 `HybridStrategy` 클래스만 작성하면 됨. model.py 수정 불필요.

### Phase 4: 시나리오 스키마 통일 (config.py 리팩토링)

```python
class ScenarioSchema(BaseModel):
    """시나리오 온톨로지 — 모든 시나리오 유형의 통합 스키마"""
    name: str
    description: str
    arrival_pattern: Literal["wave", "poisson", "scheduled"]

    # wave 패턴
    waves: Optional[List[WaveSpec]] = None

    # poisson 패턴
    poisson_lambda: Optional[float] = None
    duration: Optional[float] = None
    threat_mix: Optional[Dict[str, float]] = None

    # 공통
    approach_azimuth: tuple = (240, 360)
    approach_distance: float = 200
    jamming_level: float = 0.0
    detection_factor: float = 1.0
    latency_factor: float = 1.0
    node_destructions: Optional[Dict[str, List]] = None  # architecture → events

    @model_validator(mode='after')
    def validate_pattern(self):
        if self.arrival_pattern == "wave" and not self.waves:
            raise ValueError("wave 패턴은 waves 필드 필수")
        # ...
```

### Phase 5: CZML 내보내기 모듈 (modules/exporters.py 신규)

```python
class CZMLExporter:
    """시뮬레이션 결과 → CZML 변환 (Cesium.js 연동)"""

    def __init__(self, origin_lat, origin_lon, km_to_deg_factor):
        self.origin = (origin_lat, origin_lon)

    def export_simulation(self, result: dict) -> list:
        """시뮬레이션 결과를 CZML 패킷 리스트로 변환"""
        packets = [{"id": "document", "version": "1.0", "clock": {...}}]

        # 위협 궤적 → CZML path entity
        for snapshot in result["snapshots"]:
            for threat in snapshot["threats"]:
                packets.append(self._threat_to_czml(threat, snapshot["time"]))

        # 방어 자산 → CZML billboard/point
        # 교전 이벤트 → CZML polyline (사수→위협)
        # 센서 범위 → CZML ellipse
        return packets

    def _km_to_wgs84(self, x_km, y_km, alt_km):
        """로컬 km 좌표 → WGS84 (lat, lon, alt_m) 변환"""
        ...
```

---

## 구현 전략 (v0.6 이전에 우선 수행)

**의사결정**: 사용자 확인 완료
- 온톨로지 리팩토링을 v0.6 Monte Carlo **이전에** 수행
- Pydantic 의존성 사용 승인

### 구현 순서

| 단계 | 작업 | 파일 변경 | 위험도 | 의존성 |
|------|------|----------|--------|--------|
| **1** | Pydantic 설치 + `ontology.py` 도메인 모델 정의 | 신규 파일 | 낮음 | 없음 |
| **2** | `registry.py` 레지스트리 + config 어댑터 | 신규 + config.py 소폭 수정 | 낮음 | 단계 1 |
| **3** | `strategies.py` 아키텍처 전략 분리 | 신규 + **model.py 대폭 리팩토링** | **높음** | 단계 1,2 |
| **4** | 시나리오 스키마 통일 | config.py + threats.py 리팩토링 | 중간 | 단계 1 |
| **5** | `exporters.py` CZML 내보내기 | 신규 파일 | 낮음 | 단계 1 |
| **6** | 테스트 추가 + 회귀 확인 | tests/ 신규/수정 | 낮음 | 전체 |
| **7** | v0.6 Monte Carlo 작업 진행 | 기존 plan.md 참고 | - | 단계 1-6 |

**핵심 원칙**: 각 단계별 86개 기존 테스트가 통과해야 함 (회귀 방지)

### 역호환성 보장

- `config.py`의 기존 딕셔너리 구조 유지 → `registry.load_from_config()`가 자동 변환
- 기존 `AirDefenseModel(architecture="linear")` API 동일하게 유지
- 전략 패턴은 내부적으로 디스패치, 외부 인터페이스 불변

---

## Cesium.js 연동 아키텍처

```
[Python Backend]                    [Frontend]

AirDefenseModel                     Cesium.js Viewer
    ↓ run_full()                        ↑
result dict (snapshots + events)    CZML packets
    ↓                                   ↑
CZMLExporter.export_simulation()  → JSON file/API
    ↓                                   ↑
km좌표 → WGS84 변환                CzmlDataSource.load()
```

**CZML 패킷 구조 (예시)**:
```json
[
  {"id": "document", "version": "1.0"},
  {
    "id": "threat_SRBM_001",
    "position": {
      "epoch": "2024-01-01T00:00:00Z",
      "cartographicDegrees": [0, 37.5, 127.0, 50000, 30, 37.4, 126.9, 45000, ...]
    },
    "point": {"pixelSize": 8, "color": {"rgba": [255, 0, 0, 255]}},
    "path": {"show": true, "width": 2}
  },
  {
    "id": "shooter_PATRIOT_001",
    "position": {"cartographicDegrees": [37.3, 127.1, 0]},
    "billboard": {"image": "patriot_icon.png"}
  }
]
```

---

## 리스크 평가

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| model.py 전략 분리 시 회귀 버그 | 높음 | 86개 테스트 + seed=42 기준값 비교 |
| Pydantic 의존성 추가 | 낮음 | dataclasses 대안 가능 (타입 검증만 포기) |
| 성능 오버헤드 (Pydantic 검증) | 낮음 | 초기화 시에만 검증, 런타임 경로 미영향 |
| 팀 학습 곡선 | 중간 | 단계별 점진 도입 + 기존 API 유지 |
| v0.6 일정 지연 | 낮음 | 온톨로지 리팩토링 우선 수행 (사용자 결정) |

---

## 수정 대상 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `modules/ontology.py` (신규) | 도메인 모델 계층 (Pydantic BaseModel) |
| `modules/registry.py` (신규) | 엔티티 타입 레지스트리 + config 어댑터 |
| `modules/strategies.py` (신규) | ArchitectureStrategy ABC + Linear/KillWeb 구현 |
| `modules/exporters.py` (신규) | CZMLExporter (Cesium.js 연동) |
| `modules/model.py` (리팩토링) | 9개 아키텍처 분기 → strategy.method() 위임 |
| `modules/config.py` (소폭 수정) | ScenarioSchema 통일, 기존 딕셔너리 유지 |
| `modules/threats.py` (소폭 수정) | ScenarioSchema 기반 위협 생성 |
| `tests/test_ontology.py` (신규) | 도메인 모델 + 레지스트리 + 전략 테스트 |

---

## 검증 방법

1. **회귀 테스트**: `python -m pytest tests/ -v` — 86개 기존 테스트 전체 통과
2. **기준값 비교**: seed=42 시나리오 1에서 리팩토링 전후 지표 동일 확인
   ```bash
   python -c "
   from modules.model import AirDefenseModel
   for arch in ['linear', 'killweb']:
       m = AirDefenseModel(architecture=arch, scenario='scenario_1_saturation', seed=42)
       r = m.run_full()
       print(f'{arch}: leaker={r[\"metrics\"][\"leaker_rate\"]:.1f}%')
   "
   ```
3. **CZML 검증**: 내보낸 CZML을 Cesium Sandcastle에서 로드하여 3D 궤적 확인
4. **새 아키텍처 테스트**: `HybridStrategy` 클래스 추가 후 시뮬레이션 실행 가능 여부 확인
