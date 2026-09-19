"""Offline tests for the warehouse schema and primary-pipe parsers.

These refuse a network. Fixtures are hand-written and carry no provider name
and no picture URL.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from woong.ingest.parse import (
    parse_stock_series,
    parse_symbols,
)
from woong.metrics.catalogue import CATALOGUE_ROWS
from woong.warehouse.schema import (
    BACKTEST_RUNS,
    DEPLOY_ORDERS,
    INSTRUMENTS,
    PRICES_DAILY,
    WEIGHT_RUNS,
)
from woong.warehouse.store import Warehouse

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "primary"


def test_symbols_map_to_stock_etf_or_index() -> None:
    payload = json.loads((FIXTURES / "symbols.json").read_text(encoding="utf-8"))
    frame = parse_symbols(payload)
    kinds = set(frame["instrument_kind"])
    assert kinds == {"stock", "etf", "index"}
    idx = frame.set_index("symbol")
    assert idx.loc["AAA", "instrument_kind"] == "stock"
    assert idx.loc["BBB", "instrument_kind"] == "etf"
    assert idx.loc["IDX50", "instrument_kind"] == "index"
    assert idx.loc["IDX50", "index_class"] == "market"
    assert idx.loc["IDXIT", "index_class"] == "sector"
    assert "picture_link" not in frame.columns


def test_unknown_instrument_type_is_refused() -> None:
    payload = json.loads((FIXTURES / "symbols.json").read_text(encoding="utf-8"))
    payload["data"]["symbols"][0]["type"] = "warrant"
    with pytest.raises(ValueError, match="Unknown instrument type"):
        parse_symbols(payload)


def test_price_series_keeps_ohlcv_empty_without_session_bars() -> None:
    payload = json.loads((FIXTURES / "stock_series.json").read_text(encoding="utf-8"))
    prices, metrics = parse_stock_series(payload, "NSE")
    assert list(prices["close"]) == [100.0, 110.0, 121.0]
    assert prices["open"].isna().all()
    assert prices["high"].isna().all()
    assert prices["low"].isna().all()
    assert prices["volume"].isna().all()
    assert metrics.loc[1, "return_1d"] == pytest.approx(0.1)


def test_upsert_is_idempotent(tmp_path: Path) -> None:
    store = Warehouse(tmp_path)
    payload = json.loads((FIXTURES / "symbols.json").read_text(encoding="utf-8"))
    frame = parse_symbols(payload)
    first = store.upsert(INSTRUMENTS, frame)
    second = store.upsert(INSTRUMENTS, frame)
    assert first == 4
    assert second == 4
    assert len(store.read(INSTRUMENTS)) == 4


def test_reserved_tables_are_created_empty(tmp_path: Path) -> None:
    store = Warehouse(tmp_path)
    store.create_empty_tables()
    assert store.read(WEIGHT_RUNS).empty
    assert store.read(BACKTEST_RUNS).empty
    assert store.read(DEPLOY_ORDERS).empty
    assert store.path_for(PRICES_DAILY).exists()


def test_catalogue_refuses_a_52w_high_without_high() -> None:
    by_id = {row["id"]: row for row in CATALOGUE_ROWS}
    assert by_id["close"]["available"] is True
    assert by_id["close"]["comparable"] is False
    assert by_id["fall_from_52w_high_pct"]["available"] is False
    assert "session high" in str(by_id["fall_from_52w_high_pct"]["off_reason"])
    assert by_id["pe"]["available"] is False
    assert by_id["sma_200"]["available"] is True
    assert by_id["return"]["source_table"] == "prices_daily"
    for row in CATALOGUE_ROWS:
        if row["available"]:
            assert row["off_reason"] == ""
        else:
            assert str(row["off_reason"]).strip()
