# v0.4 상세 구현 계획

> 작성일: 2026-03-11
> 기반: v0.3 (45개 테스트 PASS, 7 시나리오 × 2 아키텍처 검증 완료)

---

## 작업 개요

| # | 작업 | 파일 | 난이도 | 영향 범위 |
|---|------|------|--------|-----------|
| 1 | jamming_level 오버라이드 정리 | model.py, config.py | 낮음 | 기존 테스트 호환 |
| 2 | 죽은 코드 삭제 (comms.py) | comms.py | 낮음 | 테스트 무영향 |
| 3 | 죽은 설정 삭제 (config.py) | config.py | 낮음 | 테스트 무영향 |
| 4 | 다중 교전 모델링 | config.py, model.py, agents.py, metrics.py | **높음** | 핵심 로직 변경 |
| 5 | 테스트 추가/수정 | tests/ | 중간 | 작업 4 검증 |
| 6 | Monte Carlo 배치 실험 | notebook3, notebook4 | 중간 | 노트북만 |
| 7 | 문서 업데이트 | CHANGELOG.md, CLAUDE.md, plan.md | 낮음 | 문서만 |

**실행 순서**: 1 → 2 → 3 → 4 → 5 → 6 → 7 (의존성 순)

---

## 작업 1: jamming_level 오버라이드 정리

### 문제
`model.py:63-65`에서 생성자 `jamming_level` 파라미터가 시나리오 config에 의해 **묵시적으로** 덮어씌워짐:
```python
self.jamming_level = jamming_level                                    # 63행
if hasattr(self.scenario, 'get'):                                     # 64행
    self.jamming_level = self.scenario.get("jamming_level", jamming_level)  # 65행
```

### 해결 방안
**"명시적 오버라이드 우선" 패턴** 적용:
- 생성자 `jamming_level` 파라미터에 기본값 `None` 사용
- `None`이면 시나리오 config 값 사용, 명시적 값이면 생성자 값 우선

### 변경 사항

#### `model.py` (4행 수정)

**변경 전** (`model.py:38-39`):
```python
def __init__(self, architecture="linear", scenario="scenario_1_saturation",
             seed=None, jamming_level=0.0):
```

**변경 후**:
```python
def __init__(self, architecture="linear", scenario="scenario_1_saturation",
             seed=None, jamming_level=None):
```

**변경 전** (`model.py:62-65`):
```python
# 재밍 수준
self.jamming_level = jamming_level
if hasattr(self.scenario, 'get'):
    self.jamming_level = self.scenario.get("jamming_level", jamming_level)
```

**변경 후**:
```python
# 재밍 수준: 명시적 파라미터 > 시나리오 config > 기본값 0.0
if jamming_level is not None:
    self.jamming_level = jamming_level  # 명시적 오버라이드
elif hasattr(self.scenario, 'get'):
    self.jamming_level = self.scenario.get("jamming_level", 0.0)
else:
    self.jamming_level = 0.0
```

### 기존 테스트 영향 분석
- `test_edge_cases.py:TestExtremeJamming.test_max_jamming_no_crash` — `jamming_level=1.0` 명시적 전달 → **동작 동일** (명시적 값 우선)
- 나머지 테스트 — `jamming_level` 미전달 → `None` → 시나리오 config 사용 → **동작 동일**
- ✅ 기존 45개 테스트 모두 PASS 유지 예상

---

## 작업 2: 죽은 코드 삭제 (comms.py)

### 문제
`comms.py:85-202`의 `linear_killchain()`과 `killweb_killchain()` 메서드가 **한 번도 호출되지 않음**.
실제 킬체인 로직은 `model.py:292-398`의 `_killchain_process()`에 인라인 구현됨.

### 해결 방안
**죽은 코드 삭제** (사용자 선택):
- `comms.py`에서 `linear_killchain()` (85-145행), `killweb_killchain()` (147-202행) 삭제
- `KillChainProcess` 클래스는 `log_event()` 메서드와 `event_log` 데이터 저장 역할로 유지

### 변경 사항

#### `comms.py` (118행 삭제 → 약 85행으로 축소)

**삭제 대상**: `comms.py:85-202` (두 메서드 전체)

**유지 항목**:
- `CommChannel` 클래스 전체 (12-55행)
- `KillChainProcess.__init__()` (61-73행)
- `KillChainProcess.log_event()` (75-83행)

### 기존 테스트 영향
- ✅ 무영향 — 삭제 대상 메서드를 호출하는 테스트 없음

---

## 작업 3: 죽은 설정 삭제 (config.py)

### 문제
`config.py:383-399`의 `scenario_3_ew` 원본 설정이 v0.3에서 3개 하위 시나리오(`_light`/`_moderate`/`_heavy`)로 대체됨.
원본은 참조되지 않으나 코드에 잔존.

### 변경 사항

#### `config.py` (17행 삭제)

**삭제 대상**: `config.py:383-399` (`scenario_3_ew` 딕셔너리 항목)

**유지 항목**:
- `scenario_3_ew_light` (400-413행)
- `scenario_3_ew_moderate` (414-427행)
- `scenario_3_ew_heavy` (428-441행)

### 주의
- `EXPERIMENT_CONFIG.scenarios` 리스트에 `scenario_3_ew`가 **포함되어 있지 않음** → 안전
- `conftest.py:EXPERIMENT_SCENARIOS`에도 포함되지 않음 → 안전
- ✅ 기존 테스트 무영향

---

## 작업 4: 다중 교전 모델링 (핵심 기능)

### 설계 개요
**위협 우선도 기반 다중 교전** (사용자 선택):
- 고위협(SRBM, CRUISE_MISSILE) → 최대 2~3기 사수 동시 교전
- 저위협(AIRCRAFT, UAS) → 1기 사수 교전 유지
- 결합 격추 확률: P(kill) = 1 - ∏(1 - Pk_i)

### 4-1. config.py 변경

#### ENGAGEMENT_POLICY에 다중 교전 파라미터 추가

```python
ENGAGEMENT_POLICY = {
    # ... 기존 파라미터 유지 ...

    # ── 다중 교전 정책 (v0.4) ──
    # 위협 유형별 최대 동시 교전 사수 수
    "max_simultaneous_shooters": {
        "SRBM": 3,
        "CRUISE_MISSILE": 2,
        "AIRCRAFT": 1,
        "UAS": 1,
    },
    # 다중 교전 기본값 (미정의 위협 유형)
    "default_max_simultaneous": 1,
}
```

**설계 근거**:
- SRBM: 고속(~3km/s) + 고위협 → 최대 3기 동시 교전으로 격추 확률 극대화
- CRUISE_MISSILE: 중위협 → 2기 동시 교전
- AIRCRAFT/UAS: 비교적 저속 + 재교전 기회 충분 → 1기 유지 (탄약 절약)

### 4-2. model.py 변경 — `_execute_engagements()` 리팩토링

**현재 구조** (`model.py:437-515`):
```
for threat in cleared_threats:
    shooter = _find_available_shooter(threat, engaged_shooters)  # 1기만
    if _should_engage_now(shooter, threat):
        engaged_shooters.add(shooter)
        hit = shooter.engage(threat)
```

**변경 구조**:
```
for threat in cleared_threats:
    max_shooters = ENGAGEMENT_POLICY["max_simultaneous_shooters"]
                   .get(threat.threat_type, default_max)

    assigned_shooters = []
    for _ in range(max_shooters):
        shooter = _find_available_shooter(threat, engaged_shooters)
        if not shooter or not _should_engage_now(shooter, threat):
            break
        assigned_shooters.append(shooter)
        engaged_shooters.add(shooter.agent_id)

    if not assigned_shooters:
        continue

    # 다중 교전 실행 + 결합 Pk 계산
    _execute_multi_engagement(threat, assigned_shooters)
```

#### 상세 구현: `_execute_multi_engagement()` 신규 메서드

```python
def _execute_multi_engagement(self, threat, shooters):
    """다중 사수 동시 교전 실행.

    결합 격추 확률: P(kill) = 1 - ∏(1 - Pk_i)
    각 사수는 독립적으로 교전하며, 하나라도 명중하면 격추.
    """
    if threat.engaged_time is None:
        threat.engaged_time = self.sim_time

    # 각 사수별 독립 교전 결과 계산
    individual_hits = []
    for shooter in shooters:
        hit = shooter.engage(threat, self.jamming_level)
        individual_hits.append((shooter, hit))

        optimal = self._find_best_shooter(threat)
        optimal_id = optimal.agent_id if optimal else shooter.agent_id

        self.metrics.record_engagement(
            threat.unique_id, self.sim_time,
            shooter.agent_id, hit, optimal_id,
        )
        self.killchain.log_event(
            threat.unique_id, "engagement",
            f"shooter={shooter.agent_id}, hit={hit}, "
            f"Pk={shooter.compute_pk(threat, self.jamming_level):.2f}"
        )

    # 다중 교전 메트릭 기록
    if len(shooters) > 1:
        self.metrics.record_multi_engagement(
            threat.unique_id, self.sim_time, len(shooters)
        )

    # 하나라도 명중하면 격추
    any_hit = any(hit for _, hit in individual_hits)
    if any_hit:
        threat.destroy()

    # 노드 손실 후 첫 교전 → 복구 시간 기록
    if (self.metrics.node_loss_time is not None
            and self.metrics.recovery_time is None):
        self.metrics.recovery_time = self.sim_time
        if self.metrics.total_shots > 0:
            self.metrics.post_loss_performance = (
                self.metrics.total_kills / self.metrics.total_shots
            )
```

### 4-3. agents.py 변경 — `ShooterAgent.engage()` 수정

현재 `engage()` 메서드는 위협이 이미 파괴된 경우를 고려하지 않음.
다중 교전에서 첫 번째 사수가 격추하면, 두 번째 사수는 이미 죽은 위협에 사격하는 문제.

**해결**: `_execute_multi_engagement()`에서 **각 사수의 Pk를 먼저 계산** → 결합 확률로 **단일 판정** 수행

**대안 (더 심플)**: 현재 `engage()`의 독립 Bernoulli 방식 유지하되, `threat.destroy()`를 **모든 사수 결과 수집 후** 1회만 호출 (위 구현에 이미 반영됨)

> 참고: `engage()` 내부에서 `threat` 상태를 변경하지 않으므로 (hit/miss만 반환) 현재 구조로 충분. `threat.destroy()`는 외부에서 호출.

실제 `engage()` 확인 필요 — `agents.py:213-227`:

```python
def engage(self, threat, jamming_level=0.0):
    pk = self.compute_pk(threat, jamming_level)
    hit = random.random() < pk
    self.ammo_count -= 1
    self.shots_fired += 1
    # engagement_timer 설정 (재장전 시간)
    self.engagement_timer = self.params.get("reload_time", 5)
    return hit
```

→ `engage()`는 위협 상태를 변경하지 않음 ✅ → 다중 교전 시 문제없음

### 4-4. metrics.py 변경 — 다중 교전 메트릭 추가

#### 새 필드 추가 (`__init__`):
```python
# v0.4: 다중 교전 추적
self.multi_engagements = []      # [(threat_id, time, num_shooters)]
self.total_multi_engagement_count = 0
```

#### 새 메서드 추가:
```python
def record_multi_engagement(self, threat_id, time, num_shooters):
    """다중 교전 기록"""
    self.multi_engagements.append((threat_id, time, num_shooters))
    self.total_multi_engagement_count += 1
```

#### `collect_all_metrics()` 수정:
기존 10개 메트릭에 추가:
```python
# 메트릭 11: 다중 교전 비율
"multi_engagement_rate": (self.total_multi_engagement_count / max(self.threats_engaged, 1)) * 100,
# 메트릭 12: 평균 동시 교전 사수 수
"avg_shooters_per_engagement": (
    sum(n for _, _, n in self.multi_engagements) / max(len(self.multi_engagements), 1)
    if self.multi_engagements else 1.0
),
```

### 4-5. 기존 메트릭 영향 분석

| 메트릭 | 다중 교전 영향 | 대응 |
|--------|---------------|------|
| engagement_success_rate | total_shots 증가 → 성공률 변화 | 의도된 동작 (shot 기반) |
| ammo_efficiency | 탄약 소비 증가 | 의도된 동작 |
| max_concurrent_engagements | 동시 교전 수 증가 | 의도된 동작 |
| leaker_rate | 결합 Pk 향상 → 누출률 감소 | **핵심 개선 목표** |
| target_assignment_efficiency | 복수 사수 할당 시 최적 비교 | 첫 번째 사수 기준 유지 |

---

## 작업 5: 테스트 추가/수정

### 새 테스트 파일: `tests/test_multi_engagement.py`

#### 테스트 케이스 (8~10개):

```python
class TestMultiEngagementConfig:
    """다중 교전 설정 검증"""

    def test_max_simultaneous_shooters_in_config(self):
        """ENGAGEMENT_POLICY에 max_simultaneous_shooters 존재"""

    def test_srbm_gets_3_shooters(self):
        """SRBM 위협에 최대 3기 사수 할당 확인"""

    def test_uas_gets_1_shooter(self):
        """UAS 위협에 1기 사수만 할당 확인"""


class TestMultiEngagementExecution:
    """다중 교전 실행 검증"""

    def test_combined_pk_higher_than_single(self):
        """다중 교전 시 격추 확률이 단일 교전보다 높음 (멀티 시드)"""

    def test_ammo_consumption_increases(self):
        """다중 교전 시 탄약 소비가 단일보다 많음"""

    def test_multi_engagement_metrics_recorded(self):
        """multi_engagements 메트릭이 기록됨"""

    def test_no_double_destroy(self):
        """한 위협이 두 번 destroy 되지 않음"""


class TestMultiEngagementRegression:
    """기존 동작 호환성"""

    def test_killweb_still_beats_linear(self):
        """다중 교전 도입 후에도 Kill Web이 Linear보다 누출률 낮음"""

    def test_scenario1_completes_both_arch(self):
        """시나리오 1 양쪽 아키텍처 에러 없이 완료"""
```

### 기존 테스트 수정
- `test_edge_cases.py:TestExtremeJamming.test_max_jamming_no_crash` — `jamming_level=1.0` 전달 방식이 작업 1에서 변경되나, 명시적 전달이므로 **코드 변경 불필요**
- 기존 45개 테스트 모두 **코드 수정 없이** PASS 유지 목표

---

## 작업 6: Monte Carlo 배치 실험

### notebook3_batch_experiment.ipynb 업데이트

#### 실험 설계
- **규모**: 300회 × 7 시나리오 × 2 아키텍처 = **4,200 시뮬레이션**
- **시딩**: `seed = run_index * 7919 + hash(f"{scenario}_{arch}") % 10000`
  - 재현성 보장 + 시나리오/아키텍처 간 독립성
- **체크포인팅**: 50회마다 중간 저장 (`EXPERIMENT_CONFIG["checkpoint_interval"]`)
- **수렴 분석**: 파일럿 10회 → 표준오차 확인 → 300회 본 실험

#### 핵심 코드 구조
```python
results = []
for run_idx in range(EXPERIMENT_CONFIG["monte_carlo_runs"]):
    for scenario in EXPERIMENT_CONFIG["scenarios"]:
        for arch in EXPERIMENT_CONFIG["architectures"]:
            seed = run_idx * 7919 + hash(f"{scenario}_{arch}") % 10000
            model = AirDefenseModel(architecture=arch, scenario=scenario, seed=seed)
            result = model.run_full()
            results.append({
                "run": run_idx, "scenario": scenario, "architecture": arch,
                "seed": seed, **result["metrics"]
            })

    # 체크포인팅
    if (run_idx + 1) % EXPERIMENT_CONFIG["checkpoint_interval"] == 0:
        pd.DataFrame(results).to_csv(f"data/checkpoint_{run_idx+1}.csv")
```

### notebook4_analysis_viz.ipynb 업데이트

#### 분석 항목
1. **기술 통계**: 시나리오×아키텍처별 평균/표준편차/95%CI
2. **통계 검정**:
   - Shapiro-Wilk 정규성 검정
   - 정규: Independent t-test
   - 비정규: Mann-Whitney U test
3. **수렴 분석**: 누적 평균 그래프 (50~300회)
4. **효과 크기**: Cohen's d 계산
5. **다중 교전 분석** (v0.4 신규):
   - 다중 교전 비율 비교 (Linear vs Kill Web)
   - 다중 교전이 누출률 감소에 미치는 효과
   - 위협 유형별 평균 동시 교전 사수 수

#### 시각화
- 박스플롯: 아키텍처별 누출률/성공률 분포
- 히트맵: 시나리오×메트릭 비교
- 수렴 곡선: 시드별 누적 평균
- 레이더 차트: 10+2 메트릭 종합 비교

---

## 작업 7: 문서 업데이트

### CHANGELOG.md
- v0.4 섹션 추가 (변경사항, 성능 비교표, 발견된 문제, 개선 계획)

### CLAUDE.md
- "현재 버전" → v0.4 업데이트
- "핵심 아키텍처 비교" 표 갱신 (다중 교전 반영)
- "알려진 문제" v0.3 이슈 제거, v0.4 이슈 추가

### plan.md
- v0.3 → v0.4 완료 기록, v0.5 계획 초안

---

## 리스크 및 완화 전략

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 다중 교전으로 탄약 고갈 가속 | 후반부 교전 불가 | 잔여 탄약 임계값 추가 검토 (v0.5) |
| 기존 테스트 깨짐 | 회귀 버그 | 작업 1-3 후 즉시 `pytest` 실행 |
| Monte Carlo 실행 시간 | 4,200회 → 수 시간 | 파일럿 10회로 단위 시간 추정 후 진행 |
| 다중 교전 + 재밍 상호작용 | 예상치 못한 성능 변화 | EW 시나리오 별도 검증 |

---

## 검증 체크리스트

- [ ] 작업 1 후: `python -m pytest tests/ -v` → 45개 PASS
- [ ] 작업 1 후: `AirDefenseModel(jamming_level=0.5)` 테스트 → 0.5 적용 확인
- [ ] 작업 2-3 후: `python -m pytest tests/ -v` → 45개 PASS
- [ ] 작업 4-5 후: `python -m pytest tests/ -v` → 53+개 PASS (기존 45 + 신규 8+)
- [ ] 작업 4 후: 스모크 테스트 (시나리오 1, 두 아키텍처)
- [ ] 작업 4 후: Kill Web이 여전히 Linear보다 누출률 우위
- [ ] 작업 6 후: 파일럿 10회 정상 완료 확인

---

## 다음: v0.5 계획 (예고)

| 작업 | 설명 |
|------|------|
| 센서 융합 고도화 (COP 품질 차별화) | Kill Web: 복수 센서 동시 추적 시 위치 오차 감소 (√N 법칙) → Pk 추가 향상. Linear: 단일 센서 보고 의존 → 오차 그대로. `fusion_error_reduction` 파라미터 + `_sensor_detection()` 융합 로직 추가 |
| 잔여 탄약 기반 교전 정책 적응 | 다중 교전으로 인한 탄약 고갈 가속 대응 — 잔여 탄약 임계값 이하 시 자동으로 단일 교전 전환 |
| 통신 네트워크 동적 열화 | 재밍 환경에서 링크별 차등 열화 모델링 |

---

## v0.3 완료 기록

> 작업 완료일: 2026-03-09
> 테스트: 45개 전부 PASS

### 완료된 작업 (v0.3)
1. 코드 품질 리뷰 ✅ — shooter_score() 3D 수정, 매직 넘버 제거
2. 엣지 케이스 테스트 ✅ — 12개 추가
3. 전 시나리오 검증 ✅ — 14개 조합 PASS
4. 문서 업데이트 ✅
