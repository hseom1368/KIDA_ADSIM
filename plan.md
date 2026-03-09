# v0.3 개선 계획 — 시나리오 확장 및 모델 정합성 강화

> v0.2에서 비행 프로파일 현실화 + 최적 교전 시점 로직 구현 완료.
> v0.3에서는 미검증 시나리오(2~4) 활성화, 메트릭 버그 수정, 전자전 모델 고도화에 집중.

---

## 현재 상태 (v0.2 완료 기준)

### v0.2에서 해결된 문제
1. **위협 비행 프로파일 현실화** — 4종 위협 모두 단계별 동적 고도/속도/기동 적용
2. **3D 경사거리(Slant Range)** — 탐지·교전 거리에 고도차 반영
3. **최적 교전 시점 로직** — `_should_engage_now()` 구현 → 조기교전 역설 해소
4. **SRBM 교전 가능 창** — 종말단계(30→0km) 하강 시 PAC-3 교전 가능 확인

### v0.2 성과 (시나리오 1 기준)
| 지표 | Linear C2 | Kill Web |
|------|-----------|----------|
| 누출률 | 35.6% | **11.1%** |
| 교전 성공률 | 37.5% | **44.4%** |
| 평균 Pk | 0.430 | 0.405 |
| Pk<0.2 저효율 교전 | 0건 | 0건 |
| 격추수 | 12기 | **20기** |

---

## v0.3 작업 항목

### 1단계: defense_coverage 메트릭 수정 (버그 픽스)

**문제**: `metric_9_defense_coverage()`가 `shooters=None`으로 호출되어 항상 0.0 반환.

**파일**: `modules/metrics.py`

**수정 방안**:
- `MetricsCollector`가 초기화 시 shooter 목록 참조를 보유하도록 변경
- `compute_all_metrics()`에서 `self.shooters`를 자동 전달
- 또는 `MetricsCollector.__init__()`에 shooters 파라미터 추가 후
  `model.py`에서 초기화 시 전달

**예상 코드**:
```python
# metrics.py
class MetricsCollector:
    def __init__(self):
        ...
        self.shooters = []  # model에서 설정

    def compute_all_metrics(self):
        ...
        "defense_coverage": self.metric_9_defense_coverage(self.shooters),
        ...

# model.py (초기화 시)
self.metrics.shooters = self.shooter_agents
```

---

### 2단계: 시나리오 3(전자전) — 재밍 레벨 동적 전환 구현

**문제**: `scenario_3_ew`에 `jamming_levels` 3단계가 정의되어 있으나,
모델은 `jamming_level` 스칼라 값만 사용. 3단계 재밍 효과가 차별화되지 않음.

**파일**: `modules/model.py`, `modules/config.py`

**수정 방안**:
시나리오 3은 **3회 연속 실행** (light/moderate/heavy) 또는
**시간 구간별 재밍 강도 변화** 두 가지 접근이 가능.

#### 방안 A: 3회 분할 실행 (권장)
- 시나리오 3을 3개 하위 시나리오로 분할
- `scenario_3_ew_light`, `scenario_3_ew_moderate`, `scenario_3_ew_heavy`
- 각각 `jamming_level`을 다르게 설정
- 실험 config에서 3개를 모두 포함

#### 방안 B: 시간대별 재밍 전환
- 시뮬레이션 진행 중 시간에 따라 재밍 강도를 light→moderate→heavy로 전환
- `detection_factor`는 센서 탐지 확률에, `latency_factor`는 C2 처리 지연에 곱산

**추가 수정 필요**:
- `SensorAgent.detect()`에 `detection_factor` 반영 (탐지 확률 감소)
- 킬체인 프로세스 내 C2 처리 시간에 `latency_factor` 반영 (지연 증가)
- 현재 `jamming_level`은 `compute_pk()`에서만 `(1 - jamming * 0.3)` 적용

---

### 3단계: 시나리오 2~4 검증 실행

**문제**: 시나리오 2~4는 config에 정의되어 있지만 실행 검증 없음.

**작업**:
1. 시나리오 2(복합위협): 4종 혼합 동시 교전 정상 동작 확인
2. 시나리오 3(전자전): 재밍 레벨별 성능 차이 확인
3. 시나리오 4(순차교전): Poisson 도착 + 60분 지속 작전 확인
4. 각 시나리오별 linear vs killweb 비교 결과 기록

**예상 이슈**:
- 시나리오 4: `max_sim_time=1800` (30분) < `duration=3600` (60분) → config 충돌 가능
- 시나리오 3: 재밍 효과가 Pk에만 반영 → 탐지·C2 영향 미반영

---

### 4단계: EXPERIMENT_CONFIG 시나리오 확장

**문제**: `EXPERIMENT_CONFIG["scenarios"]`에 시나리오 1, 5만 포함.

**파일**: `modules/config.py` (line 466)

**수정**:
```python
"scenarios": [
    "scenario_1_saturation",
    "scenario_2_complex",
    "scenario_3_ew_light",
    "scenario_3_ew_moderate",
    "scenario_3_ew_heavy",
    "scenario_4_sequential",
    "scenario_5_node_destruction",
],
```

---

### 5단계: 시나리오 4 타이머 호환성 수정

**문제**: 시나리오 4는 `duration=3600`(60분)이지만 `SIM_CONFIG["max_sim_time"]=1800`(30분).
모델이 시나리오별 최대 시간을 동적으로 조절해야 함.

**파일**: `modules/model.py`

**수정 방안**:
```python
# 시나리오별 최대 시뮬레이션 시간
if "duration" in scenario_params:
    self.max_sim_time = scenario_params["duration"]
```

---

### 6단계: 단위 테스트 프레임워크 구축

**문제**: `tests/` 디렉토리 미존재 → CLAUDE.md의 테스트 명령어 실패.

**작업**:
- `tests/` 디렉토리 생성
- `tests/test_agents.py` — 비행 프로파일 단위 테스트 (SRBM 교전고도 진입 확인)
- `tests/test_model.py` — 각 시나리오 스모크 테스트 (실행 완료 확인)
- `tests/test_metrics.py` — defense_coverage 등 메트릭 정합성 테스트
- `tests/test_slant_range.py` — 3D 경사거리 계산 정확성

---

## 구현 순서 요약

| 순서 | 작업 | 파일 | 난이도 |
|------|------|------|--------|
| 1 | defense_coverage 메트릭 수정 | metrics.py, model.py | 낮음 |
| 2 | 시나리오 3 재밍 레벨 동적 전환 | model.py, config.py, agents.py | 중간 |
| 3 | 시나리오 2~4 검증 실행 | (테스트) | 낮음 |
| 4 | EXPERIMENT_CONFIG 확장 | config.py | 낮음 |
| 5 | 시나리오 4 타이머 호환성 | model.py | 낮음 |
| 6 | 단위 테스트 프레임워크 | tests/*.py | 중간 |

---

## 예상 효과

- 시나리오 3(전자전): 재밍 강도별 Kill Web vs Linear C2 내구성 차이 정량화
- 시나리오 4(순차교전): 장시간 작전 시 탄약 소진, C2 큐잉 병목 비교
- 시나리오 2(복합위협): 다층 방어(SRBM+CM+항공기+UAS 동시) 효과 검증
- 테스트 프레임워크: 향후 변경 시 회귀 방지
- defense_coverage 메트릭: 방어 면적 비교 데이터 활성화
