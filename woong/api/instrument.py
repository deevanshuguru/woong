"""Assemble one instrument page from the warehouse.

Refuses to compute a new metric. It reads stored facts, already-built snapshot
columns and chart geometry. Refuses to invent a row when the instrument is not
in the master. Refuses to hide a switched-off metric: the page states the metric
and the stored reason it is off, in place of a number.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from woong.api.chart import Point, bar_geometry, line_windows
from woong.metrics.catalogue import CATALOGUE_ROWS
from woong.metrics.display import display_value
from woong.warehouse.schema import (
    INSIDER_TRADES,
    INSTRUMENTS,
    MARKET_EVENTS,
    PRICES_DAILY,
    SCAN_SNAPSHOT,
    SEASONALITY,
)
from woong.warehouse.store import Warehouse

# One group list per instrument kind. A kind that is not listed gets the price
# groups, because a traded instrument with a close series has the same facts
# whatever it is called.
PRICE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Price and Moving Average", ("close", "sma_50", "sma_200", "dist_sma_50_pct", "dist_sma_200_pct")),
    ("Volatility", ("volatility_21d",)),
    ("Supplied factor", ("momentum_score",)),
)

SEASONALITY_GROUP: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Seasonality",
        (
            "seasonality_avg_return",
            "seasonality_median_return",
            "seasonality_positive_ratio",
            "seasonality_std_return",
            "seasonality_years",
        ),
    ),
)

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

PRICE_TAIL = 60
INSIDER_TAIL = 25


class InstrumentNotFound(Exception):
    """No master row for that symbol and exchange."""


def _is_na(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _jsonable(value: Any) -> Any:
    if _is_na(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def lookup_instruments(warehouse: Warehouse, query: str) -> list[dict[str, Any]]:
    text = query.strip().upper()
    if not text:
        return []
    instruments = warehouse.read(INSTRUMENTS)
    if instruments.empty:
        return []
    match = instruments[instruments["symbol"].astype(str).str.upper() == text]
    if match.empty:
        starts = instruments[instruments["symbol"].astype(str).str.upper().str.startswith(text)]
        named = instruments[
            instruments["name"].astype(str).str.upper().str.contains(text, regex=False)
        ]
        match = pd.concat([starts, named], ignore_index=True).drop_duplicates(
            subset=["symbol", "exchange"]
        )
    if not match.empty:
        nse = match[match["exchange"].astype(str) == "NSE"]
        other = match[match["exchange"].astype(str) != "NSE"]
        match = pd.concat([nse, other], ignore_index=True)
    rows = []
    for rec in match.head(20).to_dict(orient="records"):
        rows.append(
            {
                "symbol": rec["symbol"],
                "exchange": rec["exchange"],
                "name": rec["name"],
                "instrument_kind": rec["instrument_kind"],
            }
        )
    return rows


def _metric_cell(metric_id: str, catalogue: dict[str, dict[str, Any]], snap_row: Any) -> dict[str, Any]:
    cat = catalogue.get(metric_id)
    if cat is None:
        return {"id": metric_id, "label": metric_id, "available": False,
                "missing": True, "reason": "Metric not in current catalogue.",
                "value": None, "display": None, "unit": "", "definition": ""}

    raw = None if snap_row is None else snap_row.get(metric_id)
    missing = snap_row is None or _is_na(raw)
    reason = ""
    if not cat["available"]:
        reason = str(cat["off_reason"])
    elif missing:
        reason = "No value on the snapshot date."
    return {
        "id": metric_id,
        "label": cat["label"],
        "definition": cat["definition"],
        "unit": cat["unit"],
        "value": None if missing else _jsonable(raw),
        "display": None if missing else display_value(raw, str(cat["unit"])),
        "available": bool(cat["available"]),
        "missing": bool(missing),
        "reason": reason,
    }


def _contiguous_closes(history: pd.DataFrame) -> list[Point]:
    """The most recent run of sessions that all have a stored close.

    A gap ends the run. Drawing across a gap would put a straight line where
    there is no data and let the reader measure a slope that was never traded.
    """
    points: list[Point] = []
    for rec in reversed(history.to_dict(orient="records")):
        if _is_na(rec.get("close")):
            break
        points.append(Point(date=str(rec["date"]), value=float(rec["close"])))
    points.reverse()
    return points


def instrument_page(warehouse: Warehouse, symbol: str, exchange: str) -> dict[str, Any]:
    instruments = warehouse.read(INSTRUMENTS)
    if instruments.empty:
        raise InstrumentNotFound(f"{symbol} on {exchange} is not in the master.")
    hit = instruments[
        (instruments["symbol"].astype(str) == symbol)
        & (instruments["exchange"].astype(str) == exchange)
    ]
    if hit.empty:
        raise InstrumentNotFound(f"{symbol} on {exchange} is not in the master.")
    ident = hit.iloc[0].to_dict()
    kind = str(ident["instrument_kind"])

    snapshot = warehouse.read(SCAN_SNAPSHOT)
    snap_row = None
    if not snapshot.empty:
        snap = snapshot[
            (snapshot["symbol"].astype(str) == symbol)
            & (snapshot["exchange"].astype(str) == exchange)
        ]
        if not snap.empty:
            snap_row = snap.iloc[0]
    catalogue = {str(row["id"]): row for row in CATALOGUE_ROWS}

    groups: list[dict[str, Any]] = []
    wanted = PRICE_GROUPS if kind != "index" else ()
    for title, metric_ids in wanted:
        groups.append(
            {
                "title": title,
                "metrics": [_metric_cell(mid, catalogue, snap_row) for mid in metric_ids],
            }
        )
    season_month = None if snap_row is None else _jsonable(snap_row.get("seasonality_month"))
    if season_month:
        for title, metric_ids in SEASONALITY_GROUP:
            groups.append(
                {
                    "title": f"{title} for {season_month}",
                    "metrics": [_metric_cell(mid, catalogue, snap_row) for mid in metric_ids],
                }
            )

    prices = warehouse.read(PRICES_DAILY)
    history = pd.DataFrame()
    if not prices.empty:
        history = prices[
            (prices["symbol"].astype(str) == symbol)
            & (prices["exchange"].astype(str) == exchange)
        ].sort_values("date")

    price_chart: list[dict[str, Any]] = []
    price_chart_reason = ""
    series: list[dict[str, Any]] = []
    if history.empty:
        price_chart_reason = (
            "No close series is stored for this instrument. The primary pipe "
            "publishes a daily series for a stock and an exchange-traded fund "
            "(ETF), and refuses the request for an index."
            if kind == "index"
            else "No close series is stored for this instrument yet."
        )
    else:
        points = _contiguous_closes(history)
        if len(points) < 2:
            price_chart_reason = "Fewer than two stored sessions. There is no line to draw."
        else:
            price_chart = line_windows(points)
        for rec in history.tail(PRICE_TAIL).to_dict(orient="records"):
            series.append(
                {
                    "date": rec["date"],
                    "close": _jsonable(rec["close"]),
                    "open": _jsonable(rec["open"]),
                    "high": _jsonable(rec["high"]),
                    "low": _jsonable(rec["low"]),
                    "volume": _jsonable(rec["volume"]),
                }
            )

    stored = warehouse.read(SEASONALITY)
    season_chart = None
    season_rows: list[dict[str, Any]] = []
    season_reason = ""
    mine = pd.DataFrame()
    if not stored.empty:
        mine = stored[stored["symbol"].astype(str) == symbol]
    if mine.empty:
        season_reason = (
            "Monthly seasonality is published for index symbols only. "
            "There is none stored for this instrument."
        )
    else:
        by_month = {str(rec["month"]): rec for rec in mine.to_dict(orient="records")}
        values: list[float | None] = []
        for month in MONTHS:
            rec = by_month.get(month)
            value = None if rec is None else rec.get("avg_monthly_return")
            values.append(None if _is_na(value) else float(value))
        season_chart = bar_geometry(list(MONTHS), values)
        for month in MONTHS:
            rec = by_month.get(month)
            if rec is None:
                season_rows.append({"month": month, "missing": True})
                continue
            season_rows.append(
                {
                    "month": month,
                    "missing": False,
                    "avg_monthly_return": _jsonable(rec.get("avg_monthly_return")),
                    "median_monthly_return": _jsonable(rec.get("median_monthly_return")),
                    "std_monthly_return": _jsonable(rec.get("std_monthly_return")),
                    "positive_return_ratio": _jsonable(rec.get("positive_return_ratio")),
                    "positive_months": _jsonable(rec.get("positive_months")),
                    "total_months": _jsonable(rec.get("total_months")),
                    "start_year": _jsonable(rec.get("start_year")),
                    "end_year": _jsonable(rec.get("end_year")),
                    "years_of_data": _jsonable(rec.get("years_of_data")),
                }
            )

    events = warehouse.read(MARKET_EVENTS)
    event_rows = []
    if not events.empty:
        ev = events[events["symbol"].astype(str) == symbol].sort_values("primary_date")
        for rec in ev.to_dict(orient="records"):
            event_rows.append(
                {
                    "event_type": rec.get("event_type"),
                    "primary_date": rec.get("primary_date"),
                    "description": rec.get("description"),
                    "details": rec.get("details"),
                }
            )

    insider = warehouse.read(INSIDER_TRADES)
    insider_rows = []
    insider_total = 0
    if not insider.empty:
        ins = insider[insider["symbol"].astype(str) == symbol].copy()
        if "trade_date" in ins.columns:
            ins = ins.sort_values("trade_date", ascending=False)
        insider_total = int(len(ins))
        for rec in ins.head(INSIDER_TAIL).to_dict(orient="records"):
            insider_rows.append(
                {
                    "trade_date": rec.get("trade_date"),
                    "person_name": rec.get("person_name"),
                    "person_category": rec.get("person_category"),
                    "transaction_type": rec.get("transaction_type"),
                    "acquired_quantity": _jsonable(rec.get("acquired_quantity")),
                    "disposed_quantity": _jsonable(rec.get("disposed_quantity")),
                    "holdings_after": _jsonable(rec.get("holdings_after")),
                }
            )

    switched_off = [
        {
            "label": str(row["label"]),
            "definition": str(row["definition"]),
            "reason": str(row["off_reason"]),
        }
        for row in CATALOGUE_ROWS
        if not row["available"]
    ]

    close_value = None if snap_row is None else _jsonable(snap_row.get("close"))
    day_move = None if snap_row is None else _jsonable(snap_row.get("return_1d"))
    return {
        "symbol": ident["symbol"],
        "exchange": ident["exchange"],
        "name": ident["name"],
        "instrument_kind": kind,
        "index_class": ident.get("index_class") or "",
        "isin": ident.get("isin"),
        "as_of": None if snap_row is None else str(snap_row["as_of"]),
        "headline": {
            "close": close_value,
            "close_display": display_value(close_value, "INR"),
            "return_1d": None,  # removed: computed dynamically
            "return_1d_display": display_value(day_move, "ratio"),
        },
        "session_count": 0 if history.empty else int(len(history)),
        "first_date": None if history.empty else str(history.iloc[0]["date"]),
        "last_date": None if history.empty else str(history.iloc[-1]["date"]),
        "metric_groups": groups,
        "price_chart": price_chart,
        "price_chart_reason": price_chart_reason,
        "prices": series,
        "seasonality_chart": season_chart,
        "seasonality_month": season_month,
        "seasonality_rows": season_rows,
        "seasonality_reason": season_reason,
        "events": event_rows,
        "insider": insider_rows,
        "insider_total": insider_total,
        "switched_off": switched_off,
        "disclaimer": (
            "This is warehouse data for one instrument. "
            "Not a buy or sell recommendation."
        ),
    }
