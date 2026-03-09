"""
metrics.py - 10대 성능 메트릭 수집기
Performance metrics collector for the air defense simulation.
"""

import math
import numpy as np
from collections import defaultdict


class MetricsCollector:
    """10대 성능 메트릭 자동 수집기"""

    def __init__(self):
        self.reset()

    def reset(self):
        """메트릭 초기화"""
        # 이벤트 기록
        self.detection_times = {}       # {threat_id: detection_time}
        self.clearance_times = {}       # {threat_id: killchain_completion_time}
        self.engagement_times = {}      # {threat_id: engagement_time}
        self.engagement_results = {}    # {threat_id: bool (hit)}
        self.shooter_assignments = {}   # {threat_id: shooter_id}
        self.optimal_assignments = {}   # {threat_id: best_shooter_id}

        # 집계 데이터
        self.total_threats = 0
        self.threats_detected = 0
        self.threats_engaged = 0
        self.threats_destroyed = 0
        self.threats_leaked = 0         # 방어구역 돌파
        self.total_shots = 0
        self.total_kills = 0

        # 시간별 동시 교전 수
        self.concurrent_engagements = []

        # C2 처리량
        self.c2_decisions = []          # [(time, c2_id)]

        # 노드 손실 관련
        self.pre_loss_performance = None
        self.post_loss_performance = None
        self.node_loss_time = None
        self.recovery_time = None

        # 킬체인 이벤트 로그
        self.killchain_events = []

        # 사수별 탄약 사용
        self.ammo_usage = {}            # {shooter_id: shots_fired}

    def record_detection(self, threat_id, time):
        """탐지 기록"""
        if threat_id not in self.detection_times:
            self.detection_times[threat_id] = time
            self.threats_detected += 1

    def record_clearance(self, threat_id, time):
        """킬체인 완료 (교전 승인) 시간 기록"""
        if threat_id not in self.clearance_times:
            self.clearance_times[threat_id] = time

    def record_engagement(self, threat_id, time, shooter_id, hit,
                          optimal_shooter_id=None):
        """교전 기록"""
        self.engagement_times[threat_id] = time
        self.engagement_results[threat_id] = hit
        self.shooter_assignments[threat_id] = shooter_id
        self.threats_engaged += 1
        self.total_shots += 1

        if hit:
            self.threats_destroyed += 1
            self.total_kills += 1

        if optimal_shooter_id:
            self.optimal_assignments[threat_id] = optimal_shooter_id

        # 탄약 사용 기록
        self.ammo_usage[shooter_id] = self.ammo_usage.get(shooter_id, 0) + 1

    def record_leak(self, threat_id):
        """방어구역 돌파 기록"""
        self.threats_leaked += 1

    def record_concurrent_engagements(self, count, time):
        """동시 교전 수 기록"""
        self.concurrent_engagements.append((time, count))

    def record_c2_decision(self, time, c2_id):
        """C2 의사결정 기록"""
        self.c2_decisions.append((time, c2_id))

    def record_node_loss(self, time):
        """노드 손실 시점 기록"""
        self.node_loss_time = time

    def record_recovery(self, time):
        """교전 재개 시점 기록"""
        self.recovery_time = time

    # =========================================================================
    # 10대 메트릭 계산
    # =========================================================================

    def compute_all_metrics(self):
        """모든 메트릭 계산 및 반환"""
        return {
            "sensor_to_shooter_time": self.metric_1_sensor_to_shooter(),
            "leaker_rate": self.metric_2_leaker_rate(),
            "engagement_success_rate": self.metric_3_engagement_success(),
            "target_assignment_efficiency": self.metric_4_assignment_efficiency(),
            "max_concurrent_engagements": self.metric_5_concurrent_engagements(),
            "ammo_efficiency": self.metric_6_ammo_efficiency(),
            "system_resilience": self.metric_7_resilience(),
            "c2_throughput": self.metric_8_c2_throughput(),
            "defense_coverage": self.metric_9_defense_coverage(),
            "node_loss_recovery_time": self.metric_10_recovery_time(),
        }

    def metric_1_sensor_to_shooter(self):
        """메트릭 1: 센서-투-슈터 시간 (초)
        = 탐지 → 킬체인 완료(교전 승인) 시간 (C2 지연 측정)"""
        s2s_times = []
        for tid in self.clearance_times:
            if tid in self.detection_times:
                s2s = self.clearance_times[tid] - self.detection_times[tid]
                s2s_times.append(s2s)

        # 킬체인 완료 기록이 없으면 교전 시간 기반으로 fallback
        if not s2s_times:
            for tid in self.engagement_times:
                if tid in self.detection_times:
                    s2s = self.engagement_times[tid] - self.detection_times[tid]
                    s2s_times.append(s2s)

        if not s2s_times:
            return {"mean": float("inf"), "median": float("inf"),
                    "std": 0, "min": float("inf"), "max": float("inf"),
                    "values": []}

        return {
            "mean": np.mean(s2s_times),
            "median": np.median(s2s_times),
            "std": np.std(s2s_times),
            "min": np.min(s2s_times),
            "max": np.max(s2s_times),
            "values": s2s_times,
        }

    def metric_2_leaker_rate(self):
        """메트릭 2: 누출률 (%)"""
        if self.total_threats == 0:
            return 0.0
        return (self.threats_leaked / self.total_threats) * 100

    def metric_3_engagement_success(self):
        """메트릭 3: 교전 성공률 (%)"""
        if self.total_shots == 0:
            return 0.0
        return (self.total_kills / self.total_shots) * 100

    def metric_4_assignment_efficiency(self):
        """메트릭 4: 표적 할당 효율 (%)"""
        if not self.optimal_assignments:
            return 100.0
        matches = sum(
            1 for tid in self.shooter_assignments
            if tid in self.optimal_assignments
            and self.shooter_assignments[tid] == self.optimal_assignments[tid]
        )
        return (matches / max(len(self.shooter_assignments), 1)) * 100

    def metric_5_concurrent_engagements(self):
        """메트릭 5: 동시 교전 능력 (최대 동시 교전 수)"""
        if not self.concurrent_engagements:
            return 0
        return max(c for _, c in self.concurrent_engagements)

    def metric_6_ammo_efficiency(self):
        """메트릭 6: 탄약 효율 (발/격추)"""
        if self.total_kills == 0:
            return float("inf")
        return self.total_shots / self.total_kills

    def metric_7_resilience(self):
        """메트릭 7: 체계 회복탄력성 (%)"""
        if self.pre_loss_performance is None or self.post_loss_performance is None:
            return 100.0
        if self.pre_loss_performance == 0:
            return 0.0
        return (self.post_loss_performance / self.pre_loss_performance) * 100

    def metric_8_c2_throughput(self):
        """메트릭 8: C2 의사결정 처리량 (건/분)"""
        if not self.c2_decisions:
            return 0.0
        times = [t for t, _ in self.c2_decisions]
        if len(times) < 2:
            return len(times) * 60  # 1건이면 분당 환산
        duration_minutes = (max(times) - min(times)) / 60.0
        if duration_minutes <= 0:
            return float("inf")
        return len(self.c2_decisions) / duration_minutes

    def metric_9_defense_coverage(self, shooters=None):
        """메트릭 9: 방어 커버리지 (km²) - 사격체 포락선 합집합 면적 추정"""
        if shooters is None:
            return 0.0
        total_area = 0
        for sh in shooters:
            if sh.is_operational and sh.ammo_count > 0:
                total_area += math.pi * sh.max_range ** 2
        # 중첩 고려 대략적 보정 (70%)
        return total_area * 0.7

    def metric_10_recovery_time(self):
        """메트릭 10: 노드 손실 후 복구시간 (초)"""
        if self.node_loss_time is None or self.recovery_time is None:
            return 0.0
        return self.recovery_time - self.node_loss_time

    def to_dict(self):
        """결과를 딕셔너리로 반환 (DataFrame 변환용)"""
        metrics = self.compute_all_metrics()
        flat = {}
        for key, value in metrics.items():
            if isinstance(value, dict):
                for subkey, subval in value.items():
                    if subkey != "values":
                        flat[f"{key}_{subkey}"] = subval
            else:
                flat[key] = value
        return flat
