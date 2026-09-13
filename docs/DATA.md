# Data

## Source tags

Only these five values ever appear in a `source` column. No provider name is
recorded anywhere.

| Tag | Meaning |
|---|---|
| `primary` | The primary market data application programming interface (API) |
| `broker` | The broker connection, used for the official daily close |
| `exchange` | Published exchange files, used for index membership |
| `fundamentals` | The fundamentals feed |
| `manual` | Hand-entered and hand-verified |

## Coverage

The harvest covers the **full symbol master and every index**. Not a small index
slice.

Rows may be null. A symbol listed last month has no three-year return, and that
is correct. What is not acceptable is a symbol missing because ingest never
asked for it, because nothing downstream can tell those two cases apart.

## Canonical tables

### Reference

| Table | Grain | Notes |
|---|---|---|
| `instruments` | symbol | Symbol, exchange, International Securities Identification Number (ISIN), name, instrument type |
| `universes` | universe identifier | Name and kind: all equity, index, sector, custom |
| `universe_members` | universe, symbol, as-of | Snapshotted every harvest, so membership history accumulates from day one |

### Market

| Table | Grain | Notes |
|---|---|---|
| `prices_daily` | symbol, date, source | Open, high, low, close, volume. Both pipes may hold the same date |
| `price_metrics_daily` | symbol, date | Returns over standard windows, distance from the 52-week high, moving averages, realised volatility |
| `factors_daily` | symbol, date, source | Externally supplied factor scores. Stored as supplied. Never presented as Woong's own calculation |
| `seasonality` | symbol, month | Average, median and dispersion of monthly returns, plus the sample window. Every symbol and every index |
| `market_breadth` | date, index | Share of constituents above each moving average, counts near 52-week extremes |
| `market_flows` | date, frequency | Institutional buy, sell and net values |
| `market_events` | event identifier | Corporate actions and result dates. Payload kept whole alongside the parsed columns |
| `insider_trades` | symbol, date, disclosure, person, type | Holdings before and after, quantities and values |

### Fundamentals

Line-item grain on purpose. Any future feed maps into the same two tables
without a second data model.

| Table | Grain |
|---|---|
| `fundamentals_annual` | symbol, financial year, line item |
| `fundamentals_quarterly` | symbol, period end, line item |
| `ratios_asof` | symbol, as-of |

`ratios_asof` holds only ratios computed from stored line items, or supplied by
a source with a stated definition. It stays empty, and the matching metrics stay
switched off, until that pipe exists.

### Engine and product

| Table | Purpose |
|---|---|
| `metric_catalog` | One row per metric: definition, formula, source table, comparability, direction, on or off, and the reason when off |
| `scan_snapshot` | Wide table, one row per symbol per as-of date. What the engine actually scans |
| `studies` | A named author's query, with a one-line statement of the idea |
| `scan_runs` | Every execution: the query, the as-of date, how many passed, how many had no value |
| `ingest_jobs` | One row per pipe and endpoint: watermark, cursor, status, last error |

### Reserved

`weight_runs`, `backtest_runs` and `deploy_orders` are created empty. They make
the product path visible in the schema and stop the scanner from hardening into
the only thing the shape supports.

## Refresh

| Pipe | Cadence | Notes |
|---|---|---|
| `primary` | Full harvest once, then incremental by watermark | Checkpointed per symbol |
| `broker` | After each session | Official close. Takes precedence in the snapshot |
| `exchange` | Every harvest | Index membership, snapshotted |
| `fundamentals` | When it exists | Into the same line-item tables |

### Precedence in the snapshot

When more than one pipe holds the same fact for the same symbol and date:

1. `broker` close, because it is the official session close.
2. `primary` close.
3. Anything else, in the order documented in the snapshot builder.

Both rows stay in `prices_daily`. Precedence is applied when the snapshot is
built, never by deleting data.

## Ingest rules

1. Write raw before parsing. A parse bug must not cost a re-fetch.
2. Checkpoint after every symbol or page into `ingest_jobs`.
3. A crash resumes from the checkpoint. It never restarts the harvest.
4. Upserts are idempotent. A second run adds nothing.
5. Rate limit and bound retries. A provider is not a load test target.
6. Failures are collected, printed and returned as a non-zero exit code. A run
   that half-worked must not look like a run that worked.
7. Never author reference data. Download it or derive it. Do not type it.
