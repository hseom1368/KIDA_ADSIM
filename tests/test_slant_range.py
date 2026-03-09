"""test_slant_range.py - 3D 경사거리 계산 테스트"""

import math
import pytest
from modules.agents import _slant_range


def test_same_position_same_altitude():
    """동일 위치, 동일 고도 → 거리 0"""
    assert _slant_range((10, 20), 5, (10, 20), 5) == 0.0


def test_horizontal_only():
    """고도차 0 → 수평 거리와 일치"""
    result = _slant_range((0, 0), 0, (3, 4), 0)
    expected = math.dist((0, 0), (3, 4))  # 5.0
    assert abs(result - expected) < 1e-10


def test_vertical_only():
    """같은 위치, 고도차만 → 고도차"""
    result = _slant_range((5, 5), 0, (5, 5), 10)
    assert abs(result - 10.0) < 1e-10


def test_3_4_5_triangle():
    """3-4-5 삼각형: 수평 3km, 고도차 4km → 5km"""
    result = _slant_range((0, 0), 0, (3, 0), 4)
    assert abs(result - 5.0) < 1e-10


def test_symmetry():
    """대칭성: slant_range(A,B) == slant_range(B,A)"""
    r1 = _slant_range((10, 20), 5, (30, 40), 15)
    r2 = _slant_range((30, 40), 15, (10, 20), 5)
    assert abs(r1 - r2) < 1e-10
