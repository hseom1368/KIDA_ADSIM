"""tests/test_stats.py - 통계 분석 모듈 테스트"""

import numpy as np
import pandas as pd
import pytest

from modules.stats import (
    normality_test,
    cohens_d,
    confidence_interval,
    compare_groups,
    bonferroni_correct,
    full_comparison,
)


class TestNormalityTest:
    """정규성 검정 테스트"""

    def test_normal_data(self):
        """정규 분포 데이터 → is_normal=True"""
        np.random.seed(42)
        data = np.random.normal(50, 5, 100)
        result = normality_test(data)
        assert result["is_normal"] is True
        assert result["p_value"] > 0.05

    def test_skewed_data(self):
        """비정규 분포 데이터 → is_normal=False"""
        np.random.seed(42)
        data = np.random.exponential(2, 100)
        result = normality_test(data)
        assert result["is_normal"] is False

    def test_large_sample_skips(self):
        """n>5000이면 검정 skip"""
        data = np.ones(6000)
        result = normality_test(data)
        assert result["p_value"] == 0.0
        assert result["is_normal"] is False

    def test_insufficient_data(self):
        """n<3이면 검정 불가"""
        result = normality_test([1.0, 2.0])
        assert result["is_normal"] is False
        assert result["statistic"] is None


class TestCohensD:
    """Cohen's d 효과 크기 테스트"""

    def test_known_value(self):
        """mean 차이=1, std=1 → d ≈ 1.0"""
        g1 = np.random.normal(1, 1, 1000)
        g2 = np.random.normal(0, 1, 1000)
        np.random.seed(42)
        g1 = np.random.normal(1, 1, 10000)
        g2 = np.random.normal(0, 1, 10000)
        d = cohens_d(g1, g2)
        assert abs(d - 1.0) < 0.1  # 대략 1.0

    def test_identical_groups(self):
        """동일 그룹 → d = 0"""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        d = cohens_d(data, data)
        assert d == 0.0

    def test_handles_inf_nan(self):
        """inf, nan 값 제거 후 계산"""
        g1 = [1.0, 2.0, np.nan, 3.0]
        g2 = [4.0, 5.0, np.inf, 6.0]
        d = cohens_d(g1, g2)
        assert np.isfinite(d)


class TestConfidenceInterval:
    """신뢰구간 테스트"""

    def test_contains_mean(self):
        """95% CI가 표본 평균을 포함"""
        np.random.seed(42)
        data = np.random.normal(50, 5, 100)
        lo, hi = confidence_interval(data)
        mean = np.mean(data)
        assert lo <= mean <= hi

    def test_wider_with_variance(self):
        """분산이 클수록 CI 넓음"""
        np.random.seed(42)
        narrow = np.random.normal(50, 1, 100)
        wide = np.random.normal(50, 10, 100)
        ci_narrow = confidence_interval(narrow)
        ci_wide = confidence_interval(wide)
        assert (ci_narrow[1] - ci_narrow[0]) < (ci_wide[1] - ci_wide[0])


class TestCompareGroups:
    """그룹 비교 테스트"""

    def test_selects_ttest_for_normal(self):
        """양쪽 정규 분포 → Welch's t-test"""
        np.random.seed(42)
        g1 = np.random.normal(50, 5, 100)
        g2 = np.random.normal(52, 5, 100)
        result = compare_groups(g1, g2, "test_metric")
        assert result["test_used"] == "welch_t"
        assert result["metric"] == "test_metric"
        assert result["p_value"] is not None

    def test_selects_mannwhitney_for_nonnormal(self):
        """비정규 분포 → Mann-Whitney U"""
        np.random.seed(42)
        g1 = np.random.exponential(2, 100)
        g2 = np.random.exponential(4, 100)
        result = compare_groups(g1, g2, "test_metric")
        assert result["test_used"] == "mann_whitney_u"


class TestBonferroni:
    """Bonferroni 보정 테스트"""

    def test_correction(self):
        """p-value가 n_tests배로 보정"""
        p_values = [0.01, 0.03, 0.05]
        results = bonferroni_correct(p_values, alpha=0.05)
        assert len(results) == 3
        assert results[0]["adjusted_p"] == pytest.approx(0.03, abs=1e-10)
        assert results[1]["adjusted_p"] == pytest.approx(0.09, abs=1e-10)
        assert results[2]["adjusted_p"] == pytest.approx(0.15, abs=1e-10)
        # 보정 후: 0.01*3=0.03 < 0.05 → significant
        assert results[0]["significant"] is True
        assert results[1]["significant"] is False

    def test_caps_at_one(self):
        """보정된 p-value는 1.0을 초과하지 않음"""
        results = bonferroni_correct([0.8, 0.9])
        assert all(r["adjusted_p"] <= 1.0 for r in results)


class TestFullComparison:
    """full_comparison 통합 테스트"""

    def test_output_schema(self):
        """출력 DataFrame 스키마 검증"""
        np.random.seed(42)
        rows = []
        for scenario in ["s1", "s2"]:
            for arch in ["linear", "killweb"]:
                for _ in range(30):
                    rows.append({
                        "scenario": scenario,
                        "architecture": arch,
                        "leaker_rate": np.random.normal(30, 5),
                        "engagement_success_rate": np.random.normal(40, 3),
                    })
        df = pd.DataFrame(rows)
        report = full_comparison(df, metrics=["leaker_rate", "engagement_success_rate"])

        assert isinstance(report, pd.DataFrame)
        assert len(report) == 4  # 2 시나리오 × 2 메트릭
        required_cols = [
            "scenario", "metric", "test_used", "p_value",
            "cohens_d", "significance", "mean_linear", "mean_killweb",
        ]
        for col in required_cols:
            assert col in report.columns, f"Missing column: {col}"
