"""
strategies.py - 아키텍처 전략 패턴
Architecture strategy pattern: Linear C2 vs Kill Web.

각 전략은 킬체인, 토폴로지 구축, 사수 선정 등 아키텍처별 분기를
캡슐화하여 model.py에서 if/else 분기를 제거한다.
"""

from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generator, Optional, Set

import numpy as np
import networkx as nx

from .config import (
    COMM_PARAMS, ENGAGEMENT_POLICY, COP_CONFIG,
    ADAPTIVE_ENGAGEMENT, COMM_DEGRADATION,
)
from .network import (
    build_linear_topology, build_killweb_topology,
)

if TYPE_CHECKING:
    from .model import AirDefenseModel
    from .agents import ShooterAgent, ThreatAgent
    from .registry import EntityRegistry


class ArchitectureStrategy(ABC):
    """아키텍처 전략 추상 기본 클래스"""

    def __init__(self, registry: EntityRegistry):
        self.registry = registry

    @abstractmethod
    def build_topology(self, sensors, c2_nodes, shooters) -> nx.DiGraph:
        """네트워크 토폴로지 구축"""
        ...

    @abstractmethod
    def run_killchain(self, model: AirDefenseModel, threat: ThreatAgent) -> Generator:
        """SimPy 킬체인 프로세스 (generator)"""
        ...

    @abstractmethod
    def select_shooter(
        self, model: AirDefenseModel, threat: ThreatAgent,
        excluded: Optional[Set[str]] = None,
    ) -> Optional[ShooterAgent]:
        """최적 사수 선정"""
        ...

    @abstractmethod
    def fuse_tracks(self, threat_id, track_info, c2_node) -> None:
        """센서 추적 보고 처리 (융합 또는 단순 수신)"""
        ...

    @abstractmethod
    def update_cop(self, model: AirDefenseModel) -> None:
        """COP 갱신 (아군 상태 공유 등)"""
        ...

    @abstractmethod
    def get_max_simultaneous(self, model: AirDefenseModel, threat: ThreatAgent) -> int:
        """위협당 최대 동시 교전 사수 수"""
        ...

    @abstractmethod
    def compute_fusion_bonus(self, model: AirDefenseModel, threat: ThreatAgent) -> float:
        """센서 융합 Pk 보너스"""
        ...

    @abstractmethod
    def share_engagement_plan(
        self, model: AirDefenseModel, threat: ThreatAgent, shooters: list,
    ) -> None:
        """교전 계획 공유"""
        ...

    def get_redundancy_factor(self) -> float:
        """통신 중복 경로 완화 계수 (Gemini #7)"""
        return 1.0


# =============================================================================
# 선형 C2 전략
# =============================================================================

class LinearC2Strategy(ArchitectureStrategy):
    """선형 C2 아키텍처: 계층적 킬체인, 고정 사수 매칭"""

    def build_topology(self, sensors, c2_nodes, shooters) -> nx.DiGraph:
        return build_linear_topology(sensors, c2_nodes, shooters)

    def run_killchain(self, model: AirDefenseModel, threat: ThreatAgent) -> Generator:
        """선형 킬체인: 센서→C2 → MCRC 큐 대기 → 위협평가 → 승인 → 사수 지정"""
        threat_id = threat.unique_id

        # 1. 센서 → C2 보고 전달
        delay = model.comm_channel.get_delay("sensor_to_c2")
        model.killchain.log_event(threat_id, "report_sent",
                                  f"sensor→C2 delay={delay:.1f}s")
        yield model.simpy_env.timeout(delay)

        if not model.comm_channel.is_message_delivered():
            model.killchain.log_event(threat_id, "report_lost", "통신 두절")
            return

        # 2. C2 체인 순차 처리
        operational_c2 = [c for c in model.c2_agents if c.is_operational]
        for c2 in operational_c2:
            if c2.agent_id not in model.c2_resources:
                continue
            resource = model.c2_resources[c2.agent_id]

            model.killchain.log_event(
                threat_id, "c2_queue_enter",
                f"{c2.agent_id} (load={resource.count}/{resource.capacity})")
            req = resource.request()
            yield req

            proc_delay = model.comm_channel.get_delay("c2_processing")
            model.killchain.log_event(
                threat_id, "c2_processing",
                f"{c2.agent_id} proc={proc_delay:.1f}s")
            yield model.simpy_env.timeout(proc_delay)

            # MCRC에서만 승인 지연
            if c2.node_type == "MCRC":
                auth_delay = c2.get_auth_delay("linear")
                model.killchain.log_event(
                    threat_id, "auth_delay",
                    f"승인 대기={auth_delay:.1f}s")
                yield model.simpy_env.timeout(auth_delay)

            resource.release(req)
            c2.processed_count += 1
            model.metrics.record_c2_decision(model.simpy_env.now, c2.agent_id)

        # 3. C2 → 사수 통보
        delay = model.comm_channel.get_delay("c2_to_shooter")
        model.killchain.log_event(
            threat_id, "shooter_notified",
            f"C2→shooter delay={delay:.1f}s")
        yield model.simpy_env.timeout(delay)

        if not model.comm_channel.is_message_delivered():
            model.killchain.log_event(threat_id, "assign_lost", "통신 두절")
            return

        # 킬체인 완료
        killchain_time = model.simpy_env.now - (threat.detected_time or 0)
        model.killchain.log_event(
            threat_id, "cleared_for_engagement",
            f"killchain_time={killchain_time:.1f}s")
        model._threats_cleared.add(threat_id)
        model.metrics.record_clearance(threat_id, model.simpy_env.now)

    def select_shooter(
        self, model: AirDefenseModel, threat: ThreatAgent,
        excluded: Optional[Set[str]] = None,
    ) -> Optional[ShooterAgent]:
        """선형 C2: Pk 기반 우선순위 사수 매칭 (Gemini #6)"""
        excluded = excluded or set()
        prioritized = self.registry.get_prioritized_shooters(threat.threat_type)
        preferred_types = [st.type_id for st in prioritized]

        for weapon in preferred_types:
            for sh in model.shooter_agents:
                if (sh.weapon_type == weapon
                        and sh.agent_id not in excluded
                        and sh.can_engage(threat)):
                    return sh

        # Fallback: 아무 교전 가능한 사수
        for sh in model.shooter_agents:
            if sh.agent_id not in excluded and sh.can_engage(threat):
                return sh
        return None

    def fuse_tracks(self, threat_id, track_info, c2_node) -> None:
        """선형 C2: 단순 항적 수신"""
        c2_node.receive_track(track_info)

    def update_cop(self, model: AirDefenseModel) -> None:
        """선형 C2: COP 업데이트 없음 (위협 항적만 유지)"""
        pass

    def get_max_simultaneous(self, model: AirDefenseModel, threat: ThreatAgent) -> int:
        """선형 C2: 고정 다중 교전 정책"""
        return ENGAGEMENT_POLICY["max_simultaneous_shooters"].get(
            threat.threat_type,
            ENGAGEMENT_POLICY["default_max_simultaneous"],
        )

    def compute_fusion_bonus(self, model: AirDefenseModel, threat: ThreatAgent) -> float:
        """선형 C2: 센서 융합 없음"""
        return 0.0

    def share_engagement_plan(
        self, model: AirDefenseModel, threat: ThreatAgent, shooters: list,
    ) -> None:
        """선형 C2: 교전 계획 공유 없음"""
        pass

    def get_redundancy_factor(self) -> float:
        return 1.0


# =============================================================================
# Kill Web 전략
# =============================================================================

class KillWebStrategy(ArchitectureStrategy):
    """Kill Web 아키텍처: 분산 COP, 최적 사수 선정, 적응형 교전"""

    def build_topology(self, sensors, c2_nodes, shooters) -> nx.DiGraph:
        return build_killweb_topology(sensors, c2_nodes, shooters)

    def run_killchain(self, model: AirDefenseModel, threat: ThreatAgent) -> Generator:
        """Kill Web 킬체인: 자동 COP 융합 → 최적 사수 선정 → 교전"""
        threat_id = threat.unique_id

        # 1. 자동 COP 융합
        delay = model.comm_channel.get_delay("sensor_to_c2")
        model.killchain.log_event(
            threat_id, "cop_fusion",
            f"auto COP delay={delay:.1f}s")
        yield model.simpy_env.timeout(delay)

        if not model.comm_channel.is_message_delivered():
            model.killchain.log_event(threat_id, "cop_lost", "통신 두절")
            return

        # 2. 가용 C2에서 처리 (부하 분산)
        operational_c2 = [c for c in model.c2_agents if c.is_operational]
        processed = False
        for c2 in operational_c2:
            if c2.agent_id not in model.c2_resources:
                continue
            resource = model.c2_resources[c2.agent_id]
            if resource.count < resource.capacity:
                req = resource.request()
                yield req

                proc_delay = model.comm_channel.get_delay("c2_processing")
                model.killchain.log_event(
                    threat_id, "shooter_selection",
                    f"{c2.agent_id} proc={proc_delay:.1f}s")
                yield model.simpy_env.timeout(proc_delay)
                resource.release(req)
                c2.processed_count += 1
                model.metrics.record_c2_decision(model.simpy_env.now, c2.agent_id)
                processed = True
                break

        if not processed:
            model.killchain.log_event(threat_id, "c2_overloaded", "모든 C2 포화")
            return

        # 3. 사수 통보
        delay = model.comm_channel.get_delay("c2_to_shooter")
        model.killchain.log_event(
            threat_id, "shooter_notified",
            f"C2→shooter delay={delay:.1f}s")
        yield model.simpy_env.timeout(delay)

        if not model.comm_channel.is_message_delivered():
            model.killchain.log_event(threat_id, "assign_lost", "통신 두절")
            return

        # 킬체인 완료
        killchain_time = model.simpy_env.now - (threat.detected_time or 0)
        model.killchain.log_event(
            threat_id, "cleared_for_engagement",
            f"killchain_time={killchain_time:.1f}s")
        model._threats_cleared.add(threat_id)
        model.metrics.record_clearance(threat_id, model.simpy_env.now)

    def select_shooter(
        self, model: AirDefenseModel, threat: ThreatAgent,
        excluded: Optional[Set[str]] = None,
    ) -> Optional[ShooterAgent]:
        """Kill Web: 가중합 점수 기반 최적 사수 선정 + COP 아군 상태 보너스"""
        excluded = excluded or set()
        best_score = 0
        best_shooter = None

        # COP에서 아군 상태 정보 수집
        friendly_info = {}
        for c2 in model.c2_agents:
            if c2.is_operational and c2.friendly_status:
                friendly_info = c2.friendly_status
                break

        for sh in model.shooter_agents:
            if sh.agent_id in excluded:
                continue
            score = sh.shooter_score(threat, model.jamming_level)
            if score <= 0:
                continue

            # 아군 상태 정보 활용 보너스
            if friendly_info and sh.agent_id in friendly_info:
                status = friendly_info[sh.agent_id]
                ammo_ratio = status["ammo_remaining"] / max(status["max_ammo"], 1)
                if not status["is_engaged"] and ammo_ratio > 0.3:
                    score += COP_CONFIG["friendly_status_bonus"]

            if score > best_score:
                best_score = score
                best_shooter = sh
        return best_shooter

    def fuse_tracks(self, threat_id, track_info, c2_node) -> None:
        """Kill Web: 복수 센서 추적 시 융합 오차 감소 (√N 법칙)"""
        existing = c2_node.air_picture.get(threat_id)
        base_error = ENGAGEMENT_POLICY["tracking_position_error_std"]

        if existing and "tracking_sensors" in existing:
            sensors = existing["tracking_sensors"]
            if track_info["sensor_id"] not in sensors:
                sensors.append(track_info["sensor_id"])
            n = len(sensors)
            if COP_CONFIG["fusion_error_reduction"]:
                fused_error = max(
                    base_error / math.sqrt(n),
                    COP_CONFIG["min_fused_error"],
                )
            else:
                fused_error = base_error
            existing["fused_error"] = fused_error
            existing["pos"] = track_info["pos"]
            existing["speed"] = track_info["speed"]
            existing["altitude"] = track_info["altitude"]
            existing["time"] = track_info["time"]
        else:
            track_info["tracking_sensors"] = [track_info["sensor_id"]]
            track_info["fused_error"] = base_error
            c2_node.air_picture[threat_id] = track_info

    def update_cop(self, model: AirDefenseModel) -> None:
        """Kill Web: 모든 C2 노드에 아군 사수 상태 공유"""
        for c2 in model.c2_agents:
            if not c2.is_operational:
                continue
            for sh in model.shooter_agents:
                c2.update_friendly_status(sh.agent_id, {
                    "pos": sh.pos,
                    "ammo_remaining": sh.ammo_count,
                    "max_ammo": sh.initial_ammo,
                    "is_engaged": sh.is_engaged,
                    "is_operational": sh.is_operational,
                })

    def get_max_simultaneous(self, model: AirDefenseModel, threat: ThreatAgent) -> int:
        """Kill Web: 잔여 탄약 기반 적응형 교전 규모 결정"""
        available = [
            s for s in model.shooter_agents
            if s.is_operational and s.ammo_count > 0
        ]
        if not available:
            return 0

        avg_ammo_ratio = np.mean([
            s.ammo_count / max(s.initial_ammo, 1)
            for s in available
        ])

        if avg_ammo_ratio <= ADAPTIVE_ENGAGEMENT["critical_ammo_ratio"]:
            if threat.threat_type not in ADAPTIVE_ENGAGEMENT["critical_threat_types"]:
                return 0
            return 1

        if avg_ammo_ratio <= ADAPTIVE_ENGAGEMENT["ammo_threshold_ratio"]:
            return ADAPTIVE_ENGAGEMENT["degraded_max_shooters"]

        return ENGAGEMENT_POLICY["max_simultaneous_shooters"].get(
            threat.threat_type,
            ENGAGEMENT_POLICY["default_max_simultaneous"],
        )

    def compute_fusion_bonus(self, model: AirDefenseModel, threat: ThreatAgent) -> float:
        """Kill Web: 센서 융합 Pk 보너스 계산"""
        for c2 in model.c2_agents:
            if c2.is_operational and threat.unique_id in c2.air_picture:
                track = c2.air_picture[threat.unique_id]
                fused_error = track.get(
                    "fused_error",
                    ENGAGEMENT_POLICY["tracking_position_error_std"],
                )
                base_error = ENGAGEMENT_POLICY["tracking_position_error_std"]
                if base_error > 0:
                    return (
                        (base_error - fused_error) / base_error
                        * COP_CONFIG["fusion_pk_bonus_max"]
                    )
                break
        return 0.0

    def share_engagement_plan(
        self, model: AirDefenseModel, threat: ThreatAgent, shooters: list,
    ) -> None:
        """Kill Web: 교전 계획을 C2 노드에 공유"""
        plan = {
            "assigned_shooters": [s.agent_id for s in shooters],
            "planned_engagement_time": model.sim_time,
            "threat_type": threat.threat_type,
        }
        for c2 in model.c2_agents:
            if c2.is_operational:
                c2.update_engagement_plan(threat.unique_id, plan)

    def get_redundancy_factor(self) -> float:
        """Kill Web: 메시 구조 다중 경로 완화"""
        return COMM_DEGRADATION["killweb_redundancy_factor"]
