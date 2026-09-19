# Broker Auth

## How it works
Kite /connect/authorize is a React SPA. API session cookies do not carry over
to the web session. Headless automation is not possible.

## Daily flow (~20 seconds, once per day)
1. python -m woong.ingest.broker_auth --check
2. Browser opens -- log in with Zerodha credentials, click Allow
3. Browser tries http://127.0.0.1?request_token=... (will not load -- expected)
4. Copy full URL from address bar, paste at Paste URL: prompt
5. Token saved to data/.broker_token (0600, never committed)

## Token freshness
- 20h max age, invalidated at 00:30 UTC (06:00 IST) daily reset
- Fresh token: --check exits immediately, no browser

## Redirect chain
GET /connect/login -> 302 /connect/finish -> 302 /connect/authorize -> 302 redirect URL

## Debug
python -m woong.ingest.broker_auth --clear
python -m woong.ingest.broker_auth --check
