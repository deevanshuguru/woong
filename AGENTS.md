# Working agreement for Woong

Read this first, then [`STATUS.md`](STATUS.md) for locked decisions and
[`mvp/tasks.json`](mvp/tasks.json) for the one item currently open.

Woong is a private repository. There is one developer. Never attribute work to
an assistant, a tool or a collaborator in code, comments, documentation or
commit bodies.

---

## 1. What Woong is

An analysis desk for swing traders and short-term investors. The user writes a
rule. Woong returns the stocks that match it, ranked, computed from real data.

The product is the rule result. Not advice, not a portfolio, not a forecast.

---

## 2. The five rules that cannot be broken

### 2.1 No buy or sell recommendation

No buy, sell, hold, target price, entry, exit or "top pick" language anywhere:
code, comments, documentation, interface copy, study names, commit messages.

A ranked list is "what this rule returns today". Every study block carries a
named human author. Woong itself never recommends.

Why this is absolute: a tool where the user authors the rule is a statistical
summary of financial data. A list we put our own name behind is a different,
regulated thing.

### 2.2 No estimated, approximated or proxy number

If a metric cannot be computed from a real source to its real definition, it is
switched **off** in the metric catalogue with a stored reason, and the reason is
shown instead of the number.

Never substitute something close, not even labelled as close. One unauditable
number makes every number beside it suspect.

A missing value is not a failure and not a pass. It is reported separately.

### 2.3 No upstream provider names

No provider, vendor or competitor name appears in code, comments, documentation,
schema, test fixtures, log output, commit messages or the interface.

Sources are generic tags, and only these:

| Tag | Meaning |
|---|---|
| `primary` | The primary market data application programming interface (API) |
| `broker` | The broker connection, used for the official daily close |
| `exchange` | Published exchange files, used for index membership |
| `fundamentals` | The fundamentals feed |
| `manual` | Hand-entered and hand-verified |

Connection details live in `.env` only. Read them through
`woong/config.py`, never inline.

### 2.4 Python computes, the browser presents

Every metric, filter, rank and aggregate is computed in Python. The browser
posts a query and renders the response. It must never learn a habit the platform
will not have.

### 2.5 Filter and rank stay separate

Filter decides who is in the conversation. Rank decides the order and how many.
Collapsing them hides the mistake most users make, and teaching that difference
is part of the product.

---

## 3. Before building anything

Answer these, in writing, in the issue:

1. What is the one thing this change results in for a user?
2. Is it really the next thing? Why?
3. Can it be split smaller and still leave something testable behind?

Do not start until those are clear. One thing at a time. No parallel builds.
Finish and validate before starting the next.

---

## 4. Code standards

- Every module opens with a docstring stating what it does and what it refuses
  to do.
- Comment the constraint, not the narration. Explain why a rule exists where the
  code cannot show it. Never write comments that describe the obvious.
- Fetching and computing never live in the same module. A bad metric must be
  recomputable without re-fetching, and a bad fetch must never look like a bad
  metric.
- The raw store is raw. Vendor field names stay as received inside `data/raw/`.
  Renaming happens on the way into the canonical warehouse, in one documented
  place.
- Fail loudly. Never return an empty result on error. A run that half-worked
  must not look like a run that worked.
- Resolve everything cheap before doing anything expensive.
- Validate before writing, not after.
- Every check must be able to fail the run. A check that only prints is
  decoration.
- Pure logic lives where it can be tested without a network.
- Never author reference data. Download it or derive it. Do not type it.

---

## 5. Git and GitHub

Full detail in [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md). The short form:

- Verify identity before any git operation. `deevanshuguru` and
  `deevanshu0@gmail.com`. Never commit as any other account.
- Every change starts from an issue and lands through a pull request. Never
  commit to `main`.
- Branch names: `feat/`, `fix/`, `test/`, `docs/`, `chore/`, `research/`.
- `pytest -q` must pass before a pull request is opened.
- `git add` names files explicitly. Never `git add -A`.
- Never commit `.env`, tokens, `data/` or logs.

---

## 6. Response style when working in this repository

- Short, plain sentences. No marketing words. No em dashes.
- Give the full form alongside every abbreviation, every time it appears, for
  example "Price to Earnings (P/E)".
- Close one item, report the result, then stop.
