# Woong

**Rules in, stocks out.**

Woong is a desktop analysis desk for swing traders and short-term investors. You
write a rule. Woong returns the stocks that match it, ranked, on real numbers.

Woong does **not** give buy or sell recommendations. It is an analysis tool. The
user authors the rule, and the result is that rule's output for a given date.

---

## Why this exists

A short-term investor already knows the common tools: Price to Earnings (P/E),
the 200-Day Moving Average (200 DMA), 52-week highs. Those are fine, and Woong
supports them.

The actual problem is different. It is not a shortage of filters. It is not
knowing **which question to ask next**, and being handed eighty knobs instead of
an answer.

So Woong is two things:

1. **An engine.** Pick a universe, filter it, rank what survives.
2. **A few study blocks.** A named person's rule, already written and already
   run, with the resulting list on screen. Open one, read the idea, then change
   it on the left. You are never dropped onto a blank page of metrics.

---

## What it is not

- Not a recommendation service. No buy, sell, hold, or target price.
- Not a model portfolio.
- Not an estimate. If a number cannot be computed from a real source to its real
  definition, the metric is switched **off** and says why. Never a close-enough
  substitute.

---

## Status

Early build. See [`STATUS.md`](STATUS.md) for locked decisions and
[`mvp/tasks.json`](mvp/tasks.json) for the current work item.

## Documentation

| Document | What it covers |
|---|---|
| [`docs/PRODUCT.md`](docs/PRODUCT.md) | The user, the problem, the first screen |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layers, data flow, where computation lives |
| [`docs/QUERY.md`](docs/QUERY.md) | The `woong_scanner_query` object |
| [`docs/DATA.md`](docs/DATA.md) | Canonical tables and how data is refreshed |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | Branches, commits, pull requests, review |

## Developer setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in the values
pytest -q
```

Private repository. All rights reserved.
