"""Validate a scanner query before it touches data.

Cheapest refusal first. Parametric metrics (return, sma) bypass the
catalogue lookup and require a valid window instead. Non-parametric
metrics must exist in the catalogue and be available.
"""
from __future__ import annotations

from typing import Any

from woong.engine.types import QueryError
from woong.metrics.windows import PARAMETRIC_METRICS, UNIT_SESSIONS, parse_window

LEGAL_CMP = {"<", "<=", ">", ">=", "=", "!=", "between", "is", "is_not"}
RESERVED = ("weight", "backtest", "deploy")
LEGAL_UNITS = {"percent", "ratio"}


def catalogue_by_id(catalogue: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["id"]): row for row in catalogue}


def _validate_window(raw: Any, field: str) -> None:
    """Raise QueryError if the window object is malformed."""
    if not isinstance(raw, dict):
        raise QueryError(f"{field} must be an object with n and unit.")
    n = raw.get("n")
    unit = str(raw.get("unit", "")).upper()
    if not isinstance(n, int) or n <= 0:
        raise QueryError(f"{field}.n must be a positive integer, got {n!r}.")
    if unit not in UNIT_SESSIONS:
        raise QueryError(f"{field}.unit must be D, W, M, or Y — got {unit!r}.")
    max_sessions = 30 * 252  # 30 years cap
    if n * UNIT_SESSIONS[unit] > max_sessions:
        raise QueryError(f"{field} exceeds the 30-year maximum window.")


def _require_metric(
    metric: str,
    by_id: dict[str, dict[str, Any]],
    role: str,
    window: Any,
) -> dict[str, Any] | None:
    """Return catalogue row for non-parametric metrics.

    Parametric metrics (return, sma) do not have catalogue rows. They return
    None when valid. A window is required for parametric metrics.
    """
    if metric in PARAMETRIC_METRICS:
        if window is None:
            raise QueryError(
                f"{role} metric {metric!r} requires a window — add window: {{n, unit}}."
            )
        _validate_window(window, "window")
        return None
    if window is not None:
        raise QueryError(
            f"window is only valid for parametric metrics ({sorted(PARAMETRIC_METRICS)}). "
            f"Metric {metric!r} does not accept a window."
        )
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
    if metric in PARAMETRIC_METRICS:
        # Parametric return is always ratio — percent is valid.
        if unit != "percent":
            raise QueryError(f"Only percent is accepted as a unit for {metric!r}.")
        return
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
    # Validate windows for parametric metrics
    window = node.get("window")
    other_window = node.get("other_window")
    if cmp == "between":
        if node.get("other_metric"):
            raise QueryError("between cannot be used with another metric. Use a number range.")
        value = node.get("value")
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise QueryError("between needs a two-element value.")
    if other_window is not None:
        other_name = str(other or "")
        if other_name not in PARAMETRIC_METRICS:
            raise QueryError(
                f"other_window is only valid for parametric metrics. "
                f"Metric {other_name!r} does not accept a window."
            )
        _validate_window(other_window, "other_window")


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

        def check_metrics(node: dict[str, Any]) -> None:
            if "op" in node:
                for child in node.get("args") or []:
                    check_metrics(child)
                return
            if node.get("enabled") is False:
                return
            metric = str(node.get("metric") or "")
            window = node.get("window")
            _require_metric(metric, by_id, "Filter", window)
            other = node.get("other_metric")
            if other:
                other_window = node.get("other_window")
                _require_metric(str(other), by_id, "Filter (other metric)", other_window)

        check_metrics(filt)

    rank = query.get("rank") or {}
    rank_metrics: list[str] = []
    for item in rank.get("by") or []:
        metric = item.get("metric")
        if not metric:
            raise QueryError("A rank clause is missing a metric.")
        used.append(str(metric))
        rank_metrics.append(str(metric))
        if item.get("dir") not in {None, "asc", "desc"}:
            raise QueryError(f"Rank direction {item.get('dir')!r} must be asc or desc.")
        window = item.get("window")
        row = _require_metric(str(metric), by_id, "Ranking", window)
        if row is not None and not row.get("comparable"):
            raise QueryError(
                f"{row['label']} is not comparable across companies. "
                "Ranking it would be ranking by size under another name."
            )
        if metric in PARAMETRIC_METRICS:
            # Parametric return is always ratio and always comparable.
            pass
