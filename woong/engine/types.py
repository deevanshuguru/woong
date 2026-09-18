"""Engine result and refusal types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class QueryError(Exception):
    """A query that must not run. Never answered with an empty list."""


@dataclass
class QueryResult:
    as_of: str
    read_back: str
    passed: int
    had_no_value: int
    removed: int
    universe_size: int
    rows: list[dict[str, Any]]
    used_metrics: list[str]
    attribution: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)
    disclaimer: str = (
        "This is a filter and rank result. Not a buy or sell recommendation."
    )
