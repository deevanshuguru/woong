"""Read connection details from the environment.

Refuses to accept an inline base URL, token, or password. Those values live in
`.env` only. This module never prints a secret.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    primary_api_base: str
    primary_api_token: str
    data_dir: Path
    # Broker pipe. Empty until Part 1 credentials are filled. The harvest entry
    # point refuses to start when these are missing; other commands do not.
    broker_api_base: str
    broker_login_base: str
    broker_api_key: str
    broker_api_secret: str
    broker_user_id: str
    broker_password: str
    broker_totp_secret: str
    broker_access_token: str
    broker_http_version_header: str
    broker_http_version: str


def load_settings(env_file: Path | None = None) -> Settings:
    load_dotenv(env_file or (REPO_ROOT / ".env"), override=False)
    base = os.environ.get("WOONG_PRIMARY_API_BASE", "").strip().rstrip("/")
    if not base:
        raise RuntimeError(
            "WOONG_PRIMARY_API_BASE is empty. Copy .env.example to .env and fill it."
        )
    data_dir = Path(os.environ.get("WOONG_DATA_DIR", "data"))
    if not data_dir.is_absolute():
        data_dir = REPO_ROOT / data_dir
    return Settings(
        primary_api_base=base,
        primary_api_token=os.environ.get("WOONG_PRIMARY_API_TOKEN", "").strip(),
        data_dir=data_dir,
        broker_api_base=os.environ.get("WOONG_BROKER_API_BASE", "").strip().rstrip("/"),
        broker_login_base=os.environ.get("WOONG_BROKER_LOGIN_BASE", "").strip().rstrip("/"),
        broker_api_key=os.environ.get("WOONG_BROKER_API_KEY", "").strip(),
        broker_api_secret=os.environ.get("WOONG_BROKER_API_SECRET", "").strip(),
        broker_user_id=os.environ.get("WOONG_BROKER_USER_ID", "").strip(),
        broker_password=os.environ.get("WOONG_BROKER_PASSWORD", "").strip(),
        broker_totp_secret=os.environ.get("WOONG_BROKER_TOTP_SECRET", "").strip(),
        broker_access_token=os.environ.get("WOONG_BROKER_ACCESS_TOKEN", "").strip(),
        broker_http_version_header=os.environ.get(
            "WOONG_BROKER_HTTP_VERSION_HEADER", ""
        ).strip(),
        broker_http_version=os.environ.get("WOONG_BROKER_HTTP_VERSION", "").strip(),
    )


def require_broker(settings: Settings) -> None:
    """Refuse a broker harvest when connection details are incomplete."""
    if not settings.broker_api_base:
        raise RuntimeError(
            "WOONG_BROKER_API_BASE is empty. Set the broker market-data host in .env."
        )
    if not settings.broker_api_key or not settings.broker_api_secret:
        raise RuntimeError(
            "WOONG_BROKER_API_KEY and WOONG_BROKER_API_SECRET must both be set."
        )
    if not settings.broker_http_version_header or not settings.broker_http_version:
        raise RuntimeError(
            "WOONG_BROKER_HTTP_VERSION_HEADER and WOONG_BROKER_HTTP_VERSION must "
            "both be set to the values the broker HTTP API requires."
        )
    if settings.broker_access_token:
        return
    missing = [
        name
        for name, value in (
            ("WOONG_BROKER_LOGIN_BASE", settings.broker_login_base),
            ("WOONG_BROKER_USER_ID", settings.broker_user_id),
            ("WOONG_BROKER_PASSWORD", settings.broker_password),
            ("WOONG_BROKER_TOTP_SECRET", settings.broker_totp_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "No WOONG_BROKER_ACCESS_TOKEN, and login fields are incomplete: "
            + ", ".join(missing)
        )
