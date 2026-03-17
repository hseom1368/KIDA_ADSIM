"""tests/test_batch.py - BatchRunner 배치 실행기 테스트"""

import os
import pytest
import pandas as pd

from modules.batch import run_single, BatchRunner


class TestRunSingle:
    """run_single 단위 테스트"""

    def test_returns_valid_dict(self):
        """정상 실행 시 metrics_flat dict 반환"""
        result = run_single(("linear", "scenario_1_saturation", 42))
        assert result is not None
        assert isinstance(result, dict)
        assert result["architecture"] == "linear"
        assert result["scenario"] == "scenario_1_saturation"
        assert result["seed"] == 42
        assert "leaker_rate" in result
        assert "engagement_success_rate" in result

    def test_both_architectures(self):
        """linear, killweb 모두 정상 실행"""
        for arch in ["linear", "killweb"]:
            result = run_single((arch, "scenario_1_saturation", 0))
            assert result is not None
            assert result["architecture"] == arch


class TestBatchRunner:
    """BatchRunner 클래스 테스트"""

    def test_pilot_returns_dataframe(self):
        """파일럿 실행이 DataFrame 반환"""
        runner = BatchRunner(
            config={
                "monte_carlo_runs": 300,
                "pilot_runs": 1,
                "architectures": ["linear", "killweb"],
                "scenarios": ["scenario_1_saturation"],
                "checkpoint_interval": 50,
            }
        )
        df = runner.run_pilot(n=1)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2  # 1 시나리오 × 2 아키텍처 × 1 run
        assert "leaker_rate" in df.columns

    def test_creates_results_dir(self, tmp_path):
        """results 디렉토리 자동 생성"""
        results_dir = str(tmp_path / "new_results")
        runner = BatchRunner(results_dir=results_dir)
        assert os.path.isdir(results_dir)

    def test_convergence_check_stable(self):
        """안정된 데이터에 대해 converged=True"""
        runner = BatchRunner()
        # 안정된 데이터 (평균 50 근처, 소량 노이즈)
        df = pd.DataFrame({"metric": [50 + 0.1 * i % 3 for i in range(200)]})
        result = runner.check_convergence(df, "metric", threshold=0.01)
        assert result["converged"] is True
        assert result["final_mean"] is not None

    def test_convergence_check_insufficient_data(self):
        """데이터 부족 시 converged=False"""
        runner = BatchRunner()
        df = pd.DataFrame({"metric": [1.0, 2.0, 3.0]})
        result = runner.check_convergence(df, "metric")
        assert result["converged"] is False
