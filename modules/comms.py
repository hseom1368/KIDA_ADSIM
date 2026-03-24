"""
comms.py - SimPy 통신 채널 모델
Communication channel model with delays, queuing, and degradation.
"""

import random
import simpy

from .config import COMM_PARAMS, COMM_DEGRADATION


class CommChannel:
    """통신 채널 - 지연, 큐잉, 재밍 열화 모델링
    v0.5: 링크별 차등 열화 + Kill Web 메시 다중 경로 완화"""

    def __init__(self, env, architecture="linear", redundancy_factor=None):
        self.env = env
        self.architecture = architecture
        self.params = COMM_PARAMS[architecture]
        self.jamming_level = 0.0
        self.latency_factor = 1.0
        self.message_log = []
        # v0.5: 링크별 열화 상태
        self.link_degradation = {}  # {(src, dst): degradation_factor}
        # v0.6: 전략에서 주입된 중복 경로 완화 계수 (Gemini #7)
        self.redundancy_factor = (
            redundancy_factor if redundancy_factor is not None
            else COMM_DEGRADATION.get("killweb_redundancy_factor", 0.5)
            if architecture == "killweb" else 1.0
        )

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

    def get_delay(self, link_type, src_id=None, dst_id=None):
        """링크 유형별 지연 시간 반환 (v0.5: 링크별 차등 열화 포함)"""
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

        # v0.5: 링크별 동적 열화 적용
        if self.jamming_level > 0 and src_id and dst_id:
            link_latency = self.get_link_latency(src_id, dst_id)
            if link_latency == float('inf'):
                return float('inf')  # 링크 두절
            return base_delay * link_latency

        return base_delay * self.latency_factor

    def get_link_latency(self, src_id, dst_id):
        """v0.5: 링크별 차등 지연 계산 (재밍 영향 + 아키텍처 완화)"""
        # 링크별 재밍 효과: 재밍 수준에 random perturbation 적용
        link_key = (src_id, dst_id)
        if link_key not in self.link_degradation:
            # 링크별 고유 열화 계수 (0.5~1.5 범위)
            self.link_degradation[link_key] = random.uniform(0.5, 1.5)

        degradation = self.link_degradation[link_key]
        jamming_effect = self.jamming_level * degradation

        # 링크 두절 판정
        if jamming_effect >= COMM_DEGRADATION["link_failure_threshold"]:
            return float('inf')

        latency_multiplier = (COMM_DEGRADATION["base_latency_factor"]
                              + jamming_effect * COMM_DEGRADATION["jamming_latency_multiplier"])

        # 메시 구조 다중 경로로 열화 완화 (전략에서 주입된 계수 사용)
        latency_multiplier *= self.redundancy_factor

        return latency_multiplier

    def is_message_delivered(self, src_id=None, dst_id=None):
        """메시지 전달 성공 여부 (v0.5: 링크별 차등 열화 반영)"""
        resistance = self.params["jamming_resistance"]

        # v0.5: 링크별 열화가 있으면 사용
        if self.jamming_level > 0 and src_id and dst_id:
            link_key = (src_id, dst_id)
            degradation = self.link_degradation.get(link_key, 1.0)
            jamming_effect = self.jamming_level * degradation
            if jamming_effect >= COMM_DEGRADATION["link_failure_threshold"]:
                return False
            failure_prob = jamming_effect * (1 - resistance)
        else:
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

