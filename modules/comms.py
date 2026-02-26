"""
comms.py - SimPy 통신 채널 모델
Communication channel model with delays, queuing, and degradation.
"""

import random
import simpy

from .config import COMM_PARAMS


class CommChannel:
    """통신 채널 - 지연, 큐잉, 재밍 열화 모델링"""

    def __init__(self, env, architecture="linear"):
        self.env = env
        self.architecture = architecture
        self.params = COMM_PARAMS[architecture]
        self.jamming_level = 0.0
        self.latency_factor = 1.0
        self.message_log = []

    def set_jamming(self, level):
        """재밍 수준 설정 (0.0 ~ 1.0)"""
        self.jamming_level = level
        if level <= 0.2:
            self.latency_factor = 1.0
        elif level <= 0.5:
            self.latency_factor = 1.5
        elif level <= 0.8:
            self.latency_factor = 3.0
        else:
            self.latency_factor = 5.0

    def get_delay(self, link_type):
        """링크 유형별 지연 시간 반환 (재밍 보정 포함)"""
        if link_type == "sensor_to_c2":
            delay_range = self.params["sensor_to_c2_delay"]
        elif link_type == "c2_processing":
            delay_range = self.params["c2_processing_delay"]
        elif link_type == "c2_to_shooter":
            delay_range = self.params["c2_to_shooter_delay"]
        elif link_type == "auth":
            delay_range = self.params["auth_delay"]
        else:
            delay_range = (1, 5)

        base_delay = random.uniform(*delay_range)
        return base_delay * self.latency_factor

    def is_message_delivered(self):
        """메시지 전달 성공 여부 (재밍에 의한 통신 두절 가능)"""
        resistance = self.params["jamming_resistance"]
        failure_prob = self.jamming_level * (1 - resistance)
        return random.random() > failure_prob


class KillChainProcess:
    """킬체인 프로세스 - SimPy 기반 이산사건 시뮬레이션"""

    def __init__(self, env, comm_channel, c2_resources, architecture="linear"):
        """
        Args:
            env: SimPy environment
            comm_channel: CommChannel instance
            c2_resources: dict of {c2_id: simpy.Resource}
            architecture: 'linear' or 'killweb'
        """
        self.env = env
        self.comm = comm_channel
        self.c2_resources = c2_resources
        self.architecture = architecture
        self.event_log = []

    def log_event(self, threat_id, event_type, detail=""):
        """이벤트 로그 기록"""
        self.event_log.append({
            "time": self.env.now,
            "threat_id": threat_id,
            "event": event_type,
            "detail": detail,
            "architecture": self.architecture,
        })

    def linear_killchain(self, threat_id, sensor, c2_chain, shooter,
                         engage_callback):
        """
        선형 킬체인 프로세스:
        탐지 → 보고 전달 → MCRC 큐 대기 → 위협평가 → 교전승인 → 사수지정 → 교전
        """
        # 1. 센서 → C2 보고 전달
        delay = self.comm.get_delay("sensor_to_c2")
        self.log_event(threat_id, "report_sent",
                       f"sensor→C2 delay={delay:.1f}s")
        yield self.env.timeout(delay)

        if not self.comm.is_message_delivered():
            self.log_event(threat_id, "report_lost", "통신 두절")
            return False

        # 2. C2 체인을 따라 순차 처리
        for c2_id in c2_chain:
            if c2_id not in self.c2_resources:
                continue

            resource = self.c2_resources[c2_id]

            # C2 큐 대기
            self.log_event(threat_id, "c2_queue_enter",
                           f"{c2_id} queue (capacity={resource.capacity})")
            req = resource.request()
            yield req

            # C2 처리 지연
            proc_delay = self.comm.get_delay("c2_processing")
            self.log_event(threat_id, "c2_processing",
                           f"{c2_id} processing={proc_delay:.1f}s")
            yield self.env.timeout(proc_delay)

            # 승인 지연 (MCRC에서만)
            if c2_id.startswith("MCRC"):
                auth_delay = self.comm.get_delay("auth")
                self.log_event(threat_id, "auth_delay",
                               f"승인 대기={auth_delay:.1f}s")
                yield self.env.timeout(auth_delay)

            resource.release(req)

        # 3. C2 → 사수 지정
        delay = self.comm.get_delay("c2_to_shooter")
        self.log_event(threat_id, "shooter_assigned",
                       f"C2→shooter delay={delay:.1f}s")
        yield self.env.timeout(delay)

        if not self.comm.is_message_delivered():
            self.log_event(threat_id, "assign_lost", "통신 두절")
            return False

        # 4. 교전 실행
        self.log_event(threat_id, "engagement_start", f"shooter={shooter}")
        result = engage_callback()
        self.log_event(threat_id, "engagement_result",
                       f"hit={result}")

        return result

    def killweb_killchain(self, threat_id, sensor, c2_nodes, shooter,
                          engage_callback):
        """
        Kill Web 프로세스:
        탐지 → 자동 COP 융합 → 최적 사수 선정 → 교전
        """
        # 1. 자동 COP 융합 (모든 C2에 동시 전파)
        delay = self.comm.get_delay("sensor_to_c2")
        self.log_event(threat_id, "cop_fusion",
                       f"auto COP fusion delay={delay:.1f}s")
        yield self.env.timeout(delay)

        if not self.comm.is_message_delivered():
            self.log_event(threat_id, "cop_lost", "통신 두절")
            return False

        # 2. 최적 사수 선정 (가용 C2 중 하나에서 처리)
        processed = False
        for c2_id in c2_nodes:
            if c2_id not in self.c2_resources:
                continue
            resource = self.c2_resources[c2_id]
            if resource.count < resource.capacity:
                req = resource.request()
                yield req

                proc_delay = self.comm.get_delay("c2_processing")
                self.log_event(threat_id, "shooter_selection",
                               f"{c2_id} selecting shooter, "
                               f"delay={proc_delay:.1f}s")
                yield self.env.timeout(proc_delay)
                resource.release(req)
                processed = True
                break

        if not processed:
            self.log_event(threat_id, "c2_overloaded", "모든 C2 포화")
            return False

        # 3. C2 → 사수 지정
        delay = self.comm.get_delay("c2_to_shooter")
        self.log_event(threat_id, "shooter_assigned",
                       f"C2→shooter delay={delay:.1f}s")
        yield self.env.timeout(delay)

        if not self.comm.is_message_delivered():
            self.log_event(threat_id, "assign_lost", "통신 두절")
            return False

        # 4. 교전 실행
        self.log_event(threat_id, "engagement_start", f"shooter={shooter}")
        result = engage_callback()
        self.log_event(threat_id, "engagement_result",
                       f"hit={result}")

        return result
