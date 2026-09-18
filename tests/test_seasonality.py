"""Hand-worked tests for calendar-month returns and windowed aggregates.

Every expected number here was worked out by hand from the fixture closes. If a
test fails, the arithmetic changed, not the expectation.
"""

from __future__ import annotations

import pandas as pd
import pytest

from woong.metrics.seasonality import (
    month_label,
    month_window_stats,
    monthly_returns,
    resolve_month,
)


def _prices(rows: list[tuple[str, float]], symbol: str = "AAA") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"symbol": symbol, "exchange": "NSE", "date": day, "close": close}
            for day, close in rows
        ]
    )


def test_month_label_and_resolve_are_two_ways_of_one_thing() -> None:
    assert month_label(9) == "Sep"
    assert resolve_month("sep") == 9
    assert resolve_month("September") == 9
    assert resolve_month(9) == 9
    with pytest.raises(ValueError, match="not a calendar month"):
        resolve_month("Smarch")
    with pytest.raises(ValueError, match="between 1 and 12"):
        resolve_month(13)


def test_a_month_return_divides_by_the_previous_month_end() -> None:
    # January ends at 100, February ends at 110, March ends at 99.
    frame = monthly_returns(
        _prices(
            [
                ("2026-01-29", 98.0),
                ("2026-01-30", 100.0),
                ("2026-02-27", 110.0),
                ("2026-03-30", 99.0),
                ("2026-03-31", 99.0),
            ]
        ),
        as_of="2026-04-15",
    )
    by_month = {int(row["month"]): row for row in frame.to_dict(orient="records")}
    # January has no previous month in this series, so it has no return.
    assert pd.isna(by_month[1]["month_return"])
    assert by_month[1]["sessions"] == 2
    assert by_month[2]["month_return"] == pytest.approx(0.10)
    assert by_month[2]["close_start"] == pytest.approx(100.0)
    assert by_month[2]["close_end"] == pytest.approx(110.0)
    assert by_month[3]["month_return"] == pytest.approx(-0.10)
    assert by_month[3]["end_date"] == "2026-03-31"


def test_a_missing_month_is_not_bridged() -> None:
    # February has no stored session at all. March must not divide by January.
    frame = monthly_returns(
        _prices([("2026-01-30", 100.0), ("2026-03-31", 150.0), ("2026-04-30", 165.0)]),
        as_of="2026-05-10",
    )
    by_month = {int(row["month"]): row for row in frame.to_dict(orient="records")}
    assert 2 not in by_month
    assert pd.isna(by_month[3]["month_return"])
    assert pd.isna(by_month[3]["close_start"])
    # April follows March, so it is fine.
    assert by_month[4]["month_return"] == pytest.approx(0.10)


def test_the_as_of_month_is_marked_partial() -> None:
    frame = monthly_returns(
        _prices([("2026-08-29", 100.0), ("2026-09-11", 110.0)]),
        as_of="2026-09-11",
    )
    by_month = {int(row["month"]): row for row in frame.to_dict(orient="records")}
    assert bool(by_month[8]["partial"]) is False
    assert bool(by_month[9]["partial"]) is True
    # The return is still computed and stored. It is the aggregate that excludes
    # it, so nothing is silently thrown away.
    assert by_month[9]["month_return"] == pytest.approx(0.10)


def test_history_after_the_as_of_date_is_ignored() -> None:
    frame = monthly_returns(
        _prices([("2026-01-30", 100.0), ("2026-02-27", 110.0), ("2026-03-31", 200.0)]),
        as_of="2026-02-27",
    )
    assert sorted(int(month) for month in frame["month"]) == [1, 2]


def test_window_stats_are_hand_worked() -> None:
    # Three Septembers: +10 percent, -20 percent, +30 percent.
    rows = [
        ("2023-08-31", 100.0), ("2023-09-29", 110.0),
        ("2024-08-30", 100.0), ("2024-09-30", 80.0),
        ("2025-08-29", 100.0), ("2025-09-30", 130.0),
    ]
    monthly = monthly_returns(_prices(rows), as_of="2026-03-31")
    stats = month_window_stats(monthly, "Sep", years=10, as_of_year=2026)
    row = stats.iloc[0]
    assert row["month_years_counted"] == 3
    assert row["month_avg_return"] == pytest.approx((0.10 - 0.20 + 0.30) / 3)
    assert row["month_median_return"] == pytest.approx(0.10)
    assert row["month_best_return"] == pytest.approx(0.30)
    assert row["month_worst_return"] == pytest.approx(-0.20)
    assert row["month_positive_count"] == 2
    assert row["month_positive_ratio"] == pytest.approx(2 / 3)
    assert row["month_last_return"] == pytest.approx(0.30)


def test_a_short_window_reports_the_years_it_found() -> None:
    rows = [("2025-08-29", 100.0), ("2025-09-30", 110.0)]
    monthly = monthly_returns(_prices(rows), as_of="2026-03-31")
    stats = month_window_stats(monthly, "Sep", years=10, as_of_year=2026)
    # One year found, not ten. The count is the only honest guard on the average.
    assert stats.iloc[0]["month_years_counted"] == 1
    assert stats.iloc[0]["month_avg_return"] == pytest.approx(0.10)


def test_a_window_keeps_only_the_most_recent_years() -> None:
    rows = [
        ("2023-08-31", 100.0), ("2023-09-29", 200.0),
        ("2024-08-30", 100.0), ("2024-09-30", 110.0),
        ("2025-08-29", 100.0), ("2025-09-30", 120.0),
    ]
    monthly = monthly_returns(_prices(rows), as_of="2026-03-31")
    stats = month_window_stats(monthly, "Sep", years=2, as_of_year=2026)
    row = stats.iloc[0]
    assert row["month_years_counted"] == 2
    # The 2023 September of +100 percent is outside a two year window.
    assert row["month_best_return"] == pytest.approx(0.20)
    assert row["month_avg_return"] == pytest.approx(0.15)


def test_the_partial_month_is_left_out_of_the_window() -> None:
    rows = [
        ("2025-08-29", 100.0), ("2025-09-30", 110.0),
        ("2026-08-31", 100.0), ("2026-09-11", 500.0),
    ]
    monthly = monthly_returns(_prices(rows), as_of="2026-09-11")
    stats = month_window_stats(monthly, "Sep", years=10, as_of_year=2026)
    row = stats.iloc[0]
    assert row["month_years_counted"] == 1
    assert row["month_best_return"] == pytest.approx(0.10)


def test_a_zero_window_is_refused() -> None:
    monthly = monthly_returns(_prices([("2026-01-30", 100.0)]), as_of="2026-02-01")
    with pytest.raises(ValueError, match="at least one year"):
        month_window_stats(monthly, "Jan", years=0, as_of_year=2026)


def test_stats_are_computed_per_symbol() -> None:
    frame = pd.concat(
        [
            _prices([("2025-08-29", 100.0), ("2025-09-30", 110.0)], symbol="AAA"),
            _prices([("2025-08-29", 100.0), ("2025-09-30", 90.0)], symbol="BBB"),
        ],
        ignore_index=True,
    )
    monthly = monthly_returns(frame, as_of="2026-01-31")
    stats = month_window_stats(monthly, "Sep", years=5, as_of_year=2026).set_index("symbol")
    assert stats.loc["AAA", "month_avg_return"] == pytest.approx(0.10)
    assert stats.loc["BBB", "month_avg_return"] == pytest.approx(-0.10)
    assert stats.loc["BBB", "month_positive_count"] == 0
