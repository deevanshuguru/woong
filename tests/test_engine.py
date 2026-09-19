"""Offline tests for filter, rank, missing values and refusals."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from woong.engine.run import run_query
from woong.engine.types import QueryError
from woong.metrics.catalogue import CATALOGUE_ROWS


def _snapshot() -> pd.DataFrame:
    return pd.DataFrame([
        {"symbol": "AAA", "exchange": "NSE", "name": "Alpha", "instrument_kind": "stock",
         "as_of": "2026-09-11", "close": 121.0,
         "sma_50": 115.0, "sma_200": 100.0,
         "dist_sma_50_pct": 0.052, "dist_sma_200_pct": 0.21,
         "volatility_21d": 0.015, "momentum_score": None},
        {"symbol": "BBB", "exchange": "NSE", "name": "Beta", "instrument_kind": "stock",
         "as_of": "2026-09-11", "close": 80.0,
         "sma_50": 85.0, "sma_200": 90.0,
         "dist_sma_50_pct": -0.059, "dist_sma_200_pct": -0.111,
         "volatility_21d": 0.022, "momentum_score": None},
        {"symbol": "CCC", "exchange": "NSE", "name": "Gamma", "instrument_kind": "stock",
         "as_of": "2026-09-11", "close": 50.0,
         "sma_50": None, "sma_200": None,
         "dist_sma_50_pct": None, "dist_sma_200_pct": None,
         "volatility_21d": None, "momentum_score": None},
    ])


def _prices() -> pd.DataFrame:
    n, as_of = 270, date(2026, 9, 11)
    dates = [str(as_of - timedelta(days=n - 1 - i)) for i in range(n)]
    aaa = [93.0 + i * (121.0 - 93.0) / (n - 1) for i in range(n)]
    bbb = []
    for i in range(n):
        if i <= 17:
            bbb.append(65.0 + i * (72.73 - 65.0) / 17)
        elif i <= 143:
            bbb.append(72.73 + (i - 17) * (70.0 - 72.73) / (143 - 17))
        elif i <= 248:
            bbb.append(70.0 + (i - 143) * (90.0 - 70.0) / (248 - 143))
        else:
            bbb.append(90.0 + (i - 248) * (80.0 - 90.0) / (269 - 248))
    ccc_dates = [str(as_of - timedelta(days=i)) for i in range(4, -1, -1)]
    rows = (
        [{"symbol": "AAA", "exchange": "NSE", "date": d, "close": round(c, 4)} for d, c in zip(dates, aaa)]
        + [{"symbol": "BBB", "exchange": "NSE", "date": d, "close": round(c, 4)} for d, c in zip(dates, bbb)]
        + [{"symbol": "CCC", "exchange": "NSE", "date": d, "close": 50.0} for d in ccc_dates]
    )
    return pd.DataFrame(rows)



def _members() -> pd.DataFrame:
    return pd.DataFrame([
        {"universe_id": "nse_equity", "symbol": "AAA", "exchange": "NSE"},
        {"universe_id": "nse_equity", "symbol": "BBB", "exchange": "NSE"},
        {"universe_id": "nse_equity", "symbol": "CCC", "exchange": "NSE"},
    ])


def _universes() -> pd.DataFrame:
    return pd.DataFrame([{
        "universe_id": "nse_equity",
        "name": "National Stock Exchange (NSE) equity",
        "kind": "all_equity",
    }])


def _run(query: dict) -> object:
    return run_query(
        query, _snapshot(), _members(), list(CATALOGUE_ROWS), _universes(),
        prices=_prices(),
    )


# ── Dynamic return tests ────────────────────────────────────────────────

def test_filter_rank_and_missing_value_are_separate() -> None:
    # AAA 1Y ~27.7% > 15% → passes; BBB ~8.2% → fails; CCC no data → had_no_value
    result = _run({
        "universe": {"set": "nse_equity"},
        "as_of": "latest",
        "filter": {"op": "and", "args": [
            {"metric": "return", "window": {"n": 1, "unit": "Y"},
             "period": "latest", "cmp": ">", "value": 15, "unit": "percent"},
        ]},
        "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc", "weight": 1}], "top_n": 30},
    })
    assert result.passed == 1
    assert result.had_no_value == 1
    assert result.removed == 1
    assert result.rows[0]["symbol"] == "AAA"
    assert "National Stock Exchange (NSE) equity" in result.read_back


def test_close_above_moving_average() -> None:
    # AAA close=121 > sma_200=100 → passes; BBB close=80 < sma_200=90 → fails; CCC sma_200=None → had_no_value
    result = _run({
        "universe": {"set": "nse_equity"},
        "filter": {"op": "and", "args": [
            {"metric": "close", "cmp": ">", "other_metric": "sma_200"},
        ]},
        "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "M"}, "dir": "desc"}]},
    })
    assert result.passed == 1
    assert result.had_no_value == 1
    assert result.rows[0]["symbol"] == "AAA"


def test_or_group_passes_when_one_side_is_true() -> None:
    # OR: 1Y>25% OR 1M>0; AAA passes (1Y~27.7%>25%), BBB fails both, CCC had_no_value
    result = _run({
        "universe": {"set": "nse_equity"},
        "filter": {"op": "or", "args": [
            {"metric": "return", "window": {"n": 1, "unit": "Y"}, "cmp": ">", "value": 25, "unit": "percent"},
            {"metric": "return", "window": {"n": 1, "unit": "M"}, "cmp": ">", "value": 0},
        ]},
        "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc"}]},
    })
    assert result.passed == 1
    assert result.rows[0]["symbol"] == "AAA"


def test_switched_off_metric_is_refused() -> None:
    with pytest.raises(QueryError, match="Price to Earnings"):
        _run({
            "universe": {"set": "nse_equity"},
            "filter": {"op": "and", "args": [{"metric": "pe", "cmp": "<", "value": 18}]},
            "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc"}]},
        })


def test_ranking_by_close_is_refused() -> None:
    with pytest.raises(QueryError, match="not comparable"):
        _run({
            "universe": {"set": "nse_equity"},
            "rank": {"by": [{"metric": "close", "dir": "desc"}]},
        })


def test_reserved_weight_key_is_refused() -> None:
    with pytest.raises(QueryError, match="reserved"):
        _run({
            "universe": {"set": "nse_equity"},
            "weight": {"method": "equal"},
            "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc"}]},
        })


def test_a_percent_value_is_converted_in_python() -> None:
    # 15 percent typed → compared as 0.15 ratio; AAA 27.7% passes
    result = _run({
        "universe": {"set": "nse_equity"},
        "filter": {"op": "and", "args": [
            {"metric": "return", "window": {"n": 1, "unit": "Y"},
             "cmp": ">", "value": 15, "unit": "percent"},
        ]},
        "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc", "weight": 1}]},
    })
    assert result.passed == 1
    assert result.rows[0]["symbol"] == "AAA"
    assert "15 percent" in result.read_back


def test_a_percent_value_against_a_rupee_metric_is_refused() -> None:
    with pytest.raises(QueryError, match="not a ratio"):
        _run({
            "universe": {"set": "nse_equity"},
            "filter": {"op": "and", "args": [
                {"metric": "close", "cmp": ">", "value": 50, "unit": "percent"},
            ]},
            "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc"}]},
        })


def test_rows_carry_python_formatted_display_strings() -> None:
    # Dynamic return column should have a formatted percent string
    result = _run({
        "universe": {"set": "nse_equity"},
        "filter": {"op": "and", "args": [
            {"metric": "return", "window": {"n": 1, "unit": "Y"}, "cmp": ">", "value": 0},
        ]},
        "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc", "weight": 1}]},
    })
    # Both AAA and BBB have positive 1Y return
    assert result.passed == 2
    col = "_dyn_return_1Y"
    display_val = result.rows[0]["display"].get(col, "")
    assert "%" in str(display_val), f"expected % format, got {display_val!r}"


def test_display_query_restates_a_ratio_as_percent() -> None:
    from woong.api.present import to_display_query
    shown = to_display_query(
        {"universe": {"set": "nse_equity"},
         "filter": {"op": "and", "args": [
             {"metric": "return", "window": {"n": 1, "unit": "Y"}, "cmp": ">", "value": 0.20},
             {"metric": "close", "cmp": ">", "value": 100.0},
         ]}},
        list(CATALOGUE_ROWS),
    )
    ratio_cond, rupee_cond = shown["filter"]["args"]
    assert ratio_cond["value"] == pytest.approx(20.0)
    assert ratio_cond["unit"] == "percent"
    assert rupee_cond["value"] == pytest.approx(100.0)
    assert "unit" not in rupee_cond


def test_empty_snapshot_is_refused() -> None:
    with pytest.raises(QueryError, match="empty"):
        run_query(
            {"universe": {"set": "nse_equity"}},
            pd.DataFrame(), _members(), list(CATALOGUE_ROWS), _universes(),
        )


# ── between tests ────────────────────────────────────────────────────────

def test_between_ratio_inclusive() -> None:
    # AAA 1M ~1.8% → between [0%, 10%] → passes
    # BBB 1M ~-11% → fails
    # CCC no data → had_no_value
    result = _run({
        "universe": {"set": "nse_equity"},
        "filter": {"op": "and", "args": [
            {"metric": "return", "window": {"n": 1, "unit": "M"},
             "period": "latest", "cmp": "between", "value": [0, 10], "unit": "percent"},
        ]},
        "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc"}]},
    })
    assert result.passed == 1
    assert result.removed == 1
    assert result.had_no_value == 1
    assert result.rows[0]["symbol"] == "AAA"


def test_between_refuses_single_number() -> None:
    with pytest.raises(QueryError, match="between needs a two-element value"):
        _run({
            "universe": {"set": "nse_equity"},
            "filter": {"op": "and", "args": [
                {"metric": "return", "window": {"n": 1, "unit": "M"}, "cmp": "between", "value": 5, "unit": "percent"},
            ]},
            "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc"}]},
        })


def test_between_refuses_three_values() -> None:
    with pytest.raises(QueryError, match="between needs a two-element value"):
        _run({
            "universe": {"set": "nse_equity"},
            "filter": {"op": "and", "args": [
                {"metric": "return", "window": {"n": 1, "unit": "M"}, "cmp": "between", "value": [5, 10, 20], "unit": "percent"},
            ]},
            "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc"}]},
        })


def test_between_refuses_other_metric() -> None:
    with pytest.raises(QueryError, match="between cannot be used with another metric"):
        _run({
            "universe": {"set": "nse_equity"},
            "filter": {"op": "and", "args": [
                {"metric": "return", "window": {"n": 1, "unit": "M"}, "cmp": "between",
                 "other_metric": "return", "other_window": {"n": 1, "unit": "Y"}},
            ]},
            "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc"}]},
        })


def test_between_missing_value_on_either_side_returns_unknown() -> None:
    # None bound → UNKNOWN for all tickers with enough history
    result = _run({
        "universe": {"set": "nse_equity"},
        "filter": {"op": "and", "args": [
            {"metric": "return", "window": {"n": 1, "unit": "M"}, "cmp": "between", "value": [None, 0.10]},
        ]},
        "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc"}]},
    })
    assert result.passed == 0
    assert result.had_no_value == 3


def test_display_query_restates_between_ratio_as_percent() -> None:
    from woong.api.present import to_display_query
    shown = to_display_query(
        {"universe": {"set": "nse_equity"},
         "filter": {"op": "and", "args": [
             {"metric": "return", "window": {"n": 1, "unit": "M"},
              "cmp": "between", "value": [0.05, 0.20]},
         ]}},
        list(CATALOGUE_ROWS),
    )
    low, high = shown["filter"]["args"][0]["value"]
    assert low == pytest.approx(5.0)
    assert high == pytest.approx(20.0)
    assert shown["filter"]["args"][0]["unit"] == "percent"


# ── dynamic window validation tests ─────────────────────────────────────

def test_return_without_window_is_refused() -> None:
    with pytest.raises(QueryError, match="requires a window"):
        _run({
            "universe": {"set": "nse_equity"},
            "filter": {"op": "and", "args": [
                {"metric": "return", "cmp": ">", "value": 0},
            ]},
            "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc"}]},
        })


def test_window_with_bad_unit_is_refused() -> None:
    with pytest.raises(QueryError, match="must be D, W, M, or Y"):
        _run({
            "universe": {"set": "nse_equity"},
            "filter": {"op": "and", "args": [
                {"metric": "return", "window": {"n": 6, "unit": "Q"}, "cmp": ">", "value": 0},
            ]},
            "rank": {"by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc"}]},
        })


def test_six_month_up_one_month_down() -> None:
    # The user case: 6M > 0 AND 5M < 0
    # AAA: 6M return positive, 1M positive (fails 1M < 0)
    # BBB: 6M return positive (rises to 90), 1M negative (falls to 80) → passes
    result = _run({
        "universe": {"set": "nse_equity"},
        "filter": {"op": "and", "args": [
            {"metric": "return", "window": {"n": 6, "unit": "M"}, "cmp": ">", "value": 0},
            {"metric": "return", "window": {"n": 1, "unit": "M"}, "cmp": "<", "value": 0},
        ]},
        "rank": {"by": [{"metric": "return", "window": {"n": 6, "unit": "M"}, "dir": "desc"}]},
    })
    assert result.passed == 1
    assert result.rows[0]["symbol"] == "BBB"
