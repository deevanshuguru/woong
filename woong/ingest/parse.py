"""Turn a raw primary payload into warehouse rows.

Refuses to compute a return, a moving average, or a ratio. Refuses to keep a
picture URL or any other remote asset path.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pandas as pd

SOURCE = "primary"

KIND_MAP = {
    "stock": ("stock", ""),
    "etf": ("etf", ""),
    "market": ("index", "market"),
    "sector": ("index", "sector"),
    "thematic": ("index", "thematic"),
    "strategy": ("index", "strategy"),
}


def _as_of(payload: dict[str, Any]) -> str:
    stamp = payload.get("timestamp")
    if not stamp:
        raise ValueError("Payload has no timestamp. Cannot set as_of.")
    return str(stamp)[:10]


def _require_success(payload: dict[str, Any]) -> None:
    if payload.get("status") != "success":
        raise ValueError(f"Payload status is {payload.get('status')!r}, not success")


def parse_symbols(payload: dict[str, Any]) -> pd.DataFrame:
    _require_success(payload)
    as_of = _as_of(payload)
    rows = []
    for item in payload["data"]["symbols"]:
        feed_type = item["type"]
        if feed_type not in KIND_MAP:
            raise ValueError(f"Unknown instrument type {feed_type!r}")
        kind, index_class = KIND_MAP[feed_type]
        rows.append(
            {
                "symbol": item["symbol"],
                "exchange": item["exchange"],
                "name": item["name"],
                "instrument_kind": kind,
                "index_class": index_class,
                "isin": item.get("isin") or None,
                "source": SOURCE,
                "as_of": as_of,
            }
        )
    return pd.DataFrame(rows)


def default_universes(instruments: pd.DataFrame, as_of: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Universes we can derive from the master without a membership file."""
    universes = [
        {
            "universe_id": "nse_equity",
            "name": "National Stock Exchange (NSE) equity",
            "kind": "all_equity",
            "source": SOURCE,
            "as_of": as_of,
        },
        {
            "universe_id": "nse_etf",
            "name": "National Stock Exchange (NSE) exchange-traded funds",
            "kind": "etf",
            "source": SOURCE,
            "as_of": as_of,
        },
        {
            "universe_id": "bse_equity",
            "name": "Bombay Stock Exchange (BSE) equity",
            "kind": "all_equity",
            "source": SOURCE,
            "as_of": as_of,
        },
        # An index is a scannable row in its own right, not only a membership
        # list. Monthly seasonality is published per index and for nothing else,
        # so a rule about seasonality needs a universe of indexes to stand on.
        {
            "universe_id": "nse_index",
            "name": "National Stock Exchange (NSE) indexes",
            "kind": "index_list",
            "source": SOURCE,
            "as_of": as_of,
        },
        {
            "universe_id": "bse_index",
            "name": "Bombay Stock Exchange (BSE) indexes",
            "kind": "index_list",
            "source": SOURCE,
            "as_of": as_of,
        },
    ]
    members = []
    for _, row in instruments.iterrows():
        uid = None
        if row["instrument_kind"] == "stock" and row["exchange"] == "NSE":
            uid = "nse_equity"
        elif row["instrument_kind"] == "stock" and row["exchange"] == "BSE":
            uid = "bse_equity"
        elif row["instrument_kind"] == "etf" and row["exchange"] == "NSE":
            uid = "nse_etf"
        elif row["instrument_kind"] == "index" and row["exchange"] == "NSE":
            uid = "nse_index"
        elif row["instrument_kind"] == "index" and row["exchange"] == "BSE":
            uid = "bse_index"
        if uid:
            members.append(
                {
                    "universe_id": uid,
                    "symbol": row["symbol"],
                    "exchange": row["exchange"],
                    "as_of": as_of,
                    "source": SOURCE,
                }
            )
        if row["instrument_kind"] == "index":
            universes.append(
                {
                    "universe_id": f"{row['exchange']}:{row['symbol']}",
                    "name": row["name"],
                    "kind": "index",
                    "source": SOURCE,
                    "as_of": as_of,
                }
            )
    return pd.DataFrame(universes), pd.DataFrame(members)


def _session_date(value: Any) -> str:
    return str(value)[:10]


def parse_stock_series(
    payload: dict[str, Any], exchange: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    _require_success(payload)
    as_of = _as_of(payload)
    data = payload["data"]
    prices = []
    metrics = []
    for item in data["data"]:
        date = _session_date(item["date"])
        prices.append(
            {
                "symbol": item["symbol"],
                "exchange": exchange,
                "date": date,
                "open": None,
                "high": None,
                "low": None,
                "close": item.get("close"),
                "volume": None,
                "source": SOURCE,
                "as_of": as_of,
            }
        )
        metrics.append(
            {
                "symbol": item["symbol"],
                "exchange": exchange,
                "date": date,
                "return_1d": item.get("return1D"),
                "return_1w": item.get("return1W"),
                "return_1m": item.get("return1M"),
                "return_3m": item.get("return3M"),
                "return_1y": item.get("return1Y"),
                "return_3y": item.get("return3Y"),
                "return_5y": item.get("return5Y"),
                "source": SOURCE,
                "as_of": as_of,
            }
        )
    return pd.DataFrame(prices), pd.DataFrame(metrics)


def parse_factors(payload: dict[str, Any]) -> pd.DataFrame:
    _require_success(payload)
    as_of = _as_of(payload)
    rows = []
    for item in payload["data"]["data"]:
        rows.append(
            {
                "symbol": item["symbol"],
                "date": _session_date(item["date"]),
                "momentum_score": item.get("momentum_score"),
                "value_score": item.get("value_score"),
                "quality_score": item.get("quality_score"),
                "volatility_score": item.get("volatility_score"),
                "source": SOURCE,
                "as_of": as_of,
            }
        )
    return pd.DataFrame(rows)


def parse_seasonality(payload: dict[str, Any]) -> pd.DataFrame:
    _require_success(payload)
    as_of = _as_of(payload)
    rows = []
    for item in payload["data"]["data"]:
        rows.append(
            {
                "symbol": item["symbol"],
                "month": item["month"],
                "avg_monthly_return": item.get("avg_monthly_return"),
                "median_monthly_return": item.get("median_monthly_return"),
                "std_monthly_return": item.get("std_monthly_return"),
                "max_monthly_return": item.get("max_monthly_return"),
                "min_monthly_return": item.get("min_monthly_return"),
                "positive_months": item.get("positive_months"),
                "total_months": item.get("total_months"),
                "start_year": item.get("start_year"),
                "end_year": item.get("end_year"),
                "positive_return_ratio": item.get("positive_return_ratio"),
                "return_risk_ratio": item.get("return_risk_ratio"),
                "years_of_data": item.get("years_of_data"),
                "source": SOURCE,
                "as_of": as_of,
            }
        )
    return pd.DataFrame(rows)


def parse_breadth(payload: dict[str, Any]) -> pd.DataFrame:
    _require_success(payload)
    as_of = _as_of(payload)
    rows = []
    for item in payload["data"]:
        rows.append(
            {
                "date": _session_date(item["date"]),
                "symbol": item["symbol"],
                "index_name": item.get("index_name"),
                "index_class": item.get("category") or item.get("type") or "",
                "constituent_count": item.get("total_stocks"),
                "above_ema_20": item.get("above_ema_20"),
                "above_ema_50": item.get("above_ema_50"),
                "above_ema_100": item.get("above_ema_100"),
                "above_ema_200": item.get("above_ema_200"),
                "above_ema_20_pct": item.get("above_ema_20_pct"),
                "above_ema_50_pct": item.get("above_ema_50_pct"),
                "above_ema_100_pct": item.get("above_ema_100_pct"),
                "above_ema_200_pct": item.get("above_ema_200_pct"),
                "near_52w_high_5pct": item.get("near_52w_high_5pct"),
                "near_52w_low_5pct": item.get("near_52w_low_5pct"),
                "source": SOURCE,
                "as_of": as_of,
            }
        )
    return pd.DataFrame(rows)


def parse_flows(payload: dict[str, Any]) -> pd.DataFrame:
    _require_success(payload)
    as_of = _as_of(payload)
    rows = []
    for freq in ("daily", "monthly", "yearly"):
        for item in payload["data"][freq]:
            rows.append(
                {
                    "date": str(item["date"]),
                    "frequency": freq,
                    "domestic_inst_purchase": item.get("dii_buy"),
                    "domestic_inst_disposal": item.get("dii_sell"),
                    "domestic_inst_net": item.get("dii_net"),
                    "foreign_inst_purchase": item.get("fii_buy"),
                    "foreign_inst_disposal": item.get("fii_sell"),
                    "foreign_inst_net": item.get("fii_net"),
                    "total_net": item.get("total_net"),
                    "source": SOURCE,
                    "as_of": as_of,
                }
            )
    return pd.DataFrame(rows)


def parse_events(payload: dict[str, Any]) -> pd.DataFrame:
    _require_success(payload)
    as_of = _as_of(payload)
    rows = []
    for item in payload["data"]:
        pill = item.get("corporateEventPillDto") or {}
        clean = {
            key: value
            for key, value in item.items()
            if key not in {"logoUrl", "picture_link"}
        }
        event_id = item.get("id")
        if not event_id:
            # RESULTS rows arrive with a null id. The natural key is built from
            # fields that are actually on the row, not invented.
            event_id = "|".join(
                [
                    str(item.get("gsin") or ""),
                    str(item.get("type") or ""),
                    str(pill.get("primaryDate") or ""),
                    str(item.get("details") or ""),
                    str(item.get("nseSymbol") or item.get("bseSymbol") or ""),
                ]
            )
        rows.append(
            {
                "event_id": event_id,
                "symbol": item.get("nseSymbol") or item.get("bseSymbol"),
                "event_type": item.get("type"),
                "event_category": item.get("event_category"),
                "primary_date": _session_date(pill.get("primaryDate")) if pill.get("primaryDate") else None,
                "description": item.get("description"),
                "details": item.get("details"),
                "old_isin": item.get("oldIsin"),
                "new_isin": item.get("newIsin"),
                "payload_json": json.dumps(clean, ensure_ascii=True),
                "source": SOURCE,
                "as_of": as_of,
            }
        )
    return pd.DataFrame(rows)


def _nested_symbol(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("symbol") or "")
    return str(value or "")


def parse_insider(payload: dict[str, Any]) -> pd.DataFrame:
    _require_success(payload)
    as_of = _as_of(payload) if payload.get("timestamp") else "1970-01-01"
    if as_of == "1970-01-01":
        # The on-disk dump has a timestamp field on the envelope. If it is
        # missing, refuse rather than invent a fetch date.
        stamp = payload.get("timestamp")
        if not stamp:
            raise ValueError("Insider payload has no timestamp")
        as_of = str(stamp)[:10]
    rows = []
    for item in payload["data"]["data"]:
        fingerprint = {key: value for key, value in item.items() if key != "symbol"}
        symbol = _nested_symbol(item.get("symbol"))
        fingerprint["symbol"] = symbol
        disclosure_id = hashlib.sha256(
            json.dumps(fingerprint, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        rows.append(
            {
                "disclosure_id": disclosure_id,
                "symbol": symbol,
                "trade_date": _session_date(item.get("date")),
                "person_name": item.get("acqName") or "",
                "person_category": item.get("personCategory"),
                "transaction_type": item.get("tdpTransactionType"),
                "acquired_value": item.get("buyValue"),
                "disposed_value": item.get("sellValue"),
                "acquired_quantity": item.get("buyQuantity"),
                "disposed_quantity": item.get("sellquantity"),
                "holdings_before": item.get("befAcqSharesNo"),
                "holdings_before_pct": item.get("befAcqSharesPer"),
                "holdings_after": item.get("afterAcqSharesNo"),
                "holdings_after_pct": item.get("afterAcqSharesPer"),
                "security_type": item.get("secType"),
                "acquisition_mode": item.get("acqMode"),
                "period_from": item.get("acqfromDt"),
                "period_to": item.get("acqtoDt"),
                "intim_date": _session_date(item.get("intimDt")) if item.get("intimDt") else "",
                "exchange": item.get("exchange"),
                "source": SOURCE,
                "as_of": as_of,
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    # A disclosure with no symbol is not a row we can join later.
    return frame[frame["symbol"].astype(str).str.len() > 0].copy()
