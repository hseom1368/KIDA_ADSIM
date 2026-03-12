# v0.6 상세 구현 계획

> 작성일: 2026-03-12
> 기반: v0.5 (86개 테스트 PASS, COP 차별화 + 적응형 교전 + 통신 열화 + 2D 시각화 완료)

---

## 작업 개요

| # | 작업 | 파일 | 난이도 | 영향 범위 |
|---|------|------|--------|-----------|
| 1 | Monte Carlo 배치 실험 프레임워크 | model.py, notebook3 | **높음** | 실험 인프라 |
| 2 | 통계 분석 모듈 | modules/stats.py (신규), notebook4 | **높음** | 분석 파이프라인 |
| 3 | 최종 분석 보고서 구조 | notebook4, notebook6 (신규) | 중간 | 보고서 |
| 4 | 인터랙티브 시각화 (선택) | modules/dashboard.py (신규) | 낮음 | 선택 기능 |
| 5 | 테스트 추가 | tests/ | 중간 | 작업 1~2 검증 |
| 6 | 문서 업데이트 | CHANGELOG.md, CLAUDE.md, README.md | 낮음 | 문서만 |

**실행 순서**: 1 → 2 → 3 → 5 → 6 (작업 4는 선택)

---

## 작업 1: Monte Carlo 300회 배치 실험 프레임워크

### 목표
- 전 시나리오(S1~S5, EW 3단계 포함 7개) × 2 아키텍처 × 300 시드 = **4,200회** 시뮬레이션
- 수렴 분석으로 300회 충분성 검증
- 결과를 CSV/Parquet로 저장하여 재현 가능한 분석 기반 구축

### 현재 상태
- `notebook3`에서 단일 시나리오 × 2 아키텍처 × 300회 실행 가능
- 그러나 전 시나리오 일괄 실행 + 결과 저장 + 수렴 분석 프레임워크 부재

### 설계

#### 1-1. 배치 실험 실행기

```python
# notebook3 또는 별도 스크립트에서 실행
import itertools
import pandas as pd
from modules.model import AirDefenseModel

SCENARIOS = [
    "scenario_1_saturation",
    "scenario_2_mixed",
    "scenario_3_ew_light",
    "scenario_3_ew_moderate",
    "scenario_3_ew_heavy",
    "scenario_4_sequential",
    "scenario_5_node_kill",
]
ARCHITECTURES = ["linear", "killweb"]
N_SEEDS = 300

results = []
for scenario, arch in itertools.product(SCENARIOS, ARCHITECTURES):
    for seed in range(N_SEEDS):
        m = AirDefenseModel(
            architecture=arch,
            scenario=scenario,
            seed=seed,
            record_snapshots=False,  # 메모리 절약
        )
        r = m.run_full()
        row = {
            "scenario": scenario,
            "architecture": arch,
            "seed": seed,
            "leaker_rate": r["metrics"]["leaker_rate"],
            "success_rate": r["metrics"]["engagement_success_rate"],
            "s2s_mean": r["metrics"]["sensor_to_shooter_time"]["mean"],
            "multi_engagement_rate": r["metrics"]["multi_engagement_rate"],
            "ammo_efficiency": r["metrics"]["ammo_efficiency"],
            "defense_coverage": r["metrics"]["defense_coverage"],
            "system_resilience": r["metrics"]["system_resilience"],
            # ... 12개 메트릭 전부 수집
        }
        results.append(row)

df = pd.DataFrame(results)
df.to_csv("results/monte_carlo_v06.csv", index=False)
```

#### 1-2. 수렴 분석

```python
def convergence_analysis(df, metric, window_sizes=[50, 100, 150, 200, 250, 300]):
    """누적 평균의 안정성으로 300회 충분성 검증"""
    for scenario in df["scenario"].unique():
        for arch in df["architecture"].unique():
            subset = df[(df.scenario == scenario) & (df.architecture == arch)]
            cumulative_means = [subset[metric].iloc[:w].mean() for w in window_sizes]
            # 최종 50회 누적 평균 변화율 < 1% → 수렴 판정
```

#### 1-3. 병렬화 (선택)

```python
# multiprocessing Pool 활용
from multiprocessing import Pool

def run_single(args):
    scenario, arch, seed = args
    m = AirDefenseModel(architecture=arch, scenario=scenario, seed=seed)
    return m.run_full()["metrics"]

with Pool(processes=4) as pool:
    results = pool.map(run_single, all_combinations)
```

### 결과 저장 구조

```
results/
├── monte_carlo_v06.csv          # 전체 원시 데이터 (4,200행 × 12열)
├── convergence_analysis.csv     # 수렴 분석 결과
└── summary_statistics.csv       # 시나리오별 요약 통계
```

### 예상 실행 시간
- 단일 시뮬레이션: ~0.5초 (v0.5 기준, record_snapshots=False)
- 4,200회: ~35분 (직렬) / ~10분 (4코어 병렬)

---

## 작업 2: 통계 분석 모듈

### 목표
- 아키텍처 간 성능 차이의 **통계적 유의성** 검정
- **효과 크기** (Cohen's d) 산출로 실질적 의미 판단
- **신뢰 구간** 95% CI로 결과 불확실성 정량화

### 설계: `modules/stats.py` (신규)

```python
"""통계 분석 모듈 — v0.6 Monte Carlo 결과 분석"""

import numpy as np
import pandas as pd
from scipy import stats

class MonteCarloAnalyzer:
    """Monte Carlo 실험 결과 통계 분석기"""

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def compare_architectures(self, scenario, metric):
        """두 아키텍처 간 성능 비교 (통계 검정 + 효과 크기)"""
        linear = self.df[(self.df.scenario == scenario) & (self.df.architecture == "linear")][metric]
        killweb = self.df[(self.df.scenario == scenario) & (self.df.architecture == "killweb")][metric]

        result = {
            "scenario": scenario,
            "metric": metric,
            "linear_mean": linear.mean(),
            "linear_std": linear.std(),
            "killweb_mean": killweb.mean(),
            "killweb_std": killweb.std(),
        }

        # 1. 정규성 검정 (Shapiro-Wilk)
        _, p_normal_l = stats.shapiro(linear)
        _, p_normal_k = stats.shapiro(killweb)
        result["normal_linear"] = p_normal_l > 0.05
        result["normal_killweb"] = p_normal_k > 0.05

        # 2. 등분산 검정 (Levene)
        _, p_levene = stats.levene(linear, killweb)
        result["equal_variance"] = p_levene > 0.05

        # 3. 모수 검정 (독립 표본 t-test, Welch's t-test)
        t_stat, p_ttest = stats.ttest_ind(linear, killweb, equal_var=result["equal_variance"])
        result["t_statistic"] = t_stat
        result["p_value_ttest"] = p_ttest

        # 4. 비모수 검정 (Mann-Whitney U test)
        u_stat, p_mann = stats.mannwhitneyu(linear, killweb, alternative='two-sided')
        result["u_statistic"] = u_stat
        result["p_value_mann_whitney"] = p_mann

        # 5. 효과 크기 (Cohen's d)
        pooled_std = np.sqrt((linear.std()**2 + killweb.std()**2) / 2)
        cohens_d = (linear.mean() - killweb.mean()) / pooled_std if pooled_std > 0 else 0
        result["cohens_d"] = cohens_d
        result["effect_size"] = self._interpret_cohens_d(cohens_d)

        # 6. 95% 신뢰 구간 (차이의 CI)
        diff = linear.values - killweb.values[:len(linear)]
        ci_low, ci_high = stats.t.interval(0.95, len(diff)-1, loc=diff.mean(), scale=stats.sem(diff))
        result["ci_95_low"] = ci_low
        result["ci_95_high"] = ci_high

        return result

    def full_analysis(self, metrics=None):
        """전 시나리오 × 전 메트릭 종합 분석"""
        if metrics is None:
            metrics = ["leaker_rate", "success_rate", "s2s_mean", "multi_engagement_rate"]
        results = []
        for scenario in self.df["scenario"].unique():
            for metric in metrics:
                results.append(self.compare_architectures(scenario, metric))
        return pd.DataFrame(results)

    @staticmethod
    def _interpret_cohens_d(d):
        d = abs(d)
        if d < 0.2:
            return "negligible"
        elif d < 0.5:
            return "small"
        elif d < 0.8:
            return "medium"
        else:
            return "large"
```

### 분석 항목 체크리스트

| 분석 | 방법 | 목적 |
|------|------|------|
| 정규성 검정 | Shapiro-Wilk | 모수/비모수 검정 선택 |
| 평균 차이 검정 | Welch's t-test | 아키텍처 간 유의차 |
| 비모수 검정 | Mann-Whitney U | 비정규 분포 시 보완 |
| 효과 크기 | Cohen's d | 실질적 차이 크기 |
| 신뢰 구간 | 95% CI (부트스트랩) | 추정 불확실성 |
| 수렴 분석 | 누적 평균 안정성 | 300회 충분성 |
| 다중 비교 보정 | Bonferroni/FDR | 7개 시나리오 동시 검정 보정 |

---

## 작업 3: 최종 분석 보고서 구조

### 보고서 구성 (notebook4 확장 또는 notebook6 신규)

1. **서론**: 연구 목적, 비교 대상, 시뮬레이션 설계
2. **실험 설계**: Monte Carlo 방법론, 파라미터, 시나리오 설명
3. **수렴 분석**: 300회 충분성 그래프
4. **시나리오별 결과**:
   - 기술 통계 (평균, 표준편차, 중앙값, IQR)
   - 박스플롯 / 바이올린 플롯
   - 통계 검정 결과표 (p-value, Cohen's d, 95% CI)
5. **종합 비교**:
   - 히트맵: 시나리오 × 메트릭 × 아키텍처
   - 레이더 차트: 다차원 성능 비교
6. **정책 제언**:
   - Kill Web 도입 시 기대 효과 정량화
   - 시나리오별 최적 아키텍처 권장
   - 한계점 및 향후 연구 과제

### 시각화 계획

| 차트 유형 | 내용 | 라이브러리 |
|-----------|------|------------|
| 박스플롯 | 300회 메트릭 분포 비교 | seaborn |
| 바이올린 플롯 | 분포 형태 비교 | seaborn |
| 히트맵 | 시나리오 × 메트릭 효과 크기 | matplotlib/seaborn |
| 레이더 차트 | 다차원 성능 종합 비교 | matplotlib |
| 수렴 곡선 | 누적 평균 안정성 | matplotlib |
| 포레스트 플롯 | 시나리오별 효과 크기 + CI | matplotlib |

---

## 작업 4: 인터랙티브 시각화 (선택)

### 목표
- plotly/dash 기반 웹 대시보드
- 시나리오, 아키텍처, 메트릭 필터링
- 개별 시뮬레이션 drill-down

### 우선순위
- v0.6의 핵심 목표는 **통계 분석 보고서**이므로 인터랙티브 시각화는 **선택 사항**
- 시간 여유 시 구현, 아니면 v0.7로 연기

---

## 작업 5: 테스트 추가

### 신규 테스트 (예상)

#### `tests/test_stats.py` (8~10개)
```python
class TestMonteCarloAnalyzer:
    def test_compare_architectures_returns_all_fields(self):
    def test_cohens_d_interpretation(self):
    def test_full_analysis_covers_all_scenarios(self):
    def test_convergence_analysis(self):

class TestBatchExperiment:
    def test_single_scenario_batch_runs(self):
    def test_results_dataframe_structure(self):
    def test_reproducibility_with_same_seeds(self):
```

### 테스트 목표: 기존 86개 + 신규 ~10개 = **~96개**

---

## 리스크 및 완화 전략

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 4,200회 배치 실행 시간 | 직렬 35분+ | multiprocessing 병렬화, 중간 저장 |
| 메모리 사용량 | DataFrame 대형화 | record_snapshots=False, 청크 처리 |
| 비정규 분포 메트릭 | 모수 검정 부적절 | Mann-Whitney U 비모수 검정 병행 |
| 다중 비교 문제 | 유형 I 오류 증가 | Bonferroni 보정, FDR 적용 |
| 시뮬레이션 재현성 | 시드 관리 실수 | 시드 0~299 고정, CSV 원시 데이터 보관 |

---

## 검증 체크리스트

- [ ] 작업 1 후: S1 × 2 아키텍처 × 10회 파일럿 배치 정상 완료
- [ ] 작업 1 후: CSV 저장/로드 정상 확인
- [ ] 작업 1 후: 수렴 분석 그래프 생성
- [ ] 작업 2 후: `MonteCarloAnalyzer.compare_architectures()` 정상 동작
- [ ] 작업 2 후: Cohen's d, 95% CI, p-value 계산 검증
- [ ] 작업 3 후: 전 시나리오 보고서 시각화 정상 렌더링
- [ ] 작업 5 후: `python -m pytest tests/ -v` → ~96개 PASS
- [ ] 최종: 4,200회 전체 배치 실행 완료 + 결과 보고서 생성

---

## v0.5 완료 기록

> 작업 완료일: 2026-03-12
> 테스트: 86개 전부 PASS (9개 파일)

### 완료된 작업 (v0.5)
1. COP 품질 차별화 ✅ — 센서 융합 √N 오차, 아군 상태 공유, 교전 계획 공유
2. 적응형 교전 정책 ✅ — 탄약 30%/10% 임계치 기반 자동 전환
3. 통신 네트워크 동적 열화 ✅ — 링크별 차등 재밍, 메시 다중경로 완화
4. 2D 전술 시각화 모듈 ✅ — TacticalVisualizer (렌더/애니메이션/비교/타임라인)
5. 시각화 노트북 ✅ — notebook5 (전술 애니메이션 + 아키텍처 비교)
6. 테스트 확장 ✅ — 57개 → 86개 (COP 11개, 적응형 13개, 시각화 5개)
7. 문서 업데이트 ✅ — CHANGELOG, CLAUDE.md, README 갱신

### 성능 기준선 (v0.5, seed=42)
- Kill Web 전 시나리오 평균 누출률: **20.2%** (vs Linear 32.3%)
- Kill Web S2S: **5~25초** (vs Linear 114~589초)
- Kill Web S3 EW Heavy 누출률: **21.1%** (vs Linear 39.5%)

---

## v0.4 완료 기록

> 작업 완료일: 2026-03-11
> 테스트: 57개 전부 PASS

### 완료된 작업 (v0.4)
1. jamming_level 오버라이드 정리 ✅
2. comms.py 죽은 코드 삭제 ✅
3. config.py 죽은 설정 삭제 ✅
4. 다중 교전 모델링 ✅ (SRBM=3, CM=2)
5. 메트릭 확장 12개 ✅
6. 테스트 확장 57개 ✅
7. 노트북 업데이트 ✅
