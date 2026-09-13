# STATUS

One place for locked facts. The current work item is
[`mvp/tasks.json`](mvp/tasks.json). If this file and that board disagree, the
board is right about what we are doing now, and this file is right about LOCKED.

Last updated: 2026-09-13

---

## The one thing

A desktop screen where the left side writes a rule (universe, conditions,
ranking) and the right side shows the stocks that match, ranked, on real
numbers. Plus a small number of named study blocks so a user learns the tool by
using it rather than by reading a metric list.

That is the Minimum Viable Product (MVP). A short-term investor can argue with
the list.

## Where we are

**Doing: W1.** Canonical warehouse schema and the metric catalogue.

W0 is done. Nothing is shippable yet. There is no data in the warehouse, so
there is no stock list.

## The product path

```
universe -> filter -> rank -> weight -> backtest -> broker deploy
```

The first shippable slice is **universe, filter, rank**. Weight, backtest and
broker deploy get reserved schema slots so the model is visible, and get no
interface, no charts and no live orders in this slice.

## LOCKED (append only)

| Date | Decision |
|---|---|
| 2026-09-13 | Woong is an analysis tool. It never gives a buy or sell recommendation. |
| 2026-09-13 | No estimated, approximated or proxy number is ever shown. A metric that cannot be computed to its real definition is switched off and says why. |
| 2026-09-13 | No upstream provider name appears in the repository or the interface. Sources are generic tags: `primary`, `broker`, `exchange`, `fundamentals`, `manual`. |
| 2026-09-13 | Python computes every number. The browser only presents. |
| 2026-09-13 | Filter and rank are separate stages and stay separate. |
| 2026-09-13 | The harvest covers the full symbol master and every index. Nulls are acceptable. A universe is a filter on that master, never a reason to narrow ingest. |
| 2026-09-13 | A study or basket is a rule, not a frozen list of tickers. |
| 2026-09-13 | Every study block carries a named human author. Never Woong. |
| 2026-09-13 | Version one is desktop and light mode only. No mobile pass, no visual polish pass. |
| 2026-09-13 | Natural language to query translation is phase two. The structured interface ships first, and both compile to the same query object. |
| 2026-09-13 | A missing value never passes a filter and never counts as a failure. It is reported separately. |
| 2026-09-13 | Every change starts from an issue and lands through a pull request. Nothing is committed to `main` directly. |

## Pending, not this slice

| Question | Note |
|---|---|
| Fundamentals coverage | Price to Earnings (P/E), sales growth and Debt to Equity stay off until the line items are really in the warehouse with a written definition. |
| Historical index membership | Membership is snapshotted on every harvest. Until that history is deep, any backtest would be survivorship biased. |
| Corporate action adjustment | Must be confirmed for the price series before any long lookback is trusted. |
| Data licensing | To be closed before any outside user sees the numbers. |
