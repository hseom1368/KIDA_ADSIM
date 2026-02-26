"""
threats.py - 위협 생성기
Threat generator: wave patterns, Poisson arrival, multi-axis approach.
"""

import math
import random
import numpy as np

from .config import THREAT_PARAMS, SCENARIO_PARAMS, DEFAULT_DEPLOYMENT


def generate_threats_for_scenario(scenario_name, model, seed=None):
    """
    시나리오별 위협 에이전트 목록 생성.

    Args:
        scenario_name: 시나리오 키 (e.g., 'scenario_1_saturation')
        model: Mesa Model 인스턴스
        seed: 난수 시드

    Returns:
        list of (threat_type, pos, target_pos, launch_time) 튜플
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    scenario = SCENARIO_PARAMS[scenario_name]
    defense_target = DEFAULT_DEPLOYMENT["defense_target"]
    approach_azimuth = scenario.get("approach_azimuth", (240, 360))
    approach_distance = scenario.get("approach_distance", 200)

    threat_specs = []

    if scenario_name == "scenario_4_sequential":
        # 포아송 도착 패턴
        threat_specs = _generate_poisson_threats(
            scenario, defense_target, approach_azimuth, approach_distance
        )
    else:
        # 파상 공격 패턴
        waves = scenario.get("waves", [])
        for wave in waves:
            t = wave["time"]
            for threat_type, count in wave["threats"].items():
                for _ in range(count):
                    pos = _random_approach_position(
                        defense_target, approach_azimuth, approach_distance
                    )
                    threat_specs.append((threat_type, pos, defense_target, t))

    return threat_specs


def _generate_poisson_threats(scenario, defense_target, approach_azimuth,
                              approach_distance):
    """포아송 도착 패턴 위협 생성"""
    lam = scenario["poisson_lambda"]
    duration = scenario["duration"]
    threat_mix = scenario["threat_mix"]

    threat_specs = []
    t = 0
    while t < duration:
        inter_arrival = np.random.exponential(1.0 / lam)
        t += inter_arrival
        if t >= duration:
            break

        # 위협 유형 확률적 선택
        threat_type = np.random.choice(
            list(threat_mix.keys()),
            p=list(threat_mix.values()),
        )
        pos = _random_approach_position(
            defense_target, approach_azimuth, approach_distance
        )
        threat_specs.append((threat_type, pos, defense_target, t))

    return threat_specs


def _random_approach_position(defense_target, azimuth_range, distance):
    """
    방어 목표 기준으로 접근 방향에서 랜덤 위치 생성.

    Args:
        defense_target: (x, y) 방어 목표
        azimuth_range: (min_deg, max_deg) 접근 방위각 범위
        distance: 접근 거리 (km)

    Returns:
        (x, y) 위협 시작 위치
    """
    az_min, az_max = azimuth_range
    azimuth = random.uniform(az_min, az_max)
    azimuth_rad = math.radians(azimuth)

    # 약간의 거리 변동
    dist = distance + random.uniform(-20, 20)

    x = defense_target[0] + dist * math.sin(azimuth_rad)
    y = defense_target[1] + dist * math.cos(azimuth_rad)

    return (x, y)


def get_scenario_node_destructions(scenario_name, architecture):
    """시나리오별 노드 파괴 스케줄 반환"""
    scenario = SCENARIO_PARAMS.get(scenario_name, {})

    if architecture == "linear":
        return scenario.get("node_destruction_linear", [])
    else:
        return scenario.get("node_destruction_killweb", [])
