"""Offline tests for filter, rank, missing values and refusals."""

from __future__ import annotations

import pandas as pd
import pytest

from woong.engine.run import run_query
from woong.engine.types import QueryError
from woong.metrics.catalogue import CATALOGUE_ROWS


def _snapshot() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "exchange": "NSE",
                "name": "Alpha",
                "instrument_kind": "stock",
                "as_of": "2026-09-11",
                "close": 121.0,
                "return_1d": 0.10,
                "return_1w": 0.21,
                "return_1m": 0.05,
                "return_3m": None,
                "return_1y": 0.30,
                "return_3y": None,
                "return_5y": None,
                "sma_200": 100.0,
                "momentum_score": None,
            },
            {
                "symbol": "BBB",
                "exchange": "NSE",
                "name": "Beta",
                "instrument_kind": "stock",
                "as_of": "2026-09-11",
                "close": 80.0,
                "return_1d": -0.02,
                "return_1w": 0.01,
                "return_1m": -0.04,
                "return_3m": None,
                "return_1y": 0.10,
                "return_3y": None,
                "return_5y": None,
                "sma_200": 90.0,
                "momentum_score": None,
            },
            {
                "symbol": "CCC",
                "exchange": "NSE",
                "name": "Gamma",
                "instrument_kind": "stock",
                "as_of": "2026-09-11",
                "close": 50.0,
                "return_1d": None,
                "return_1w": None,
                "return_1m": None,
                "return_3m": None,
                "return_1y": None,
                "return_3y": None,
                "return_5y": None,
                "sma_200": None,
                "momentum_score": None,
            },
        ]
    )


def _members() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"universe_id": "nse_equity", "symbol": "AAA", "exchange": "NSE"},
            {"universe_id": "nse_equity", "symbol": "BBB", "exchange": "NSE"},
            {"universe_id": "nse_equity", "symbol": "CCC", "exchange": "NSE"},
        ]
    )


def _universes() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "universe_id": "nse_equity",
                "name": "National Stock Exchange (NSE) equity",
                "kind": "all_equity",
            }
        ]
    )


def _run(query: dict) -> object:
    return run_query(query, _snapshot(), _members(), list(CATALOGUE_ROWS), _universes())


def test_filter_rank_and_missing_value_are_separate() -> None:
    result = _run(
        {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [{"metric": "return_1y", "cmp": ">", "value": 0.15}],
            },
            "rank": {"by": [{"metric": "return_1y", "dir": "desc", "weight": 1}], "top_n": 30},
        }
    )
    assert result.passed == 1
    assert result.had_no_value == 1
    assert result.removed == 1
    assert result.rows[0]["symbol"] == "AAA"
    assert result.rows[0]["return_1y"] == pytest.approx(0.30)
    labels = {item["label"]: item for item in result.attribution}
    assert labels["return_1y > 0.15"]["removed"] == 1
    assert labels["return_1y > 0.15"]["had_no_value"] == 1
    assert "National Stock Exchange (NSE) equity" in result.read_back
    assert "one-year" in result.read_back.lower() or "One-year" in result.read_back


def test_close_above_moving_average() -> None:
    result = _run(
        {
            "universe": {"set": "nse_equity"},
            "filter": {
                "op": "and",
                "args": [{"metric": "close", "cmp": ">", "other_metric": "sma_200"}],
            },
            "rank": {"by": [{"metric": "return_1m", "dir": "desc"}]},
        }
    )
    assert result.passed == 1
    assert result.had_no_value == 1
    assert result.rows[0]["symbol"] == "AAA"


def test_or_group_passes_when_one_side_is_true() -> None:
    result = _run(
        {
            "universe": {"set": "nse_equity"},
            "filter": {
                "op": "or",
                "args": [
                    {"metric": "return_1y", "cmp": ">", "value": 0.25},
                    {"metric": "return_1m", "cmp": ">", "value": 0.0},
                ],
            },
            "rank": {"by": [{"metric": "return_1y", "dir": "desc"}]},
        }
    )
    assert result.passed == 1
    assert result.rows[0]["symbol"] == "AAA"


def test_switched_off_metric_is_refused() -> None:
    with pytest.raises(QueryError, match="Price to Earnings"):
        _run(
            {
                "universe": {"set": "nse_equity"},
                "filter": {"op": "and", "args": [{"metric": "pe", "cmp": "<", "value": 18}]},
                "rank": {"by": [{"metric": "return_1y", "dir": "desc"}]},
            }
        )


def test_ranking_by_close_is_refused() -> None:
    with pytest.raises(QueryError, match="not comparable"):
        _run(
            {
                "universe": {"set": "nse_equity"},
                "rank": {"by": [{"metric": "close", "dir": "desc"}]},
            }
        )


def test_reserved_weight_key_is_refused() -> None:
    with pytest.raises(QueryError, match="reserved"):
        _run(
            {
                "universe": {"set": "nse_equity"},
                "weight": {"method": "equal"},
                "rank": {"by": [{"metric": "return_1y", "dir": "desc"}]},
            }
        )


def test_a_percent_value_is_converted_in_python() -> None:
    result = _run(
        {
            "universe": {"set": "nse_equity"},
            "filter": {
                "op": "and",
                # 15 percent, typed the way a user types it.
                "args": [{"metric": "return_1y", "cmp": ">", "value": 15, "unit": "percent"}],
            },
            "rank": {"by": [{"metric": "return_1y", "dir": "desc", "weight": 1}]},
        }
    )
    assert result.passed == 1
    assert result.rows[0]["symbol"] == "AAA"
    assert "15 percent" in result.read_back


def test_a_percent_value_against_a_rupee_metric_is_refused() -> None:
    with pytest.raises(QueryError, match="not a ratio"):
        _run(
            {
                "universe": {"set": "nse_equity"},
                "filter": {
                    "op": "and",
                    "args": [{"metric": "close", "cmp": ">", "value": 50, "unit": "percent"}],
                },
                "rank": {"by": [{"metric": "return_1y", "dir": "desc"}]},
            }
        )


def test_rows_carry_python_formatted_display_strings() -> None:
    result = _run(
        {
            "universe": {"set": "nse_equity"},
            "filter": {"op": "and", "args": [{"metric": "return_1y", "cmp": ">", "value": 0.0}]},
            "rank": {"by": [{"metric": "return_1y", "dir": "desc", "weight": 1}]},
        }
    )
    assert result.rows[0]["display"]["return_1y"] == "30.00%"


def test_display_query_restates_a_ratio_as_percent() -> None:
    from woong.api.present import to_display_query

    shown = to_display_query(
        {
            "universe": {"set": "nse_equity"},
            "filter": {
                "op": "and",
                "args": [
                    {"metric": "return_1y", "cmp": ">", "value": 0.20},
                    {"metric": "close", "cmp": ">", "value": 100.0},
                ],
            },
        },
        list(CATALOGUE_ROWS),
    )
    ratio_condition, rupee_condition = shown["filter"]["args"]
    assert ratio_condition["value"] == pytest.approx(20.0)
    assert ratio_condition["unit"] == "percent"
    assert rupee_condition["value"] == pytest.approx(100.0)
    assert "unit" not in rupee_condition


def test_empty_snapshot_is_refused() -> None:
    with pytest.raises(QueryError, match="empty"):
        run_query(
            {"universe": {"set": "nse_equity"}},
            pd.DataFrame(),
            _members(),
            list(CATALOGUE_ROWS),
            _universes(),
        )
