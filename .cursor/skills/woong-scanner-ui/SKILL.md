---
name: woong-scanner-ui
description: Build or change the Woong desktop scanner screen. Use when working on the left operations panel, the right results table, condition rows, ranking controls, study blocks, or interface copy.
---

# Scanner interface

Desktop, light mode. No mobile layout, no dark mode, no charts, no visual polish
pass, no component library. Product first.

Operations on the left. Results on the right.

## The browser computes nothing

It builds a `woong_scanner_query`, posts it, and renders the response. No metric,
threshold, percentile, sort key or aggregate is calculated in JavaScript.

If a number needs computing, it belongs in the engine.

## Left panel, in this order

1. **Studies.** A few named blocks. Clicking one fills the panel and runs it.
2. **Universe.** All equity, an index, a sector, or a custom list.
3. **Conditions.** Rows of metric, operator, value, with an and/or join and a
   remove control. Groups indent. A row can be disabled without being deleted.
4. **Ranking.** Metric, direction, optional weights, top N.

A user never lands on a blank metric list. They land on a study and edit it.

## Right panel, always

- Count that passed, and separately the count that had no value.
- The columns the rule used, so the result can be checked by eye.
- The rule in one plain-English sentence, from the engine.
- The as-of date.
- The line: "This is a filter and rank result. Not a buy or sell
  recommendation."

## Copy rules

- No advice words. No buy, sell, hold, target, entry, exit, top pick,
  recommended.
- Study blocks name a human author. Never Woong.
- Full form alongside every abbreviation, every time.
- A switched-off metric shows its stored reason where its value would be.

## Calm over dense

Adding a control needs a reason. The problem being solved is bombardment. If a
panel starts to look like a settings page, remove something.
