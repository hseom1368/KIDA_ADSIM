"""v0.5 시각화 모듈 테스트"""

import pytest
import matplotlib
matplotlib.use("Agg")  # 비대화형 백엔드

from modules.model import AirDefenseModel
from modules.viz import TacticalVisualizer


@pytest.fixture
def viz_result():
    """Kill Web S1 시뮬레이션 결과 (스냅샷 포함)"""
    m = AirDefenseModel(architecture="killweb",
                        scenario="scenario_1_saturation", seed=42,
                        record_snapshots=True)
    return m.run_full()


class TestTacticalVisualizer:
    def test_init_requires_snapshots(self):
        """스냅샷 없으면 ValueError"""
        m = AirDefenseModel(architecture="killweb",
                            scenario="scenario_1_saturation", seed=42)
        result = m.run_full()
        with pytest.raises(ValueError):
            TacticalVisualizer(result)

    def test_snapshot_data_recorded(self, viz_result):
        """스냅샷 데이터 정상 수집 확인"""
        assert len(viz_result["snapshots"]) > 0
        snap = viz_result["snapshots"][0]
        assert "time" in snap
        assert "threats" in snap
        assert "sensors" in snap
        assert "shooters" in snap

    def test_render_frame_no_error(self, viz_result):
        """render_frame() 에러 없이 렌더링"""
        viz = TacticalVisualizer(viz_result)
        fig = viz.render_frame(0)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close("all")

    def test_render_frame_out_of_bounds(self, viz_result):
        """범위 초과 프레임 인덱스 시 IndexError"""
        viz = TacticalVisualizer(viz_result)
        with pytest.raises(IndexError):
            viz.render_frame(999999)

    def test_event_timeline_no_error(self, viz_result):
        """event_timeline() 에러 없이 렌더링"""
        viz = TacticalVisualizer(viz_result)
        fig = viz.event_timeline()
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close("all")
