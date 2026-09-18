"""Plain HTTP for the broker pipe.

Refuses to log a host, a token, a password or a one-time code. Refuses to
hard-code a base URL: hosts come from Settings. Vendor client libraries are
refused; this module uses plain requests so a bad dependency cannot hide a
credential.

Session creation lives in broker_auth. This module only carries the authenticated
client and the time-based one-time password helper used by that login.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
import time
from base64 import b32decode
from typing import Any

import requests

from woong.config import Settings


class BrokerError(Exception):
    def __init__(self, path: str, status: int, body: str) -> None:
        self.path = path
        self.status = status
        self.body = body
        super().__init__(f"{path} failed with status {status}")


def totp_code(secret: str, when: int | None = None) -> str:
    """Six-digit time-based one-time password from a base32 secret."""
    key = b32decode(secret.strip().replace(" ", "").upper())
    counter = int((when if when is not None else time.time()) // 30)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 1_000_000:06d}"


def _checksum(api_key: str, request_token: str, api_secret: str) -> str:
    raw = f"{api_key}{request_token}{api_secret}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class BrokerSession:
    """Authenticated client for the broker market-data host."""

    def __init__(self, settings: Settings, access_token: str) -> None:
        self.settings = settings
        self.access_token = access_token
        self._session = requests.Session()
        headers = {
            "Authorization": f"token {settings.broker_api_key}:{access_token}",
            "User-Agent": "woong-broker-harvest/0",
        }
        headers[settings.broker_http_version_header] = settings.broker_http_version
        self._session.headers.update(headers)

    def get_bytes(self, path: str, params: dict[str, str] | None = None) -> bytes:
        url = f"{self.settings.broker_api_base}/{path.lstrip('/')}"
        response = self._session.get(url, params=params, timeout=120)
        if response.status_code >= 400:
            raise BrokerError(path, response.status_code, response.text[:500])
        return response.content

    def get_json(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        data = json.loads(self.get_bytes(path, params).decode("utf-8"))
        if not isinstance(data, dict):
            raise BrokerError(path, 200, "response was not a JSON object")
        return data


def create_session(settings: Settings) -> BrokerSession:
    """Return an authenticated session. Delegates to broker_auth for login."""
    from woong.ingest.broker_auth import ensure_session

    return ensure_session(settings)
