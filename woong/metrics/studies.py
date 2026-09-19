"""Built-in study blocks — named starting points for the scanner.

All studies use the dynamic query shape.
No hardbound metric IDs (return_1y, return_1m, etc.).
Each study must be reproducible exactly from its query.
"""
from __future__ import annotations

STUDY_ROWS: tuple[dict[str, object], ...] = (
    {
        "study_id": "one_year_return",
        "title": "One-year return above 20 percent",
        "shelf": "Return",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) stocks have a one-year close-to-close return above 20 percent?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {
                        "metric": "return",
                        "window": {"n": 1, "unit": "Y"},
                        "period": "latest",
                        "cmp": ">",
                        "value": 20,
                        "unit": "percent",
                    }
                ],
            },
            "rank": {
                "by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc", "weight": 1}],
                "top_n": 30,
            },
        },
    },
    {
        "study_id": "six_month_up_one_month_down",
        "title": "Six months up, last month down",
        "shelf": "Return",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) stocks have a six-month return above 0 while the last one-month return is negative? Potential pullback entries."
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {
                        "metric": "return",
                        "window": {"n": 6, "unit": "M"},
                        "period": "latest",
                        "cmp": ">",
                        "value": 0,
                    },
                    {
                        "metric": "return",
                        "window": {"n": 1, "unit": "M"},
                        "period": "latest",
                        "cmp": "<",
                        "value": 0,
                    },
                ],
            },
            "rank": {
                "by": [{"metric": "return", "window": {"n": 6, "unit": "M"}, "dir": "desc"}],
                "top_n": 30,
            },
        },
    },
    {
        "study_id": "five_year_up_one_month_down",
        "title": "Five years up, last month down",
        "shelf": "Return",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) stocks have a five-year return above 100 percent while the last month is negative?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {
                        "metric": "return",
                        "window": {"n": 5, "unit": "Y"},
                        "period": "latest",
                        "cmp": ">",
                        "value": 100,
                        "unit": "percent",
                    },
                    {
                        "metric": "return",
                        "window": {"n": 1, "unit": "M"},
                        "period": "latest",
                        "cmp": "<",
                        "value": 0,
                    },
                ],
            },
            "rank": {
                "by": [{"metric": "return", "window": {"n": 5, "unit": "Y"}, "dir": "desc"}],
                "top_n": 30,
            },
        },
    },
    {
        "study_id": "above_200_dma",
        "title": "Close above 200-Day Moving Average",
        "shelf": "Trend",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) stocks are trading above their 200-Day Simple Moving Average (200 DMA)?"
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
            "rank": {
                "by": [{"metric": "return", "window": {"n": 1, "unit": "Y"}, "dir": "desc"}],
                "top_n": 30,
            },
        },
    },
    {
        "study_id": "golden_cross",
        "title": "50-Day Moving Average above 200-Day Moving Average",
        "shelf": "Trend",
        "author": "Deevanshu",
        "idea": (
            "Which National Stock Exchange (NSE) stocks show the 50-Day Simple Moving Average (50 DMA) above the 200-Day Simple Moving Average (200 DMA)?"
        ),
        "query": {
            "universe": {"set": "nse_equity"},
            "as_of": "latest",
            "filter": {
                "op": "and",
                "args": [
                    {
                        "metric": "sma_50",
                        "period": "latest",
                        "cmp": ">",
                        "other_metric": "sma_200",
                    }
                ],
            },
            "rank": {
                "by": [{"metric": "return", "window": {"n": 6, "unit": "M"}, "dir": "desc"}],
                "top_n": 30,
            },
        },
    },
)
