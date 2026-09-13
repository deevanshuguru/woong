---
name: woong-metrics
description: Add or change a Woong metric or the metric catalogue. Use when defining a metric formula, deciding whether a metric can be switched on, recording comparability and direction, or promoting a research idea into a usable metric.
---

# Metrics

The catalogue is the only place that decides whether a filter or a ranking on a
metric is legal.

## Every catalogue row states

| Field | Meaning |
|---|---|
| `id` | Stable identifier used in queries |
| `label` | What the user reads. Never an internal name |
| `definition` | The exact arithmetic, in words |
| `formula` | How it is computed from warehouse columns |
| `source_table` | Where the inputs come from |
| `unit` | For display |
| `dim` | Comparability class. Two numbers compare only when this matches |
| `comparable` | False when the value is tied to share price or company size |
| `direction` | Which way is better. Drives ranking, never legality |
| `available` | False switches it off |
| `off_reason` | Required when `available` is false, refused when true |

## Switching a metric on

All four must hold:

1. The inputs are really in the warehouse, as columns, with a source tag.
2. The formula matches the metric's real definition. Not an approximation.
3. There is a test with a hand-worked example.
4. Comparability is recorded honestly.

If any fails, the row is created with `available` false and a reason. A user sees
the reason. A metric never quietly disappears, because a missing metric and a
broken metric look identical from outside.

## Comparability

Mark `comparable` false when the number scales with share price or company size,
for example a price level, a band level, or an absolute rupee amount.

Such metrics may still be filtered. They may never be ranked, because ranking
them is ranking by size under another name. The engine enforces this.

## Promotion from an idea

Route: [`docs/metric-ideas.md`](../../../docs/metric-ideas.md), then warehouse
columns, then a catalogue row, then tests, then optionally a study block. No
step is skippable, and a new metric never appears as a surprise column.

## Forbidden

- A formula that fills a gap with something close.
- A metric whose definition is "commonly used" with no stated source.
- Presenting an externally supplied score as Woong's own calculation. Store it
  with its source tag and label it as supplied.
