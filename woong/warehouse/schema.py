"""Column lists and natural keys for every warehouse table.

Refuses to invent a column that the ingest has not mapped from a real payload,
and refuses to put a provider name or a picture URL on any table.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableSpec:
    name: str
    natural_key: tuple[str, ...]
    columns: tuple[str, ...]


# instrument_kind is exactly stock, etf, or index.
# index_class keeps the feed's market / sector / thematic / strategy split
# without promoting those words into instrument_kind.
INSTRUMENTS = TableSpec(
    "instruments",
    ("symbol", "exchange"),
    (
        "symbol",
        "exchange",
        "name",
        "instrument_kind",
        "index_class",
        "isin",
        "source",
        "as_of",
    ),
)

UNIVERSES = TableSpec(
    "universes",
    ("universe_id",),
    ("universe_id", "name", "kind", "source", "as_of"),
)

UNIVERSE_MEMBERS = TableSpec(
    "universe_members",
    ("universe_id", "symbol", "exchange", "as_of"),
    ("universe_id", "symbol", "exchange", "as_of", "source"),
)

PRICES_DAILY = TableSpec(
    "prices_daily",
    ("symbol", "exchange", "date", "source"),
    (
        "symbol",
        "exchange",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
        "as_of",
    ),
)

# Maps a warehouse listing to the broker's opaque instrument id. The broker
# historical path keys on that id, not on (symbol, exchange). Kept separate so
# a master refresh cannot rewrite price rows.
BROKER_INSTRUMENTS = TableSpec(
    "broker_instruments",
    ("symbol", "exchange"),
    (
        "symbol",
        "exchange",
        "broker_token",
        "instrument_kind",
        "segment",
        "source",
        "as_of",
    ),
)

PRICE_METRICS_DAILY = TableSpec(
    "price_metrics_daily",
    ("symbol", "exchange", "date"),
    (
        "symbol",
        "exchange",
        "date",
        "return_1d",
        "return_1w",
        "return_1m",
        "return_3m",
        "return_1y",
        "return_3y",
        "return_5y",
        "source",
        "as_of",
    ),
)

FACTORS_DAILY = TableSpec(
    "factors_daily",
    ("symbol", "date", "source"),
    (
        "symbol",
        "date",
        "momentum_score",
        "value_score",
        "quality_score",
        "volatility_score",
        "source",
        "as_of",
    ),
)

# One calendar-month return per symbol and year, derived from stored closes.
# `month` is an integer 1 to 12 so it sorts. The three-letter label is derived
# where it is displayed and is not stored twice.
# `sessions` is carried because a month with four stored sessions is a real
# month return that nobody should lean on, and the count is the only thing that
# says so. `partial` marks the month the as-of date falls in, which is excluded
# from every aggregate.
MONTHLY_RETURNS = TableSpec(
    "monthly_returns",
    ("symbol", "exchange", "year", "month"),
    (
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
    ),
)

SEASONALITY = TableSpec(
    "seasonality",
    ("symbol", "month"),
    (
        "symbol",
        "month",
        "avg_monthly_return",
        "median_monthly_return",
        "std_monthly_return",
        "max_monthly_return",
        "min_monthly_return",
        "positive_months",
        "total_months",
        "start_year",
        "end_year",
        "positive_return_ratio",
        "return_risk_ratio",
        "years_of_data",
        "source",
        "as_of",
    ),
)

MARKET_BREADTH = TableSpec(
    "market_breadth",
    ("symbol", "date"),
    (
        "date",
        "symbol",
        "index_name",
        "index_class",
        "constituent_count",
        "above_ema_20",
        "above_ema_50",
        "above_ema_100",
        "above_ema_200",
        "above_ema_20_pct",
        "above_ema_50_pct",
        "above_ema_100_pct",
        "above_ema_200_pct",
        "near_52w_high_5pct",
        "near_52w_low_5pct",
        "source",
        "as_of",
    ),
)

MARKET_FLOWS = TableSpec(
    "market_flows",
    ("date", "frequency"),
    (
        "date",
        "frequency",
        "domestic_inst_purchase",
        "domestic_inst_disposal",
        "domestic_inst_net",
        "foreign_inst_purchase",
        "foreign_inst_disposal",
        "foreign_inst_net",
        "total_net",
        "source",
        "as_of",
    ),
)

MARKET_EVENTS = TableSpec(
    "market_events",
    ("event_id",),
    (
        "event_id",
        "symbol",
        "event_type",
        "event_category",
        "primary_date",
        "description",
        "details",
        "old_isin",
        "new_isin",
        "payload_json",
        "source",
        "as_of",
    ),
)

INSIDER_TRADES = TableSpec(
    "insider_trades",
    ("disclosure_id",),
    (
        "disclosure_id",
        "symbol",
        "trade_date",
        "person_name",
        "person_category",
        "transaction_type",
        "acquired_value",
        "disposed_value",
        "acquired_quantity",
        "disposed_quantity",
        "holdings_before",
        "holdings_before_pct",
        "holdings_after",
        "holdings_after_pct",
        "security_type",
        "acquisition_mode",
        "period_from",
        "period_to",
        "intim_date",
        "exchange",
        "source",
        "as_of",
    ),
)

FUNDAMENTALS_ANNUAL = TableSpec(
    "fundamentals_annual",
    ("symbol", "financial_year", "line_item"),
    ("symbol", "financial_year", "line_item", "value", "source", "as_of"),
)

FUNDAMENTALS_QUARTERLY = TableSpec(
    "fundamentals_quarterly",
    ("symbol", "period_end", "line_item"),
    ("symbol", "period_end", "line_item", "value", "source", "as_of"),
)

RATIOS_ASOF = TableSpec(
    "ratios_asof",
    ("symbol", "as_of", "ratio"),
    ("symbol", "as_of", "ratio", "value", "source"),
)

METRIC_CATALOG = TableSpec(
    "metric_catalog",
    ("id",),
    (
        "id",
        "label",
        "definition",
        "formula",
        "source_table",
        "unit",
        "comparable",
        "direction",
        "available",
        "off_reason",
    ),
)

SCAN_SNAPSHOT = TableSpec(
    "scan_snapshot",
    ("symbol", "exchange", "as_of"),
    (
        "symbol",
        "exchange",
        "name",
        "instrument_kind",
        "as_of",
        "close",
        "return_1d",
        "return_1w",
        "return_1m",
        "return_3m",
        "return_1y",
        "return_3y",
        "return_5y",
        "sma_50",
        "sma_200",
        "dist_sma_50_pct",
        "dist_sma_200_pct",
        "volatility_21d",
        "momentum_score",
        # The month label is carried so a seasonality figure on this row can say
        # which month it describes without the reader inferring it from as_of.
        "seasonality_month",
        "seasonality_avg_return",
        "seasonality_median_return",
        "seasonality_positive_ratio",
        "seasonality_std_return",
        "seasonality_years",
    ),
)

STUDIES = TableSpec(
    "studies",
    ("study_id",),
    # `title` is a short handle for a crowded list. `idea` stays the full
    # question, because a handle on its own is a label a user cannot check.
    ("study_id", "title", "shelf", "author", "idea", "query_json"),
)

SCAN_RUNS = TableSpec(
    "scan_runs",
    ("run_id",),
    ("run_id", "query_json", "as_of", "passed", "had_no_value"),
)

INGEST_JOBS = TableSpec(
    "ingest_jobs",
    ("pipe", "endpoint", "unit"),
    (
        "pipe",
        "endpoint",
        "unit",
        "status",
        "watermark",
        "http_status",
        "byte_count",
        "last_error",
        "updated_at",
    ),
)

WEIGHT_RUNS = TableSpec("weight_runs", ("run_id",), ("run_id",))
BACKTEST_RUNS = TableSpec("backtest_runs", ("run_id",), ("run_id",))
DEPLOY_ORDERS = TableSpec("deploy_orders", ("order_id",), ("order_id",))

TABLE_SPECS: tuple[TableSpec, ...] = (
    INSTRUMENTS,
    UNIVERSES,
    UNIVERSE_MEMBERS,
    BROKER_INSTRUMENTS,
    PRICES_DAILY,
    PRICE_METRICS_DAILY,
    FACTORS_DAILY,
    MONTHLY_RETURNS,
    SEASONALITY,
    MARKET_BREADTH,
    MARKET_FLOWS,
    MARKET_EVENTS,
    INSIDER_TRADES,
    FUNDAMENTALS_ANNUAL,
    FUNDAMENTALS_QUARTERLY,
    RATIOS_ASOF,
    METRIC_CATALOG,
    SCAN_SNAPSHOT,
    STUDIES,
    SCAN_RUNS,
    INGEST_JOBS,
    WEIGHT_RUNS,
    BACKTEST_RUNS,
    DEPLOY_ORDERS,
)
