"""Parse broker payloads into warehouse frames.

Refuses to invent a bar. A candle missing open, high, low, close or volume is
dropped from the frame and counted, never filled. Refuses to put a provider
name on any column. Bars are treated as the broker's continuous adjusted
session series; that contract is documented in DATA.md, not invented here.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any

import pandas as pd

SOURCE = "broker"

# Equity and exchange-traded fund (ETF) cash listings on the cash segment.
CASH_EXCHANGES = {"NSE", "BSE"}
CASH_TYPES = {"EQ"}


def parse_broker_instruments(
    csv_text: str,
    wanted: dict[tuple[str, str], str],
    as_of: str,
) -> pd.DataFrame:
    """Keep cash equity rows that match a warehouse (symbol, exchange) pair.

    `wanted` maps (symbol, exchange) to the warehouse `instrument_kind`. Kind
    comes from our master, never from a name heuristic on the broker dump.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    rows: list[dict[str, Any]] = []
    for raw in reader:
        exchange = str(raw.get("exchange") or "").strip().upper()
        symbol = str(raw.get("tradingsymbol") or "").strip().upper()
        instrument_type = str(raw.get("instrument_type") or "").strip().upper()
        if exchange not in CASH_EXCHANGES or instrument_type not in CASH_TYPES:
            continue
        key = (symbol, exchange)
        if key not in wanted:
            continue
        token = raw.get("instrument_token")
        if token is None or str(token).strip() == "":
            continue
        rows.append(
            {
                "symbol": symbol,
                "exchange": exchange,
                "broker_token": int(token),
                "instrument_kind": wanted[key],
                "segment": str(raw.get("segment") or "").strip(),
                "source": SOURCE,
                "as_of": as_of,
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "symbol",
                "exchange",
                "broker_token",
                "instrument_kind",
                "segment",
                "source",
                "as_of",
            ]
        )
    frame = pd.DataFrame(rows)
    # A duplicate listing for the same key would make the harvest ambiguous.
    frame = frame.drop_duplicates(subset=["symbol", "exchange"], keep="first")
    return frame.reset_index(drop=True)


def parse_daily_candles(
    payload: dict[str, Any],
    symbol: str,
    exchange: str,
    as_of: str,
) -> pd.DataFrame:
    """Turn a historical day response into `prices_daily` rows."""
    data = payload.get("data") or {}
    candles = data.get("candles")
    if candles is None:
        raise ValueError("Broker historical payload has no data.candles list.")
    rows: list[dict[str, Any]] = []
    skipped = 0
    for candle in candles:
        if not isinstance(candle, (list, tuple)) or len(candle) < 6:
            skipped += 1
            continue
        stamp, open_, high, low, close, volume = candle[:6]
        if any(value is None for value in (open_, high, low, close, volume)):
            skipped += 1
            continue
        day = str(stamp)[:10]
        try:
            date.fromisoformat(day)
        except ValueError as exc:
            raise ValueError(f"Bad candle date {stamp!r}") from exc
        rows.append(
            {
                "symbol": symbol,
                "exchange": exchange,
                "date": day,
                "open": float(open_),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "volume": float(volume),
                "source": SOURCE,
                "as_of": as_of,
            }
        )
    if skipped and not rows:
        raise ValueError(f"Every candle was incomplete ({skipped} skipped).")
    if not rows:
        return pd.DataFrame(
            columns=[
                "symbol",
                "exchange",
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "source",
                "as_of",
            ]
        )
    return pd.DataFrame(rows)
