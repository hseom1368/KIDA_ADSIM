"""
stats.py - 통계 분석 모듈
Statistical analysis utilities for architecture comparison.
"""

import numpy as np
import pandas as pd
from scipy import stats as sp_stats


def normality_test(data, alpha=0.05):
    """Shapiro-Wilk 정규성 검정

    Args:
        data: array-like, 검정할 데이터
        alpha: 유의수준 (기본 0.05)

    Returns:
        dict with {statistic, p_value, is_normal}
    """
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data) & ~np.isinf(data)]

    if len(data) < 3:
        return {"statistic": None, "p_value": None, "is_normal": False}

    # Shapiro-Wilk은 n>5000에서 부정확 → skip
    if len(data) > 5000:
        return {"statistic": None, "p_value": 0.0, "is_normal": False}

    stat, p = sp_stats.shapiro(data)
    return {"statistic": float(stat), "p_value": float(p), "is_normal": bool(p > alpha)}


def cohens_d(group1, group2):
    """Cohen's d 효과 크기

    Args:
        group1, group2: array-like

    Returns:
        float: Cohen's d (양수 = group1 > group2)
    """
    g1 = np.asarray(group1, dtype=float)
    g2 = np.asarray(group2, dtype=float)
    g1 = g1[~np.isnan(g1) & ~np.isinf(g1)]
    g2 = g2[~np.isnan(g2) & ~np.isinf(g2)]

    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2:
        return 0.0

    pooled_std = np.sqrt(
        ((n1 - 1) * g1.var(ddof=1) + (n2 - 1) * g2.var(ddof=1)) / (n1 + n2 - 2)
    )
    if pooled_std == 0:
        return 0.0
    return float((g1.mean() - g2.mean()) / pooled_std)


def confidence_interval(data, confidence=0.95):
    """평균의 신뢰구간 (t-분포 기반)

    Args:
        data: array-like
        confidence: 신뢰수준 (기본 0.95)

    Returns:
        (lower, upper) tuple
    """
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data) & ~np.isinf(data)]

    if len(data) < 2:
        mean = data[0] if len(data) == 1 else 0.0
        return (mean, mean)

    mean = np.mean(data)
    se = sp_stats.sem(data)
    h = se * sp_stats.t.ppf((1 + confidence) / 2, len(data) - 1)
    return (float(mean - h), float(mean + h))


def compare_groups(group1, group2, metric_name=""):
    """두 그룹 비교: 정규성에 따라 t-test 또는 Mann-Whitney U 자동 선택

    Args:
        group1: array-like (예: linear 결과)
        group2: array-like (예: killweb 결과)
        metric_name: 메트릭 이름 (출력용)

    Returns:
        dict with {metric, test_used, statistic, p_value, cohens_d,
                   ci_lower, ci_upper, significance,
                   mean_group1, mean_group2}
    """
    g1 = np.asarray(group1, dtype=float)
    g2 = np.asarray(group2, dtype=float)
    g1 = g1[~np.isnan(g1) & ~np.isinf(g1)]
    g2 = g2[~np.isnan(g2) & ~np.isinf(g2)]

    if len(g1) < 2 or len(g2) < 2:
        return {
            "metric": metric_name,
            "test_used": "none",
            "statistic": None,
            "p_value": None,
            "cohens_d": 0.0,
            "ci_lower": None,
            "ci_upper": None,
            "significance": "ns",
            "mean_group1": float(g1.mean()) if len(g1) > 0 else None,
            "mean_group2": float(g2.mean()) if len(g2) > 0 else None,
        }

    # 정규성 검정
    norm1 = normality_test(g1)
    norm2 = normality_test(g2)
    both_normal = norm1["is_normal"] and norm2["is_normal"]

    # 검정 수행
    if both_normal:
        stat, p = sp_stats.ttest_ind(g1, g2)
        test_used = "welch_t"
    else:
        stat, p = sp_stats.mannwhitneyu(g1, g2, alternative="two-sided")
        test_used = "mann_whitney_u"

    # 효과 크기 및 신뢰구간
    d = cohens_d(g1, g2)
    diff = g1 - g2.mean()  # 차이의 CI 대신 group1의 CI 사용
    ci_lo, ci_hi = confidence_interval(g1)

    # 유의성 표기
    sig = _significance_label(p)

    return {
        "metric": metric_name,
        "test_used": test_used,
        "statistic": float(stat),
        "p_value": float(p),
        "cohens_d": d,
        "ci_lower": ci_lo,
        "ci_upper": ci_hi,
        "significance": sig,
        "mean_group1": float(g1.mean()),
        "mean_group2": float(g2.mean()),
    }


def bonferroni_correct(p_values, alpha=0.05):
    """Bonferroni 다중비교 보정

    Args:
        p_values: list of p-values
        alpha: 원래 유의수준

    Returns:
        list of dicts with {original_p, adjusted_p, significant}
    """
    n = len(p_values)
    if n == 0:
        return []

    results = []
    for p in p_values:
        if p is None:
            results.append(
                {"original_p": None, "adjusted_p": None, "significant": False}
            )
        else:
            adj = min(p * n, 1.0)
            results.append(
                {
                    "original_p": float(p),
                    "adjusted_p": float(adj),
                    "significant": adj < alpha,
                }
            )
    return results


def full_comparison(df, metrics=None, scenarios=None):
    """전체 비교 보고서: 모든 시나리오 × 메트릭에 대해 통계 검정

    Args:
        df: 실험 결과 DataFrame (architecture, scenario 컬럼 필수)
        metrics: 비교할 메트릭 목록 (기본: 핵심 6개)
        scenarios: 시나리오 목록 (기본: df에 있는 전체)

    Returns:
        pd.DataFrame with columns:
            scenario, metric, test_used, statistic, p_value, p_adjusted,
            cohens_d, ci_lower, ci_upper, significance,
            mean_linear, mean_killweb
    """
    if metrics is None:
        metrics = [
            "leaker_rate",
            "engagement_success_rate",
            "sensor_to_shooter_time_mean",
            "ammo_efficiency",
            "c2_throughput",
            "multi_engagement_rate",
        ]

    if scenarios is None:
        scenarios = sorted(df["scenario"].unique())

    # 사용 가능한 메트릭만 필터링
    available_metrics = [m for m in metrics if m in df.columns]

    rows = []
    for scenario in scenarios:
        for metric in available_metrics:
            linear = df[
                (df["scenario"] == scenario) & (df["architecture"] == "linear")
            ][metric]
            killweb = df[
                (df["scenario"] == scenario) & (df["architecture"] == "killweb")
            ][metric]

            result = compare_groups(
                linear.values, killweb.values, metric_name=metric
            )
            result["scenario"] = scenario
            result["mean_linear"] = result.pop("mean_group1")
            result["mean_killweb"] = result.pop("mean_group2")
            rows.append(result)

    report = pd.DataFrame(rows)

    # Bonferroni 보정
    if not report.empty:
        p_values = report["p_value"].tolist()
        corrections = bonferroni_correct(p_values)
        report["p_adjusted"] = [c["adjusted_p"] for c in corrections]
        report["sig_adjusted"] = [
            _significance_label(c["adjusted_p"]) if c["adjusted_p"] is not None else "ns"
            for c in corrections
        ]

    # 컬럼 순서 정리
    col_order = [
        "scenario", "metric", "test_used", "statistic", "p_value", "p_adjusted",
        "cohens_d", "ci_lower", "ci_upper", "significance", "sig_adjusted",
        "mean_linear", "mean_killweb",
    ]
    existing_cols = [c for c in col_order if c in report.columns]
    return report[existing_cols]


def _significance_label(p):
    """p-value를 유의성 라벨로 변환"""
    if p is None:
        return "ns"
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"
