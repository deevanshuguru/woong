# Seasonality: jobs, decisions and the work breakdown

Seasonality is the first thing Woong will hold that is not a single number as of
today. It is a distribution across years. That changes what the warehouse
stores, what the query object can say, and what a screen has to show alongside
every figure. This file is the plan, and the definitions it fixes are binding.

---

## 1. The jobs to be done

Stated as the user stated them, in the order they were asked for.

**J1. Write a condition about one calendar month over a chosen window.**
"Has this name returned more than 10 percent in any September in the last 10
years?" The month and the window are the user's choice, not ours.

**J2. Judge cyclicality on one instrument's page.**
See every calendar month against every year, so the eye finds the pattern. See
month on month and year on year, because a single average hides whether a month
is reliably good or occasionally spectacular.

**J3. Rank a universe on one month over a chosen window.**
"Which names did best in October over the last 5 years?" The user then draws
their own correlation. Woong returns the ordering and the sample size behind it,
and says nothing about what to do with it.

Everything below exists to serve these three and nothing wider.

---

## 2. The central data decision

There are two possible bases for every seasonality figure.

**Option A, the supplied aggregate.** Twelve rows for each symbol: the average,
median, spread, best, worst and positive share for each calendar month, computed
over that symbol's whole sample. This is what the primary pipe publishes.

**Option B, derived from our own stored closes.** One row for each symbol, year
and month, holding that month's return. Aggregates are computed from it on
demand.

Option A cannot do the job. It cannot be narrowed to the last 10 years, because
it is already averaged over the whole sample. It cannot show a year by year
grid, because the years are gone. It answers none of J1, J2 or J3 without us
inventing a window it does not have, and inventing a window is exactly the proxy
number the project refuses.

**Decision: Option B is the basis for every seasonality metric and every screen.**
The supplied aggregate is still harvested, and it is used for one purpose: an
independent check that our derivation agrees with a second source. It is never
shown next to our figure as an alternative, because two numbers for one idea is
how a user stops trusting both.

---

## 3. Definitions this fixes

These are binding. A screen or a metric that does not match them is wrong.

### 3.1 A calendar-month return

For one symbol, one year and one month:

```
month_return = close(last stored session in that month)
             / close(last stored session in the previous month)
             - 1
```

Consequences, each of which is a refusal:

- A month with no stored session has no return. It is absent, not zero.
- The first month of a symbol's series has no return, because there is no
  previous month to divide by. It is absent.
- A gap of a whole month breaks the chain. The month after a missing month has
  no return, because its divisor is not the previous month.
- The row carries `sessions`, the count of stored sessions in that month. A month
  with four stored sessions is a real month return and the count is what tells
  the reader not to lean on it.
- The month the as-of date falls in is marked `partial`. A part month is excluded
  from every aggregate, because comparing three weeks against a run of full
  months measures two different things.

### 3.2 A window

"The last N years" means the N most recent calendar years that end before or on
the as-of year, counting only years that have a value for the month in question.
The count of years actually used is `month_years_counted` and it is always
returned. A window that found 3 years is not a 10 year window and never reports
itself as one.

### 3.3 The rule that follows

**A seasonal figure never appears without its sample size.** Not in a table cell,
not in a chart, not in a read-back sentence. An average October over 2 years and
an average October over 20 years are different claims, and the number alone
cannot tell them apart. This goes into the design standard.

---

## 4. What the query object gains

Today a condition names a metric and compares it to a value. A seasonal metric
needs parameters, because "September over 10 years" is not a different metric
from "October over 5 years", it is the same metric asked a different question.

```json
{
  "metric": "month_best_return",
  "params": { "month": "Sep", "years": 10 },
  "cmp": ">",
  "value": 10,
  "unit": "percent"
}
```

The family, all resolved from `monthly_returns`:

| Metric | Meaning |
|---|---|
| `month_avg_return` | Mean of that month's returns across the window |
| `month_median_return` | Median of them |
| `month_best_return` | The largest single one |
| `month_worst_return` | The smallest single one |
| `month_positive_ratio` | Share of years in the window that closed up |
| `month_positive_count` | Count of years that closed up |
| `month_years_counted` | Years the window actually found |
| `month_last_return` | The most recent year's return for that month |

J1 is `month_best_return(Sep, 10) > 10 percent`. J3 is a rank by
`month_avg_return(Oct, 5)`.

Because these depend on parameters, they are resolved at query time from
`monthly_returns` rather than read from `scan_snapshot`. That is still Python
computing every number, and the cheap refusals still happen first: an unknown
month, a window of zero years or a metric that is switched off is rejected before
any table is touched.

---

## 5. What this change touches

| Area | Change |
|---|---|
| `.env` | The bearer token. Already read through `woong/config.py`, so no code change. |
| `woong/ingest/primary.py` | Seasonality harvest widens from indexes to every stock and exchange-traded fund (ETF). An HTTP 401 must stop the run loudly, because a silent expiry looks like a symbol with no data. |
| `woong/warehouse/schema.py` | New table `monthly_returns`, keyed on symbol, exchange, year, month. |
| `woong/metrics/` | New derivation of monthly returns from stored closes. Catalogue gains the parameterised family and a `parameters` field. |
| `woong/engine/` | Validate `params`. Resolve seasonal metrics from `monthly_returns`. Read-back names the month and the window. |
| `woong/api/` | Instrument page gains the month by year grid, month on month and year on year. Chart module gains grid geometry. |
| `woong/web/` | Condition row gains month and window pickers. The read-back moves to the top of the results pane. Quick-add chips cut the cost of a first condition. |
| Docs | `DATA.md`, `QUERY.md`, `DESIGN.md`, `STATUS.md`, `mvp/tasks.json`. |
| Snapshot | The whole-sample `seasonality_*` columns come out once the parameterised family lands. One idea, one number. |

---

## 6. The work, in order

Each item leaves something testable behind and is one issue, one branch, one
pull request.

**S1. Harvest per-stock seasonality.** Ingest only. The token is the perishable
part of this plan, so fetching comes before anything that only needs a computer.
Done when a raw payload is on disk for every stock and ETF, an HTTP 401 fails the
run with a message that names token expiry, and a second run fetches nothing.

**S2. Derive `monthly_returns` from stored closes.** Pure computation, no
network. Done when a hand-worked three month example passes, a gap produces an
absent month rather than a bridged one, the partial month is flagged, and the
table builds for every symbol that has closes.

**S3. Cross-check the derivation against the supplied aggregate.** Done when a
check compares our whole-sample average per month against the supplied one,
reports every symbol that disagrees beyond a stated tolerance, and can fail the
run. A check that only prints is decoration.

**S4. Parameterised seasonal metrics in the catalogue and the engine.** Done when
J1 runs from a query object, an unknown month or an empty window is refused with
a sentence, the read-back says "the best September in the last 10 years", and
`month_years_counted` comes back on every row that carries a seasonal figure.

**S5. Scanner pane.** Done when J1 and J3 can be built with pickers, the
read-back sits at the top of the results pane in plain English, and adding a
first condition takes one click.

**S6. Instrument page seasonality.** Done when J2 is answerable: month by year
grid, month on month, year on year, every figure beside its sample size.

**S7. Studies.** Done when the seasonality studies run over stocks instead of
indexes, and each one still reads as a question.

---

## 7. What this plan refuses

- To window the supplied aggregate. It has no years left in it to window.
- To fill a missing month with a zero, an average, or the month before it.
- To compare a part month against full months.
- To show a seasonal average without the count of years behind it.
- To read the month after the as-of month. A row a user reads today describes
  today and what has already closed.
- To describe any of this as a pattern that will repeat. A monthly distribution
  is a summary of what happened. The screen says that and stops.
