"""Metric catalogue — every metric the scanner can use.

Parametric metrics (return, sma) have no window baked in. The user
supplies the window in the condition node. The engine computes the value
at query time from prices_daily.

Non-parametric metrics are read directly from the scan snapshot.

A metric that cannot be computed to its real definition is marked
available=False with an exact off_reason. No proxy, no estimate.
"""
from __future__ import annotations

PARAMETRIC_METRICS: frozenset[str] = frozenset({"return", "sma"})

CATALOGUE_ROWS: tuple[dict[str, object], ...] = (
    {
        "id": "return",
        "label": "Return",
        "definition": (
            "Close-to-close return over a chosen window ending on the as-of date. "
            "Requires a window (n, unit) in the condition. "
            "If the series is shorter than the window, the value is missing."
        ),
        "formula": "close[as_of] / close[as_of - window] - 1",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "higher",
        "available": True,
        "off_reason": "",
        "parametric": True,
    },
    {
        "id": "sma",
        "label": "Simple Moving Average",
        "definition": (
            "Arithmetic mean of the last N closes, where N is supplied via the window. "
            "If the series is shorter than the window, the value is missing."
        ),
        "formula": "mean(close over window sessions)",
        "source_table": "prices_daily",
        "unit": "INR",
        "comparable": False,
        "direction": "none",
        "available": True,
        "off_reason": "",
        "parametric": True,
    },
    {
        "id": "close",
        "label": "Close",
        "definition": "The last traded price of the session.",
        "formula": "prices_daily.close for the as-of date",
        "source_table": "prices_daily",
        "unit": "INR",
        "comparable": False,
        "direction": "none",
        "available": True,
        "off_reason": "",
        "parametric": False,
    },
    {
        "id": "sma_50",
        "label": "50-Day Simple Moving Average",
        "definition": "Arithmetic mean of the last 50 closes.",
        "formula": "mean(close over 50 sessions)",
        "source_table": "prices_daily",
        "unit": "INR",
        "comparable": False,
        "direction": "none",
        "available": True,
        "off_reason": "",
        "parametric": False,
    },
    {
        "id": "sma_200",
        "label": "200-Day Simple Moving Average",
        "definition": "Arithmetic mean of the last 200 closes.",
        "formula": "mean(close over 200 sessions)",
        "source_table": "prices_daily",
        "unit": "INR",
        "comparable": False,
        "direction": "none",
        "available": True,
        "off_reason": "",
        "parametric": False,
    },
    {
        "id": "dist_sma_50_pct",
        "label": "Distance from the 50-Day Moving Average",
        "definition": "Close divided by the 50-day moving average, minus one.",
        "formula": "close / sma_50 - 1",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
        "parametric": False,
    },
    {
        "id": "dist_sma_200_pct",
        "label": "Distance from the 200-Day Moving Average",
        "definition": "Close divided by the 200-day moving average, minus one.",
        "formula": "close / sma_200 - 1",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
        "parametric": False,
    },
    {
        "id": "volatility_21d",
        "label": "Volatility over 21 Sessions",
        "definition": (
            "Sample standard deviation of the last 21 daily close-to-close returns. "
            "Not annualised."
        ),
        "formula": "stdev(daily_return over 21 sessions)",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
        "parametric": False,
    },
    {
        "id": "fall_from_52w_high_pct",
        "label": "Fall from 52-week high",
        "definition": "One minus close divided by the highest high over 252 sessions.",
        "formula": "1 - close / max(high over 252 sessions)",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "higher",
        "available": False,
        "off_reason": (
            "session high is not available from the current data source. "
            "A fall computed from close alone is not the 52-week high."
        ),
        "parametric": False,
    },
    {
        "id": "seasonality_avg_return",
        "label": "Average Return in the As-Of Month",
        "definition": (
            "Mean calendar-month return for the month the as-of date falls in, "
            "across all years with data."
        ),
        "formula": "mean(month_return) for month(as_of)",
        "source_table": "seasonality",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
        "parametric": False,
    },
    {
        "id": "seasonality_median_return",
        "label": "Median Return in the As-Of Month",
        "definition": "Median calendar-month return for the month the as-of date falls in.",
        "formula": "median(month_return) for month(as_of)",
        "source_table": "seasonality",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
        "parametric": False,
    },
    {
        "id": "seasonality_positive_ratio",
        "label": "Share of Years the As-Of Month Closed Up",
        "definition": "Months closed positive divided by months counted, for the as-of month.",
        "formula": "positive_months / total_months for month(as_of)",
        "source_table": "seasonality",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
        "parametric": False,
    },
    {
        "id": "seasonality_std_return",
        "label": "Spread of Returns in the As-Of Month",
        "definition": "Standard deviation of that calendar month returns across years.",
        "formula": "stdev(month_return) for month(as_of)",
        "source_table": "seasonality",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
        "parametric": False,
    },
    {
        "id": "seasonality_years",
        "label": "Years of Seasonality History",
        "definition": "How many years the monthly seasonality sample covers.",
        "formula": "years_of_data for month(as_of)",
        "source_table": "seasonality",
        "unit": "years",
        "comparable": True,
        "direction": "higher",
        "available": True,
        "off_reason": "",
        "parametric": False,
    },
    {
        "id": "momentum_score",
        "label": "Supplied Momentum Score",
        "definition": "Momentum score as supplied by the primary feed, stored as received.",
        "formula": "factors_daily.momentum_score",
        "source_table": "factors_daily",
        "unit": "score",
        "comparable": True,
        "direction": "higher",
        "available": True,
        "off_reason": "",
        "parametric": False,
    },
    {
        "id": "pe",
        "label": "Price to Earnings (P/E)",
        "definition": "Close divided by earnings per share for a stated period.",
        "formula": "close / earnings_per_share",
        "source_table": "ratios_asof",
        "unit": "times",
        "comparable": True,
        "direction": "lower",
        "available": False,
        "off_reason": "Earnings per share is not in the warehouse. No fundamentals pipe has been loaded.",
        "parametric": False,
    },
)
