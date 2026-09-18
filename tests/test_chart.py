"""Chart geometry is arithmetic, so it is tested like arithmetic.

These tests exist because the browser cannot check any of this. If the scaling is
wrong, the page draws a confident line through the wrong shape.
"""

from __future__ import annotations

import pytest

from woong.api.chart import Point, bar_geometry, line_geometry, line_windows


def _points(values: list[float]) -> list[Point]:
    return [Point(date=f"2026-09-{index + 1:02d}", value=value) for index, value in enumerate(values)]


def test_line_geometry_puts_the_high_at_the_top_pad() -> None:
    geometry = line_geometry(_points([100.0, 110.0, 120.0]), width=100, height=50, pad=5)
    coords = [tuple(float(part) for part in pair.split(",")) for pair in geometry["points"].split(" ")]
    assert coords[0] == (5.0, 45.0)
    assert coords[-1] == (95.0, 5.0)
    assert geometry["low"] == pytest.approx(100.0)
    assert geometry["high"] == pytest.approx(120.0)
    assert geometry["low_date"] == "2026-09-01"
    assert geometry["high_date"] == "2026-09-03"


def test_a_flat_window_is_drawn_flat_not_stretched() -> None:
    geometry = line_geometry(_points([50.0, 50.0, 50.0]), width=100, height=50, pad=5)
    ys = {pair.split(",")[1] for pair in geometry["points"].split(" ")}
    assert ys == {"25.00"}
    assert geometry["flat"] is True


def test_one_session_is_refused() -> None:
    with pytest.raises(ValueError, match="at least two"):
        line_geometry(_points([100.0]))


def test_a_short_window_reports_what_it_had() -> None:
    windows = line_windows(_points([100.0, 101.0, 102.0]))
    assert len(windows) == 1
    assert windows[0]["session_count"] == 3
    assert windows[0]["short"] is True
    assert windows[0]["label"] == "All stored sessions"


def test_bar_geometry_places_a_zero_line_and_skips_a_missing_slot() -> None:
    geometry = bar_geometry(["Jan", "Feb", "Mar"], [0.02, None, -0.02], width=100, height=50, pad=5)
    assert geometry["zero_y"] == pytest.approx(25.0)
    assert geometry["missing_count"] == 1
    jan, feb, mar = geometry["bars"]
    assert jan["sign"] == "up"
    assert jan["y"] == pytest.approx(5.0)
    assert feb["missing"] is True
    assert "value" not in feb
    assert mar["sign"] == "down"
    assert mar["y"] == pytest.approx(25.0)


def test_bar_geometry_refuses_an_all_missing_series() -> None:
    with pytest.raises(ValueError, match="No stored value"):
        bar_geometry(["Jan", "Feb"], [None, None])
