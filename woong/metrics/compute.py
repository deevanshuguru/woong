"""Formulas over warehouse closes.

Refuses to invent a session high, a ratio from missing line items, or a
substitute lookback when the series is too short. A short series is a null.
"""

from __future__ import annotations

import pandas as pd

RETURN_WINDOWS: dict[str, int] = {
    "return_1d": 1,
    "return_1w": 5,
    "return_1m": 21,
    "return_3m": 63,
    "return_1y": 252,
    "return_3y": 756,
    "return_5y": 1260,
}

SMA_WINDOWS: dict[str, int] = {"sma_50": 50, "sma_200": 200}

# Distance from a moving average is a ratio, so it is comparable across
# companies in a way the moving average itself is not.
SMA_DISTANCE: dict[str, str] = {
    "dist_sma_50_pct": "sma_50",
    "dist_sma_200_pct": "sma_200",
}

VOLATILITY_WINDOW = 21


def close_to_close_return(close_now: float, close_then: float) -> float:
    if pd.isna(close_now) or pd.isna(close_then) or close_then == 0:
        return float("nan")
    return float(close_now) / float(close_then) - 1.0


def distance_from_average(close: float, average: float) -> float:
    """Close divided by a moving average, minus one."""
    if pd.isna(close) or pd.isna(average) or average == 0:
        return float("nan")
    return float(close) / float(average) - 1.0


def return_volatility(closes: list[float], window: int = VOLATILITY_WINDOW) -> float:
    """Sample standard deviation of the last `window` daily returns.

    Needs `window` returns, which needs `window + 1` closes. A shorter series is
    a null, never a standard deviation over whatever happened to be there.
    """
    if window < 2:
        raise ValueError("A standard deviation needs at least two returns.")
    if len(closes) < window + 1:
        return float("nan")
    sample = closes[-(window + 1) :]
    if any(pd.isna(value) for value in sample):
        return float("nan")
    returns = [
        close_to_close_return(sample[i], sample[i - 1]) for i in range(1, len(sample))
    ]
    if any(pd.isna(value) for value in returns):
        return float("nan")
    return float(pd.Series(returns).std(ddof=1))


def simple_moving_average(closes: list[float], window: int) -> float:
    if window <= 0:
        raise ValueError("A moving average window must be a positive count of sessions.")
    if len(closes) < window:
        return float("nan")
    sample = closes[-window:]
    if any(pd.isna(value) for value in sample):
        return float("nan")
    return float(sum(sample) / window)


def metrics_as_of(prices: pd.DataFrame, as_of: str) -> pd.DataFrame:
    """One row per symbol and exchange on a single as-of date.

    A symbol whose last close is not on that date is omitted. The engine treats
    a missing snapshot row as a missing value.
    """
    if prices.empty:
        return pd.DataFrame()
    needed = {"symbol", "exchange", "date", "close"}
    missing = needed - set(prices.columns)
    if missing:
        raise ValueError(f"prices_daily is missing columns: {sorted(missing)}")
    history = prices.loc[prices["date"] <= as_of, ["symbol", "exchange", "date", "close"]].copy()
    if history.empty:
        return pd.DataFrame()
    history = history.sort_values(["symbol", "exchange", "date"])
    grouped = history.groupby(["symbol", "exchange"], sort=False)
    for name, lag in RETURN_WINDOWS.items():
        history[name] = grouped["close"].shift(lag)
    for name, window in SMA_WINDOWS.items():
        history[name] = grouped["close"].transform(
            lambda series, window=window: series.rolling(window, min_periods=window).mean()
        )
    daily = grouped["close"].pct_change(1)
    history["_vol"] = daily.groupby([history["symbol"], history["exchange"]]).transform(
        lambda series: series.rolling(VOLATILITY_WINDOW, min_periods=VOLATILITY_WINDOW).std(ddof=1)
    )
    today = history.loc[history["date"] == as_of].copy()
    if today.empty:
        return pd.DataFrame()
    for name in RETURN_WINDOWS:
        today[name] = [
            close_to_close_return(now, then)
            for now, then in zip(today["close"], today[name])
        ]
    for name, average in SMA_DISTANCE.items():
        today[name] = [
            distance_from_average(close, mean)
            for close, mean in zip(today["close"], today[average])
        ]
    today["volatility_21d"] = today["_vol"]
    return today.drop(columns=["_vol"]).reset_index(drop=True)
