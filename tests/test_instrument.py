"""Offline tests for the one-instrument page payload."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from woong.api.instrument import InstrumentNotFound, display_value, instrument_page, lookup_instruments
from woong.ingest.parse import parse_stock_series, parse_symbols
from woong.metrics.snapshot import build_snapshot
from woong.warehouse.schema import INSTRUMENTS, PRICES_DAILY
from woong.warehouse.store import Warehouse

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "primary"


def _store(tmp_path: Path) -> Warehouse:
    store = Warehouse(tmp_path)
    store.create_empty_tables()
    symbols = json.loads((FIXTURES / "symbols.json").read_text(encoding="utf-8"))
    store.upsert(INSTRUMENTS, parse_symbols(symbols))
    prices, _metrics = parse_stock_series(
        json.loads((FIXTURES / "stock_series.json").read_text(encoding="utf-8")),
        "NSE",
    )
    store.upsert(PRICES_DAILY, prices)
    build_snapshot(store)
    return store


def test_display_value_formats_a_ratio_in_python() -> None:
    assert display_value(0.1, "ratio") == "10.00%"
    assert display_value(121.0, "INR") == "121.00"
    assert display_value(None, "ratio") is None


def test_instrument_page_reads_warehouse_facts(tmp_path: Path) -> None:
    store = _store(tmp_path)
    page = instrument_page(store, "AAA", "NSE")
    assert page["symbol"] == "AAA"
    assert page["exchange"] == "NSE"
    assert page["session_count"] == 3
    by_id = {
        metric["id"]: metric
        for group in page["metric_groups"]
        for metric in group["metrics"]
    }
    assert by_id["return_1d"]["display"] == "10.00%"
    assert by_id["return_1y"]["missing"] is True
    assert "Not a buy or sell recommendation" in page["disclaimer"]
    assert page["prices"][-1]["close"] == pytest.approx(121.0)


def test_price_chart_geometry_comes_from_python(tmp_path: Path) -> None:
    store = _store(tmp_path)
    page = instrument_page(store, "AAA", "NSE")
    window = page["price_chart"][0]
    assert window["session_count"] == 3
    assert window["low"] == pytest.approx(100.0)
    assert window["high"] == pytest.approx(121.0)
    # Three sessions cannot fill a 21-session window, and the page says so.
    assert window["short"] is True
    assert window["label"] == "All stored sessions"
    assert len(window["points"].split(" ")) == 3


def test_seasonality_is_refused_with_a_reason_when_absent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    page = instrument_page(store, "AAA", "NSE")
    assert page["seasonality_chart"] is None
    assert "index symbols only" in page["seasonality_reason"]


def test_switched_off_metrics_carry_their_stored_reason(tmp_path: Path) -> None:
    store = _store(tmp_path)
    page = instrument_page(store, "AAA", "NSE")
    labels = {item["label"]: item["reason"] for item in page["switched_off"]}
    assert "Fall from 52-week high" in labels
    assert labels["Fall from 52-week high"]
    assert all(item["reason"] for item in page["switched_off"])


def test_unknown_instrument_is_refused(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(InstrumentNotFound, match="ZZZ"):
        instrument_page(store, "ZZZ", "NSE")


def test_lookup_prefers_an_exact_symbol(tmp_path: Path) -> None:
    store = _store(tmp_path)
    matches = lookup_instruments(store, "aaa")
    assert matches[0]["symbol"] == "AAA"
    assert lookup_instruments(store, "") == []
