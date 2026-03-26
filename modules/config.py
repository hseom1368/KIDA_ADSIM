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
    # 유효 교전 범위: max_range × 이 비율 (경계에서 Pk≈0 방지)
    "effective_range_ratio": 0.95,
    # 재밍 Pk 패널티 계수: Pk × (1 - jamming_level × 이 값)
    "jamming_pk_penalty": 0.3,
    # 센서 추적 위치 오차 (km, 표준편차)
    "tracking_position_error_std": 0.5,
    # 방어 커버리지 중첩 보정 계수
    "coverage_overlap_factor": 0.7,
    # 위협 목표 도달 판정 거리 (km)
    "target_arrival_distance": 1.0,
    # ── 다중 교전 정책 (v0.4) ──
    # 위협 유형별 최대 동시 교전 사수 수
    "max_simultaneous_shooters": {
        "SRBM": 3,
        "CRUISE_MISSILE": 2,
        "AIRCRAFT": 1,
        "UAS": 1,
    },
    # 다중 교전 기본값 (미정의 위협 유형)
    "default_max_simultaneous": 1,
}

# =============================================================================
# 1-2. COP 품질 설정 (v0.5)
# =============================================================================
COP_CONFIG = {
    # 센서 융합 오차 감소 (Kill Web)
    "fusion_error_reduction": True,      # √N 법칙 적용 여부
    "min_fused_error": 0.1,              # 최소 융합 오차 (km)

    # COP 공유 수준
    "linear_cop_level": "threat_only",         # 위협 항적만
    "killweb_cop_level": "full_situational",   # 위협 + 아군 상태 + 대응 계획

    # 아군 상태 공유가 사수 점수에 미치는 보너스
    "friendly_status_bonus": 0.15,

    # 센서 융합에 의한 Pk 보너스 상한 (최대 +10%)
    "fusion_pk_bonus_max": 0.10,
}

# =============================================================================
# 1-3. 적응형 교전 정책 (v0.5)
# =============================================================================
ADAPTIVE_ENGAGEMENT = {
    "ammo_threshold_ratio": 0.3,     # 잔여 탄약 30% 이하 시 정책 전환
    "degraded_max_shooters": 1,      # 절약 모드: 위협당 1기만
    "critical_ammo_ratio": 0.1,      # 10% 이하: 고위협만 교전
    "critical_threat_types": ["SRBM", "CRUISE_MISSILE"],
}

# =============================================================================
# 1-4. 통신 네트워크 동적 열화 (v0.5)
# =============================================================================
COMM_DEGRADATION = {
    "base_latency_factor": 1.0,       # 기본 지연 배수
    "jamming_latency_multiplier": 3.0, # 재밍 시 최대 지연 배수
    "link_failure_threshold": 0.8,     # 재밍 0.8 이상 시 링크 두절
    "killweb_redundancy_factor": 0.5,  # Kill Web 메시 경로 다중화로 열화 완화
}

# =============================================================================
# 2. 센서 파라미터
# =============================================================================
SENSOR_PARAMS = {
    # ── 기존 센서 (무기체계 전용 레이더) ──
    "EWR": {
        "sensor_type": "EWR",
        "detection_range": 500,     # km
        "tracking_capacity": 100,
        "scan_rate": 1.0,           # 초당 스캔
        "role": "weapon_fc",        # v0.7: 기존 호환 기본값
        "label": "EWR (그린파인급)",
    },
    "PATRIOT_RADAR": {
        "sensor_type": "PATRIOT_RADAR",
        "detection_range": 170,     # km (TBM 기준)
        "tracking_capacity": 100,
        "scan_rate": 1.0,
        "role": "weapon_fc",
        "label": "PATRIOT Radar (AN/MPQ-65)",
    },
    "MSAM_MFR": {
        "sensor_type": "MSAM_MFR",
        "detection_range": 100,     # km
        "tracking_capacity": 50,
        "scan_rate": 1.0,
        "role": "weapon_fc",
        "label": "M-SAM MFR (천궁)",
    },
    "SHORAD_RADAR": {
        "sensor_type": "SHORAD_RADAR",
        "detection_range": 17,      # km
        "tracking_capacity": 10,
        "scan_rate": 2.0,
        "role": "weapon_fc",
        "label": "SHORAD Radar (TPS-830K)",
    },
    # ── v0.7 신규 센서 ──
    "GREEN_PINE": {
        "sensor_type": "GREEN_PINE",
        "detection_range": 800,     # km (슈퍼 그린파인)
        "tracking_capacity": 200,
        "scan_rate": 0.1,           # 지속 감시 (비회전)
        "role": "early_warning",    # 교전통제 불가, 큐잉만
        "detectable_types": ["SRBM"],
        "provides_cueing_to": ["KAMD_OPS"],
        "min_detection_altitude": 0,
        "label": "Green Pine/Super Green Pine (BMD EW)",
    },
    "FPS117": {
        "sensor_type": "FPS117",
        "detection_range": 470,     # km
        "tracking_capacity": 100,
        "scan_rate": 0.17,          # 6 RPM
        "role": "surveillance",     # 영공 감시
        "detectable_types": ["AIRCRAFT", "CRUISE_MISSILE"],
        "provides_cueing_to": ["MCRC"],
        "min_detection_altitude": 1.0,  # km (레이더 수평선 제한)
        "label": "AN/FPS-117 Surveillance Radar",
    },
    "TPS880K": {
        "sensor_type": "TPS880K",
        "detection_range": 40,      # km (추정, X밴드 AESA)
        "tracking_capacity": 30,
        "scan_rate": 1.0,
        "role": "local_surveillance",   # 야전 저고도
        "detectable_types": ["AIRCRAFT", "CRUISE_MISSILE", "UAS"],
        "provides_cueing_to": ["ARMY_LOCAL_AD"],
        "min_detection_altitude": 0.05,  # km (50m, 저고도 특화)
        "label": "TPS-880K Local AD Radar",
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
    # ── v0.7 신규 C2 노드 ──
    "KAMD_OPS": {
        "node_type": "KAMD_OPS",
        "processing_capacity": 8,
        "auth_delay_linear": (10, 60),      # 초 (탄도탄 전담)
        "auth_delay_killweb": (1, 3),       # 초
        "label": "KAMD 작전센터 (탄도탄 방어)",
    },
    "ARMY_LOCAL_AD": {
        "node_type": "ARMY_LOCAL_AD",
        "processing_capacity": 3,
        "auth_delay_linear": (3, 10),       # 초 (육군 독자)
        "auth_delay_killweb": (1, 3),       # 초
        "label": "육군 국지방공 C2",
    },
    "IAOC": {
        "node_type": "IAOC",
        "processing_capacity": 10,
        "auth_delay_linear": None,          # 선형 C2에서 사용 안함
        "auth_delay_killweb": (1, 3),       # 초 (통합 자동화)
        "label": "통합 방공작전센터 (IAOC)",
    },
}

# =============================================================================
# 4. 사격체 파라미터
# =============================================================================
SHOOTER_PARAMS = {
    "PATRIOT_PAC3": {
        "weapon_type": "PATRIOT_PAC3",
        "max_range": 90,            # km (PAC-3 MSE 실사거리)
        "min_range": 3,             # km
        "max_altitude": 40,         # km (PAC-3 MSE 스펙 반영)
        "min_altitude": 0,          # km
        "pk_table": {
            "SRBM": 0.85,
            "CRUISE_MISSILE": 0.80,
            "AIRCRAFT": 0.90,
            "UAS": 0.70,
        },
        "ammo_count": 16,
        "reload_time": 1800,        # 초
        "engagement_time": 5,       # 초
        "intercept_method": "hit_to_kill",
        "label": "PATRIOT PAC-3 MSE",
    },
    "CHEONGUNG2": {
        "weapon_type": "CHEONGUNG2",
        "max_range": 40,
        "min_range": 1,
        "max_altitude": 20,
        "min_altitude": 0,          # km
        "pk_table": {
            "SRBM": 0.75,
            "CRUISE_MISSILE": 0.80,
            "AIRCRAFT": 0.85,
            "UAS": 0.65,
        },
        "ammo_count": 8,
        "reload_time": 1200,
        "engagement_time": 5,
        "intercept_method": "proximity_fuse",
        "label": "천궁-II",
    },
    "BIHO": {
        "weapon_type": "BIHO",
        "max_range": 7,
        "min_range": 0.5,
        "max_altitude": 3,
        "min_altitude": 0,          # km
        "pk_table": {
            "SRBM": 0.0,
            "CRUISE_MISSILE": 0.30,
            "AIRCRAFT": 0.50,
            "UAS": 0.60,
        },
        "ammo_count": 502,          # 500(기관포) + 2(미사일)
        "reload_time": 5,
        "engagement_time": 3,
        "intercept_method": "proximity_fuse",
        "label": "비호 복합",
    },
    "KF16": {
        "weapon_type": "KF16",
        "max_range": 100,
        "min_range": 5,
        "max_altitude": 15,
        "min_altitude": 0,          # km
        "pk_table": {
            "SRBM": 0.0,
            "CRUISE_MISSILE": 0.75,
            "AIRCRAFT": 0.85,
            "UAS": 0.50,
        },
        "ammo_count": 6,
        "reload_time": float("inf"),    # 비행장 복귀 필요
        "engagement_time": 8,
        "intercept_method": "air_to_air",
        "label": "KF-16 (CAP)",
    },
    # ── v0.7 신규 무기체계 ──
    "THAAD": {
        "weapon_type": "THAAD",
        "max_range": 200,           # km
        "min_range": 0,
        "max_altitude": 150,        # km
        "min_altitude": 40,         # km (적외선 탐색기 한계 — 고고도 전용)
        "pk_table": {
            "SRBM": 0.90,
            "CRUISE_MISSILE": 0.0,
            "AIRCRAFT": 0.0,
            "UAS": 0.0,
        },
        "ammo_count": 48,           # 6 발사대 × 8발
        "reload_time": 1800,
        "engagement_time": 15,
        "intercept_method": "hit_to_kill",
        "label": "THAAD",
    },
    "LSAM_ABM": {
        "weapon_type": "LSAM_ABM",
        "max_range": 150,           # km (추정)
        "min_range": 0,
        "max_altitude": 60,         # km
        "min_altitude": 40,         # km (적외선 탐색기 한계 — 고고도 전용)
        "pk_table": {
            "SRBM": 0.85,
            "CRUISE_MISSILE": 0.0,
            "AIRCRAFT": 0.0,
            "UAS": 0.0,
        },
        "ammo_count": 8,            # 발사대 2대 × 4발 (추정)
        "reload_time": 1800,
        "engagement_time": 12,
        "intercept_method": "hit_to_kill",
        "label": "L-SAM ABM",
    },
    "LSAM_AAM": {
        "weapon_type": "LSAM_AAM",
        "max_range": 200,           # km (최소 150~300km)
        "min_range": 10,
        "max_altitude": 20,         # km
        "min_altitude": 0,          # km
        "pk_table": {
            "SRBM": 0.0,
            "CRUISE_MISSILE": 0.85,
            "AIRCRAFT": 0.90,
            "UAS": 0.50,
        },
        "ammo_count": 8,            # 발사대 2대 × 4발 (추정)
        "reload_time": 1200,
        "engagement_time": 10,
        "intercept_method": "proximity_fuse",
        "label": "L-SAM AAM",
    },
    "CHEONGUNG1": {
        "weapon_type": "CHEONGUNG1",
        "max_range": 40,
        "min_range": 1,
        "max_altitude": 15,         # km
        "min_altitude": 0,          # km
        "pk_table": {
            "SRBM": 0.0,
            "CRUISE_MISSILE": 0.80,
            "AIRCRAFT": 0.85,
            "UAS": 0.60,
        },
        "ammo_count": 32,           # 발사대 4대 × 8발
        "reload_time": 600,
        "engagement_time": 5,
        "intercept_method": "proximity_fuse",
        "label": "천궁-I (M-SAM)",
    },
    "CHUNMA": {
        "weapon_type": "CHUNMA",
        "max_range": 9,             # km 유효사거리
        "min_range": 0.5,
        "max_altitude": 5,          # km
        "min_altitude": 0,          # km
        "pk_table": {
            "SRBM": 0.0,
            "CRUISE_MISSILE": 0.40,
            "AIRCRAFT": 0.65,
            "UAS": 0.55,
        },
        "ammo_count": 8,            # 미사일 8발
        "reload_time": 300,
        "engagement_time": 3,
        "intercept_method": "command_guidance",
        "label": "천마 (K-SAM)",
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
    "scenario_3_ew_light": {
        "name": "전자전 (Light)",
        "description": "재밍 Light: detection_factor=0.8, latency_factor=1.5",
        "waves": [
            {"time": 0, "threats": {"SRBM": 10, "CRUISE_MISSILE": 5,
                                     "AIRCRAFT": 3, "UAS": 20}},
        ],
        "approach_azimuth": (240, 360),
        "approach_distance": 200,
        "jamming_level": 0.2,
        "detection_factor": 0.8,
        "latency_factor": 1.5,
        "node_destruction": [],
    },
    "scenario_3_ew_moderate": {
        "name": "전자전 (Moderate)",
        "description": "재밍 Moderate: detection_factor=0.5, latency_factor=3.0",
        "waves": [
            {"time": 0, "threats": {"SRBM": 10, "CRUISE_MISSILE": 5,
                                     "AIRCRAFT": 3, "UAS": 20}},
        ],
        "approach_azimuth": (240, 360),
        "approach_distance": 200,
        "jamming_level": 0.5,
        "detection_factor": 0.5,
        "latency_factor": 3.0,
        "node_destruction": [],
    },
    "scenario_3_ew_heavy": {
        "name": "전자전 (Heavy)",
        "description": "재밍 Heavy: detection_factor=0.2, latency_factor=5.0",
        "waves": [
            {"time": 0, "threats": {"SRBM": 10, "CRUISE_MISSILE": 5,
                                     "AIRCRAFT": 3, "UAS": 20}},
        ],
        "approach_azimuth": (240, 360),
        "approach_distance": 200,
        "jamming_level": 0.8,
        "detection_factor": 0.2,
        "latency_factor": 5.0,
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
    "scenarios": [
        "scenario_1_saturation",
        "scenario_2_complex",
        "scenario_3_ew_light",
        "scenario_3_ew_moderate",
        "scenario_3_ew_heavy",
        "scenario_4_sequential",
        "scenario_5_node_destruction",
    ],
    "checkpoint_interval": 50,      # 50회마다 중간 저장
}

# =============================================================================
# 10. 토폴로지 관계 매핑 (선형 C2 계층 구조)
# =============================================================================
TOPOLOGY_RELATIONS = {
    "sensor_to_c2": {
        # 기존 (DEFAULT_DEPLOYMENT용)
        "EWR": "MCRC",
        "PATRIOT_RADAR": "TOC_PAT",
        "MSAM_MFR": "TOC_MSAM",
        "SHORAD_RADAR": "TOC_SHORAD",      # fallback: TOC_MSAM
        # v0.7 신규
        "GREEN_PINE": "KAMD_OPS",
        "FPS117": "MCRC",
        "TPS880K": "ARMY_LOCAL_AD",
    },
    "shooter_to_c2": {
        # 기존 (DEFAULT_DEPLOYMENT용)
        "PATRIOT_PAC3": "TOC_PAT",
        "CHEONGUNG2": "TOC_MSAM",
        "BIHO": "TOC_SHORAD",              # fallback: TOC_MSAM
        "KF16": "MCRC",
        # v0.7 신규
        "THAAD": "KAMD_OPS",
        "LSAM_ABM": "KAMD_OPS",
        "LSAM_AAM": "KAMD_OPS",
        "CHEONGUNG1": "MCRC",
        "CHUNMA": "ARMY_LOCAL_AD",
    },
    "c2_hierarchy": {
        "BATTALION_TOC": "MCRC",
        "EOC": None,                        # Kill Web에서는 계층 없음
        # v0.7 신규
        "KAMD_OPS": None,                   # 공군 미사일방어사령부 (MCRC와 독립)
        "ARMY_LOCAL_AD": None,              # 육군 독자 (MCRC/KAMD와 독립)
        "IAOC": None,                       # Kill Web 통합 C2
    },
}

# =============================================================================
# 11. 센서 큐잉 지연 파라미터 (v0.7)
# =============================================================================
SENSOR_CUEING_DELAYS = {
    # 조기경보 탐지 → C2 경보 전파
    "early_warning_to_c2": (2, 5),          # 초
    # C2 → 무기체계 큐잉 명령
    "c2_to_weapon_cueing_linear": (3, 10),  # 초 (Linear)
    "c2_to_weapon_cueing_killweb": (1, 3),  # 초 (Kill Web)
    # 무기체계 레이더 빔 지향 → 추적 획득
    "weapon_radar_acquisition": (5, 15),    # 초
    # 추적 → 화력통제 품질 달성
    "track_to_fire_control": (2, 5),        # 초
    # 교전 승인 → 요격미사일 발사
    "fire_command_to_launch": (1, 5),       # 초
}

# =============================================================================
# 12. 한반도 방어구역 정의 (v0.7)
# =============================================================================
SIMULATION_MAP = {
    "x_range": (0, 200),        # km (서해~동해)
    "y_range": (-400, 350),     # km (NK interior ~ Busan)
    "dmz_y": 0,                 # DMZ 위치
    "seoul_y": 50,              # Seoul
    "osan_y": 60,               # Osan AB
    "daejeon_y": 150,           # Daejeon
    "seongju_y": 230,           # Seongju (THAAD)
    "daegu_y": 250,             # Daegu
    "busan_y": 330,             # Busan
}

DEFENSE_ZONES = {
    "ZONE_A": {
        "name": "Forward Corps Local AD",
        "y_range": (0, 30),
        "threats_facing": ["AIRCRAFT", "CRUISE_MISSILE", "UAS"],
    },
    "ZONE_B": {
        "name": "Capital Area Multi-Layer AD",
        "y_range": (30, 80),
    },
    "ZONE_C": {
        "name": "Central Strategic Surveillance",
        "y_range": (80, 180),
    },
    "ZONE_D": {
        "name": "Southern High-Altitude Defense",
        "y_range": (180, 350),
    },
}

# =============================================================================
# 13. 현실적 배치 (v0.7 — 한반도 방어구역 기반)
# =============================================================================
REALISTIC_DEPLOYMENT = {
    "sensors": [
        # 전략 조기경보 (Zone C/D)
        {"type": "GREEN_PINE", "id": "GP_1", "pos": (100, 130)},
        {"type": "GREEN_PINE", "id": "GP_2", "pos": (80, 250)},
        # 방공관제 (전국 산악 고지대)
        {"type": "FPS117", "id": "FPS_1", "pos": (50, 60)},
        {"type": "FPS117", "id": "FPS_2", "pos": (150, 60)},
        {"type": "FPS117", "id": "FPS_3", "pos": (100, 150)},
        {"type": "FPS117", "id": "FPS_4", "pos": (100, 250)},
        # 국지방공 (전방군단)
        {"type": "TPS880K", "id": "TPS_1", "pos": (60, 15)},
        {"type": "TPS880K", "id": "TPS_2", "pos": (100, 15)},
        {"type": "TPS880K", "id": "TPS_3", "pos": (140, 15)},
        # 무기체계 전용 레이더 (Zone B)
        {"type": "PATRIOT_RADAR", "id": "PAT_RADAR_1", "pos": (80, 55)},
        {"type": "PATRIOT_RADAR", "id": "PAT_RADAR_2", "pos": (120, 55)},
        {"type": "MSAM_MFR", "id": "MFR_1", "pos": (70, 50)},
        {"type": "MSAM_MFR", "id": "MFR_2", "pos": (130, 50)},
        {"type": "SHORAD_RADAR", "id": "SH_RADAR_1", "pos": (100, 20)},
    ],
    "c2_nodes": {
        "linear": [
            # 공군 MCRC (오산)
            {"type": "MCRC", "id": "MCRC_1", "pos": (100, 60)},
            # 공군 KAMD작전센터 (오산, 별도 조직)
            {"type": "KAMD_OPS", "id": "KAMD_OPS_1", "pos": (100, 60)},
            # 육군 국지방공 C2
            {"type": "ARMY_LOCAL_AD", "id": "ARMY_AD_1", "pos": (100, 20)},
            # 대대 TOC
            {"type": "BATTALION_TOC", "id": "TOC_PAT", "pos": (80, 55)},
            {"type": "BATTALION_TOC", "id": "TOC_MSAM", "pos": (120, 50)},
        ],
        "killweb": [
            # 통합 방공작전센터 (IAOC)
            {"type": "IAOC", "id": "IAOC_1", "pos": (100, 60)},
            # 분산 EOC
            {"type": "EOC", "id": "EOC_1", "pos": (80, 55)},
            {"type": "EOC", "id": "EOC_2", "pos": (120, 50)},
            {"type": "EOC", "id": "EOC_3", "pos": (100, 20)},
        ],
    },
    "shooters": [
        # 고고도 (Zone D) — THAAD, L-SAM ABM
        {"type": "THAAD", "id": "THAAD_1", "pos": (100, 230)},
        {"type": "LSAM_ABM", "id": "LSAM_ABM_1", "pos": (80, 200)},
        {"type": "LSAM_ABM", "id": "LSAM_ABM_2", "pos": (120, 200)},
        # 중고도 (Zone B/C) — PAC-3, 천궁-II, L-SAM AAM
        {"type": "PATRIOT_PAC3", "id": "PAT_1", "pos": (70, 55)},
        {"type": "PATRIOT_PAC3", "id": "PAT_2", "pos": (130, 55)},
        {"type": "CHEONGUNG2", "id": "MSAM_1", "pos": (60, 50)},
        {"type": "CHEONGUNG2", "id": "MSAM_2", "pos": (140, 50)},
        {"type": "LSAM_AAM", "id": "LSAM_AAM_1", "pos": (90, 180)},
        {"type": "LSAM_AAM", "id": "LSAM_AAM_2", "pos": (110, 180)},
        # 중저고도 (Zone B) — 천궁-I
        {"type": "CHEONGUNG1", "id": "CG1_1", "pos": (80, 45)},
        {"type": "CHEONGUNG1", "id": "CG1_2", "pos": (120, 45)},
        # 저고도 (Zone A/B) — 천마, 비호, KF-16
        {"type": "CHUNMA", "id": "CHUNMA_1", "pos": (60, 15)},
        {"type": "CHUNMA", "id": "CHUNMA_2", "pos": (100, 15)},
        {"type": "CHUNMA", "id": "CHUNMA_3", "pos": (140, 15)},
        {"type": "BIHO", "id": "BIHO_1", "pos": (80, 10)},
        {"type": "BIHO", "id": "BIHO_2", "pos": (120, 10)},
        {"type": "KF16", "id": "KF16_1", "pos": (100, 60)},
    ],
    "defense_target": (100, 50),    # 수도권
}

# =============================================================================
# 14. 위협 발사원점 (v0.7)
# =============================================================================
THREAT_ORIGINS = {
    "DMZ_FRONT": {
        "y": -10,
        "threat_types": ["CRUISE_MISSILE", "UAS", "AIRCRAFT"],
    },
    "PYONGYANG_AREA": {
        "y": -180,
        "threat_types": ["SRBM", "CRUISE_MISSILE"],
    },
    "NORTH_INTERIOR": {
        "y": -400,
        "threat_types": ["SRBM"],
    },
}
