"""Seed rows for `metric_catalog`.

Refuses to mark a metric available unless its inputs are in the warehouse and
the formula matches the real definition.
"""

from __future__ import annotations

CATALOGUE_ROWS: tuple[dict[str, object], ...] = (
    {
        "id": "close",
        "label": "Close",
        "definition": "The last traded price of the session, as stored in prices_daily.close.",
        "formula": "prices_daily.close for the as-of date",
        "source_table": "prices_daily",
        "unit": "INR",
        "comparable": False,
        "direction": "none",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "return_1d",
        "label": "One-day return",
        "definition": "Close today divided by close one session earlier, minus one.",
        "formula": "close[t] / close[t-1] - 1",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "higher",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "return_1w",
        "label": "One-week return",
        "definition": "Close today divided by close five sessions earlier, minus one.",
        "formula": "close[t] / close[t-5] - 1",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "higher",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "return_1m",
        "label": "One-month return",
        "definition": "Close today divided by close twenty-one sessions earlier, minus one.",
        "formula": "close[t] / close[t-21] - 1",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "higher",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "return_3m",
        "label": "Three-month return",
        "definition": "Close today divided by close sixty-three sessions earlier, minus one.",
        "formula": "close[t] / close[t-63] - 1",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "higher",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "return_1y",
        "label": "One-year return",
        "definition": "Close today divided by close two hundred and fifty-two sessions earlier, minus one.",
        "formula": "close[t] / close[t-252] - 1",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "higher",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "return_3y",
        "label": "Three-year return",
        "definition": "Close today divided by close seven hundred and fifty-six sessions earlier, minus one.",
        "formula": "close[t] / close[t-756] - 1",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "higher",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "return_5y",
        "label": "Five-year return",
        "definition": "Close today divided by close one thousand two hundred and sixty sessions earlier, minus one.",
        "formula": "close[t] / close[t-1260] - 1",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "higher",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "fall_from_52w_high_pct",
        "label": "Fall from 52-week high",
        "definition": "One minus close divided by the highest high over the last two hundred and fifty-two sessions.",
        "formula": "1 - close / max(high over 252 sessions)",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "higher",
        "available": False,
        "off_reason": (
            "The primary application programming interface (API) does not release "
            "the session high without authentication. A fall computed from close "
            "alone is not the 52-week high."
        ),
    },
    {
        "id": "sma_200",
        "label": "200-Day Simple Moving Average",
        "definition": "The arithmetic mean of the last two hundred closes.",
        "formula": "mean(close over 200 sessions)",
        "source_table": "prices_daily",
        "unit": "INR",
        "comparable": False,
        "direction": "none",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "sma_50",
        "label": "50-Day Simple Moving Average",
        "definition": "The arithmetic mean of the last fifty closes.",
        "formula": "mean(close over 50 sessions)",
        "source_table": "prices_daily",
        "unit": "INR",
        "comparable": False,
        "direction": "none",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "dist_sma_200_pct",
        "label": "Distance from the 200-day moving average",
        "definition": (
            "Close divided by the two hundred day simple moving average, minus one. "
            "Positive means the close is above the average."
        ),
        "formula": "close / mean(close over 200 sessions) - 1",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "dist_sma_50_pct",
        "label": "Distance from the 50-day moving average",
        "definition": (
            "Close divided by the fifty day simple moving average, minus one. "
            "Positive means the close is above the average."
        ),
        "formula": "close / mean(close over 50 sessions) - 1",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "volatility_21d",
        "label": "Volatility over 21 sessions",
        "definition": (
            "The sample standard deviation of the last twenty-one daily "
            "close-to-close returns. It is not annualised."
        ),
        "formula": "stdev(close[t] / close[t-1] - 1 over 21 sessions)",
        "source_table": "prices_daily",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "seasonality_avg_return",
        "label": "Average return in the as-of month",
        "definition": (
            "The mean calendar-month return for the month the as-of date falls in, "
            "over every year the feed holds. Published for index symbols only, so a "
            "stock or an exchange-traded fund (ETF) has no value for it."
        ),
        "formula": "seasonality.avg_monthly_return for month(as_of)",
        "source_table": "seasonality",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "seasonality_median_return",
        "label": "Median return in the as-of month",
        "definition": (
            "The median calendar-month return for the month the as-of date falls in. "
            "Published for index symbols only."
        ),
        "formula": "seasonality.median_monthly_return for month(as_of)",
        "source_table": "seasonality",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "seasonality_positive_ratio",
        "label": "Share of years the as-of month closed up",
        "definition": (
            "Months that closed positive divided by months counted, for the month the "
            "as-of date falls in. Published for index symbols only."
        ),
        "formula": "seasonality.positive_return_ratio for month(as_of)",
        "source_table": "seasonality",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "seasonality_std_return",
        "label": "Spread of returns in the as-of month",
        "definition": (
            "The standard deviation of that calendar month's returns across years. "
            "Published for index symbols only."
        ),
        "formula": "seasonality.std_monthly_return for month(as_of)",
        "source_table": "seasonality",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "seasonality_years",
        "label": "Years of seasonality history",
        "definition": (
            "How many years the monthly seasonality sample covers. A small sample "
            "makes every other seasonality figure on this row weak."
        ),
        "formula": "seasonality.years_of_data for month(as_of)",
        "source_table": "seasonality",
        "unit": "years",
        "comparable": True,
        "direction": "higher",
        "available": True,
        "off_reason": "",
    },
    {
        "id": "seasonality_next_month_avg_return",
        "label": "Average return in the month after the as-of month",
        "definition": "The mean calendar-month return for the month after the as-of date.",
        "formula": "seasonality.avg_monthly_return for month(as_of) + 1",
        "source_table": "seasonality",
        "unit": "ratio",
        "comparable": True,
        "direction": "none",
        "available": False,
        "off_reason": (
            "Reading the next month would state what has not happened yet against a "
            "row the user is looking at today. The as-of month is the only month "
            "this snapshot carries."
        ),
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
    },
    {
        "id": "momentum_score",
        "label": "Supplied momentum score",
        "definition": "The momentum score as supplied by the primary feed, stored as received.",
        "formula": "factors_daily.momentum_score",
        "source_table": "factors_daily",
        "unit": "score",
        "comparable": True,
        "direction": "higher",
        "available": True,
        "off_reason": "",
    },
)
