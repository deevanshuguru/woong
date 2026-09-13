# Metric ideas

A parking lot, not a plan. Nothing here is a commitment.

## How an idea becomes a metric

```mermaid
flowchart LR
  idea["Written here: claim and where it came from"]
  cols["Warehouse columns exist to compute it"]
  cat["Catalogue row: definition, formula, comparability"]
  tests["Tests, including a hand-worked example"]
  live["Available in the interface"]

  idea --> cols --> cat --> tests --> live
```

No step is skippable. A metric with no real formula over real columns is created
as switched off, with the reason stored, and the reason is what a user sees.

## Recording an idea

Each entry states:

- **Claim.** What the metric is supposed to capture, in one sentence.
- **Definition.** The exact arithmetic, not a description.
- **Inputs.** Which warehouse columns it needs, and whether we have them.
- **Comparability.** Whether the number can be compared across companies.
  Anything tied to share price or company size cannot be, and must never be
  offered as a ranking.
- **Origin.** Paper, book or observation. A named source, not "commonly used".
- **Status.** `idea`, `blocked on data`, `catalogued off`, or `live`.

## Open ideas

None recorded yet. The first entries wait until the warehouse is filled, so that
"inputs" can be answered with a column name instead of a hope.

## Standing cautions

These are traps worth writing down before the first metric is added.

- **Non-comparable metrics used as rankings.** Ranking by a price level, or by a
  band derived from a price level, is ranking by share price. It looks like a
  strategy and is not one. The catalogue records comparability so the engine can
  refuse it.
- **Window shopping.** Trying many lookback windows and keeping the best one
  produces a metric that describes the past and predicts nothing. If a window is
  chosen, the reason is recorded.
- **Restated fundamentals.** Statement values available today are often as
  currently restated, not as originally reported. Any metric used in a backtest
  needs the original publication date, or the backtest sees the future.
- **Survivorship in universes.** Today's index constituents are the ones that
  survived. This is why membership is snapshotted on every harvest.
- **A metric that is really a sector bet.** A threshold on some ratios selects an
  industry rather than a quality. Worth checking the sector spread of any new
  metric's top decile before it becomes a study block.
