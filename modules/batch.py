"""
batch.py - Monte Carlo 배치 실험 실행기
Parallel batch runner for air defense simulation experiments.
"""

import os
import time
import logging
from multiprocessing import Pool, cpu_count

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

from .config import EXPERIMENT_CONFIG

logger = logging.getLogger(__name__)


def run_single(args):
    """단일 시뮬레이션 실행 (multiprocessing worker용)

    Args:
        args: (architecture, scenario, seed) tuple

    Returns:
        dict with metrics_flat + metadata, or None on failure
    """
    architecture, scenario, seed = args
    try:
        # worker 프로세스 내에서 import (pickle 호환)
        from .model import AirDefenseModel

        model = AirDefenseModel(
            architecture=architecture,
            scenario=scenario,
            seed=seed,
            record_snapshots=False,
        )
        result = model.run_full()
        flat = result["metrics_flat"]
        flat["architecture"] = architecture
        flat["scenario"] = scenario
        flat["seed"] = seed
        flat["sim_time"] = result["sim_time"]
        flat["total_steps"] = result["total_steps"]
        return flat
    except Exception as e:
        logger.warning(f"Run failed: {architecture}/{scenario}/seed={seed}: {e}")
        return None


class BatchRunner:
    """Monte Carlo 배치 실험 실행기

    EXPERIMENT_CONFIG 기반으로 전체 실험을 병렬 실행하고 CSV로 저장한다.
    """

    def __init__(self, config=None, results_dir="results"):
        self.config = config or EXPERIMENT_CONFIG
        self.results_dir = results_dir
        os.makedirs(self.results_dir, exist_ok=True)

    def _build_run_args(self, n_runs=None, scenarios=None, architectures=None):
        """실행 인자 목록 생성"""
        n = n_runs or self.config["monte_carlo_runs"]
        scenarios = scenarios or self.config["scenarios"]
        architectures = architectures or self.config["architectures"]

        args_list = []
        for scenario in scenarios:
            for arch in architectures:
                for run_idx in range(n):
                    seed = run_idx * 7919 + hash(f"{arch}_{scenario}") % 10000
                    args_list.append((arch, scenario, seed))
        return args_list

    def run_pilot(self, n=None):
        """파일럿 실행: 소수 실행으로 시간 추정 + 정상 동작 확인

        Args:
            n: 시나리오×아키텍처당 실행 횟수 (기본: config pilot_runs)

        Returns:
            pd.DataFrame with pilot results
        """
        n = n or self.config.get("pilot_runs", 10)
        args_list = self._build_run_args(n_runs=n)

        start = time.time()
        results = []
        for args in tqdm(args_list, desc="Pilot"):
            result = run_single(args)
            if result is not None:
                results.append(result)

        elapsed = time.time() - start
        df = pd.DataFrame(results)

        # 시간 추정
        total_runs = self._total_runs()
        estimated = elapsed / max(len(args_list), 1) * total_runs
        n_workers = min(cpu_count(), 8)
        estimated_parallel = estimated / n_workers

        logger.info(
            f"Pilot: {len(results)}/{len(args_list)} OK, "
            f"{elapsed:.1f}s elapsed, "
            f"estimated full run: {estimated_parallel:.0f}s "
            f"({n_workers} workers)"
        )
        return df

    def run_all(self, n_workers=None, n_runs=None):
        """전체 배치 실행 (multiprocessing 병렬화)

        Args:
            n_workers: 병렬 워커 수 (기본: cpu_count, 최대 8)
            n_runs: 시나리오×아키텍처당 실행 수 (기본: config monte_carlo_runs)

        Returns:
            pd.DataFrame with all results
        """
        n_workers = n_workers or min(cpu_count(), 8)
        args_list = self._build_run_args(n_runs=n_runs)
        checkpoint_interval = self.config.get("checkpoint_interval", 50)
        checkpoint_file = os.path.join(self.results_dir, "checkpoint.csv")

        # 기존 체크포인트 로드
        results = []
        start_from = 0
        if os.path.exists(checkpoint_file):
            df_existing = pd.read_csv(checkpoint_file)
            results = df_existing.to_dict("records")
            start_from = len(results)
            logger.info(f"Checkpoint loaded: {start_from} existing results")

        remaining_args = args_list[start_from:]
        if not remaining_args:
            return pd.DataFrame(results)

        start = time.time()
        pbar = tqdm(total=len(args_list), initial=start_from, desc="Batch")

        with Pool(processes=n_workers) as pool:
            for result in pool.imap_unordered(run_single, remaining_args):
                if result is not None:
                    results.append(result)
                pbar.update(1)

                # 체크포인팅
                if len(results) % checkpoint_interval == 0:
                    pd.DataFrame(results).to_csv(checkpoint_file, index=False)
                    pbar.set_postfix({"saved": len(results)})

        pbar.close()

        # 최종 저장
        df = pd.DataFrame(results)
        final_file = os.path.join(self.results_dir, "monte_carlo_results.csv")
        df.to_csv(final_file, index=False)

        # 체크포인트 정리
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)

        elapsed = time.time() - start
        logger.info(
            f"Batch complete: {len(results)} results, {elapsed:.1f}s, "
            f"saved → {final_file}"
        )
        return df

    def check_convergence(self, df, metric, threshold=0.01, window=50):
        """수렴성 검사: 누적 평균의 안정성 확인

        Args:
            df: 실험 결과 DataFrame
            metric: 검사할 메트릭 컬럼명
            threshold: 수렴 판정 기준 (마지막 window 구간 변동률)
            window: 수렴 검사 윈도우 크기

        Returns:
            dict with {converged, final_mean, max_variation, cumulative_means}
        """
        values = df[metric].replace([np.inf, -np.inf], np.nan).dropna().values
        if len(values) < window * 2:
            return {
                "converged": False,
                "final_mean": np.mean(values) if len(values) > 0 else None,
                "max_variation": None,
                "cumulative_means": [],
            }

        cumulative_means = np.cumsum(values) / np.arange(1, len(values) + 1)
        tail = cumulative_means[-window:]
        variation = np.abs(np.diff(tail) / tail[:-1])
        max_var = float(np.max(variation))

        return {
            "converged": max_var < threshold,
            "final_mean": float(cumulative_means[-1]),
            "max_variation": max_var,
            "cumulative_means": cumulative_means.tolist(),
        }

    def _total_runs(self):
        """전체 실행 수 계산"""
        return (
            self.config["monte_carlo_runs"]
            * len(self.config["architectures"])
            * len(self.config["scenarios"])
        )
