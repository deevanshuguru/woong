"""Broker session: headless login, token file, freshness against daily reset.

Refuses to print a password, a one-time code, an access token or a host.
Refuses to hard-code login or market-data hosts: those come from Settings.
Refuses a vendor client library; login is plain HTTP so credentials cannot
hide inside a dependency.

Token rules match the broker's daily reset: a token written before the most
recent reset is stale even if it is only a few hours old. The file lives under
the data directory and is mode 0600. It is never committed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse, urljoin

import requests

from woong.config import Settings, load_settings, require_broker
from woong.ingest.broker_http import (
    BrokerError,
    BrokerSession,
    _checksum,
    totp_code,
)

TOKEN_MAX_AGE_HOURS = 20
# Broker sessions reset at 06:00 India Standard Time (IST) = 00:30 Coordinated
# Universal Time (UTC). A token issued before that instant is invalid.
RESET_UTC_HOUR = 0
RESET_UTC_MIN = 30


def token_path(settings: Settings) -> Path:
    return settings.data_dir / ".broker_token"


def connect_login_url(settings: Settings) -> str:
    """URL the browser session must hit after two-factor auth for request_token."""
    if not settings.broker_login_base:
        raise RuntimeError("WOONG_BROKER_LOGIN_BASE is required for connect login.")
    return (
        f"{settings.broker_login_base}/connect/login"
        f"?api_key={settings.broker_api_key}&v={settings.broker_http_version}"
    )


def token_is_fresh(token_data: dict[str, Any], now: datetime | None = None) -> bool:
    """True only if issued after the last daily reset and within max age."""
    ts = token_data.get("login_time")
    if not ts:
        return False
    login_dt = datetime.fromisoformat(str(ts))
    if login_dt.tzinfo is None:
        login_dt = login_dt.replace(tzinfo=timezone.utc)
    now_utc = now if now is not None else datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    today_reset = now_utc.replace(
        hour=RESET_UTC_HOUR, minute=RESET_UTC_MIN, second=0, microsecond=0
    )
    last_reset = today_reset if now_utc >= today_reset else today_reset - timedelta(days=1)
    if login_dt < last_reset:
        return False
    age_hours = (now_utc - login_dt).total_seconds() / 3600
    return age_hours < TOKEN_MAX_AGE_HOURS


def save_token(path: Path, access_token: str, user_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "access_token": access_token,
                "user_id": user_id,
                "login_time": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    path.chmod(0o600)


def load_fresh_token(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not token_is_fresh(data):
        return None
    token = data.get("access_token")
    return str(token) if token else None


def clear_token(path: Path) -> bool:
    if path.exists():
        path.unlink()
        return True
    return False


def login_headless(settings: Settings) -> tuple[str, str]:
    """Password + one-time password + connect redirect. Returns (token, user_id)."""
    if not settings.broker_login_base:
        raise RuntimeError("WOONG_BROKER_LOGIN_BASE is required for headless login.")

    browser = requests.Session()
    browser.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Referer": f"{settings.broker_login_base}/",
            settings.broker_http_version_header: settings.broker_http_version,
        }
    )

    login = browser.post(
        f"{settings.broker_login_base}/api/login",
        data={"user_id": settings.broker_user_id, "password": settings.broker_password},
        timeout=60,
    )
    if login.status_code >= 400:
        raise BrokerError("login", login.status_code, login.text[:500])
    login_body = login.json()
    if login_body.get("status") != "success":
        raise BrokerError(
            "login",
            login.status_code,
            str(login_body.get("message") or login_body)[:500],
        )
    request_id = (login_body.get("data") or {}).get("request_id")
    if not request_id:
        raise BrokerError("login", login.status_code, "login response had no request_id")

    twofa = browser.post(
        f"{settings.broker_login_base}/api/twofa",
        data={
            "user_id": settings.broker_user_id,
            "request_id": request_id,
            "twofa_value": totp_code(settings.broker_totp_secret),
            "twofa_type": "totp",
        },
        timeout=60,
        allow_redirects=False,
    )
    if twofa.status_code >= 400:
        raise BrokerError("twofa", twofa.status_code, twofa.text[:500])

    # Connect login must hit the login host, not the market-data host. Hops
    # are followed by hand so the token is read from the Location header
    # without dialing a redirect target that may not resolve.
    url = connect_login_url(settings)
    request_token = None
    last_status = 0
    for _ in range(10):
        answer = browser.get(url, allow_redirects=False, timeout=60)
        last_status = answer.status_code
        location = answer.headers.get("Location")
        if answer.status_code in (301, 302, 303, 307, 308) and location:
            next_url = urljoin(str(answer.url), location)
            query = parse_qs(urlparse(next_url).query)
            if query.get("request_token"):
                request_token = query["request_token"][0]
                break
            url = next_url
            continue
        query = parse_qs(urlparse(str(answer.url)).query)
        if query.get("request_token"):
            request_token = query["request_token"][0]
        break
    if not request_token:
        raise BrokerError(
            "connect/login",
            last_status,
            "request_token missing from redirect",
        )

    checksum = _checksum(
        settings.broker_api_key, str(request_token), settings.broker_api_secret
    )
    session = requests.post(
        f"{settings.broker_api_base}/session/token",
        data={
            "api_key": settings.broker_api_key,
            "request_token": request_token,
            "checksum": checksum,
        },
        timeout=60,
    )
    if session.status_code >= 400:
        raise BrokerError("session/token", session.status_code, session.text[:500])
    body = session.json()
    data = body.get("data") or {}
    access = data.get("access_token")
    user_id = data.get("user_id") or settings.broker_user_id
    if not access:
        raise BrokerError(
            "session/token", session.status_code, "session response had no access_token"
        )
    return str(access), str(user_id)


def resolve_access_token(settings: Settings) -> str:
    """Env token, then fresh file, then headless login. Never logs the token."""
    if settings.broker_access_token:
        return settings.broker_access_token
    path = token_path(settings)
    cached = load_fresh_token(path)
    if cached:
        return cached
    access, user_id = login_headless(settings)
    save_token(path, access, user_id)
    return access


def ensure_session(settings: Settings) -> BrokerSession:
    require_broker(settings)
    return BrokerSession(settings, resolve_access_token(settings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Broker session for Woong harvest.")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete the saved token so the next run logs in again.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Login if needed and GET /user/profile (prints user id only).",
    )
    args = parser.parse_args(argv)
    settings = load_settings()
    path = token_path(settings)

    if args.clear:
        cleared = clear_token(path)
        print("token cleared" if cleared else "no token file")
        return 0

    require_broker(settings)
    session = ensure_session(settings)
    if args.check:
        profile = session.get_json("user/profile")
        data = profile.get("data") or {}
        user_id = data.get("user_id") or "(unknown)"
        print(f"ok user_id={user_id}")
        return 0

    # Default: ensure a fresh token exists, then exit.
    print("ok token ready")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BrokerError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
