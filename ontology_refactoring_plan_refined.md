# 온톨로지 리팩토링 계획 보완 — Gemini 3.1 검토의견 반영

## Context

`ontology_refactoring_plan.md`의 Pydantic + Strategy + Registry 기반 경량 도메인 온톨로지 설계를 Gemini 3.1 Pro가 9개 항목으로 검토했다. 실제 코드(`model.py` 11개 분기, `network.py` 15개 하드코딩 타입명, `comms.py` 아키텍처 분기, `agents.py` 딕셔너리 직접 참조)를 대조 분석하여, 수용/기각 판정 후 기존 계획을 보완한다.

---

## 1. Gemini 검토의견 분석 결과

| # | Gemini 제안 | 판정 | 근거 |
|---|------------|------|------|
| 1 | Agent에 온톨로지 타입 DI 주입 | **수용** | `agents.py:27` `SENSOR_PARAMS[sensor_type]` 직접 참조 — 연결고리 필요 |
| 2 | 다중 능력 Entity-Component 패턴 | **기각 (YAGNI)** | 현재 4종 엔티티에 하이브리드 없음. 한국군 방공 M&S 범위에서 불필요 |
| 3 | KillChainContext 상태 캡슐화 | **부분 수용** | 별도 Context dataclass 대신 `model` 인스턴스 직접 전달로 충분 |
| 4 | Pydantic 런타임 금지 컨벤션 | **수용** (minor) | CLAUDE.md 코딩 규칙에 1줄 추가 |
| 5 | network.py 토폴로지 하드코딩 제거 | **수용 (핵심)** | `network.py:31-78` ~15개 타입명 문자열 — 확장 최대 병목 |
| 6 | type_priority를 pk_table 기반으로 | **수용** | `model.py:716-721` 하드코딩 우선순위 → Pk 기반 동적 추론 |
| 7 | comms.py 중복 팩터 전략 위임 | **수용** | `comms.py:81-82` `if architecture == "killweb"` 제거 |
| 8 | threats.py ScenarioSchema DI | **수용** (암묵적) | Phase 8에서 ScenarioSchema 구현 시 자연 해결 |
| 9 | Registry 생명주기 명확화 | **수용** | `AirDefenseModel.__init__`에서 초기화 순서 명시 |

### 기각 상세: #2 다중 능력 Entity-Component

Gemini는 이지스함/F-35처럼 "센서+사수+C2" 겸용 플랫폼을 위해 `List[Capability]` 구조를 제안했으나:
- 현재 모델링 대상(한국군 지상 방공체계)에 해당 엔티티 없음
- Entity-Component 도입 시 `registry.get_shooters()` 등의 카테고리 쿼리가 복잡해짐
- 향후 필요 시 상속→컴포지션 전환은 straightforward (breaking change 아님)
- **YAGNI 원칙 적용**: 현재 불필요한 추상화는 복잡도만 증가

---

## 2. 보완된 ontology.py 설계 (Gemini #5 반영)

기존 계획의 4개 EntityType에 **선형 토폴로지 관계 필드** 추가:

```python
class SensorType(EntityType):
    capability: DetectionCapability
    reporting_c2_type: Optional[str] = None  # 신규: 선형 C2에서 보고할 상위 노드

class ShooterType(EntityType):
    capability: EngagementCapability
    controlling_c2_type: Optional[str] = None  # 신규: 선형 C2에서 통제받는 노드

class C2Type(EntityType):
    capability: C2Capability
    parent_c2_type: Optional[str] = None  # 신규: 상위 C2 노드
```

이 3개 필드로 `network.py`의 하드코딩 15개를 완전 제거.

config.py에 관계 매핑 추가:
```python
TOPOLOGY_RELATIONS = {
    "sensor_to_c2": {"EWR": "MCRC", "PATRIOT_RADAR": "TOC_PAT", "MSAM_MFR": "TOC_MSAM", "SHORAD_RADAR": "TOC_SHORAD"},
    "shooter_to_c2": {"PATRIOT_PAC3": "TOC_PAT", "CHEONGUNG2": "TOC_MSAM", "BIHO": "TOC_SHORAD", "KF16": "MCRC"},
    "c2_hierarchy": {"BATTALION_TOC": "MCRC", "EOC": None},
}
```

---

## 3. 보완된 registry.py 설계 (Gemini #6, #9 반영)

추가 메서드:
- `get_prioritized_shooters(threat_type_id) -> List[ShooterType]` — pk_table 기반 Pk 내림차순 정렬 (model.py:716-721의 `type_priority` 딕셔너리 대체)
- `get_sensors_for_c2(c2_type_id)` — `reporting_c2_type` 역조회
- `get_shooters_for_c2(c2_type_id)` — `controlling_c2_type` 역조회

**생명주기** (Gemini #9): `AirDefenseModel.__init__()` 최상단에서 생성 → `self.registry`에 저장 → 시뮬레이션 동안 불변 참조

---

## 4. 보완된 strategies.py 설계 (Gemini #3, #7 반영)

### 메서드 시그니처 (Gemini #3)
- 별도 KillChainContext 대신 `model: AirDefenseModel`을 첫 인자로 전달
- SimPy generator 메서드(`run_killchain`)는 model에서 `simpy_env`, `comm`, `c2_resources` 접근

### 추가 메서드 (Gemini #7)
```python
def get_redundancy_factor(self) -> float:
    """통신 중복 경로 완화 계수"""
    # LinearC2Strategy: return 1.0
    # KillWebStrategy: return COMM_DEGRADATION["killweb_redundancy_factor"]
```

### model.py 분기 → 전략 메서드 매핑 (11개)

| model.py 위치 | 분기 내용 | 전략 메서드 |
|--------------|----------|------------|
| L143 | 토폴로지 선택 | `build_topology()` |
| L203 | Kill Web 전용 아군 상태 | `update_cop()` |
| L288 | 센서 융합 vs 단순 보고 | `fuse_tracks()` |
| L338-432 | 킬체인 전체 분기 | `run_killchain()` |
| L545 | 센서 융합 Pk 보너스 | `compute_fusion_bonus()` |
| L618 | Kill Web 전용 교전계획 | `share_engagement_plan()` |
| L672 | 적응형 교전 | `get_max_simultaneous()` |
| L708 | 사수 선정 분기 | `select_shooter()` |
| L743 | COP 아군 상태 활용 | (select_shooter 내부) |
| comms.py L81 | 중복 팩터 | `get_redundancy_factor()` |

---

## 5. 보완된 구현 순서

| Phase | 작업 | 파일 | 위험도 | Gemini 반영 |
|-------|------|------|--------|------------|
| **1** | ontology.py 도메인 모델 | 신규 | 낮음 | #5 (토폴로지 관계 필드) |
| **2** | registry.py 레지스트리 | 신규 + config.py 소폭 | 낮음 | #6, #9 |
| **3** | strategies.py 전략 클래스 | 신규 | 중간 | #3, #7 |
| **4** | model.py 리팩토링 | **대폭 수정** | **최고** | #9 (init 순서), #1 (agent DI) |
| **5** | agents.py 시그니처 변경 | 수정 | 낮음 | #1 (온톨로지 타입 DI) |
| **6** | network.py 토폴로지 리팩토링 | **대폭 수정** | 중간 | #5 (핵심) |
| **7** | comms.py 수정 | 소폭 수정 | 낮음 | #7 |
| **8** | ScenarioSchema + threats.py | config.py + threats.py 수정 | 중간 | #8 |
| **9** | CZML 내보내기 | 신규 | 낮음 | (기존 계획 유지) |
| **10** | 테스트 + 회귀 검증 | tests/ 신규/수정 | 낮음 | #4 (CLAUDE.md 컨벤션) |

### Phase 4 세부: model.py init 순서 (Gemini #9)

```python
def __init__(self, architecture="linear", ...):
    # 1. Registry 초기화
    self.registry = EntityRegistry()
    self.registry.load_from_config()

    # 2. Strategy 선택 (model.py에 남는 유일한 architecture 분기)
    self.strategy = LinearC2Strategy(self.registry) if architecture == "linear" \
                    else KillWebStrategy(self.registry)

    # 3. Agent 생성 (registry 타입 주입)
    self._create_defense_agents()  # registry에서 SensorType 등 조회 후 Agent에 전달

    # 4. Topology (strategy 위임)
    self.topology = self.strategy.build_topology(self.sensors, self.c2_nodes, self.shooters)

    # 5. CommChannel (redundancy_factor 주입)
    self.comm = CommChannel(self.simpy_env, redundancy_factor=self.strategy.get_redundancy_factor())

    # 6. KillChainProcess
    self.killchain = KillChainProcess(self.simpy_env, self.comm, self.c2_resources)
```

---

## 6. 위험 완화

| 위험 | 완화 방안 |
|------|----------|
| Phase 4 model.py 회귀 | Phase 3에서 전략 클래스 독립 테스트 → Phase 4에서 교체. seed=42 기준값 비교 |
| Phase 6 network.py 토폴로지 변경 | 기존 함수를 `_legacy()`로 보존, 결과 비교 후 제거 |
| agents.py 시그니처 변경으로 테스트 깨짐 | 과도기: 문자열/SensorType 모두 수용하는 dual 생성자 → 테스트 통과 후 문자열 경로 제거 |
| comms.py 인터페이스 변경 | `redundancy_factor=1.0` 기본값으로 역호환 |

---

## 7. 검증 방법

1. **회귀 테스트**: `python -m pytest tests/ -v` — 86개 기존 테스트 전체 통과
2. **기준값 비교**: seed=42 시나리오 1에서 리팩토링 전후 leaker_rate, s2s_time, success_rate 동일
3. **확장성 검증**: config.py에 새 센서 타입(예: `L_SAM_RADAR`) 추가 시 코드 수정 없이 시뮬레이션 동작 확인
4. **CZML 검증**: Cesium Sandcastle에서 내보낸 CZML 로드하여 3D 궤적 확인

---

## 8. 수정 대상 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `modules/ontology.py` (신규) | 도메인 모델 + 토폴로지 관계 필드 |
| `modules/registry.py` (신규) | 레지스트리 + Pk 기반 우선순위 추론 |
| `modules/strategies.py` (신규) | ArchitectureStrategy ABC + Linear/KillWeb + redundancy_factor |
| `modules/exporters.py` (신규) | CZMLExporter |
| `modules/model.py` (리팩토링) | 11개 분기 → strategy 위임 + init 순서 재구성 |
| `modules/agents.py` (수정) | 생성자: dict → 온톨로지 타입 DI |
| `modules/network.py` (리팩토링) | 하드코딩 제거 → registry 기반 동적 토폴로지 |
| `modules/comms.py` (소폭) | architecture 문자열 → redundancy_factor 수치 |
| `modules/config.py` (소폭) | TOPOLOGY_RELATIONS 추가 + ScenarioSchema |
| `modules/threats.py` (소폭) | ScenarioSchema 인스턴스 수신 |
| `tests/test_ontology.py` (신규) | 도메인 모델 테스트 |
| `tests/test_registry.py` (신규) | 레지스트리 테스트 |
| `tests/test_strategies.py` (신규) | 전략 패턴 테스트 |
| `CLAUDE.md` (소폭) | Pydantic 런타임 금지 컨벤션 추가 |
