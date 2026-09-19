"""Dynamic metric computation from price series.

Every parametric metric (return, sma) is computed here at query time from
prices_daily. No hardbound period IDs. No proxy values. If a series is too
short for the window, the result is NaN — never a substituted value.

Window units:
  D = trading sessions (1D = 1 session)
  W = weeks            (1W = 5 sessions)
  M = months           (1M = 21 sessions)
  Y = years            (1Y = 252 sessions)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

UNIT_SESSIONS: dict[str, int] = {"D": 1, "W": 5, "M": 21, "Y": 252}
PARAMETRIC_METRICS: frozenset[str] = frozenset({"return", "sma"})


@dataclass(frozen=True)
class WindowSpec:
    n: int
    unit: str  # D, W, M, Y

    def to_sessions(self) -> int:
        return self.n * UNIT_SESSIONS[self.unit]

    def label(self) -> str:
        return f"{self.n}{self.unit}"


def parse_window(raw: dict[str, Any]) -> WindowSpec:
    """Parse and validate a raw window dict. Raises ValueError on bad input."""
    if not isinstance(raw, dict):
        raise ValueError("window must be an object with n and unit.")
    n = raw.get("n")
    unit = str(raw.get("unit", "")).upper()
    if not isinstance(n, int) or n <= 0:
        raise ValueError(f"window.n must be a positive integer, got {n!r}.")
    if unit not in UNIT_SESSIONS:
        raise ValueError(f"window.unit must be D, W, M, or Y — got {unit!r}.")
    return WindowSpec(n=n, unit=unit)


def column_key(metric: str, window: WindowSpec) -> str:
    """Canonical temp column name. Never conflicts with snapshot columns."""
    return f"_dyn_{metric}_{window.label()}"


def _return_series(series: pd.Series, sessions: int) -> pd.Series:
    past = series.shift(sessions)
    result = series / past - 1.0
    result[past.isna() | (past == 0)] = float("nan")
    return result


def _sma_series(series: pd.Series, sessions: int) -> pd.Series:
    return series.rolling(sessions, min_periods=sessions).mean()


def compute_dynamic_columns(
    prices: pd.DataFrame,
    as_of: str,
    requests: list[tuple[str, WindowSpec]],
) -> pd.DataFrame:
    """Compute parametric metrics for all symbols as of a single date.

    Returns DataFrame with (symbol, exchange) + one column per request.
    Symbols whose last close is not on as_of are omitted.
    Series too short for the window: NaN — never a proxy.
    """
    if prices.empty or not requests:
        return pd.DataFrame(columns=["symbol", "exchange"])

    needed = {"symbol", "exchange", "date", "close"}
    if not needed.issubset(prices.columns):
        return pd.DataFrame(columns=["symbol", "exchange"])

    history = (
        prices.loc[prices["date"] <= as_of, ["symbol", "exchange", "date", "close"]]
        .sort_values(["symbol", "exchange", "date"])
        .copy()
    )
    if history.empty:
        return pd.DataFrame(columns=["symbol", "exchange"])

    grouped = history.groupby(["symbol", "exchange"], sort=False)

    for metric, window in requests:
        col = column_key(metric, window)
        sessions = window.to_sessions()
        if metric == "return":
            history[col] = grouped["close"].transform(
                lambda s, n=sessions: _return_series(s, n)
            )
        elif metric == "sma":
            history[col] = grouped["close"].transform(
                lambda s, n=sessions: _sma_series(s, n)
            )

    today = history.loc[history["date"] == as_of].copy()
    if today.empty:
        return pd.DataFrame(columns=["symbol", "exchange"])

    dyn_cols = ["symbol", "exchange"] + [column_key(m, w) for m, w in requests]
    return today[[c for c in dyn_cols if c in today.columns]].reset_index(drop=True)
