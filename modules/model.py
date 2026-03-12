"""
model.py - 한국군 방공체계 시뮬레이션 모델
Mesa + SimPy 통합 시뮬레이션 모델.

핵심 흐름:
1. 위협 이동 → 2. 센서 탐지 → 3. 킬체인(C2 처리, SimPy 지연)
→ 4. 교전 대기 큐 등록 → 5. 사수 교전(사거리 진입 시)
"""

import random
import math
import simpy
import numpy as np
from mesa import Model

from .config import (
    SIM_CONFIG, DEFAULT_DEPLOYMENT, COMM_PARAMS,
    SENSOR_PARAMS, C2_PARAMS, SHOOTER_PARAMS, SCENARIO_PARAMS,
    ENGAGEMENT_POLICY, COP_CONFIG, ADAPTIVE_ENGAGEMENT, COMM_DEGRADATION,
)
from .agents import SensorAgent, C2NodeAgent, ShooterAgent, ThreatAgent
from .network import (
    build_linear_topology, build_killweb_topology,
    remove_node_from_topology, get_connected_c2_for_sensor,
    get_connected_shooters, get_topology_stats,
)
from .comms import CommChannel, KillChainProcess
from .threats import generate_threats_for_scenario, get_scenario_node_destructions
from .metrics import MetricsCollector


class AirDefenseModel(Model):
    """
    한국군 방공체계 M&S 모델.
    선형 C2 vs Kill Web 아키텍처 비교 시뮬레이션.
    """

    def __init__(self, architecture="linear", scenario="scenario_1_saturation",
                 jamming_level=None, seed=None, deployment=None,
                 record_snapshots=False):
        super().__init__(seed=seed)
        self.architecture = architecture
        self.record_snapshots = record_snapshots
        self.snapshots = []
        self.scenario_name = scenario
        self.scenario = SCENARIO_PARAMS.get(scenario, SCENARIO_PARAMS["scenario_1_saturation"])
        self.time_resolution = SIM_CONFIG["time_resolution"]
        self.max_sim_time = SIM_CONFIG["max_sim_time"]
        # 시나리오별 최대 시뮬레이션 시간 동적 조정
        scenario_cfg = SCENARIO_PARAMS.get(scenario, SCENARIO_PARAMS["scenario_1_saturation"])
        if "duration" in scenario_cfg:
            self.max_sim_time = max(self.max_sim_time, scenario_cfg["duration"])
        self.sim_time = 0.0
        self.step_count = 0
        self.deployment = deployment or DEFAULT_DEPLOYMENT
        self.running = True

        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        # SimPy 환경
        self.simpy_env = simpy.Environment()

        # 재밍 수준: 명시적 파라미터 > 시나리오 config > 기본값 0.0
        if jamming_level is not None:
            self.jamming_level = jamming_level
        elif hasattr(self.scenario, 'get'):
            self.jamming_level = self.scenario.get("jamming_level", 0.0)
        else:
            self.jamming_level = 0.0

        # 재밍 세부 파라미터 (v0.3: detection_factor, latency_factor)
        self.detection_factor = self.scenario.get("detection_factor", 1.0) if hasattr(self.scenario, 'get') else 1.0
        self.latency_factor = self.scenario.get("latency_factor", 1.0) if hasattr(self.scenario, 'get') else 1.0

        # 메트릭 수집기
        self.metrics = MetricsCollector()

        # 에이전트 생성
        self.sensor_agents = []
        self.c2_agents = []
        self.shooter_agents = []
        self.threat_agents = []
        self._create_defense_agents()
        self.metrics.shooters = self.shooter_agents

        # 네트워크 토폴로지
        self.topology = self._build_topology()

        # 통신 채널 및 킬체인 프로세스
        self.comm_channel = CommChannel(self.simpy_env, architecture)
        self.comm_channel.set_jamming(self.jamming_level)
        # 시나리오별 latency_factor 직접 설정 (set_jamming의 자동 매핑 덮어쓰기)
        if self.latency_factor != 1.0:
            self.comm_channel.latency_factor = self.latency_factor

        # C2 SimPy Resource 생성
        self.c2_resources = {}
        for c2 in self.c2_agents:
            self.c2_resources[c2.agent_id] = simpy.Resource(
                self.simpy_env, capacity=c2.processing_capacity
            )

        self.killchain = KillChainProcess(
            self.simpy_env, self.comm_channel,
            self.c2_resources, architecture
        )

        # 위협 생성
        self._generate_threats()

        # 노드 파괴 스케줄
        self.node_destructions = get_scenario_node_destructions(
            self.scenario_name, self.architecture
        )

        # 상태 추적
        self._threats_in_killchain = set()      # 킬체인 처리 중
        self._threats_cleared = set()           # 킬체인 완료 → 교전 대기
        self._threats_leaked = set()            # 누출 기록 완료
        self._destroyed_nodes = set()           # 이미 파괴된 노드

    def _create_defense_agents(self):
        """방어 에이전트 생성"""
        for s_cfg in self.deployment["sensors"]:
            self.sensor_agents.append(
                SensorAgent(self, s_cfg["type"], s_cfg["id"], s_cfg["pos"])
            )

        c2_key = self.architecture if self.architecture in self.deployment["c2_nodes"] else "linear"
        for c_cfg in self.deployment["c2_nodes"][c2_key]:
            self.c2_agents.append(
                C2NodeAgent(self, c_cfg["type"], c_cfg["id"], c_cfg["pos"])
            )

        for sh_cfg in self.deployment["shooters"]:
            self.shooter_agents.append(
                ShooterAgent(self, sh_cfg["type"], sh_cfg["id"], sh_cfg["pos"])
            )

    def _build_topology(self):
        if self.architecture == "linear":
            return build_linear_topology(
                self.sensor_agents, self.c2_agents, self.shooter_agents
            )
        else:
            return build_killweb_topology(
                self.sensor_agents, self.c2_agents, self.shooter_agents
            )

    def _generate_threats(self):
        threat_specs = generate_threats_for_scenario(
            self.scenario_name, self, seed=self._seed
        )
        self.metrics.total_threats = len(threat_specs)
        for threat_type, pos, target_pos, launch_time in threat_specs:
            self.threat_agents.append(
                ThreatAgent(self, threat_type, pos, target_pos, launch_time)
            )

    # =========================================================================
    # 메인 시뮬레이션 루프
    # =========================================================================
    def step(self):
        """시뮬레이션 한 스텝 실행"""
        if not self.running:
            return

        self.sim_time = self.step_count * self.time_resolution

        # 1. 노드 파괴 확인
        self._check_node_destruction()

        # 2. 위협 활성화 및 이동
        self._activate_and_move_threats()

        # 3. 센서 탐지
        self._sensor_detection()

        # 4. 킬체인 프로세스 시작 (C2 처리 → 교전 대기 큐)
        self._start_killchain_processes()

        # 5. SimPy 환경 진행 (킬체인 지연 처리)
        target_time = self.sim_time + self.time_resolution
        try:
            self.simpy_env.run(until=target_time)
        except simpy.core.EmptySchedule:
            pass

        # 6. 교전 실행 — 교전 대기 큐에서 사거리 진입 위협 교전
        self._execute_engagements()

        # 7. 에이전트 스텝
        for agent in self.sensor_agents:
            agent.step()
        for agent in self.c2_agents:
            agent.step()
        for agent in self.shooter_agents:
            agent.step()

        # 8. Kill Web COP: 아군 상태 공유
        if self.architecture == "killweb":
            self._update_friendly_status()

        # 9. 스냅샷 기록 (시각화 모드)
        if self.record_snapshots:
            self._record_snapshot()

        # 10. 누출 확인
        self._check_leakers()

        # 11. 동시 교전 수 기록
        concurrent = sum(1 for sh in self.shooter_agents if sh.is_engaged)
        self.metrics.record_concurrent_engagements(concurrent, self.sim_time)

        # 12. 종료 조건
        self.step_count += 1
        active = [t for t in self.threat_agents if t.is_alive]
        pending = [t for t in self.threat_agents if t.launch_time > self.sim_time]
        if not active and not pending:
            self.running = False
        if self.sim_time >= self.max_sim_time:
            self.running = False

    # =========================================================================
    # 노드 파괴
    # =========================================================================
    def _check_node_destruction(self):
        for destruction in self.node_destructions:
            target_id = destruction["target"]
            if target_id in self._destroyed_nodes:
                continue
            if abs(self.sim_time - destruction["time"]) < self.time_resolution:
                self._destroyed_nodes.add(target_id)
                for c2 in self.c2_agents:
                    if c2.agent_id == target_id:
                        c2.is_operational = False
                remove_node_from_topology(self.topology, target_id)
                if target_id in self.c2_resources:
                    del self.c2_resources[target_id]

                if self.metrics.node_loss_time is None:
                    self.metrics.node_loss_time = self.sim_time
                    if self.metrics.total_shots > 0:
                        self.metrics.pre_loss_performance = (
                            self.metrics.total_kills / self.metrics.total_shots
                        )
                    else:
                        self.metrics.pre_loss_performance = 1.0

    # =========================================================================
    # 위협 이동
    # =========================================================================
    def _activate_and_move_threats(self):
        for threat in self.threat_agents:
            if threat.is_alive and threat.launch_time <= self.sim_time:
                threat.step()

    # =========================================================================
    # 센서 탐지
    # =========================================================================
    def _sensor_detection(self):
        active_threats = [
            t for t in self.threat_agents
            if t.is_alive and t.launch_time <= self.sim_time
        ]
        for sensor in self.sensor_agents:
            if not sensor.is_operational:
                continue
            for threat in active_threats:
                if not threat.is_detected:
                    if sensor.detect(threat, self.jamming_level, self.detection_factor):
                        threat.is_detected = True
                        threat.detected_time = self.sim_time
                        track_info = sensor.track(threat)
                        self.metrics.record_detection(threat.unique_id, self.sim_time)
                        self._report_to_c2(sensor, track_info)
                else:
                    if sensor.detect(threat, self.jamming_level, self.detection_factor):
                        track_info = sensor.track(threat)
                        self._report_to_c2(sensor, track_info)

    def _report_to_c2(self, sensor, track_info):
        c2_ids = get_connected_c2_for_sensor(self.topology, sensor.agent_id)
        for c2 in self.c2_agents:
            if c2.agent_id in c2_ids and c2.is_operational:
                if self.architecture == "killweb":
                    self._fuse_tracks(track_info["threat_id"], track_info, c2)
                else:
                    c2.receive_track(track_info)

    def _fuse_tracks(self, threat_id, new_track, c2_node):
        """Kill Web: 복수 센서 추적 시 융합 오차 감소 (√N 법칙)"""
        existing = c2_node.air_picture.get(threat_id)
        base_error = ENGAGEMENT_POLICY["tracking_position_error_std"]

        if existing and "tracking_sensors" in existing:
            sensors = existing["tracking_sensors"]
            if new_track["sensor_id"] not in sensors:
                sensors.append(new_track["sensor_id"])
            n = len(sensors)
            if COP_CONFIG["fusion_error_reduction"]:
                fused_error = max(base_error / math.sqrt(n),
                                  COP_CONFIG["min_fused_error"])
            else:
                fused_error = base_error
            existing["fused_error"] = fused_error
            existing["pos"] = new_track["pos"]
            existing["speed"] = new_track["speed"]
            existing["altitude"] = new_track["altitude"]
            existing["time"] = new_track["time"]
        else:
            new_track["tracking_sensors"] = [new_track["sensor_id"]]
            new_track["fused_error"] = base_error
            c2_node.air_picture[threat_id] = new_track

    # =========================================================================
    # 킬체인 프로세스 (SimPy)
    # =========================================================================
    def _start_killchain_processes(self):
        """탐지된 위협에 대해 킬체인(C2 처리) 시작"""
        newly_detected = [
            t for t in self.threat_agents
            if t.is_alive and t.is_detected
            and t.unique_id not in self._threats_in_killchain
        ]

        for threat in newly_detected:
            self._threats_in_killchain.add(threat.unique_id)
            # SimPy 프로세스로 C2 처리 → 완료 시 교전 대기 큐에 등록
            self.simpy_env.process(self._killchain_process(threat))

    def _killchain_process(self, threat):
        """킬체인 프로세스: C2 통신/처리 지연 후 교전 대기 큐 등록"""
        threat_id = threat.unique_id

        if self.architecture == "linear":
            # 선형 킬체인: 센서→C2 → MCRC 큐 대기 → 위협평가 → 승인 → 사수 지정
            # 1. 센서 → C2 보고 전달
            delay = self.comm_channel.get_delay("sensor_to_c2")
            self.killchain.log_event(threat_id, "report_sent",
                                     f"sensor→C2 delay={delay:.1f}s")
            yield self.simpy_env.timeout(delay)

            if not self.comm_channel.is_message_delivered():
                self.killchain.log_event(threat_id, "report_lost", "통신 두절")
                return

            # 2. C2 체인 순차 처리
            operational_c2 = [c for c in self.c2_agents if c.is_operational]
            for c2 in operational_c2:
                if c2.agent_id not in self.c2_resources:
                    continue
                resource = self.c2_resources[c2.agent_id]

                self.killchain.log_event(threat_id, "c2_queue_enter",
                                         f"{c2.agent_id} (load={resource.count}/{resource.capacity})")
                req = resource.request()
                yield req

                proc_delay = self.comm_channel.get_delay("c2_processing")
                self.killchain.log_event(threat_id, "c2_processing",
                                         f"{c2.agent_id} proc={proc_delay:.1f}s")
                yield self.simpy_env.timeout(proc_delay)

                # MCRC에서만 승인 지연
                if c2.node_type == "MCRC":
                    auth_delay = c2.get_auth_delay(self.architecture)
                    self.killchain.log_event(threat_id, "auth_delay",
                                             f"승인 대기={auth_delay:.1f}s")
                    yield self.simpy_env.timeout(auth_delay)

                resource.release(req)
                c2.processed_count += 1
                self.metrics.record_c2_decision(self.simpy_env.now, c2.agent_id)

            # 3. C2 → 사수 통보
            delay = self.comm_channel.get_delay("c2_to_shooter")
            self.killchain.log_event(threat_id, "shooter_notified",
                                     f"C2→shooter delay={delay:.1f}s")
            yield self.simpy_env.timeout(delay)

            if not self.comm_channel.is_message_delivered():
                self.killchain.log_event(threat_id, "assign_lost", "통신 두절")
                return

        else:
            # Kill Web 프로세스: 자동 COP 융합 → 최적 사수 선정 → 교전
            # 1. 자동 COP 융합
            delay = self.comm_channel.get_delay("sensor_to_c2")
            self.killchain.log_event(threat_id, "cop_fusion",
                                     f"auto COP delay={delay:.1f}s")
            yield self.simpy_env.timeout(delay)

            if not self.comm_channel.is_message_delivered():
                self.killchain.log_event(threat_id, "cop_lost", "통신 두절")
                return

            # 2. 가용 C2에서 처리 (부하 분산)
            operational_c2 = [c for c in self.c2_agents if c.is_operational]
            processed = False
            for c2 in operational_c2:
                if c2.agent_id not in self.c2_resources:
                    continue
                resource = self.c2_resources[c2.agent_id]
                if resource.count < resource.capacity:
                    req = resource.request()
                    yield req

                    proc_delay = self.comm_channel.get_delay("c2_processing")
                    self.killchain.log_event(threat_id, "shooter_selection",
                                             f"{c2.agent_id} proc={proc_delay:.1f}s")
                    yield self.simpy_env.timeout(proc_delay)
                    resource.release(req)
                    c2.processed_count += 1
                    self.metrics.record_c2_decision(self.simpy_env.now, c2.agent_id)
                    processed = True
                    break

            if not processed:
                self.killchain.log_event(threat_id, "c2_overloaded", "모든 C2 포화")
                return

            # 3. 사수 통보
            delay = self.comm_channel.get_delay("c2_to_shooter")
            self.killchain.log_event(threat_id, "shooter_notified",
                                     f"C2→shooter delay={delay:.1f}s")
            yield self.simpy_env.timeout(delay)

            if not self.comm_channel.is_message_delivered():
                self.killchain.log_event(threat_id, "assign_lost", "통신 두절")
                return

        # 킬체인 완료 → 교전 대기 큐에 등록
        killchain_time = self.simpy_env.now - (threat.detected_time or 0)
        self.killchain.log_event(threat_id, "cleared_for_engagement",
                                 f"killchain_time={killchain_time:.1f}s")
        self._threats_cleared.add(threat_id)
        self.metrics.record_clearance(threat_id, self.simpy_env.now)

    # =========================================================================
    # 교전 실행
    # =========================================================================
    def _should_engage_now(self, shooter, threat):
        """최적 교전 시점 판단: Pk가 충분하거나, 잔여 기회가 적으면 교전 개시.

        - 현재 Pk ≥ optimal_pk_threshold → 교전
        - 방어지역까지 잔여 거리 ≤ must_engage_distance → 긴급 교전
        - 잔여 교전 기회 ≤ emergency_opportunity_count → emergency_pk_threshold 적용
        - 그 외 → 대기 (다음 스텝에서 위협이 더 가까이 접근)
        """
        policy = ENGAGEMENT_POLICY
        pk = shooter.compute_pk(threat, self.jamming_level)
        defense_target = self.deployment["defense_target"]

        # 1) Pk가 충분하면 즉시 교전
        if pk >= policy["optimal_pk_threshold"]:
            return True

        # 2) 방어지역 근접 → 무조건 교전
        dist_to_target = math.dist(threat.pos, defense_target)
        if dist_to_target <= policy["must_engage_distance"]:
            return True

        # 3) 잔여 교전 기회 계산
        dt = SIM_CONFIG["time_resolution"]
        engagement_cycle = max(shooter.engagement_time + dt, dt)
        time_to_target = dist_to_target / max(threat.speed, 0.001)
        remaining_opportunities = time_to_target / engagement_cycle

        if remaining_opportunities <= policy["emergency_opportunity_count"]:
            # 긴급: 낮은 임계값이라도 교전
            return pk >= policy["emergency_pk_threshold"]

        # 4) 대기 — 위협이 더 가까이 접근할 때까지
        return False

    def _execute_engagements(self):
        """교전 대기 큐의 위협에 대해 사거리 내 사수로 교전 시도.
        v0.4: 위협 우선도 기반 다중 교전 — 고위협에 복수 사수 동시 교전.
        미스 시 다음 스텝에서 재교전 가능."""
        # 교전 대기 중인 살아있는 위협
        cleared_threats = [
            t for t in self.threat_agents
            if t.is_alive
            and t.unique_id in self._threats_cleared
        ]

        if not cleared_threats:
            return

        # 위협 우선순위 정렬 (위협도 높은 순, 거리 가까운 순)
        priority = {"SRBM": 10, "CRUISE_MISSILE": 8, "AIRCRAFT": 6, "UAS": 3}
        defense_target = self.deployment["defense_target"]
        cleared_threats.sort(
            key=lambda t: (
                -priority.get(t.threat_type, 1),
                math.dist(t.pos, defense_target),
            )
        )

        # 이번 스텝에서 교전한 사수 추적 (1사수 1교전/스텝)
        engaged_shooters_this_step = set()
        policy = ENGAGEMENT_POLICY

        for threat in cleared_threats:
            if not threat.is_alive:
                continue

            # 위협 유형별 최대 동시 교전 사수 수 결정 (v0.5: 적응형)
            max_shooters = self._get_adaptive_max_shooters(threat)
            if max_shooters <= 0:
                continue

            # 가용 사수 탐색 (최대 max_shooters기)
            assigned_shooters = []
            for _ in range(max_shooters):
                shooter = self._find_available_shooter(
                    threat, engaged_shooters_this_step
                )
                if not shooter:
                    break
                if not self._should_engage_now(shooter, threat):
                    break
                assigned_shooters.append(shooter)
                engaged_shooters_this_step.add(shooter.agent_id)

            if not assigned_shooters:
                continue

            # Kill Web: 교전 계획 공유
            self._update_engagement_plan(threat, assigned_shooters)
            self._execute_multi_engagement(threat, assigned_shooters)

    def _execute_multi_engagement(self, threat, shooters):
        """다중 사수 동시 교전 실행.
        각 사수는 독립적으로 교전하며, 하나라도 명중하면 격추.
        v0.5: Kill Web 센서 융합 Pk 보너스 적용."""
        if threat.engaged_time is None:
            threat.engaged_time = self.sim_time

        # Kill Web: 센서 융합 Pk 보너스 계산
        fusion_pk_bonus = 0.0
        if self.architecture == "killweb":
            for c2 in self.c2_agents:
                if c2.is_operational and threat.unique_id in c2.air_picture:
                    track = c2.air_picture[threat.unique_id]
                    fused_error = track.get("fused_error",
                                            ENGAGEMENT_POLICY["tracking_position_error_std"])
                    base_error = ENGAGEMENT_POLICY["tracking_position_error_std"]
                    if base_error > 0:
                        fusion_pk_bonus = ((base_error - fused_error) / base_error
                                           * COP_CONFIG["fusion_pk_bonus_max"])
                    break

        # 각 사수별 독립 교전 결과 수집
        individual_hits = []
        for shooter in shooters:
            hit = shooter.engage(threat, self.jamming_level,
                                 pk_bonus=fusion_pk_bonus)
            individual_hits.append((shooter, hit))

            # 최적 사수 비교 (메트릭용 — 첫 번째 사수 기준)
            optimal = self._find_best_shooter(threat)
            optimal_id = optimal.agent_id if optimal else shooter.agent_id

            self.metrics.record_engagement(
                threat.unique_id, self.sim_time,
                shooter.agent_id, hit, optimal_id,
            )

            self.killchain.log_event(
                threat.unique_id, "engagement",
                f"shooter={shooter.agent_id}, hit={hit}, "
                f"Pk={shooter.compute_pk(threat, self.jamming_level):.2f}"
            )

        # 다중 교전 메트릭 기록 (2기 이상일 때만)
        if len(shooters) > 1:
            self.metrics.record_multi_engagement(
                threat.unique_id, self.sim_time, len(shooters)
            )

        # 하나라도 명중하면 격추
        any_hit = any(hit for _, hit in individual_hits)
        if any_hit:
            threat.destroy()

        # 노드 손실 후 첫 교전 → 복구 시간 기록
        if (self.metrics.node_loss_time is not None
                and self.metrics.recovery_time is None):
            self.metrics.recovery_time = self.sim_time
            if self.metrics.total_shots > 0:
                self.metrics.post_loss_performance = (
                    self.metrics.total_kills / self.metrics.total_shots
                )

    # =========================================================================
    # COP 품질 차별화 (v0.5)
    # =========================================================================
    def _update_friendly_status(self):
        """Kill Web: 모든 C2 노드에 아군 사수 상태 공유"""
        for c2 in self.c2_agents:
            if not c2.is_operational:
                continue
            for sh in self.shooter_agents:
                c2.update_friendly_status(sh.agent_id, {
                    "pos": sh.pos,
                    "ammo_remaining": sh.ammo_count,
                    "max_ammo": sh.initial_ammo,
                    "is_engaged": sh.is_engaged,
                    "is_operational": sh.is_operational,
                })

    def _update_engagement_plan(self, threat, assigned_shooters):
        """Kill Web: 교전 계획을 C2 노드에 공유"""
        if self.architecture != "killweb":
            return
        plan = {
            "assigned_shooters": [s.agent_id for s in assigned_shooters],
            "planned_engagement_time": self.sim_time,
            "threat_type": threat.threat_type,
        }
        for c2 in self.c2_agents:
            if c2.is_operational:
                c2.update_engagement_plan(threat.unique_id, plan)

    def _record_snapshot(self):
        """현재 시점 에이전트 상태 스냅샷 기록 (시각화용)"""
        snapshot = {
            "time": self.sim_time,
            "threats": [
                {"id": t.unique_id, "pos": t.pos, "altitude": t.altitude,
                 "speed": t.speed, "alive": t.is_alive, "type": t.threat_type,
                 "detected": t.is_detected}
                for t in self.threat_agents
            ],
            "sensors": [
                {"id": s.agent_id, "pos": s.pos,
                 "tracking": [t.unique_id for t in s.current_tracks],
                 "operational": s.is_operational,
                 "detection_range": s.detection_range}
                for s in self.sensor_agents
            ],
            "shooters": [
                {"id": s.agent_id, "pos": s.pos, "ammo": s.ammo_count,
                 "max_ammo": s.initial_ammo, "engaged": s.is_engaged,
                 "operational": s.is_operational,
                 "max_range": s.max_range, "weapon_type": s.weapon_type}
                for s in self.shooter_agents
            ],
            "c2_nodes": [
                {"id": c.agent_id, "pos": c.pos,
                 "tracks": len(c.air_picture),
                 "operational": c.is_operational}
                for c in self.c2_agents
            ],
            "events": [
                e for e in self.killchain.event_log
                if e["time"] >= self.sim_time - self.time_resolution
                and e["time"] <= self.sim_time
            ],
        }
        self.snapshots.append(snapshot)

    # =========================================================================
    # 적응형 교전 (v0.5)
    # =========================================================================
    def _get_adaptive_max_shooters(self, threat):
        """잔여 탄약 기반 교전 규모 결정 (Kill Web 전용)"""
        if self.architecture != "killweb":
            return ENGAGEMENT_POLICY["max_simultaneous_shooters"].get(
                threat.threat_type,
                ENGAGEMENT_POLICY["default_max_simultaneous"]
            )

        # 가용 사수의 평균 탄약 비율 계산
        available = [s for s in self.shooter_agents
                     if s.is_operational and s.ammo_count > 0]
        if not available:
            return 0

        avg_ammo_ratio = np.mean([s.ammo_count / max(s.initial_ammo, 1)
                                  for s in available])

        if avg_ammo_ratio <= ADAPTIVE_ENGAGEMENT["critical_ammo_ratio"]:
            # 위기 모드: 고위협만 교전
            if threat.threat_type not in ADAPTIVE_ENGAGEMENT["critical_threat_types"]:
                return 0
            return 1

        if avg_ammo_ratio <= ADAPTIVE_ENGAGEMENT["ammo_threshold_ratio"]:
            return ADAPTIVE_ENGAGEMENT["degraded_max_shooters"]

        # 정상 모드: 기존 다중 교전 정책
        return ENGAGEMENT_POLICY["max_simultaneous_shooters"].get(
            threat.threat_type,
            ENGAGEMENT_POLICY["default_max_simultaneous"]
        )

    # =========================================================================
    # 사수 선정
    # =========================================================================
    def _find_available_shooter(self, threat, excluded_shooters=None):
        """교전 가능한 사수 선정 (아키텍처별 로직)"""
        excluded = excluded_shooters or set()
        if self.architecture == "linear":
            return self._find_linear_shooter(threat, excluded)
        else:
            return self._find_best_shooter(threat, excluded)

    def _find_linear_shooter(self, threat, excluded=None):
        """선형 C2: 위협 유형별 고정 우선순위 사수 매칭"""
        excluded = excluded or set()
        type_priority = {
            "SRBM": ["PATRIOT_PAC3", "CHEONGUNG2"],
            "CRUISE_MISSILE": ["PATRIOT_PAC3", "CHEONGUNG2", "KF16"],
            "AIRCRAFT": ["PATRIOT_PAC3", "KF16", "CHEONGUNG2"],
            "UAS": ["BIHO", "CHEONGUNG2"],
        }
        preferred = type_priority.get(threat.threat_type, [])
        for weapon in preferred:
            for sh in self.shooter_agents:
                if (sh.weapon_type == weapon
                        and sh.agent_id not in excluded
                        and sh.can_engage(threat)):
                    return sh
        for sh in self.shooter_agents:
            if sh.agent_id not in excluded and sh.can_engage(threat):
                return sh
        return None

    def _find_best_shooter(self, threat, excluded=None):
        """Kill Web: 가중합 점수 기반 최적 사수 선정.
        v0.5: COP 아군 상태 공유 시 재장전 중 사수 회피, 탄약 풍부 사수 우선."""
        excluded = excluded or set()
        best_score = 0
        best_shooter = None

        # Kill Web COP에서 아군 상태 정보 수집
        friendly_info = {}
        if self.architecture == "killweb":
            for c2 in self.c2_agents:
                if c2.is_operational and c2.friendly_status:
                    friendly_info = c2.friendly_status
                    break

        for sh in self.shooter_agents:
            if sh.agent_id in excluded:
                continue
            score = sh.shooter_score(threat, self.jamming_level)
            if score <= 0:
                continue

            # v0.5: 아군 상태 정보 활용 보너스
            if friendly_info and sh.agent_id in friendly_info:
                status = friendly_info[sh.agent_id]
                ammo_ratio = status["ammo_remaining"] / max(status["max_ammo"], 1)
                if not status["is_engaged"] and ammo_ratio > 0.3:
                    score += COP_CONFIG["friendly_status_bonus"]

            if score > best_score:
                best_score = score
                best_shooter = sh
        return best_shooter

    # =========================================================================
    # 누출 확인
    # =========================================================================
    def _check_leakers(self):
        """방어구역 돌파 확인"""
        for threat in self.threat_agents:
            if (not threat.is_alive
                    and threat.reached_target_time is not None
                    and threat.destroyed_time is None
                    and threat.unique_id not in self._threats_leaked):
                self._threats_leaked.add(threat.unique_id)
                self.metrics.record_leak(threat.unique_id)

    # =========================================================================
    # 결과
    # =========================================================================
    def get_results(self):
        result = {
            "architecture": self.architecture,
            "scenario": self.scenario_name,
            "jamming_level": self.jamming_level,
            "total_steps": self.step_count,
            "sim_time": self.sim_time,
            "metrics": self.metrics.compute_all_metrics(),
            "metrics_flat": self.metrics.to_dict(),
            "topology_stats": get_topology_stats(self.topology),
            "event_log": self.killchain.event_log,
        }
        if self.record_snapshots:
            result["snapshots"] = self.snapshots
            result["config"] = {
                "area_size": SIM_CONFIG["area_size"],
                "defense_target": self.deployment["defense_target"],
            }
        return result

    def run_full(self):
        while self.running:
            self.step()
        return self.get_results()
