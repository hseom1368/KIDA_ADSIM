"""
viz.py - 2D 전술 시각화 모듈 (v0.5)
matplotlib.animation 기반 전투공간 리플레이.

사용법:
    from modules.model import AirDefenseModel
    from modules.viz import TacticalVisualizer

    m = AirDefenseModel(architecture="killweb", scenario="scenario_1_saturation",
                        seed=42, record_snapshots=True)
    result = m.run_full()
    viz = TacticalVisualizer(result)
    viz.render_frame(10)        # 특정 시점 스냅샷
    anim = viz.animate()        # 전체 리플레이
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation


class TacticalVisualizer:
    """2D 전술 시각화 엔진 (matplotlib.animation 기반)"""

    # 에이전트 시각화 설정
    COLORS = {
        "sensor": "#2196F3",         # 파란색
        "c2": "#FF9800",             # 주황색
        "shooter": "#F44336",        # 빨간색
        "threat_active": "#00BCD4",  # 하늘색
        "threat_destroyed": "#9E9E9E",  # 회색
        "threat_leaked": "#E91E63",  # 분홍색
        "defense_target": "#4CAF50", # 녹색
        "killchain": "#FFEB3B",      # 노란색
        "engagement_hit": "#FF5722", # 주홍색
        "engagement_miss": "#BDBDBD",  # 밝은 회색
    }

    MARKERS = {
        "sensor": "^",      # 삼각형
        "c2": "s",           # 사각형
        "shooter": "D",      # 다이아몬드
        "threat": ">",       # 화살표
        "defense_target": "*",  # 별
    }

    def __init__(self, sim_result, figsize=(14, 10)):
        """
        Args:
            sim_result: AirDefenseModel.run_full() 반환값 (record_snapshots=True)
            figsize: 그림 크기
        """
        if "snapshots" not in sim_result:
            raise ValueError("시뮬레이션 결과에 스냅샷이 없습니다. "
                             "record_snapshots=True로 실행하세요.")

        self.snapshots = sim_result["snapshots"]
        self.event_log = sim_result.get("event_log", [])
        self.config = sim_result.get("config", {})
        self.architecture = sim_result.get("architecture", "unknown")
        self.scenario = sim_result.get("scenario", "unknown")
        self.area_size = self.config.get("area_size", 200)
        self.defense_target = self.config.get("defense_target", (100, 50))
        self.figsize = figsize
        self.fig = None
        self.ax = None

    def _setup_axes(self, ax=None):
        """축 설정"""
        if ax is None:
            self.fig, self.ax = plt.subplots(1, 1, figsize=self.figsize)
        else:
            self.ax = ax
            self.fig = ax.figure

        self.ax.set_xlim(-10, self.area_size + 10)
        self.ax.set_ylim(-10, self.area_size + 10)
        self.ax.set_aspect("equal")
        self.ax.grid(True, alpha=0.3, linestyle="--")
        self.ax.set_xlabel("X (km)")
        self.ax.set_ylabel("Y (km)")

    def _draw_snapshot(self, snapshot, ax):
        """단일 스냅샷을 축에 렌더링"""
        ax.clear()
        ax.set_xlim(-10, self.area_size + 10)
        ax.set_ylim(-10, self.area_size + 10)
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.set_xlabel("X (km)")
        ax.set_ylabel("Y (km)")

        time = snapshot["time"]
        ax.set_title(f"{self.architecture.upper()} — {self.scenario}\n"
                     f"T = {time:.0f}s", fontsize=12, fontweight="bold")

        # 방어 목표
        ax.plot(*self.defense_target, marker=self.MARKERS["defense_target"],
                color=self.COLORS["defense_target"], markersize=18,
                markeredgecolor="black", markeredgewidth=1.0, zorder=10)

        # 센서 + 탐지 범위
        for s in snapshot.get("sensors", []):
            if not s.get("operational", True):
                continue
            ax.plot(*s["pos"], marker=self.MARKERS["sensor"],
                    color=self.COLORS["sensor"], markersize=10,
                    markeredgecolor="black", markeredgewidth=0.5, zorder=5)
            circle = plt.Circle(s["pos"], s.get("detection_range", 100),
                                color=self.COLORS["sensor"], fill=False,
                                linestyle=":", alpha=0.3, linewidth=1)
            ax.add_patch(circle)
            ax.text(s["pos"][0], s["pos"][1] - 3, s["id"],
                    fontsize=6, ha="center", color=self.COLORS["sensor"])

        # C2 노드
        for c in snapshot.get("c2_nodes", []):
            if not c.get("operational", True):
                continue
            ax.plot(*c["pos"], marker=self.MARKERS["c2"],
                    color=self.COLORS["c2"], markersize=10,
                    markeredgecolor="black", markeredgewidth=0.5, zorder=5)
            ax.text(c["pos"][0], c["pos"][1] - 3,
                    f'{c["id"]}({c["tracks"]})',
                    fontsize=6, ha="center", color=self.COLORS["c2"])

        # 사수 + 교전 범위
        for sh in snapshot.get("shooters", []):
            if not sh.get("operational", True):
                continue
            color = self.COLORS["shooter"]
            ax.plot(*sh["pos"], marker=self.MARKERS["shooter"],
                    color=color, markersize=10,
                    markeredgecolor="black", markeredgewidth=0.5, zorder=5)
            circle = plt.Circle(sh["pos"], sh.get("max_range", 50),
                                color=color, fill=False,
                                linestyle="--", alpha=0.2, linewidth=1)
            ax.add_patch(circle)
            # 탄약 바
            ammo = sh.get("ammo", 0)
            max_ammo = sh.get("max_ammo", 1)
            ammo_ratio = ammo / max(max_ammo, 1)
            bar_width = 6
            bar_x = sh["pos"][0] - bar_width / 2
            bar_y = sh["pos"][1] + 2
            ax.barh(bar_y, bar_width * ammo_ratio, height=1.5,
                    left=bar_x, color="green" if ammo_ratio > 0.3 else "red",
                    alpha=0.6, edgecolor="black", linewidth=0.3)
            ax.text(sh["pos"][0], sh["pos"][1] - 3,
                    f'{sh["id"]}', fontsize=6, ha="center", color=color)

        # 위협
        for t in snapshot.get("threats", []):
            if t["alive"]:
                ax.plot(*t["pos"], marker=self.MARKERS["threat"],
                        color=self.COLORS["threat_active"], markersize=8,
                        markeredgecolor="black", markeredgewidth=0.5, zorder=7)
                ax.text(t["pos"][0] + 2, t["pos"][1] + 2,
                        f'{t["type"][:4]} h={t["altitude"]:.1f}',
                        fontsize=5, color=self.COLORS["threat_active"])
            else:
                # 격추/누출 표시
                color = self.COLORS["threat_destroyed"]
                ax.plot(*t["pos"], marker="x",
                        color=color, markersize=6, zorder=3)

        # 교전 이벤트
        for evt in snapshot.get("events", []):
            if evt["event"] == "engagement" and "hit=True" in evt.get("detail", ""):
                # 명중 — 폭발 마커
                # threat의 위치를 찾아서 표시
                pass  # 이벤트에 위치 정보가 없으므로 스킵

        # 범례
        legend_elements = [
            mpatches.Patch(color=self.COLORS["sensor"], label="센서"),
            mpatches.Patch(color=self.COLORS["c2"], label="C2"),
            mpatches.Patch(color=self.COLORS["shooter"], label="사수"),
            mpatches.Patch(color=self.COLORS["threat_active"], label="위협(활성)"),
            mpatches.Patch(color=self.COLORS["defense_target"], label="방어목표"),
        ]
        ax.legend(handles=legend_elements, loc="upper right", fontsize=8)

    def render_frame(self, frame_index, ax=None):
        """특정 프레임의 전술 상황도 렌더링"""
        if frame_index < 0 or frame_index >= len(self.snapshots):
            raise IndexError(f"프레임 인덱스 {frame_index} 범위 초과 "
                             f"(0~{len(self.snapshots) - 1})")

        if ax is None:
            self._setup_axes()
            ax = self.ax

        snapshot = self.snapshots[frame_index]
        self._draw_snapshot(snapshot, ax)
        return self.fig

    def animate(self, interval_ms=200, save_path=None):
        """전체 시뮬레이션 리플레이 애니메이션"""
        self._setup_axes()

        def update(frame):
            self._draw_snapshot(self.snapshots[frame], self.ax)

        anim = FuncAnimation(
            self.fig, update,
            frames=len(self.snapshots),
            interval=interval_ms,
            repeat=False,
        )

        if save_path:
            anim.save(save_path, writer="pillow", fps=max(1, 1000 // interval_ms))

        return anim

    def snapshot_comparison(self, frame_index, results_list, labels=None):
        """동일 시점 복수 아키텍처 나란히 비교 스냅샷

        Args:
            frame_index: 비교할 프레임 인덱스
            results_list: [result_linear, result_killweb, ...]
            labels: 각 결과의 레이블
        """
        n = len(results_list)
        if labels is None:
            labels = [r.get("architecture", f"Arch {i}")
                      for i, r in enumerate(results_list)]

        fig, axes = plt.subplots(1, n, figsize=(self.figsize[0], self.figsize[1]))
        if n == 1:
            axes = [axes]

        for i, (result, label) in enumerate(zip(results_list, labels)):
            viz = TacticalVisualizer(result, self.figsize)
            snapshots = result.get("snapshots", [])
            idx = min(frame_index, len(snapshots) - 1)
            if idx >= 0:
                viz._draw_snapshot(snapshots[idx], axes[i])
                axes[i].set_title(f"{label}\nT = {snapshots[idx]['time']:.0f}s",
                                  fontsize=11, fontweight="bold")

        plt.tight_layout()
        return fig

    def event_timeline(self):
        """이벤트 타임라인 바 차트 (탐지/교전/격추/누출)"""
        fig, ax = plt.subplots(figsize=(14, 4))

        event_types = {
            "report_sent": ("탐지 보고", "#2196F3"),
            "cleared_for_engagement": ("교전 승인", "#FF9800"),
            "engagement": ("교전", "#F44336"),
            "cop_fusion": ("COP 융합", "#4CAF50"),
        }

        y_positions = {}
        for i, (etype, (label, color)) in enumerate(event_types.items()):
            y_positions[etype] = i

        for event in self.event_log:
            etype = event["event"]
            if etype in y_positions:
                _, color = event_types[etype]
                ax.barh(y_positions[etype], 0.5,
                        left=event["time"], height=0.6,
                        color=color, alpha=0.7, edgecolor="none")

        ax.set_yticks(list(y_positions.values()))
        ax.set_yticklabels([event_types[k][0] for k in y_positions])
        ax.set_xlabel("시뮬레이션 시간 (초)")
        ax.set_title(f"킬체인 이벤트 타임라인 — {self.architecture.upper()}")
        ax.grid(True, axis="x", alpha=0.3)
        plt.tight_layout()
        return fig
