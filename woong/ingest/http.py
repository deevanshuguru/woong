"""Plain HTTP for the primary pipe.

Refuses to log a URL, a host, or a token. Retries a bounded number of times
with a growing delay.
"""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from woong.config import Settings


class FetchError(Exception):
    def __init__(self, path: str, status: int, body: str) -> None:
        self.path = path
        self.status = status
        super().__init__(f"{path} failed with status {status}")


def encode_path(path: str) -> str:
    """Encode each path segment so a space in a ticker cannot break the request.

    Hyphen and full stop stay unencoded. A space becomes %20.
    """
    return "/".join(quote(part, safe="-._") for part in path.lstrip("/").split("/"))


def get_json(
    settings: Settings,
    path: str,
    params: dict[str, str] | None = None,
    retries: int = 3,
) -> tuple[int, dict[str, Any]]:
    url = f"{settings.primary_api_base}/{encode_path(path)}"
    if params:
        url = f"{url}?{urlencode(params)}"
    headers = {"Accept": "application/json", "User-Agent": "woong-harvest/0"}
    if settings.primary_api_token:
        headers["Authorization"] = f"Bearer {settings.primary_api_token}"
    last_status = 0
    last_body = ""
    delay = 1.0
    for attempt in range(retries):
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return resp.status, payload
        except HTTPError as exc:
            last_status = exc.code
            last_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            if exc.code in {400, 401, 403, 404}:
                raise FetchError(path, exc.code, last_body) from exc
        except URLError as exc:
            last_status = 0
            last_body = str(exc)
        if attempt + 1 < retries:
            time.sleep(delay)
            delay *= 2
    raise FetchError(path, last_status, last_body)
