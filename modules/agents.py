"""
agents.py - 한국군 방공체계 시뮬레이션 에이전트 클래스
Mesa Agent classes: SensorAgent, C2NodeAgent, ShooterAgent, ThreatAgent
"""

import math
import random
from mesa import Agent

from .config import SENSOR_PARAMS, C2_PARAMS, SHOOTER_PARAMS, THREAT_PARAMS, ENGAGEMENT_POLICY, COP_CONFIG


def _slant_range(pos1, alt1, pos2, alt2):
    """3D 경사거리 = sqrt(수평거리² + 고도차²)"""
    horiz = math.dist(pos1, pos2)
    return math.sqrt(horiz ** 2 + (alt1 - alt2) ** 2)


# =============================================================================
# SensorAgent (탐지체)
# =============================================================================
class SensorAgent(Agent):
    """센서 에이전트 - EWR, PATRIOT Radar, M-SAM MFR, SHORAD Radar"""

    def __init__(self, model, sensor_type, agent_id, pos):
        super().__init__(model)
        params = SENSOR_PARAMS[sensor_type]
        self.sensor_type = params["sensor_type"]
        self.detection_range = params["detection_range"]
        self.tracking_capacity = params["tracking_capacity"]
        self.scan_rate = params["scan_rate"]
        self.pos = pos
        self.agent_id = agent_id
        self.is_operational = True
        self.current_tracks = []
        self.label = params["label"]

    def detect(self, threat, jamming_level=0.0, detection_factor=1.0):
        """탐지 확률 계산: P(detect) = max(0, 1-(d/R_max)²) × (1-jam) × detection_factor"""
        if not self.is_operational:
            return False
        if len(self.current_tracks) >= self.tracking_capacity:
            return False

        d = _slant_range(self.pos, 0, threat.pos, threat.altitude)
        r_max = self.detection_range

        # RCS 보정: 표준 레이더 방정식 (탐지거리 ∝ RCS^(1/4))
        rcs_ref = 1.0  # m² 기준
        rcs_factor = min(1.0, (threat.rcs / rcs_ref) ** 0.25)
        effective_range = r_max * rcs_factor

        if d > effective_range:
            return False

        p_detect = max(0.0, 1.0 - (d / effective_range) ** 2) * (1.0 - jamming_level) * detection_factor
        return random.random() < p_detect

    def track(self, threat):
        """추적 정보 생성 (위치 오차 포함)"""
        if threat.unique_id not in [t.unique_id for t in self.current_tracks]:
            self.current_tracks.append(threat)
        pos_error = random.gauss(0, ENGAGEMENT_POLICY["tracking_position_error_std"])
        return {
            "sensor_id": self.agent_id,
            "threat_id": threat.unique_id,
            "threat_type": threat.threat_type,
            "pos": (threat.pos[0] + pos_error, threat.pos[1] + pos_error),
            "speed": threat.speed,
            "altitude": threat.altitude,
            "time": self.model.sim_time,
        }

    def remove_track(self, threat):
        """추적 목록에서 위협 제거"""
        self.current_tracks = [
            t for t in self.current_tracks if t.unique_id != threat.unique_id
        ]

    def step(self):
        """매 스텝: 추적 중인 위협 갱신"""
        self.current_tracks = [t for t in self.current_tracks if t.is_alive]


# =============================================================================
# C2NodeAgent (지휘통제 노드)
# =============================================================================
class C2NodeAgent(Agent):
    """C2 노드 에이전트 - MCRC, 대대 TOC, EOC"""

    def __init__(self, model, node_type, agent_id, pos):
        super().__init__(model)
        params = C2_PARAMS[node_type]
        self.node_type = params["node_type"]
        self.processing_capacity = params["processing_capacity"]
        self.auth_delay_linear = params["auth_delay_linear"]
        self.auth_delay_killweb = params["auth_delay_killweb"]
        self.agent_id = agent_id
        self.pos = pos
        self.is_operational = True
        self.air_picture = {}           # {threat_id: track_info}
        self.threat_queue = []          # 처리 대기열
        self.current_load = 0           # 현재 처리 중인 위협 수
        self.processed_count = 0        # 총 처리 완료 수
        self.label = params["label"]
        # v0.5: COP 확장 (Kill Web 전용)
        self.friendly_status = {}       # {shooter_id: status_dict}
        self.engagement_plan = {}       # {threat_id: plan_dict}

    def receive_track(self, track_info):
        """탐지보고 수신 → 항적 종합"""
        if not self.is_operational:
            return False
        threat_id = track_info["threat_id"]
        self.air_picture[threat_id] = track_info
        return True

    def update_friendly_status(self, shooter_id, status_dict):
        """Kill Web 전용: 아군 사수 상태 갱신"""
        self.friendly_status[shooter_id] = status_dict

    def update_engagement_plan(self, threat_id, plan_dict):
        """Kill Web 전용: 교전 계획 공유"""
        self.engagement_plan[threat_id] = plan_dict

    def evaluate_threat(self, track_info):
        """위협 평가 → 우선순위 산출"""
        if not self.is_operational:
            return 0
        threat_type = track_info["threat_type"]
        priority_map = {"SRBM": 10, "CRUISE_MISSILE": 8, "AIRCRAFT": 6, "UAS": 3}
        return priority_map.get(threat_type, 1)

    def get_auth_delay(self, architecture):
        """아키텍처에 따른 승인 지연 시간 반환"""
        if architecture == "linear":
            if self.auth_delay_linear is None:
                return 0
            return random.uniform(*self.auth_delay_linear)
        else:
            if self.auth_delay_killweb is None:
                return 0
            return random.uniform(*self.auth_delay_killweb)

    def can_process(self):
        """처리 가능 여부 (용량 초과 여부)"""
        return self.is_operational and self.current_load < self.processing_capacity

    def step(self):
        """매 스텝: 소멸된 위협 항적 정리"""
        dead_threats = []
        for tid, info in self.air_picture.items():
            threat_agents = [
                a for a in self.model.agents
                if isinstance(a, ThreatAgent) and a.unique_id == tid
            ]
            if not threat_agents or not threat_agents[0].is_alive:
                dead_threats.append(tid)
        for tid in dead_threats:
            del self.air_picture[tid]


# =============================================================================
# ShooterAgent (사격체)
# =============================================================================
class ShooterAgent(Agent):
    """사격 에이전트 - PATRIOT PAC-3, 천궁-II, 비호, KF-16"""

    def __init__(self, model, weapon_type, agent_id, pos):
        super().__init__(model)
        params = SHOOTER_PARAMS[weapon_type]
        self.weapon_type = params["weapon_type"]
        self.max_range = params["max_range"]
        self.min_range = params["min_range"]
        self.max_altitude = params["max_altitude"]
        self.pk_table = dict(params["pk_table"])
        self.ammo_count = params["ammo_count"]
        self.initial_ammo = params["ammo_count"]
        self.reload_time = params["reload_time"]
        self.engagement_time = params["engagement_time"]
        self.agent_id = agent_id
        self.pos = pos
        self.is_operational = True
        self.is_engaged = False
        self.engagement_end_time = 0
        self.kills = 0
        self.shots_fired = 0
        self.label = params["label"]

        # v0.6a: BIHO gun/missile 분리
        self._has_dual_mode = "gun_range" in params
        if self._has_dual_mode:
            self.gun_range = params["gun_range"]
            self.missile_range = params["missile_range"]
            self.gun_ammo = params["gun_ammo"]
            self.missile_ammo = params["missile_ammo"]
            self.initial_gun_ammo = params["gun_ammo"]
            self.initial_missile_ammo = params["missile_ammo"]
            self.pk_table_gun = dict(params.get("pk_table_gun", params["pk_table"]))
            self.pk_table_missile = dict(params.get("pk_table_missile", params["pk_table"]))

    def _get_biho_mode(self, threat):
        """v0.6a: BIHO gun/missile 모드 결정. 거리 기반 자동 선택."""
        if not self._has_dual_mode:
            return None
        d = _slant_range(self.pos, 0, threat.pos, threat.altitude)
        # gun 사거리 이내 + gun 탄약 있으면 gun 모드
        if d <= self.gun_range and self.gun_ammo > 0:
            return "gun"
        # missile 사거리 이내 + missile 탄약 있으면 missile 모드
        if d <= self.missile_range and self.missile_ammo > 0:
            return "missile"
        return None

    def can_engage(self, threat, pk_threshold=0.1):
        """교전 가능 여부 (사거리, 탄약, 상태, 고도, 최소 Pk)"""
        if not self.is_operational or self.is_engaged:
            return False
        if self.ammo_count <= 0:
            return False

        d = _slant_range(self.pos, 0, threat.pos, threat.altitude)

        # v0.6a: BIHO 이중 모드 처리
        if self._has_dual_mode:
            mode = self._get_biho_mode(threat)
            if mode is None:
                return False
            pk_tbl = self.pk_table_gun if mode == "gun" else self.pk_table_missile
            mode_range = self.gun_range if mode == "gun" else self.missile_range
            base_pk = pk_tbl.get(threat.threat_type, 0)
            if base_pk <= 0:
                return False
            if threat.altitude > self.max_altitude:
                return False
            range_factor = max(0.0, 1.0 - (d / mode_range) ** 2)
            if base_pk * range_factor < pk_threshold:
                return False
            return True

        effective_max = self.max_range * ENGAGEMENT_POLICY["effective_range_ratio"]
        if d < self.min_range or d > effective_max:
            return False
        if threat.altitude > self.max_altitude:
            return False
        base_pk = self.pk_table.get(threat.threat_type, 0)
        if base_pk <= 0:
            return False
        # 최소 Pk 확인
        range_factor = max(0.0, 1.0 - (d / self.max_range) ** 2)
        if base_pk * range_factor < pk_threshold:
            return False
        return True

    def compute_pk(self, threat, jamming_level=0.0):
        """위협 유형별 Pk 계산 (거리, 기동, 재밍 보정)"""
        d = _slant_range(self.pos, 0, threat.pos, threat.altitude)

        # v0.6a: BIHO 이중 모드 Pk 계산
        if self._has_dual_mode:
            mode = self._get_biho_mode(threat)
            if mode is None:
                return 0.0
            pk_tbl = self.pk_table_gun if mode == "gun" else self.pk_table_missile
            mode_range = self.gun_range if mode == "gun" else self.missile_range
            base_pk = pk_tbl.get(threat.threat_type, 0)
            if base_pk <= 0:
                return 0.0
            range_factor = max(0.0, 1.0 - (d / mode_range) ** 2)
            maneuver_penalty = 0.85 if threat.maneuvering else 1.0
            jamming_penalty = 1.0 - (jamming_level * ENGAGEMENT_POLICY["jamming_pk_penalty"])
            return base_pk * range_factor * maneuver_penalty * jamming_penalty

        base_pk = self.pk_table.get(threat.threat_type, 0)
        if base_pk <= 0:
            return 0.0

        range_factor = max(0.0, 1.0 - (d / self.max_range) ** 2)
        maneuver_penalty = 0.85 if threat.maneuvering else 1.0
        jamming_penalty = 1.0 - (jamming_level * ENGAGEMENT_POLICY["jamming_pk_penalty"])

        return base_pk * range_factor * maneuver_penalty * jamming_penalty

    def engage(self, threat, jamming_level=0.0, pk_bonus=0.0):
        """교전 실행: Pk 기반 베르누이 시행. pk_bonus: 센서 융합 보너스 (v0.5)"""
        if not self.can_engage(threat):
            return False

        final_pk = min(1.0, self.compute_pk(threat, jamming_level) + pk_bonus)

        # v0.6a: BIHO 이중 모드 탄약 소모
        if self._has_dual_mode:
            mode = self._get_biho_mode(threat)
            if mode == "gun":
                self.gun_ammo -= 1
            elif mode == "missile":
                self.missile_ammo -= 1
            self.ammo_count = self.gun_ammo + self.missile_ammo
        else:
            self.ammo_count -= 1

        self.shots_fired += 1
        self.is_engaged = True
        self.engagement_end_time = self.model.sim_time + self.engagement_time

        hit = random.random() < final_pk
        if hit:
            self.kills += 1
        return hit

    def shooter_score(self, threat, jamming_level=0.0):
        """Kill Web 사수 선정 점수: Pk × in_envelope × (1/load) × (1/distance)"""
        if not self.can_engage(threat):
            return 0.0

        pk = self.compute_pk(threat, jamming_level)
        d = _slant_range(self.pos, 0, threat.pos, threat.altitude)
        distance_score = 1.0 / max(d, 1.0)
        ammo_ratio = self.ammo_count / max(self.initial_ammo, 1)
        load_factor = 0.5 if self.is_engaged else 1.0

        return pk * distance_score * ammo_ratio * load_factor

    def step(self):
        """매 스텝: 교전 종료 여부 확인"""
        if self.is_engaged and self.model.sim_time >= self.engagement_end_time:
            self.is_engaged = False


# =============================================================================
# ThreatAgent (위협체)
# =============================================================================
class ThreatAgent(Agent):
    """위협 에이전트 - SRBM, 순항미사일, 항공기, UAS"""

    def __init__(self, model, threat_type, pos, target_pos, launch_time=0):
        super().__init__(model)
        params = THREAT_PARAMS[threat_type]
        self.threat_type = params["threat_type"]
        self.speed = params["speed"]
        self.altitude = params["altitude"]
        self.rcs = params["rcs"]
        self.maneuvering = params["maneuvering"]
        self.pos = pos
        self.target_pos = target_pos
        self.launch_time = launch_time
        self.is_alive = True
        self.is_detected = False
        self.detected_time = None
        self.engaged_time = None
        self.destroyed_time = None
        self.reached_target_time = None
        self.label = params["label"]
        self.elapsed_flight_time = 0.0

        # 비행 프로파일 초기화
        if "flight_profile" in params:
            phases = params["flight_profile"]["phases"]
            # 가중평균 속도로 전체 비행시간 추정
            total_dist = math.dist(pos, target_pos)
            avg_speed = sum(
                p["duration_ratio"] * (p["speed_start"] + p["speed_end"]) / 2
                for p in phases
            )
            self.total_flight_time = total_dist / max(avg_speed, 0.001)

            # 각 단계 절대 시각 계산
            t = 0.0
            self.phase_timeline = []
            for p in phases:
                duration = p["duration_ratio"] * self.total_flight_time
                self.phase_timeline.append({
                    "name": p["name"],
                    "start_time": t,
                    "end_time": t + duration,
                    "duration": max(duration, 0.001),
                    "altitude_start": p["altitude_start"],
                    "altitude_end": p["altitude_end"],
                    "speed_start": p["speed_start"],
                    "speed_end": p["speed_end"],
                    "maneuvering": p["maneuvering"],
                })
                t += duration
        else:
            # 레거시: 고정 고도/속도
            self.phase_timeline = None
            self.total_flight_time = None

    def _compute_phase_state(self, elapsed):
        """경과 시간 기반 현재 비행 단계의 고도·속도·기동여부 계산"""
        for phase in self.phase_timeline:
            if elapsed <= phase["end_time"]:
                progress = (elapsed - phase["start_time"]) / phase["duration"]
                progress = max(0.0, min(1.0, progress))

                alt = phase["altitude_start"] + (phase["altitude_end"] - phase["altitude_start"]) * progress
                spd = phase["speed_start"] + (phase["speed_end"] - phase["speed_start"]) * progress
                maneuvering = phase["maneuvering"]
                return alt, spd, maneuvering

        # 마지막 단계 이후
        last = self.phase_timeline[-1]
        return last["altitude_end"], last["speed_end"], last["maneuvering"]

    def move(self, dt):
        """시간 스텝별 이동 (목표 방향으로 직선 이동, 비행 프로파일 반영)"""
        if not self.is_alive:
            return

        self.elapsed_flight_time += dt

        # 비행 프로파일에서 현재 상태 계산
        if self.phase_timeline is not None:
            self.altitude, self.speed, self.maneuvering = \
                self._compute_phase_state(self.elapsed_flight_time)

        dx = self.target_pos[0] - self.pos[0]
        dy = self.target_pos[1] - self.pos[1]
        dist_to_target = math.sqrt(dx ** 2 + dy ** 2)

        if dist_to_target < ENGAGEMENT_POLICY["target_arrival_distance"]:
            return

        move_dist = self.speed * dt
        if move_dist >= dist_to_target:
            self.pos = self.target_pos
        else:
            ratio = move_dist / dist_to_target
            self.pos = (
                self.pos[0] + dx * ratio,
                self.pos[1] + dy * ratio,
            )

    def reached_target(self):
        """방어구역 돌파 여부"""
        d = math.dist(self.pos, self.target_pos)
        return d < ENGAGEMENT_POLICY["target_arrival_distance"]

    def destroy(self):
        """위협 격추"""
        self.is_alive = False
        self.destroyed_time = self.model.sim_time

    def step(self):
        """매 스텝: 이동 및 돌파 확인"""
        if not self.is_alive:
            return
        dt = self.model.time_resolution
        self.move(dt)
        if self.reached_target():
            self.reached_target_time = self.model.sim_time
            self.is_alive = False
