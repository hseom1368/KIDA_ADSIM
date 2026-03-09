"""test_model.py - 전 시나리오 스모크 테스트 및 시나리오별 검증"""

import pytest
from modules.model import AirDefenseModel

EXPERIMENT_SCENARIOS = [
    "scenario_1_saturation",
    "scenario_2_complex",
    "scenario_3_ew_light",
    "scenario_3_ew_moderate",
    "scenario_3_ew_heavy",
    "scenario_4_sequential",
    "scenario_5_node_destruction",
]
ARCHITECTURES = ["linear", "killweb"]


@pytest.mark.parametrize("scenario", EXPERIMENT_SCENARIOS)
@pytest.mark.parametrize("arch", ARCHITECTURES)
def test_smoke_run(scenario, arch):
    """모든 시나리오×아키텍처 조합이 에러 없이 완료"""
    m = AirDefenseModel(architecture=arch, scenario=scenario, seed=42)
    result = m.run_full()
    assert result["total_steps"] > 0
    assert result["metrics"]["leaker_rate"] >= 0
    assert result["metrics"]["engagement_success_rate"] >= 0
    assert result["metrics"]["defense_coverage"] >= 0


def test_scenario4_runs_past_1800s():
    """시나리오 4: max_sim_time=3600s, 1800s에서 조기 종료 안 됨"""
    m = AirDefenseModel(architecture="killweb", scenario="scenario_4_sequential", seed=42)
    result = m.run_full()
    assert result["sim_time"] > 1800, f"sim_time={result['sim_time']}이 1800s 이하로 조기 종료"


def test_scenario3_jamming_ordering():
    """시나리오 3: 재밍 강도 증가 시 leaker_rate 증가 경향 (멀티 시드 평균)"""
    levels = ["scenario_3_ew_light", "scenario_3_ew_moderate", "scenario_3_ew_heavy"]
    avg_leakers = {}

    for sc in levels:
        total_leaker = 0
        n_seeds = 5
        for seed in range(n_seeds):
            m = AirDefenseModel(architecture="killweb", scenario=sc, seed=seed)
            r = m.run_full()
            total_leaker += r["metrics"]["leaker_rate"]
        avg_leakers[sc] = total_leaker / n_seeds

    # 전반적으로 light <= moderate <= heavy 경향
    assert avg_leakers["scenario_3_ew_light"] <= avg_leakers["scenario_3_ew_heavy"], (
        f"light({avg_leakers['scenario_3_ew_light']:.1f}%) > "
        f"heavy({avg_leakers['scenario_3_ew_heavy']:.1f}%)"
    )


def test_scenario1_reproducibility():
    """시나리오 1: 동일 seed → 동일 결과 (재현성)"""
    results = []
    for _ in range(2):
        m = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
        r = m.run_full()
        results.append(r["metrics"]["leaker_rate"])
    assert results[0] == results[1], "동일 seed에서 결과가 달라짐"
