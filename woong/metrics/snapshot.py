"""Build the scan snapshot from warehouse tables.

Refuses to scan a supplied return when a close series exists: the engine uses
returns computed here. Refuses to fill a 52-week high from close. Refuses to
carry a seasonality figure for any month other than the one the as-of date falls
in, because a row a user reads today must describe today.
"""

from __future__ import annotations

import json
import sys
from datetime import date

import pandas as pd

from woong.config import load_settings
from woong.metrics.catalogue import CATALOGUE_ROWS
from woong.metrics.compute import metrics_as_of
from woong.metrics.studies import STUDY_ROWS
from woong.warehouse.schema import (
    FACTORS_DAILY,
    INSTRUMENTS,
    METRIC_CATALOG,
    PRICES_DAILY,
    SCAN_SNAPSHOT,
    SEASONALITY,
    STUDIES,
)
from woong.warehouse.store import Warehouse

SEASONALITY_COLUMNS = {
    "avg_monthly_return": "seasonality_avg_return",
    "median_monthly_return": "seasonality_median_return",
    "positive_return_ratio": "seasonality_positive_ratio",
    "std_monthly_return": "seasonality_std_return",
    "years_of_data": "seasonality_years",
}


def _latest_price_date(prices: pd.DataFrame) -> str:
    if prices.empty or prices["date"].isna().all():
        raise RuntimeError("prices_daily is empty. Harvest closes before building a snapshot.")
    return str(prices["date"].max())


def month_label(as_of: str) -> str:
    """The three-letter month the seasonality table keys on."""
    return date.fromisoformat(as_of).strftime("%b")


def _seasonality_for_month(warehouse: Warehouse, as_of: str) -> pd.DataFrame:
    label = month_label(as_of)
    stored = warehouse.read(SEASONALITY)
    if stored.empty:
        return pd.DataFrame(columns=["symbol", "seasonality_month", *SEASONALITY_COLUMNS.values()])
    month = stored.loc[stored["month"].astype(str) == label].copy()
    if month.empty:
        return pd.DataFrame(columns=["symbol", "seasonality_month", *SEASONALITY_COLUMNS.values()])
    month = month.rename(columns=SEASONALITY_COLUMNS)
    month["seasonality_month"] = label
    keep = ["symbol", "seasonality_month", *SEASONALITY_COLUMNS.values()]
    return month.loc[:, keep].drop_duplicates(subset=["symbol"], keep="last")


def build_snapshot(warehouse: Warehouse, as_of: str | None = None) -> tuple[int, str]:
    warehouse.create_empty_tables()
    warehouse.upsert(METRIC_CATALOG, pd.DataFrame(list(CATALOGUE_ROWS)))
    study_frame = pd.DataFrame(
        [
            {
                "study_id": row["study_id"],
                "title": row["title"],
                "shelf": row["shelf"],
                "author": row["author"],
                "idea": row["idea"],
                "query_json": json.dumps(row["query"], sort_keys=True),
            }
            for row in STUDY_ROWS
        ]
    )
    warehouse.replace(STUDIES, study_frame)

    prices = warehouse.read(PRICES_DAILY)
    instruments = warehouse.read(INSTRUMENTS)
    resolved = as_of or _latest_price_date(prices)
    computed = metrics_as_of(prices, resolved)
    if computed.empty:
        raise RuntimeError(f"No close on {resolved}. Cannot build a snapshot for that date.")

    if not instruments.empty:
        computed = computed.merge(
            instruments[["symbol", "exchange", "name", "instrument_kind"]],
            on=["symbol", "exchange"],
            how="left",
        )
    else:
        computed["name"] = None
        computed["instrument_kind"] = None

    factors = warehouse.read(FACTORS_DAILY)
    if not factors.empty:
        latest_factor = (
            factors.sort_values("date")
            .drop_duplicates(subset=["symbol"], keep="last")
            [["symbol", "momentum_score"]]
        )
        computed = computed.merge(latest_factor, on="symbol", how="left")
    else:
        computed["momentum_score"] = pd.NA

    seasonality = _seasonality_for_month(warehouse, resolved)
    if not seasonality.empty:
        computed = computed.merge(seasonality, on="symbol", how="left")

    computed["as_of"] = resolved
    frames = [computed.reindex(columns=list(SCAN_SNAPSHOT.columns))]

    # An index has no close on this feed, so it cannot come through the price
    # path. It still carries stored seasonality, so it gets a row with the price
    # columns null. A null reads as "had no value", which is what it is.
    if not instruments.empty and not seasonality.empty:
        indexes = instruments.loc[
            instruments["instrument_kind"] == "index",
            ["symbol", "exchange", "name", "instrument_kind"],
        ].merge(seasonality, on="symbol", how="inner")
        if not indexes.empty:
            indexes["as_of"] = resolved
            frames.append(indexes.reindex(columns=list(SCAN_SNAPSHOT.columns)))

    snapshot = pd.concat(frames, ignore_index=True)
    snapshot = snapshot.drop_duplicates(subset=list(SCAN_SNAPSHOT.natural_key), keep="first")
    warehouse.replace(SCAN_SNAPSHOT, snapshot)
    return len(snapshot), resolved


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    settings = load_settings()
    as_of = args[0] if args else None
    count, resolved = build_snapshot(Warehouse(settings.data_dir), as_of)
    print(f"scan_snapshot {count} rows as of {resolved}")
    return 0
