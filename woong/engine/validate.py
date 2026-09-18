"""Validate a scanner query before it touches a snapshot.

Cheapest refusal first. Refuses an unknown metric, a switched-off metric, a
non-comparable rank, and reserved later-stage keys.
"""

from __future__ import annotations

from typing import Any

from woong.engine.types import QueryError

LEGAL_CMP = {"<", "<=", ">", ">=", "=", "!=", "between", "is", "is_not"}
RESERVED = ("weight", "backtest", "deploy")
# A condition may state the unit its typed value is in. The engine converts it,
# so that the screen can offer "20 percent" without JavaScript dividing anything.
LEGAL_UNITS = {"percent", "ratio"}


def catalogue_by_id(catalogue: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["id"]): row for row in catalogue}


def _require_metric(metric: str, by_id: dict[str, dict[str, Any]], role: str) -> dict[str, Any]:
    if metric not in by_id:
        raise QueryError(f"{role} uses unknown metric {metric!r}.")
    row = by_id[metric]
    if not row.get("available"):
        reason = str(row.get("off_reason") or "switched off")
        raise QueryError(f"{row['label']} is switched off. {reason}")
    return row


def _check_unit(node: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> None:
    unit = node.get("unit")
    if unit is None:
        return
    if unit not in LEGAL_UNITS:
        raise QueryError(f"Value unit {unit!r} is not one of {sorted(LEGAL_UNITS)}.")
    metric = str(node.get("metric") or "")
    row = by_id.get(metric)
    if unit == "percent" and row is not None and str(row.get("unit")) != "ratio":
        raise QueryError(
            f"{row['label']} is measured in {row['unit']}, not a ratio. "
            "A percent value cannot be stated against it."
        )


def _walk_metrics(node: dict[str, Any], found: list[str]) -> None:
    if not isinstance(node, dict):
        raise QueryError("A filter node must be an object.")
    if "op" in node:
        if node["op"] not in {"and", "or"}:
            raise QueryError(f"Filter group op must be and or or, not {node['op']!r}.")
        args = node.get("args")
        if not isinstance(args, list) or not args:
            raise QueryError("A filter group must have at least one argument.")
        for child in args:
            _walk_metrics(child, found)
        return
    if node.get("enabled") is False:
        return
    metric = node.get("metric")
    if not metric:
        raise QueryError("A condition is missing a metric.")
    found.append(str(metric))
    other = node.get("other_metric")
    if other:
        found.append(str(other))
    cmp = node.get("cmp")
    if cmp not in LEGAL_CMP:
        raise QueryError(f"Comparison {cmp!r} is not legal.")
    period = node.get("period", "latest")
    if period not in {None, "latest"}:
        raise QueryError(
            f"Period {period!r} is not resolvable yet. Only latest is implemented."
        )
    if cmp == "between":
        value = node.get("value")
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise QueryError("between needs a two-element value.")


def validate_query(
    query: dict[str, Any],
    catalogue: list[dict[str, Any]],
    universe_ids: set[str],
) -> None:
    if not isinstance(query, dict):
        raise QueryError("Query must be an object.")
    for key in RESERVED:
        if key in query:
            raise QueryError(
                f"{key} is reserved and not implemented. "
                "This slice is universe, filter and rank."
            )
    universe = query.get("universe") or {}
    if universe.get("set"):
        if universe["set"] not in universe_ids:
            raise QueryError(f"Universe {universe['set']!r} is not in the warehouse.")
    elif not universe.get("symbols"):
        raise QueryError("Universe needs a set or an explicit symbol list.")
    as_of = query.get("as_of", "latest")
    if as_of != "latest" and not isinstance(as_of, str):
        raise QueryError("as_of must be latest or an ISO date.")
    by_id = catalogue_by_id(catalogue)
    used: list[str] = []
    filt = query.get("filter")
    if filt:
        _walk_metrics(filt, used)

        def check_units(node: dict[str, Any]) -> None:
            if "op" in node:
                for child in node.get("args") or []:
                    check_units(child)
                return
            _check_unit(node, by_id)

        check_units(filt)
    rank = query.get("rank") or {}
    for item in rank.get("by") or []:
        metric = item.get("metric")
        if not metric:
            raise QueryError("A rank clause is missing a metric.")
        used.append(str(metric))
        if item.get("dir") not in {None, "asc", "desc"}:
            raise QueryError(f"Rank direction {item.get('dir')!r} must be asc or desc.")
    for metric in used:
        role = "Ranking" if any(
            item.get("metric") == metric for item in (rank.get("by") or [])
        ) else "Filter"
        row = _require_metric(metric, by_id, role)
        if role == "Ranking" and not row.get("comparable"):
            raise QueryError(
                f"{row['label']} is not comparable across companies. "
                "Ranking it would be ranking by size under another name."
            )
