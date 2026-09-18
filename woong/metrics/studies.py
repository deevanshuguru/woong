"""Named study blocks. Each one is a person's rule, already written.

Refuses to attribute a study to Woong, and refuses advice language in the idea.
Every idea is a question, because a question is what a rule answers. A study
whose metrics are not switched on is not listed here: it would fail validation
at the moment a user pressed run, which is a worse way to learn it is off.

`shelf` groups the list so a user is not reading fourteen lines to find one. It
is a filing label, never a claim that one shelf is better than another.
"""

from __future__ import annotations

from typing import Any

STUDY_ROWS: tuple[dict[str, Any], ...] = (
    {
        "study_id": "one_year_return",
        "title": "One-year return above 20 percent",
        "shelf": "Return",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) names have a one-year "
            "close-to-close return above 20 percent?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {"metric": "return_1y", "period": "latest", "cmp": ">", "value": 0.20}
                ],
            },
            "rank": {"by": [{"metric": "return_1y", "dir": "desc", "weight": 1}], "top_n": 30},
        },
    },
    {
        "study_id": "one_year_or_one_month",
        "title": "Strong year or strong month",
        "shelf": "Return",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) names have a one-year "
            "close-to-close return above 20 percent, or a one-month return "
            "above 10 percent?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "or",
                "args": [
                    {"metric": "return_1y", "period": "latest", "cmp": ">", "value": 0.20},
                    {"metric": "return_1m", "period": "latest", "cmp": ">", "value": 0.10},
                ],
            },
            "rank": {"by": [{"metric": "return_1y", "dir": "desc", "weight": 1}], "top_n": 30},
        },
    },
    {
        "study_id": "five_year_up_one_month_down",
        "title": "Five years up, last month down",
        "shelf": "Return",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) names have a five-year "
            "close-to-close return above 100 percent while the last "
            "twenty-one sessions are negative?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {"metric": "return_5y", "period": "latest", "cmp": ">", "value": 1.0},
                    {"metric": "return_1m", "period": "latest", "cmp": "<", "value": 0.0},
                ],
            },
            "rank": {"by": [{"metric": "return_5y", "dir": "desc", "weight": 1}], "top_n": 30},
        },
    },
    {
        "study_id": "above_sma_200",
        "title": "Close above the 200-day average",
        "shelf": "Moving average",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) names close above their "
            "200-Day Simple Moving Average (200 DMA)?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {
                        "metric": "close",
                        "period": "latest",
                        "cmp": ">",
                        "other_metric": "sma_200",
                    }
                ],
            },
            "rank": {"by": [{"metric": "return_1m", "dir": "desc", "weight": 1}], "top_n": 30},
        },
    },
    {
        "study_id": "above_both_averages",
        "title": "Above both averages",
        "shelf": "Moving average",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) names sit above both the "
            "50-day and the 200-day simple moving average, ordered by how far "
            "above the 200-day average they are?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {"metric": "dist_sma_50_pct", "period": "latest", "cmp": ">", "value": 0.0},
                    {"metric": "dist_sma_200_pct", "period": "latest", "cmp": ">", "value": 0.0},
                ],
            },
            "rank": {
                "by": [{"metric": "dist_sma_200_pct", "dir": "desc", "weight": 1}],
                "top_n": 30,
            },
        },
    },
    {
        "study_id": "far_below_average",
        "title": "Far below the 200-day average",
        "shelf": "Moving average",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) names are more than 25 percent "
            "below their 200-day simple moving average?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {"metric": "dist_sma_200_pct", "period": "latest", "cmp": "<", "value": -0.25}
                ],
            },
            "rank": {
                "by": [{"metric": "dist_sma_200_pct", "dir": "asc", "weight": 1}],
                "top_n": 30,
            },
        },
    },
    {
        "study_id": "quiet_year",
        "title": "Up on the year, quiet last month",
        "shelf": "Volatility",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) names are up more than 20 percent "
            "over a year while the standard deviation of their last twenty-one "
            "daily returns is under 2 percent?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {"metric": "return_1y", "period": "latest", "cmp": ">", "value": 0.20},
                    {"metric": "volatility_21d", "period": "latest", "cmp": "<", "value": 0.02},
                ],
            },
            "rank": {"by": [{"metric": "volatility_21d", "dir": "asc", "weight": 1}], "top_n": 30},
        },
    },
    {
        "study_id": "noisiest_names",
        "title": "Noisiest last month",
        "shelf": "Volatility",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) names have the widest spread of "
            "daily returns over the last twenty-one sessions?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {"metric": "volatility_21d", "period": "latest", "cmp": ">", "value": 0.0}
                ],
            },
            "rank": {"by": [{"metric": "volatility_21d", "dir": "desc", "weight": 1}], "top_n": 30},
        },
    },
    {
        "study_id": "etf_one_month",
        "title": "Exchange-traded funds by the month",
        "shelf": "Exchange-traded funds",
        "author": "Deevanshu",
        "idea": (
            "How did National Stock Exchange (NSE) exchange-traded funds (ETFs) "
            "close over the last twenty-one sessions, best first?"
        ),
        "query": {
            "universe": {"set": "nse_etf"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {"metric": "return_1m", "period": "latest", "cmp": ">", "value": -1.0}
                ],
            },
            "rank": {"by": [{"metric": "return_1m", "dir": "desc", "weight": 1}], "top_n": 30},
        },
    },
    {
        "study_id": "two_speed_blend",
        "title": "Year and month weighted together",
        "shelf": "Return",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) names rank highest when the "
            "one-year return counts for 70 percent of the order and the "
            "one-month return for 30 percent?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {"metric": "return_1y", "period": "latest", "cmp": ">", "value": 0.0},
                    {"metric": "return_1m", "period": "latest", "cmp": ">", "value": 0.0},
                ],
            },
            "rank": {
                "by": [
                    {"metric": "return_1y", "dir": "desc", "weight": 0.7},
                    {"metric": "return_1m", "dir": "desc", "weight": 0.3},
                ],
                "top_n": 30,
            },
        },
    },
    # The three below stand on the seasonality table. That table is published for
    # index symbols and for nothing else, so these run over a universe of
    # indexes. The same rule pointed at equity would return every name as "had no
    # value", which is honest and useless.
    {
        "study_id": "seasonality_month_strong",
        "title": "Indexes whose current month usually closed up",
        "shelf": "Seasonality",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) indexes closed this calendar "
            "month positive in more than 60 percent of the years on record, "
            "counting only indexes with at least 15 years of history?"
        ),
        "query": {
            "universe": {"set": "nse_index"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {
                        "metric": "seasonality_positive_ratio",
                        "period": "latest",
                        "cmp": ">",
                        "value": 0.60,
                    },
                    {
                        "metric": "seasonality_years",
                        "period": "latest",
                        "cmp": ">=",
                        "value": 15,
                    },
                ],
            },
            "rank": {
                "by": [{"metric": "seasonality_avg_return", "dir": "desc", "weight": 1}],
                "top_n": 30,
            },
        },
    },
    {
        "study_id": "seasonality_month_weak",
        "title": "Indexes whose current month usually closed down",
        "shelf": "Seasonality",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) indexes have a negative average "
            "return in this calendar month across at least 15 years of history?"
        ),
        "query": {
            "universe": {"set": "nse_index"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {
                        "metric": "seasonality_avg_return",
                        "period": "latest",
                        "cmp": "<",
                        "value": 0.0,
                    },
                    {
                        "metric": "seasonality_years",
                        "period": "latest",
                        "cmp": ">=",
                        "value": 15,
                    },
                ],
            },
            "rank": {
                "by": [{"metric": "seasonality_avg_return", "dir": "asc", "weight": 1}],
                "top_n": 30,
            },
        },
    },
    {
        "study_id": "seasonality_repeatable",
        "title": "Current month strong and not scattered",
        "shelf": "Seasonality",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) indexes average more than 1 "
            "percent in this calendar month while the spread of that month's "
            "returns across years stays under 6 percent?"
        ),
        "query": {
            "universe": {"set": "nse_index"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {
                        "metric": "seasonality_avg_return",
                        "period": "latest",
                        "cmp": ">",
                        "value": 0.01,
                    },
                    {
                        "metric": "seasonality_std_return",
                        "period": "latest",
                        "cmp": "<",
                        "value": 0.06,
                    },
                    {
                        "metric": "seasonality_years",
                        "period": "latest",
                        "cmp": ">=",
                        "value": 15,
                    },
                ],
            },
            "rank": {
                "by": [
                    {"metric": "seasonality_positive_ratio", "dir": "desc", "weight": 0.5},
                    {"metric": "seasonality_avg_return", "dir": "desc", "weight": 0.5},
                ],
                "top_n": 30,
            },
        },
    },
    {
        "study_id": "supplied_momentum",
        "title": "Supplied momentum score, highest first",
        "shelf": "Supplied factor",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) names carry the highest supplied "
            "momentum score, among those up over the last twenty-one sessions?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {"metric": "return_1m", "period": "latest", "cmp": ">", "value": 0.0},
                    {"metric": "momentum_score", "period": "latest", "cmp": ">", "value": 0.0},
                ],
            },
            "rank": {"by": [{"metric": "momentum_score", "dir": "desc", "weight": 1}], "top_n": 30},
        },
    },
)
