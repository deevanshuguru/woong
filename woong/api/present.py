"""Prepare a stored query for the fields on the screen.

A condition on a ratio metric is stored as a ratio. The screen offers percent,
because nobody types 0.20 for twenty percent. That conversion is arithmetic on a
threshold, so it happens here and not in the browser.

Refuses to change the shape of a query. The result is the same tree with values
restated in the unit its field will show, and the unit named on the condition so
the engine can convert it back.
"""

from __future__ import annotations

from typing import Any

from woong.metrics.display import to_percent


def _condition(node: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out = dict(node)
    metric = str(out.get("metric") or "")
    row = by_id.get(metric)
    if row is None or "value" not in out:
        return out
    if str(row.get("unit")) == "ratio":
        out["value"] = to_percent(out["value"])
        out["unit"] = "percent"
    return out


def to_display_query(
    query: dict[str, Any],
    catalogue: list[dict[str, Any]],
) -> dict[str, Any]:
    by_id = {str(row["id"]): row for row in catalogue}

    def walk(node: dict[str, Any]) -> dict[str, Any]:
        if "op" in node:
            return {
                **node,
                "args": [walk(child) for child in node.get("args") or []],
            }
        return _condition(node, by_id)

    out = dict(query)
    if out.get("filter"):
        out["filter"] = walk(out["filter"])
    return out
