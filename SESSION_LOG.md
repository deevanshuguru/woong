# Session log

Append after every working session. Newest entry first.
Any agent: read AGENTS.md, then STATUS.md, then this file, then mvp/tasks.json.

## 2026-09-19 — re-home, broker auth, first UX review

State:
- Full codebase pushed to github.com/deevanshuguru/woong, main = af739bf.
- Dashboard runs at 127.0.0.1:8765 with real data (primary pipe harvest of 2026-09-13).
- data/ on local disk only (~960 MB, gitignored): raw per-symbol series,
  prices_daily, price_metrics_daily, insider_trades, seasonality, breadth, flows.

Broker (Kite) pipe:
- Headless login works through password + TOTP + connect redirect.
- Patched broker_auth.py: request_token is read from the Location header so an
  unreachable redirect target cannot break login. Committed.
- Blocker: the API secret in .env does not match the API key. Old key invalid.
- Next: create a fresh app on developers.kite.trade, capture key + secret pair,
  fill .env, run python -m woong.ingest.broker_auth --check, then harvest-all.

Known issues:
- ingest_jobs.parquet reported a footer mismatch — rebuild before next harvest.
- Warehouse data is 6 days stale; refresh cadence not yet set up.
- Growthw credentials exist in .env comments; no code path yet.

UX findings (from the builder's own first-user test):
- Footer "Every number is computed in Python" is developer-speak; replace with
  data date, source, completeness.
- 2,585 of 3,176 symbols had no value and the screen did not explain why.
- Default screen loads a meaningless rule (volatility > 0). Should load a study.
- Results table lacks close, 1M, 3M columns.

Next up (M2): UX fixes 1-3 in woong/web/index.html, one commit each.
