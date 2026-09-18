"""Calendar-month returns derived from stored closes, and windowed aggregates.

The definitions here are fixed in [`docs/SEASONALITY.md`](../../docs/SEASONALITY.md).
The short form:

    month_return = close(last stored session of the month)
                 / close(last stored session of the previous month) - 1

Refuses to bridge a gap: a month whose previous calendar month has no stored
session has no return, because its divisor would be some earlier month wearing
the previous month's name. Refuses to fill a missing month with a zero or an
average. Refuses to let the part-month the as-of date falls in join an aggregate
of whole months. Refuses to report a window as N years when it found fewer, and
refuses to return any aggregate without the count of years behind it.

This module holds no network code and no display code.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

MONTH_LABELS: tuple[str, ...] = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)
LABEL_TO_MONTH: dict[str, int] = {label: index + 1 for index, label in enumerate(MONTH_LABELS)}

# Every statistic the seasonal metric family can ask for, and the column it
# lands in. The engine reads this map so a new statistic is added in one place.
STAT_COLUMNS: tuple[str, ...] = (
    "month_avg_return",
    "month_median_return",
    "month_best_return",
    "month_worst_return",
    "month_positive_ratio",
    "month_positive_count",
    "month_years_counted",
    "month_last_return",
)


_OUTPUT_COLUMNS = [
    "symbol",
    "exchange",
    "year",
    "month",
    "month_return",
    "close_start",
    "close_end",
    "start_date",
    "end_date",
    "sessions",
    "partial",
    "source",
    "as_of",
]


def month_label(month: int) -> str:
    """The three-letter label for a month number."""
    if not 1 <= int(month) <= 12:
        raise ValueError(f"{month!r} is not a month between 1 and 12.")
    return MONTH_LABELS[int(month) - 1]


def resolve_month(value: object) -> int:
    """Accept a month as a number or as its three-letter label."""
    if isinstance(value, str):
        text = value.strip().title()[:3]
        if text not in LABEL_TO_MONTH:
            raise ValueError(f"{value!r} is not a calendar month.")
        return LABEL_TO_MONTH[text]
    number = int(value)  # type: ignore[arg-type]
    if not 1 <= number <= 12:
        raise ValueError(f"{value!r} is not a month between 1 and 12.")
    return number


def monthly_returns(prices: pd.DataFrame, as_of: str, source: str = "primary") -> pd.DataFrame:
    """One row per symbol, exchange, year and month.

    `as_of` bounds the history read and decides which month is partial.
    """
    needed = {"symbol", "exchange", "date", "close"}
    missing = needed - set(prices.columns)
    if missing:
        raise ValueError(f"prices_daily is missing columns: {sorted(missing)}")
    if prices.empty:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    history = prices.loc[
        prices["date"].astype(str) <= as_of, ["symbol", "exchange", "date", "close"]
    ].copy()
    history = history.loc[history["close"].notna()]
    if history.empty:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    history["date"] = history["date"].astype(str)
    stamps = pd.to_datetime(history["date"], format="%Y-%m-%d", errors="coerce")
    if stamps.isna().any():
        bad = history.loc[stamps.isna(), "date"].iloc[0]
        raise ValueError(f"{bad!r} is not an ISO date in prices_daily.")
    history["year"] = stamps.dt.year.astype(int)
    history["month"] = stamps.dt.month.astype(int)
    history = history.sort_values(["symbol", "exchange", "date"], kind="mergesort")

    grouped = history.groupby(["symbol", "exchange", "year", "month"], sort=True)
    monthly = grouped.agg(
        close_end=("close", "last"),
        start_date=("date", "first"),
        end_date=("date", "last"),
        sessions=("close", "size"),
    ).reset_index()
    monthly = monthly.sort_values(["symbol", "exchange", "year", "month"], kind="mergesort")

    # A single ordinal for a calendar month makes "is the previous row really the
    # previous month" a subtraction instead of a date puzzle.
    monthly["_ordinal"] = monthly["year"] * 12 + monthly["month"]
    by_symbol = monthly.groupby(["symbol", "exchange"], sort=False)
    previous_close = by_symbol["close_end"].shift(1)
    previous_ordinal = by_symbol["_ordinal"].shift(1)
    adjacent = previous_ordinal.eq(monthly["_ordinal"] - 1)

    monthly["close_start"] = previous_close.where(adjacent)
    monthly["month_return"] = (monthly["close_end"] / monthly["close_start"]) - 1.0
    # A zero divisor is not a return. It is a null, like any other missing input.
    monthly.loc[monthly["close_start"].eq(0), "month_return"] = float("nan")

    as_of_date = date.fromisoformat(as_of)
    monthly["partial"] = (monthly["year"] == as_of_date.year) & (
        monthly["month"] == as_of_date.month
    )
    monthly["source"] = source
    monthly["as_of"] = as_of
    return monthly.drop(columns=["_ordinal"]).loc[:, _OUTPUT_COLUMNS].reset_index(drop=True)


def month_window_stats(
    monthly: pd.DataFrame,
    month: object,
    years: int,
    as_of_year: int,
) -> pd.DataFrame:
    """Aggregate one calendar month over the most recent `years` years.

    The window is the `years` most recent years, on or before `as_of_year`, that
    actually have a return for that month. `month_years_counted` reports what was
    found, so a window that only reached three years never claims ten.
    """
    if int(years) < 1:
        raise ValueError("A window needs at least one year.")
    number = resolve_month(month)
    columns = ["symbol", "exchange", *STAT_COLUMNS]
    if monthly.empty:
        return pd.DataFrame(columns=columns)

    picked = monthly.loc[
        (monthly["month"].astype(int) == number)
        & (~monthly["partial"].fillna(False).astype(bool))
        & (monthly["month_return"].notna())
        & (monthly["year"].astype(int) <= int(as_of_year))
    ].copy()
    if picked.empty:
        return pd.DataFrame(columns=columns)

    picked["year"] = picked["year"].astype(int)
    picked["month_return"] = picked["month_return"].astype(float)
    picked = picked.sort_values(["symbol", "exchange", "year"], kind="mergesort")
    # Keep the most recent `years` years per symbol. tail() after an ascending
    # sort is the window, and it is per group so a short history keeps whatever
    # it has instead of being dropped.
    picked = picked.groupby(["symbol", "exchange"], sort=False, group_keys=False).tail(int(years))

    # Every statistic comes out of one aggregation so nothing depends on two
    # group results landing in the same order.
    stats = picked.groupby(["symbol", "exchange"], sort=False).agg(
        month_avg_return=("month_return", "mean"),
        month_median_return=("month_return", "median"),
        month_best_return=("month_return", "max"),
        month_worst_return=("month_return", "min"),
        month_years_counted=("month_return", "size"),
        month_last_return=("month_return", "last"),
        month_positive_count=("month_return", lambda series: int((series > 0).sum())),
    ).reset_index()
    stats["month_positive_ratio"] = stats["month_positive_count"] / stats["month_years_counted"]
    return stats.loc[:, columns]


def build_monthly_returns(warehouse: object, as_of: str | None = None) -> tuple[int, str]:
    """Derive the whole `monthly_returns` table from stored closes.

    Imported lazily so this module stays free of warehouse concerns for tests
    that only exercise the arithmetic.
    """
    from woong.warehouse.schema import MONTHLY_RETURNS, PRICES_DAILY

    prices = warehouse.read(PRICES_DAILY)  # type: ignore[attr-defined]
    if prices.empty:
        raise RuntimeError("prices_daily is empty. Harvest closes before deriving months.")
    resolved = as_of or str(prices["date"].max())
    frame = monthly_returns(prices, resolved)
    if frame.empty:
        raise RuntimeError(f"No stored close on or before {resolved}. Nothing to derive.")
    warehouse.replace(MONTHLY_RETURNS, frame)  # type: ignore[attr-defined]
    return len(frame), resolved
