# The `woong_scanner_query` object

One object is shared by the interface, the engine, saved studies and, later,
natural language translation. There is no second query format.

It carries no provider field names and no interface state.

## Shape

```json
{
  "universe": { "set": "nse_equity" },
  "as_of": "latest",
  "filter": {
    "op": "and",
    "args": [
      {
        "op": "or",
        "args": [
          { "metric": "pe", "period": "latest", "cmp": "<", "value": 18 },
          { "metric": "sales_growth_yoy", "period": "fy2026", "cmp": ">", "value": 20 }
        ]
      },
      { "metric": "debt_equity", "period": "fy2026", "cmp": "<", "value": 1 },
      { "metric": "fall_from_52w_high_pct", "period": "latest", "cmp": ">", "value": 15 }
    ]
  },
  "rank": {
    "by": [{ "metric": "fall_from_52w_high_pct", "dir": "desc", "weight": 1 }],
    "top_n": 30
  }
}
```

That example reads, in plain English:

> Scanning all listed equity. Keeping the ones where Price to Earnings (P/E) is
> below 18 times, or sales growth year on year for financial year 2026 is above
> 20 percent, and Debt to Equity for financial year 2026 is below 1 time, and
> the fall from the 52-week high is above 15 percent. Ranked by that fall,
> largest first, top 30.

## Nodes

### `universe`

| Field | Values |
|---|---|
| `set` | A universe identifier from the `universes` table, for example `nse_equity` or an index identifier |
| `symbols` | Optional explicit list, used for a custom chip list |

A universe is a filter over the full symbol master. It is never a reason to
narrow what gets harvested.

### `as_of`

`"latest"` or an ISO date. The engine resolves it to one snapshot date and
reports which date it used. A screen that does not state its own date is not
auditable.

### `filter`

Two node kinds, nested freely.

**Group**

```json
{ "op": "and", "args": [ ... ] }
```

`op` is `and` or `or`. `args` holds at least one child. Groups may nest, which
is what makes "A or B, and C" expressible.

**Condition**

```json
{ "metric": "pe", "period": "latest", "cmp": "<", "value": 18, "enabled": true }
```

| Field | Meaning |
|---|---|
| `metric` | Identifier from the metric catalogue |
| `period` | `latest`, a financial year such as `fy2026`, or a quarter end |
| `cmp` | `<` `<=` `>` `>=` `=` `!=` `between` `is` `is_not` |
| `value` | Number, or a two-element list when `cmp` is `between`, or a category string |
| `enabled` | Optional, defaults true. A disabled condition is kept and ignored, so a user can toggle an idea without losing it |

A condition may also compare two metrics instead of a metric and a constant:

```json
{ "metric": "close", "cmp": ">", "other_metric": "sma_200" }
```

### `rank`

```json
{ "by": [{ "metric": "momentum_1m", "dir": "desc", "weight": 0.6 }], "top_n": 30 }
```

| Field | Meaning |
|---|---|
| `by` | One or more metrics, each with `dir` of `asc` or `desc` and an optional `weight` |
| `top_n` | Optional cut. Omitted means return everything that passed |

With more than one metric, each is converted to a percentile rank inside the
filtered set, then combined with the weights. Weights that do not sum to 1 are
normalised, and the normalisation is reported. Raw values are never added
together, because adding a rupee price to a percentage is meaningless.

## Rules the engine enforces

1. **A switched-off metric refuses the query.** The refusal names the metric and
   gives the stored reason. It is never answered with a substitute.
2. **A missing value never passes a filter and never counts as a failure.** Such
   rows are reported as "had no value", separately from rows that were measured
   and did not qualify.
3. **Every removal is attributed.** The response says which condition removed
   how many rows, in order, so a surprising result can be traced.
4. **Ranking on a value that is not comparable across companies is refused.**
   Ranking by share price, or by a band level derived from share price, is
   ranking by size. The catalogue marks such metrics as not comparable and the
   engine blocks them with an explanation.
5. **The query reads back in plain English.** A rule a user cannot read back is
   a rule they cannot check.

## Reserved for later

These keys are part of the design and are rejected until implemented, so that
nothing has to be renamed afterwards.

```json
{
  "weight":   { "method": "equal" },
  "backtest": { "from": "2018-01-01", "rebalance": "monthly" },
  "deploy":   { "paper": true }
}
```
