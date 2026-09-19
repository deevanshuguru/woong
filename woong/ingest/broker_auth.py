from __future__ import annotations
import argparse
import json
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
import requests
from woong.config import Settings, load_settings, require_broker
from woong.ingest.broker_http import BrokerError, BrokerSession, _checksum

TOKEN_MAX_AGE_HOURS = 20
RESET_UTC_HOUR = 0
RESET_UTC_MIN = 30


def token_path(settings: Settings) -> Path:
    return settings.data_dir / '.broker_token'


def connect_login_url(settings: Settings) -> str:
    if not settings.broker_login_base:
        raise RuntimeError('WOONG_BROKER_LOGIN_BASE is required')
    return (
        f"{settings.broker_login_base}/connect/login"
        f"?api_key={settings.broker_api_key}&v={settings.broker_http_version}"
    )


def token_is_fresh(token_data: dict[str, Any], now: datetime | None = None) -> bool:
    ts = token_data.get('login_time')
    if not ts:
        return False
    login_dt = datetime.fromisoformat(str(ts))
    if login_dt.tzinfo is None:
        login_dt = login_dt.replace(tzinfo=timezone.utc)
    now_utc = now if now is not None else datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    today_reset = now_utc.replace(hour=RESET_UTC_HOUR, minute=RESET_UTC_MIN, second=0, microsecond=0)
    last_reset = today_reset if now_utc >= today_reset else today_reset - timedelta(days=1)
    if login_dt < last_reset:
        return False
    return (now_utc - login_dt).total_seconds() / 3600 < TOKEN_MAX_AGE_HOURS


def save_token(path: Path, access_token: str, user_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            'access_token': access_token,
            'user_id': user_id,
            'login_time': datetime.now(timezone.utc).isoformat(),
        }),
        encoding='utf-8',
    )
    path.chmod(0o600)


def load_fresh_token(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not token_is_fresh(data):
        return None
    token = data.get('access_token')
    return str(token) if token else None


def clear_token(path: Path) -> bool:
    if path.exists():
        path.unlink()
        return True
    return False


def login_browser_assist(settings: Settings) -> tuple[str, str]:
    url = connect_login_url(settings)
    print('')
    print('Woong: broker login required (once per day)')
    print('Opening your browser now...')
    webbrowser.open(url)
    print('')
    print('Steps:')
    print('  1. Log in with your Zerodha credentials')
    print('  2. Click Allow on the permissions page')
    print('  3. Browser tries to open http://127.0.0.1?request_token=...')
    print('     The page will not load -- that is expected.')
    print('  4. Copy the full URL from the address bar and paste it below.')
    print('')
    redirected = input('Paste URL: ').strip()
    query = parse_qs(urlparse(redirected).query)
    request_token = (query.get('request_token') or [None])[0]
    if not request_token:
        raise BrokerError('connect/login', 0, 'no request_token in pasted URL')
    checksum = _checksum(settings.broker_api_key, request_token, settings.broker_api_secret)
    session = requests.post(
        f"{settings.broker_api_base}/session/token",
        data={
            'api_key': settings.broker_api_key,
            'request_token': request_token,
            'checksum': checksum,
        },
        timeout=60,
    )
    if session.status_code >= 400:
        raise BrokerError('session/token', session.status_code, session.text[:500])
    body = session.json()
    data = body.get('data') or {}
    access = data.get('access_token')
    user_id = data.get('user_id') or settings.broker_user_id
    if not access:
        raise BrokerError('session/token', session.status_code, 'no access_token in response')
    return str(access), str(user_id)


def resolve_access_token(settings: Settings) -> str:
    if settings.broker_access_token:
        return settings.broker_access_token
    path = token_path(settings)
    cached = load_fresh_token(path)
    if cached:
        return cached
    access, user_id = login_browser_assist(settings)
    save_token(path, access, user_id)
    return access


def ensure_session(settings: Settings) -> BrokerSession:
    require_broker(settings)
    return BrokerSession(settings, resolve_access_token(settings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Broker session for Woong harvest.')
    parser.add_argument('--clear', action='store_true', help='Delete saved token.')
    parser.add_argument('--check', action='store_true', help='Login and verify profile.')
    args = parser.parse_args(argv)
    settings = load_settings()
    path = token_path(settings)
    if args.clear:
        print('token cleared' if clear_token(path) else 'no token file')
        return 0
    require_broker(settings)
    session = ensure_session(settings)
    if args.check:
        profile = session.get_json('user/profile')
        data = profile.get('data') or {}
        user_id = data.get('user_id') or '(unknown)'
        print(f'ok user_id={user_id}')
        return 0
    print('ok token ready')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (BrokerError, RuntimeError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        raise SystemExit(1) from exc
