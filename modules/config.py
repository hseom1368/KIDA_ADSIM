"""
config.py - 한국군 방공체계 시뮬레이션 파라미터 설정
Parameters and configuration for K-ADS simulation.
"""

import math

# =============================================================================
# 1. 시뮬레이션 기본 설정
# =============================================================================
SIM_CONFIG = {
    "time_resolution": 5,       # 초 단위 (5초 스텝)
    "area_size": 200,           # km (200x200km 전장 공간)
    "max_sim_time": 1800,       # 초 (최대 시뮬레이션 시간: 30분)
    "random_seed": 42,
}

# =============================================================================
# 1-1. 교전 정책 (Engagement Policy)
# =============================================================================
ENGAGEMENT_POLICY = {
    # 최적 교전 Pk 임계값: 이 Pk 이상이면 교전 개시
    "optimal_pk_threshold": 0.30,
    # 긴급 교전 Pk 임계값: 잔여 교전 기회 ≤ N회이면 이 임계값 사용
    "emergency_pk_threshold": 0.10,
    # 잔여 교전 기회 기준: 방어지역까지 잔여 비행시간 / 교전 시간
    "emergency_opportunity_count": 2,
    # 방어지역 근접 거리(km): 이 이내면 무조건 교전
    "must_engage_distance": 30.0,
}

# =============================================================================
# 2. 센서 파라미터
# =============================================================================
SENSOR_PARAMS = {
    "EWR": {
        "sensor_type": "EWR",
        "detection_range": 500,     # km
        "tracking_capacity": 100,
        "scan_rate": 1.0,           # 초당 스캔
        "label": "EWR (그린파인급)",
    },
    "PATRIOT_RADAR": {
        "sensor_type": "PATRIOT_RADAR",
        "detection_range": 170,     # km (TBM 기준)
        "tracking_capacity": 100,
        "scan_rate": 1.0,
        "label": "PATRIOT Radar (AN/MPQ-65)",
    },
    "MSAM_MFR": {
        "sensor_type": "MSAM_MFR",
        "detection_range": 100,     # km
        "tracking_capacity": 50,
        "scan_rate": 1.0,
        "label": "M-SAM MFR (천궁)",
    },
    "SHORAD_RADAR": {
        "sensor_type": "SHORAD_RADAR",
        "detection_range": 17,      # km
        "tracking_capacity": 10,
        "scan_rate": 2.0,
        "label": "SHORAD Radar (TPS-830K)",
    },
}

# =============================================================================
# 3. C2 노드 파라미터
# =============================================================================
C2_PARAMS = {
    "MCRC": {
        "node_type": "MCRC",
        "processing_capacity": 5,
        "auth_delay_linear": (15, 120),     # 초
        "auth_delay_killweb": (2, 5),       # 초
        "label": "MCRC (방공통제소)",
    },
    "BATTALION_TOC": {
        "node_type": "BATTALION_TOC",
        "processing_capacity": 3,
        "auth_delay_linear": (3, 10),
        "auth_delay_killweb": (1, 3),
        "label": "대대 TOC",
    },
    "EOC": {
        "node_type": "EOC",
        "processing_capacity": 5,
        "auth_delay_linear": None,          # 선형 C2에서 사용 안함
        "auth_delay_killweb": (1, 3),
        "label": "EOC (교전작전센터)",
    },
}

# =============================================================================
# 4. 사격체 파라미터
# =============================================================================
SHOOTER_PARAMS = {
    "PATRIOT_PAC3": {
        "weapon_type": "PATRIOT_PAC3",
        "max_range": 120,           # km
        "min_range": 3,             # km
        "max_altitude": 30,         # km
        "pk_table": {
            "SRBM": 0.85,
            "CRUISE_MISSILE": 0.80,
            "AIRCRAFT": 0.90,
            "UAS": 0.70,
        },
        "ammo_count": 16,
        "reload_time": 1800,        # 초
        "engagement_time": 5,       # 초
        "label": "PATRIOT PAC-3 MSE",
    },
    "CHEONGUNG2": {
        "weapon_type": "CHEONGUNG2",
        "max_range": 40,
        "min_range": 1,
        "max_altitude": 20,
        "pk_table": {
            "SRBM": 0.75,
            "CRUISE_MISSILE": 0.80,
            "AIRCRAFT": 0.85,
            "UAS": 0.65,
        },
        "ammo_count": 8,
        "reload_time": 1200,
        "engagement_time": 5,
        "label": "천궁-II",
    },
    "BIHO": {
        "weapon_type": "BIHO",
        "max_range": 7,
        "min_range": 0.5,
        "max_altitude": 3,
        "pk_table": {
            "SRBM": 0.0,
            "CRUISE_MISSILE": 0.30,
            "AIRCRAFT": 0.50,
            "UAS": 0.60,
        },
        "ammo_count": 502,          # 500(기관포) + 2(미사일)
        "reload_time": 5,
        "engagement_time": 3,
        "label": "비호 복합",
    },
    "KF16": {
        "weapon_type": "KF16",
        "max_range": 100,
        "min_range": 5,
        "max_altitude": 15,
        "pk_table": {
            "SRBM": 0.0,
            "CRUISE_MISSILE": 0.75,
            "AIRCRAFT": 0.85,
            "UAS": 0.50,
        },
        "ammo_count": 6,
        "reload_time": float("inf"),    # 비행장 복귀 필요
        "engagement_time": 8,
        "label": "KF-16 (CAP)",
    },
}

# =============================================================================
# 5. 위협체 파라미터
# =============================================================================
THREAT_PARAMS = {
    "SRBM": {
        "threat_type": "SRBM",
        "speed": 2.0,               # km/s (Mach 6) — 레거시 기본값
        "altitude": 50.0,           # km (정점 고도) — 레거시 기본값
        "rcs": 0.5,                 # m²
        "maneuvering": True,        # 종말기동 — 레거시 기본값
        "label": "SRBM (KN-23형)",
        "flight_profile": {
            "type": "ballistic",
            "phases": [
                {   # 부스트 단계: 발사 후 급상승·가속
                    "name": "boost",
                    "duration_ratio": 0.15,
                    "altitude_start": 0.0,       # km (지상 발사)
                    "altitude_end": 50.0,        # km (정점)
                    "speed_start": 0.5,          # km/s
                    "speed_end": 2.5,            # km/s (연소 종료)
                    "maneuvering": False,
                },
                {   # 중간 단계: 탄도 비행 (포물선 정점)
                    "name": "midcourse",
                    "duration_ratio": 0.50,
                    "altitude_start": 50.0,
                    "altitude_end": 30.0,        # 하강 시작
                    "speed_start": 2.5,
                    "speed_end": 2.0,
                    "maneuvering": False,
                },
                {   # 종말 단계: 급강하 + 풀업 기동
                    "name": "terminal",
                    "duration_ratio": 0.35,
                    "altitude_start": 30.0,
                    "altitude_end": 0.0,         # 목표 충돌
                    "speed_start": 2.0,
                    "speed_end": 3.0,            # 중력 가속
                    "maneuvering": True,         # KN-23 풀업 기동
                },
            ],
        },
    },
    "CRUISE_MISSILE": {
        "threat_type": "CRUISE_MISSILE",
        "speed": 0.27,              # km/s (Mach 0.8) — 레거시 기본값
        "altitude": 0.03,           # km (30m 해면밀착) — 레거시 기본값
        "rcs": 0.05,                # m²
        "maneuvering": False,       # 레거시 기본값
        "label": "순항미사일 (금성-3형)",
        "flight_profile": {
            "type": "cruise",
            "phases": [
                {   # 부스트/상승 단계
                    "name": "boost",
                    "duration_ratio": 0.05,
                    "altitude_start": 0.0,
                    "altitude_end": 0.5,         # km (500m로 상승)
                    "speed_start": 0.10,
                    "speed_end": 0.27,
                    "maneuvering": False,
                },
                {   # 순항 단계: 해면밀착
                    "name": "cruise",
                    "duration_ratio": 0.85,
                    "altitude_start": 0.03,      # km (30m 해면밀착)
                    "altitude_end": 0.03,
                    "speed_start": 0.27,
                    "speed_end": 0.27,
                    "maneuvering": False,
                },
                {   # 종말 단계: 팝업 후 다이브 또는 저고도 유지
                    "name": "terminal",
                    "duration_ratio": 0.10,
                    "altitude_start": 0.03,
                    "altitude_end": 0.0,         # 목표 충돌
                    "speed_start": 0.27,
                    "speed_end": 0.30,           # 약간 가속
                    "maneuvering": True,         # 종말 회피기동
                },
            ],
        },
    },
    "AIRCRAFT": {
        "threat_type": "AIRCRAFT",
        "speed": 0.34,              # km/s (Mach 1.0) — 레거시 기본값
        "altitude": 10.0,           # km — 레거시 기본값
        "rcs": 5.0,                 # m²
        "maneuvering": False,       # 레거시 기본값
        "label": "고정익 항공기",
        "flight_profile": {
            "type": "aircraft",
            "phases": [
                {   # 순항 접근
                    "name": "ingress_high",
                    "duration_ratio": 0.60,
                    "altitude_start": 10.0,
                    "altitude_end": 10.0,
                    "speed_start": 0.34,
                    "speed_end": 0.34,
                    "maneuvering": False,
                },
                {   # 방공망 접근 시 저고도 침투
                    "name": "ingress_low",
                    "duration_ratio": 0.30,
                    "altitude_start": 10.0,
                    "altitude_end": 1.0,         # 1km으로 강하
                    "speed_start": 0.34,
                    "speed_end": 0.30,           # 저고도 감속
                    "maneuvering": True,         # 회피기동
                },
                {   # 공격 진입
                    "name": "attack_run",
                    "duration_ratio": 0.10,
                    "altitude_start": 1.0,
                    "altitude_end": 0.5,
                    "speed_start": 0.30,
                    "speed_end": 0.34,
                    "maneuvering": True,
                },
            ],
        },
    },
    "UAS": {
        "threat_type": "UAS",
        "speed": 0.05,              # km/s (~180km/h) — 레거시 기본값
        "altitude": 0.3,            # km (300m) — 레거시 기본값
        "rcs": 0.005,               # m²
        "maneuvering": False,       # 레거시 기본값
        "label": "UAS 군집",
        "flight_profile": {
            "type": "uas",
            "phases": [
                {   # 접근 단계
                    "name": "approach",
                    "duration_ratio": 0.80,
                    "altitude_start": 0.3,
                    "altitude_end": 0.3,
                    "speed_start": 0.05,
                    "speed_end": 0.05,
                    "maneuvering": False,
                },
                {   # 종말 강하 (목표 근접 시 고도 낮춤)
                    "name": "terminal",
                    "duration_ratio": 0.20,
                    "altitude_start": 0.3,
                    "altitude_end": 0.05,        # 50m로 강하
                    "speed_start": 0.05,
                    "speed_end": 0.07,           # 최종 돌입 가속
                    "maneuvering": True,
                },
            ],
        },
    },
}

# =============================================================================
# 6. 통신 링크 파라미터
# =============================================================================
COMM_PARAMS = {
    "linear": {
        "sensor_to_c2_delay": (5, 15),      # 초
        "c2_processing_delay": (10, 30),     # 초
        "c2_to_shooter_delay": (5, 15),      # 초
        "auth_delay": (15, 120),             # 초
        "bandwidth_kbps": 50,
        "jamming_resistance": 0.75,          # 60-85% → 평균
        "label": "선형 C2 통신",
    },
    "killweb": {
        "sensor_to_c2_delay": (1, 2),        # 초
        "c2_processing_delay": (1, 3),       # 초
        "c2_to_shooter_delay": (1, 2),       # 초
        "auth_delay": (0, 5),                # 초 (자동화)
        "bandwidth_kbps": 1000,
        "jamming_resistance": 0.90,          # 85-95% → 평균
        "label": "Kill Web 통신",
    },
}

# =============================================================================
# 7. 시나리오 파라미터 (시나리오 1 & 5 우선 구현)
# =============================================================================
SCENARIO_PARAMS = {
    "scenario_1_saturation": {
        "name": "포화공격",
        "description": "20-40 위협, 2-3 파상 공격",
        "waves": [
            {"time": 0, "threats": {"SRBM": 10, "CRUISE_MISSILE": 5}},
            {"time": 60, "threats": {"SRBM": 5, "UAS": 10}},
            {"time": 120, "threats": {"CRUISE_MISSILE": 5, "UAS": 10}},
        ],
        "approach_azimuth": (240, 360),     # 북쪽 120도 부채꼴
        "approach_distance": 200,            # km
        "jamming_level": 0.0,
        "node_destruction": [],
    },
    "scenario_2_complex": {
        "name": "복합위협",
        "description": "SRBM+CM+항공기+UAS 혼합, 다축선 동시",
        "waves": [
            {"time": 0, "threats": {"SRBM": 10, "CRUISE_MISSILE": 5,
                                     "AIRCRAFT": 3, "UAS": 20}},
        ],
        "approach_azimuth": (240, 360),
        "approach_distance": 200,
        "jamming_level": 0.0,
        "node_destruction": [],
    },
    "scenario_3_ew": {
        "name": "전자전 환경",
        "description": "재밍 3단계 (light/moderate/heavy)",
        "waves": [
            {"time": 0, "threats": {"SRBM": 10, "CRUISE_MISSILE": 5,
                                     "AIRCRAFT": 3, "UAS": 20}},
        ],
        "approach_azimuth": (240, 360),
        "approach_distance": 200,
        "jamming_levels": {
            "light": {"detection_factor": 0.8, "latency_factor": 1.5},
            "moderate": {"detection_factor": 0.5, "latency_factor": 3.0},
            "heavy": {"detection_factor": 0.2, "latency_factor": 5.0},
        },
        "jamming_level": 0.5,      # 기본 moderate
        "node_destruction": [],
    },
    "scenario_4_sequential": {
        "name": "순차교전 (지속작전)",
        "description": "Poisson 도착, 60분간 ~60 위협",
        "poisson_lambda": 1 / 60,   # 평균 60초마다 1기
        "duration": 3600,            # 60분
        "threat_mix": {"SRBM": 0.30, "CRUISE_MISSILE": 0.25,
                       "AIRCRAFT": 0.15, "UAS": 0.30},
        "approach_azimuth": (240, 360),
        "approach_distance": 200,
        "jamming_level": 0.0,
        "node_destruction": [],
    },
    "scenario_5_node_destruction": {
        "name": "노드 파괴",
        "description": "시나리오 1 기반 + C2 노드 순차 제거",
        "waves": [
            {"time": 0, "threats": {"SRBM": 10, "CRUISE_MISSILE": 5}},
            {"time": 60, "threats": {"SRBM": 5, "UAS": 10}},
            {"time": 120, "threats": {"CRUISE_MISSILE": 5, "UAS": 10}},
        ],
        "approach_azimuth": (240, 360),
        "approach_distance": 200,
        "jamming_level": 0.0,
        "node_destruction_linear": [
            {"time": 30, "target": "MCRC"},
            {"time": 60, "target": "TOC_PAT"},
            {"time": 90, "target": "TOC_MSAM"},
        ],
        "node_destruction_killweb": [
            {"time": 30, "target": "EOC_1"},
            {"time": 60, "target": "EOC_2"},
            {"time": 90, "target": "EOC_3"},
        ],
    },
}

# =============================================================================
# 8. 소규모 배치 설정 (기본 에이전트 배치)
# =============================================================================
DEFAULT_DEPLOYMENT = {
    "sensors": [
        {"type": "EWR", "id": "EWR_1", "pos": (100, 170)},
        {"type": "PATRIOT_RADAR", "id": "PAT_RADAR_1", "pos": (80, 130)},
        {"type": "MSAM_MFR", "id": "MFR_1", "pos": (120, 100)},
        {"type": "SHORAD_RADAR", "id": "SH_RADAR_1", "pos": (100, 80)},
    ],
    "c2_nodes": {
        "linear": [
            {"type": "MCRC", "id": "MCRC", "pos": (100, 140)},
            {"type": "BATTALION_TOC", "id": "TOC_PAT", "pos": (80, 120)},
            {"type": "BATTALION_TOC", "id": "TOC_MSAM", "pos": (120, 110)},
        ],
        "killweb": [
            {"type": "MCRC", "id": "MCRC", "pos": (100, 140)},
            {"type": "EOC", "id": "EOC_1", "pos": (90, 130)},
            {"type": "EOC", "id": "EOC_2", "pos": (110, 120)},
        ],
    },
    "shooters": [
        {"type": "PATRIOT_PAC3", "id": "PAT_1", "pos": (70, 110)},
        {"type": "PATRIOT_PAC3", "id": "PAT_2", "pos": (130, 110)},
        {"type": "CHEONGUNG2", "id": "MSAM_1", "pos": (90, 90)},
        {"type": "CHEONGUNG2", "id": "MSAM_2", "pos": (110, 90)},
        {"type": "BIHO", "id": "BIHO_1", "pos": (95, 70)},
        {"type": "KF16", "id": "KF16_1", "pos": (100, 60)},
    ],
    "defense_target": (100, 50),    # 방어 대상 위치 (도심/기지)
}

# =============================================================================
# 9. 실험 설정
# =============================================================================
EXPERIMENT_CONFIG = {
    "monte_carlo_runs": 300,
    "pilot_runs": 10,
    "architectures": ["linear", "killweb"],
    "scenarios": ["scenario_1_saturation", "scenario_5_node_destruction"],
    "checkpoint_interval": 50,      # 50회마다 중간 저장
}
