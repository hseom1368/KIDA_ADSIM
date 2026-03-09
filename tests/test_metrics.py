"""test_metrics.py - 메트릭 정확성 테스트"""

import pytest
from modules.model import AirDefenseModel
from modules.metrics import MetricsCollector


class TestDefenseCoverage:
    """defense_coverage 메트릭 테스트"""

    def test_coverage_nonzero_after_run(self):
        """시뮬레이션 실행 후 defense_coverage > 0"""
        model = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
        result = model.run_full()
        assert result["metrics"]["defense_coverage"] > 0, "defense_coverage가 0보다 커야 함"

    def test_coverage_zero_with_no_shooters(self):
        """shooters 없으면 coverage == 0"""
        mc = MetricsCollector()
        assert mc.metric_9_defense_coverage(shooters=[]) == 0.0
        assert mc.metric_9_defense_coverage(shooters=None) == 0.0


class TestMetricBounds:
    """메트릭 경계값 테스트"""

    def test_leaker_rate_bounds(self):
        """0 <= leaker_rate <= 100"""
        model = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
        result = model.run_full()
        lr = result["metrics"]["leaker_rate"]
        assert 0 <= lr <= 100, f"leaker_rate={lr} 범위 초과"

    def test_s2s_time_nonnegative(self):
        """S2S 시간 >= 0"""
        model = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
        result = model.run_full()
        s2s = result["metrics"]["sensor_to_shooter_time"]
        if s2s["values"]:
            assert all(v >= 0 for v in s2s["values"]), "S2S 시간이 음수"
