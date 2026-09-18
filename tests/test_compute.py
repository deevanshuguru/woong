"""Hand-worked examples for close-to-close returns and moving averages."""

from __future__ import annotations

import pandas as pd
import pytest

from woong.ingest.http import encode_path
from woong.metrics.compute import (
    close_to_close_return,
    distance_from_average,
    metrics_as_of,
    return_volatility,
    simple_moving_average,
)
from woong.metrics.display import display_value, to_percent


def test_close_to_close_return_is_hand_worked() -> None:
    assert close_to_close_return(121.0, 110.0) == pytest.approx(0.1)
    assert close_to_close_return(121.0, 100.0) == pytest.approx(0.21)
    assert pd.isna(close_to_close_return(121.0, 0.0))
    assert pd.isna(close_to_close_return(121.0, float("nan")))


def test_simple_moving_average_needs_a_full_window() -> None:
    assert simple_moving_average([1.0, 2.0, 3.0, 4.0], 3) == pytest.approx(3.0)
    assert pd.isna(simple_moving_average([1.0, 2.0], 3))


def test_metrics_as_of_uses_the_as_of_session_only() -> None:
    prices = pd.DataFrame(
        [
            {"symbol": "AAA", "exchange": "NSE", "date": "2026-09-09", "close": 100.0},
            {"symbol": "AAA", "exchange": "NSE", "date": "2026-09-10", "close": 110.0},
            {"symbol": "AAA", "exchange": "NSE", "date": "2026-09-11", "close": 121.0},
        ]
    )
    frame = metrics_as_of(prices, "2026-09-11")
    assert len(frame) == 1
    assert frame.iloc[0]["close"] == 121.0
    assert frame.iloc[0]["return_1d"] == pytest.approx(0.1)
    assert pd.isna(frame.iloc[0]["return_1w"])
    assert pd.isna(frame.iloc[0]["sma_200"])


def test_distance_from_average_is_a_ratio() -> None:
    assert distance_from_average(110.0, 100.0) == pytest.approx(0.1)
    assert distance_from_average(90.0, 100.0) == pytest.approx(-0.1)
    assert pd.isna(distance_from_average(110.0, 0.0))
    assert pd.isna(distance_from_average(110.0, float("nan")))


def test_volatility_needs_a_full_window_of_returns() -> None:
    # Two returns of +10 percent and -10 percent: the sample standard deviation
    # of 0.1 and -0.1 is 0.1 * sqrt(2).
    closes = [100.0, 110.0, 99.0]
    assert return_volatility(closes, window=2) == pytest.approx(0.1414, abs=1e-4)
    assert pd.isna(return_volatility([100.0, 110.0], window=2))
    with pytest.raises(ValueError, match="at least two"):
        return_volatility(closes, window=1)


def test_display_value_and_percent_conversion_live_in_python() -> None:
    assert display_value(0.2015, "ratio") == "20.15%"
    assert display_value(121.0, "INR") == "121.00"
    assert display_value(36, "years") == "36"
    assert display_value(None, "ratio") is None
    assert to_percent(0.2) == pytest.approx(20.0)
    assert to_percent([0.1, 0.2]) == [pytest.approx(10.0), pytest.approx(20.0)]


def test_encode_path_quotes_a_space_and_keeps_a_hyphen() -> None:
    assert encode_path("stocks/data/ALNA TRADING") == "stocks/data/ALNA%20TRADING"
    assert encode_path("stocks/data/BAJAJ-AUTO") == "stocks/data/BAJAJ-AUTO"
