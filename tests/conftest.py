"""공유 테스트 fixture 및 상수"""

import pytest
from modules.model import AirDefenseModel
from modules.config import SCENARIO_PARAMS

# 실험 대상 시나리오 (EXPERIMENT_CONFIG 기준)
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


@pytest.fixture
def linear_model_s1():
    """시나리오 1, linear 아키텍처, seed=42"""
    return AirDefenseModel(architecture="linear", scenario="scenario_1_saturation", seed=42)


@pytest.fixture
def killweb_model_s1():
    """시나리오 1, killweb 아키텍처, seed=42"""
    return AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation", seed=42)
