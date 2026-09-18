"""Turn a stored number into the string a screen shows.

This is the only place a unit becomes text. It lives in Python because the
browser is not allowed to divide a ratio by anything, not even to print it.

Refuses to round a figure into a different figure: a ratio keeps two decimal
places of a percent, which is the precision the stored value supports.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def display_value(value: Any, unit: str) -> str | None:
    """The string for one value, or None when there is no value to show."""
    if is_missing(value):
        return None
    if unit == "ratio":
        return f"{float(value) * 100:.2f}%"
    if unit == "years":
        return f"{float(value):.0f}"
    if unit == "score":
        return f"{float(value):.4f}"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}"
    return str(value)


def to_percent(value: Any) -> Any:
    """A stored ratio expressed as the percent a user types.

    The screen offers "20" for twenty percent. The multiplication belongs here so
    that no threshold is ever arithmetic in the browser.
    """
    if isinstance(value, (list, tuple)):
        return [to_percent(item) for item in value]
    if isinstance(value, bool) or is_missing(value):
        return value
    if isinstance(value, (int, float)):
        return float(value) * 100.0
    return value
