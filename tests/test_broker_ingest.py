"""Offline tests for the broker instrument map and OHLCV parser."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from woong.config import Settings
from woong.ingest.broker_auth import (
    connect_login_url,
    load_fresh_token,
    save_token,
    token_is_fresh,
)
from woong.ingest.broker_http import totp_code
from woong.ingest.broker_parse import parse_broker_instruments, parse_daily_candles
from woong.warehouse.schema import BROKER_INSTRUMENTS, PRICES_DAILY
from woong.warehouse.store import Warehouse

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "broker"


def _settings(**overrides: object) -> Settings:
    base = dict(
        primary_api_base="https://example.test/v1",
        primary_api_token="",
        data_dir=Path("/tmp/woong-test-data"),
        broker_api_base="https://api.example.test",
        broker_login_base="https://login.example.test",
        broker_api_key="key",
        broker_api_secret="secret",
        broker_user_id="AB1234",
        broker_password="pw",
        broker_totp_secret="JBSWY3DPEHPK3PXP",
        broker_access_token="",
        broker_http_version_header="X-Version",
        broker_http_version="3",
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_connect_login_url_uses_login_host_not_api_host() -> None:
    url = connect_login_url(_settings())
    assert url.startswith("https://login.example.test/connect/login?")
    assert "api_key=key" in url
    assert "v=3" in url
    assert "api.example.test" not in url


def test_token_is_fresh_rejects_pre_reset_issue() -> None:
    # 05:00 IST on 2026-09-13 = 23:30 UTC on 2026-09-12, before that day's
    # 00:30 UTC reset for the 13th.
    issued = datetime(2026, 9, 12, 23, 30, tzinfo=timezone.utc)
    now = datetime(2026, 9, 13, 1, 0, tzinfo=timezone.utc)
    assert not token_is_fresh({"login_time": issued.isoformat()}, now=now)


def test_token_is_fresh_accepts_post_reset_issue() -> None:
    issued = datetime(2026, 9, 13, 1, 0, tzinfo=timezone.utc)
    now = datetime(2026, 9, 13, 10, 0, tzinfo=timezone.utc)
    assert token_is_fresh({"login_time": issued.isoformat()}, now=now)


def test_save_and_load_fresh_token(tmp_path: Path) -> None:
    path = tmp_path / ".broker_token"
    save_token(path, "tok-abc", "AB1234")
    assert path.stat().st_mode & 0o777 == 0o600
    assert load_fresh_token(path) == "tok-abc"


def test_totp_code_is_six_digits() -> None:
    code = totp_code("JBSWY3DPEHPK3PXP", when=0)
    assert len(code) == 6
    assert code.isdigit()


def test_parse_broker_instruments_keeps_only_wanted_cash_listings() -> None:
    csv_text = (FIXTURES / "instruments.csv").read_text(encoding="utf-8")
    wanted = {
        ("AAA", "NSE"): "stock",
        ("BBB", "NSE"): "etf",
        ("AAA", "BSE"): "stock",
    }
    frame = parse_broker_instruments(csv_text, wanted, as_of="2026-09-13")
    assert set(zip(frame["symbol"], frame["exchange"])) == {
        ("AAA", "NSE"),
        ("BBB", "NSE"),
        ("AAA", "BSE"),
    }
    assert frame.set_index(["symbol", "exchange"]).loc[("BBB", "NSE"), "instrument_kind"] == "etf"
    assert int(frame.set_index(["symbol", "exchange"]).loc[("AAA", "NSE"), "broker_token"]) == 101


def test_parse_daily_candles_skips_incomplete_bars() -> None:
    payload = json.loads((FIXTURES / "candles.json").read_text(encoding="utf-8"))
    frame = parse_daily_candles(payload, "AAA", "NSE", as_of="2026-09-13")
    assert len(frame) == 2
    assert list(frame["date"]) == ["2024-01-01", "2024-01-02"]
    assert frame.iloc[0]["open"] == pytest.approx(100.0)
    assert frame.iloc[1]["close"] == pytest.approx(111.0)
    assert frame.iloc[0]["source"] == "broker"


def test_broker_prices_upsert_is_idempotent(tmp_path: Path) -> None:
    store = Warehouse(tmp_path)
    store.create_empty_tables()
    payload = json.loads((FIXTURES / "candles.json").read_text(encoding="utf-8"))
    frame = parse_daily_candles(payload, "AAA", "NSE", as_of="2026-09-13")
    assert store.upsert(PRICES_DAILY, frame) == 2
    assert store.upsert(PRICES_DAILY, frame) == 2
    assert len(store.read(PRICES_DAILY)) == 2


def test_broker_instruments_replace_overwrites(tmp_path: Path) -> None:
    store = Warehouse(tmp_path)
    store.create_empty_tables()
    csv_text = (FIXTURES / "instruments.csv").read_text(encoding="utf-8")
    frame = parse_broker_instruments(
        csv_text, {("AAA", "NSE"): "stock"}, as_of="2026-09-13"
    )
    store.replace(BROKER_INSTRUMENTS, frame)
    assert len(store.read(BROKER_INSTRUMENTS)) == 1
    store.replace(BROKER_INSTRUMENTS, frame.iloc[0:0])
    assert store.read(BROKER_INSTRUMENTS).empty
