# Woong — agent handoff context

Read this file top to bottom before touching anything. Then read the repo
files listed in ORDER OF READING. If this file and the repo disagree, the
repo wins and you should tell the human immediately.

---

## 1. What Woong is

Woong (becoming "Market Lens India") is a local investment-research desk for
Indian equities. Two products, one loop:

1. **Scanner** — the user writes a rule (universe + conditions + ranking);
   Woong returns the stocks that match, ranked, on real numbers.
2. **Baskets** — published rule outputs presented like a free smallcase:
   composition, dual-window returns vs Nifty 50, rebalance history, exact
   transaction costs, and a quantified rule tree.

Woong is an analysis tool. It NEVER gives buy/sell/hold recommendations. The
human authors the rule; the screen shows the rule's output for a date.

## 2. The law (violating any of these = the change is wrong)

Full lists live in `STATUS.md` (locked decisions) and `docs/UI_RULES.md`
(all UI decisions, append-only). The non-negotiables:

- Python computes every number; the browser only presents.
- No advice words (buy/sell/target/recommend) anywhere in the UI.
- No tech verbiage in the UI (API, engine, pipe, warehouse, snapshot).
- No raw metric IDs in the UI ("One-year return", never "return_1y").
- No estimated numbers. A metric that cannot be computed to its real
  definition is switched off and says why. Missing values render as "—".
- No upstream provider names anywhere in the repo or UI. Sources are generic
  tags: primary, broker, exchange, fundamentals, manual. (The broker is
  Zerodha Kite in practice; never write that name in code or docs.)
- Dummy/sample data pages carry a yellow pill: "Dummy data · design preview".
- Minimum investment assumes whole shares only — no fractional buying.
- Desktop only, min 1100px. Light + dark themes (tokens in
  `html[data-theme="dark"]`), font Poppins, tabular numerals.
- Border radius tokens only: cards 12px, controls 8px, pills 999px.

## 3. Order of reading (always, every session)

1. `AGENTS.md` — working agreement
2. `STATUS.md` — locked decisions and current work item
3. `docs/UI_RULES.md` — accumulated UI law (append-only)
4. `SESSION_LOG.md` — what happened in previous sessions
5. `mvp/tasks.json` — the task board
6. Then the files relevant to the current task only.

## 4. How to work with the human (the operating rhythm)

- **One thing at a time.** One task, one concern, one commit. Never build
  many files at once. Never go vague.
- **Think before code.** For any non-trivial change: present the plan /
  structural summary FIRST, get approval, then write.
- **Small complete steps.** The current task is always written as the
  smallest step that produces something the human can look at and judge.
  After each step, update the "NEXT STEP" section of this file (section 9).
- **Human visual sign-off before every commit.** No exceptions.
- **Tests before commits:** `python3 -m pytest -q` must pass (offline tests).
- **After writing any page:** audit for unescaped quotes inside string
  literals and backslashes (a file-transfer gremlin mangles `\'` sequences
  and produces half-rendered pages with console SyntaxErrors). Then the
  human hard-refreshes and judges as user #1.
- **Log everything:** append to `SESSION_LOG.md` at the end of every working
  session (what was done, what broke, what is next). Update `docs/UI_RULES.md`
  the same day a UI decision is made.
- **Git:** one concern per branch off `main`, conventional-commit messages
  that say WHY, push both the feature branch and main
  (`git push origin feat/x && git push origin feat/x:main`). Never commit
  without sign-off. Never commit `.env`, `data/`, or debug scripts.

## 5. Local setup (macOS, repo at ~/Development/woong)

    cd ~/Development/woong
    source .venv/bin/activate        # ALWAYS check (.venv) is in the prompt
    python3 -m pytest -q             # offline tests
    python3 -m woong.api             # serves 127.0.0.1:8765

Pages:
- `/`            scanner (rule in, ranked list out)
- `/baskets`     basket explorer (20 dummy baskets, sidebar filters, quick view)
- `/basket/{id}` basket detail (holdings with price/qty/value, rule tree,
                 growth chart, rebalance history, Groww cost table)

Data for baskets: `woong/web/basket-data.js` (window.BASKETS, dummy).
Warehouse: `data/warehouse/*.parquet` (real price data from the primary
pipe, harvest of 2026-09-13, 6+ days stale, ~84% of universe missing
history). `data/` is gitignored; never committed.

## 6. Where things stand (as of 2026-09-19)

Done and pushed to github.com/deevanshuguru/woong (main):
- Scanner MVP end to end on stale real data (W0-W4 of mvp/tasks.json).
- Basket explorer + detail + quick-view slide-over with 20 dummy baskets
  using platform-grade variety (asset allocation, smart beta, sector and
  group trackers, themes) and rule trees (nested ALL/ANY/NONE, IF/THEN,
  seasonality, streaks, period, guard conditions, typed badges).

Known-broken / blocked:
- Broker (Kite) pipe: login flow works through password+TOTP+redirect
  (patched broker_auth.py to read request_token from the Location header),
  but the API secret in .env does not match the API key. A fresh Kite
  Connect app (paid, ~₹4k/mo with historical data) is pending the human's
  decision. Do NOT spend time here until the human reopens it.
- Primary pipe data is stale; refresh is free (resumable harvest) but
  deferred until the scanner UI work is judged.
- ingest_jobs.parquet had a footer mismatch — rebuild before next harvest.
- basket detail page: chart tooltip, cost table etc. exist but the page has
  not had the same polish pass as the explorer (known debt).

## 7. The current task (in flight): condition-window UI upgrade

The condition builder on the scanner (left panel, step 2) needs a redesign.
Decided so far: operators as words ("is above"), unit named ("percent"),
compare-to-another-metric toggle exists, nested groups exist. The upgrade
should make building conditions feel like composing a sentence, keep all
element ids and JS behavior, and land as small commits (structure first,
paint second). Nothing else about the task is decided yet — that is the
first thing to plan with the human.

## 8. Principles for deciding "what is really the next step"

- Users before features: the product must be judged by a real person before
  more capability is added. Current judge: the human himself (he failed his
  own first-user test once already, and that feedback drove the roadmap).
- Data trust beats UI polish, but the human has explicitly chosen to do
  free development first and spend on data later. Respect that order.
- Anything that cannot be demonstrated on the screen in 5 minutes of the
  human's time is too big; split it.
- If a choice would need to be redone when real data arrives, do not make
  it now.

## 9. NEXT STEP (keep this section tiny, complete, and always current)

1. python -m woong.ingest.broker_harvest --help -- confirm flags
2. Run full OHLCV backfill into prices_daily (W2)
3. Verify row count in prices_daily via DuckDB
4. Then: condition-window UI upgrade (plan approved)
---

*Written by the previous agent session. Human: Deevanshu. Repo:
https://github.com/deevanshuguru/woong (public, safe to read; contains no
secrets — .env and data/ are local-only).*
