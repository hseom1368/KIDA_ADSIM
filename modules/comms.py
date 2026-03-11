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

