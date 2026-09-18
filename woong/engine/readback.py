"""Plain-English read-back of a scanner query.

A rule a user cannot read back is a rule they cannot check.
"""

from __future__ import annotations

from typing import Any

from woong.engine.validate import catalogue_by_id

_CMP = {
    "<": "below",
    "<=": "at most",
    ">": "above",
    ">=": "at least",
    "=": "equal to",
    "!=": "not equal to",
    "between": "between",
    "is": "is",
    "is_not": "is not",
}


def _label(metric: str, by_id: dict[str, dict[str, Any]]) -> str:
    row = by_id.get(metric)
    return str(row["label"]) if row else metric


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if abs(value) >= 1 or value == 0:
            return str(value)
        return f"{value * 100:g} percent"
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return f"{_format_value(value[0])} and {_format_value(value[1])}"
    return str(value)


def _condition(node: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> str:
    if node.get("enabled") is False:
        return ""
    left = _label(str(node["metric"]), by_id)
    cmp = _CMP.get(str(node.get("cmp")), str(node.get("cmp")))
    if node.get("other_metric"):
        right = _label(str(node["other_metric"]), by_id)
        return f"{left} is {cmp} {right}"
    return f"{left} is {cmp} {_format_value(node.get('value'))}"


def _filter_text(node: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> str:
    if "op" in node:
        parts = [text for child in node.get("args") or [] if (text := _filter_text(child, by_id))]
        if not parts:
            return ""
        joiner = " and " if node["op"] == "and" else " or "
        if len(parts) == 1:
            return parts[0]
        return "(" + joiner.join(parts) + ")" if node["op"] == "or" else joiner.join(parts)
    return _condition(node, by_id)


def read_back(
    query: dict[str, Any],
    catalogue: list[dict[str, Any]],
    universe_name: str,
) -> str:
    by_id = catalogue_by_id(catalogue)
    sentence = f"Scanning {universe_name}."
    filt = query.get("filter")
    if filt:
        body = _filter_text(filt, by_id)
        if body:
            sentence += f" Keeping the ones where {body}."
    rank = query.get("rank") or {}
    by = rank.get("by") or []
    if by:
        bits = []
        for item in by:
            label = _label(str(item["metric"]), by_id)
            direction = "smallest first" if item.get("dir") == "asc" else "largest first"
            bits.append(f"{label}, {direction}")
        sentence += " Ranked by " + "; then ".join(bits)
        top_n = rank.get("top_n")
        if top_n:
            sentence += f", top {int(top_n)}"
        sentence += "."
    return sentence
