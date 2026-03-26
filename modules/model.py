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
    SCENARIO_PARAMS, ENGAGEMENT_POLICY,
)
from .agents import SensorAgent, C2NodeAgent, ShooterAgent, ThreatAgent
from .network import (
    remove_node_from_topology, get_connected_c2_for_sensor,
    get_topology_stats,
)
from .comms import CommChannel, KillChainProcess
from .threats import generate_threats_for_scenario, get_scenario_node_destructions
from .metrics import MetricsCollector
from .registry import EntityRegistry
from .strategies import LinearC2Strategy, KillWebStrategy


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

        # 1. Registry 초기화 (Gemini #9)
        self.registry = EntityRegistry()
        self.registry.load_from_config()

        # 2. Strategy 선택 (model.py에 남는 유일한 architecture 분기)
        if architecture == "linear":
            self.strategy = LinearC2Strategy(self.registry)
        else:
            self.strategy = KillWebStrategy(self.registry)

        # 3. 에이전트 생성
        self.sensor_agents = []
        self.c2_agents = []
        self.shooter_agents = []
        self.threat_agents = []
        self._create_defense_agents()
        self.metrics.shooters = self.shooter_agents

        # 4. 네트워크 토폴로지 (strategy 위임)
        self.topology = self.strategy.build_topology(
            self.sensor_agents, self.c2_agents, self.shooter_agents
        )

        # 5. 통신 채널 (redundancy_factor 주입 — Gemini #7)
        self.comm_channel = CommChannel(
            self.simpy_env, architecture,
            redundancy_factor=self.strategy.get_redundancy_factor(),
        )
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

        # 6. 킬체인 프로세스
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
        # v0.7.2: 다층 교전 핸드오프 추적
        self._threats_engaged_layers = {}       # {threat_id: set(shooter_types)}
        # v0.7.2: 중복교전 — 축별 cleared 추적 (Linear 3축)
        self._threats_cleared_by_axis = {}      # {axis: set(threat_ids)}

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

        # 8. COP 갱신 (strategy 위임)
        self.strategy.update_cop(self)

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
        """센서 보고를 C2로 전달 (strategy 위임)"""
        c2_ids = get_connected_c2_for_sensor(self.topology, sensor.agent_id)
        for c2 in self.c2_agents:
            if c2.agent_id in c2_ids and c2.is_operational:
                self.strategy.fuse_tracks(track_info["threat_id"], track_info, c2)

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
            # v0.7.1: 위협 식별 결과 기록은 strategy.run_killchain 내에서 수행
            # strategy 위임: 아키텍처별 킬체인 프로세스
            self.simpy_env.process(self.strategy.run_killchain(self, threat))

    # =========================================================================
    # 교전 실행
    # =========================================================================
    def _should_engage_now(self, shooter, threat):
        """최적 교전 시점 판단: Pk가 충분하거나, 잔여 기회가 적으면 교전 개시."""
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
            return pk >= policy["emergency_pk_threshold"]

        # 4) 대기
        return False

    def _execute_engagements(self):
        """교전 대기 큐의 위협에 대해 사거리 내 사수로 교전 시도."""
        cleared_threats = [
            t for t in self.threat_agents
            if t.is_alive
            and t.unique_id in self._threats_cleared
        ]

        if not cleared_threats:
            return

        # 위협 우선순위 정렬 (v0.7.1: identified_type 기준)
        priority = {"SRBM": 10, "MLRS_GUIDED": 7, "CRUISE_MISSILE": 8,
                     "AIRCRAFT": 6, "UAS": 3}
        defense_target = self.deployment["defense_target"]
        cleared_threats.sort(
            key=lambda t: (
                -priority.get(t.identified_type, 1),
                math.dist(t.pos, defense_target),
            )
        )

        engaged_shooters_this_step = set()

        for threat in cleared_threats:
            if not threat.is_alive:
                continue

            # strategy 위임: 최대 동시 교전 사수 수
            max_shooters = self.strategy.get_max_simultaneous(self, threat)
            if max_shooters <= 0:
                continue

            # v0.7.2: 이미 교전 시도한 사수 유형은 제외 (다층 핸드오프)
            tried_types = self._threats_engaged_layers.get(threat.unique_id, set())
            type_excluded = set()
            for sh in self.shooter_agents:
                if sh.weapon_type in tried_types:
                    type_excluded.add(sh.agent_id)
            combined_excluded = engaged_shooters_this_step | type_excluded

            assigned_shooters = []
            for _ in range(max_shooters):
                # strategy 위임: 사수 선정
                shooter = self.strategy.select_shooter(
                    self, threat, combined_excluded
                )
                if not shooter:
                    break
                if not self._should_engage_now(shooter, threat):
                    break
                assigned_shooters.append(shooter)
                engaged_shooters_this_step.add(shooter.agent_id)
                combined_excluded.add(shooter.agent_id)

            if not assigned_shooters:
                continue

            # strategy 위임: 교전 계획 공유
            self.strategy.share_engagement_plan(self, threat, assigned_shooters)
            self._execute_multi_engagement(threat, assigned_shooters)

    def _execute_multi_engagement(self, threat, shooters):
        """다중 사수 동시 교전 실행."""
        if threat.engaged_time is None:
            threat.engaged_time = self.sim_time

        # strategy 위임: 센서 융합 Pk 보너스
        fusion_pk_bonus = self.strategy.compute_fusion_bonus(self, threat)

        individual_hits = []
        for shooter in shooters:
            hit = shooter.engage(threat, self.jamming_level,
                                 pk_bonus=fusion_pk_bonus)
            individual_hits.append((shooter, hit))

            # v0.7.2: 다층 교전 추적 — 교전 시도한 사수 유형 기록
            tid = threat.unique_id
            if tid not in self._threats_engaged_layers:
                self._threats_engaged_layers[tid] = set()
            self._threats_engaged_layers[tid].add(shooter.weapon_type)

            # 최적 사수 비교 (메트릭용)
            optimal = self.strategy.select_shooter(self, threat)
            optimal_id = optimal.agent_id if optimal else shooter.agent_id

            self.metrics.record_engagement(
                threat.unique_id, self.sim_time,
                shooter.agent_id, hit, optimal_id,
            )

            # v0.7.1: 고가 자산 소모 기록
            if hasattr(threat, 'cost_ratio'):
                self.metrics.record_expensive_asset_use(
                    shooter.weapon_type, threat.actual_type, threat.cost_ratio,
                )

            # v0.7.2: 교전 계층 기록
            self.metrics.record_layer_attempt(
                threat.unique_id, shooter.weapon_type, self.sim_time, hit,
            )
            if hasattr(threat, 'engagement_attempts'):
                threat.engagement_attempts.append(
                    (shooter.weapon_type, self.sim_time, hit))

            self.killchain.log_event(
                threat.unique_id, "engagement",
                f"shooter={shooter.agent_id}, hit={hit}, "
                f"Pk={shooter.compute_pk(threat, self.jamming_level):.2f}"
            )

        if len(shooters) > 1:
            self.metrics.record_multi_engagement(
                threat.unique_id, self.sim_time, len(shooters)
            )

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
    # 역호환 위임 메서드
    # =========================================================================
    def _get_adaptive_max_shooters(self, threat):
        """역호환: strategy.get_max_simultaneous() 위임"""
        return self.strategy.get_max_simultaneous(self, threat)

    def _find_available_shooter(self, threat, excluded_shooters=None):
        """역호환: strategy.select_shooter() 위임"""
        return self.strategy.select_shooter(self, threat, excluded_shooters)

    def _find_best_shooter(self, threat, excluded=None):
        """역호환: strategy.select_shooter() 위임 (Kill Web 전용)"""
        return self.strategy.select_shooter(self, threat, excluded)

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
