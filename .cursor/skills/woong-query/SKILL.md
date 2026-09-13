---
name: woong-query
description: Work on the Woong scanner query object or the engine that runs it. Use when changing query validation, nested filter groups, ranking, top N, plain-English read-back, or the removal attribution breakdown.
---

# Query and engine

The specification is [`docs/QUERY.md`](../../../docs/QUERY.md). One query object
is shared by the interface, the engine, saved studies and later natural language
translation. Do not invent a second format.

## Validate before running

In this order, so the cheapest refusal happens first:

1. Metric exists in the catalogue.
2. Metric is switched on. If off, refuse and give the stored reason.
3. Comparison operator is legal for that metric's kind.
4. Period is resolvable.
5. A ranking metric is comparable across companies. If not, refuse with an
   explanation.

A refusal names the metric and the reason. It never answers with a substitute.

## Filter

- Group nodes carry `op` of `and` or `or` and nest freely.
- A disabled condition is kept and ignored.
- A missing value never passes, whichever way the comparison points, and never
  counts as a failure. Count it as "had no value".
- Attribute every removal to the condition that caused it, in order.

## Rank

- One metric: sort by value, honouring direction, missing values last.
- More than one: convert each to a percentile rank inside the filtered set, then
  combine with weights. Never add raw values of different kinds.
- Normalise weights that do not sum to 1, and report that it happened.
- `top_n` cuts after ranking.

## Read-back

Produce one plain-English sentence for any query. A rule a user cannot read back
is a rule they cannot check. Cover the group structure, not only the leaves.

## Tests

Every change needs a hand-worked example, plus a case for each refusal path and
for the missing-value rule.
