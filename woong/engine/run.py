"""Run a validated scanner query against a snapshot plus live price data.

Non-parametric metrics are read from the snapshot.
Parametric metrics (return, sma with a window) are computed on the fly
from prices_daily and merged into the work frame before filtering.

A missing value is unknown: it never passes and never counts as a failure.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from woong.engine.readback import read_back
from woong.engine.types import QueryError, QueryResult
from woong.engine.validate import catalogue_by_id, validate_query
from woong.metrics.display import display_value
from woong.metrics.windows import (
    PARAMETRIC_METRICS,
    WindowSpec,
    column_key,
    compute_dynamic_columns,
    parse_window,
)

TRUE = 1
FALSE = 0
UNKNOWN = -1

CMP_FNS = {
    "<": lambda left, right: left < right,
    "<=": lambda left, right: left <= right,
    ">": lambda left, right: left > right,
    ">=": lambda left, right: left >= right,
    "=": lambda left, right: left == right,
    "!=": lambda left, right: left != right,
    "is": lambda left, right: left == right,
    "is_not": lambda left, right: left != right,
}


def _is_na(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _cell(row: pd.Series, metric: str, window: Any | None) -> Any:
    """Resolve a metric value from the work row.

    For parametric metrics (return, sma), the temp column name includes the
    window label. For snapshot metrics, the column name is the metric id.
    """
    if metric in PARAMETRIC_METRICS and window is not None:
        col = column_key(metric, parse_window(window))
    else:
        col = metric
    if col not in row.index:
        return None
    return row[col]


def _compare(left: Any, cmp: str, right: Any) -> int:
    if _is_na(left) or _is_na(right):
        return UNKNOWN
    if cmp == "between":
        low, high = right
        if _is_na(low) or _is_na(high):
            return UNKNOWN
        return TRUE if low <= left <= high else FALSE
    fn = CMP_FNS[cmp]
    return TRUE if fn(left, right) else FALSE


def _to_ratio(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [_to_ratio(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return float(value) / 100.0
    return value


def normalise_units(node: dict[str, Any]) -> None:
    if "op" in node:
        for child in node.get("args") or []:
            normalise_units(child)
        return
    if node.pop("unit", None) == "percent" and "value" in node:
        node["value"] = _to_ratio(node["value"])


def _annotate(node: dict[str, Any], prefix: str, counter: list[int]) -> None:
    if "op" in node:
        node["_id"] = prefix or node["op"]
        node["_label"] = f"group {node['op']}"
        for i, child in enumerate(node.get("args") or []):
            _annotate(child, f"{node['_id']}.{i}", counter)
        return
    counter[0] += 1
    node["_id"] = f"c{counter[0]}"
    metric = node.get("metric", "")
    cmp = node.get("cmp", "")
    window = node.get("window")
    window_label = f" {window['n']}{window['unit']}" if window else ""
    if node.get("other_metric"):
        other_window = node.get("other_window")
        other_label = f" {other_window['n']}{other_window['unit']}" if other_window else ""
        node["_label"] = f"{metric}{window_label} {cmp} {node['other_metric']}{other_label}"
    else:
        node["_label"] = f"{metric}{window_label} {cmp} {node.get('value')}"


def _eval(node: dict[str, Any], row: pd.Series) -> tuple[int, str | None]:
    if node.get("enabled") is False:
        return TRUE, None
    if "op" in node:
        unknown_id: str | None = None
        if node["op"] == "and":
            for child in node["args"]:
                value, attr = _eval(child, row)
                if value == FALSE:
                    return FALSE, attr
                if value == UNKNOWN and unknown_id is None:
                    unknown_id = attr
            if unknown_id:
                return UNKNOWN, unknown_id
            return TRUE, None
        for child in node["args"]:
            value, attr = _eval(child, row)
            if value == TRUE:
                return TRUE, None
            if value == UNKNOWN and unknown_id is None:
                unknown_id = attr
        if unknown_id:
            return UNKNOWN, unknown_id
        return FALSE, str(node["_id"])
    left = _cell(row, str(node["metric"]), node.get("window"))
    if node.get("other_metric"):
        right = _cell(row, str(node["other_metric"]), node.get("other_window"))
    else:
        right = node.get("value")
    outcome = _compare(left, str(node["cmp"]), right)
    return outcome, str(node["_id"])


def _collect_dynamic_requests(
    node: dict[str, Any],
    seen: set[tuple[str, str]],
    result: list[tuple[str, WindowSpec]],
) -> None:
    """Walk query tree, collect all (metric, window) pairs that need computing."""
    if "op" in node:
        for child in node.get("args") or []:
            _collect_dynamic_requests(child, seen, result)
        return
    if node.get("enabled") is False:
        return
    for field, window_field in [("metric", "window"), ("other_metric", "other_window")]:
        metric = str(node.get(field) or "")
        raw_window = node.get(window_field)
        if metric in PARAMETRIC_METRICS and raw_window is not None:
            spec = parse_window(raw_window)
            key = (metric, spec.label())
            if key not in seen:
                seen.add(key)
                result.append((metric, spec))


def _universe_frame(
    query: dict[str, Any],
    members: pd.DataFrame,
    snapshot: pd.DataFrame,
) -> pd.DataFrame:
    universe = query.get("universe") or {}
    if universe.get("symbols"):
        rows = []
        for item in universe["symbols"]:
            if isinstance(item, dict):
                rows.append({"symbol": item["symbol"], "exchange": item.get("exchange", "")})
            else:
                text = str(item)
                if ":" in text:
                    exchange, symbol = text.split(":", 1)
                    rows.append({"symbol": symbol, "exchange": exchange})
                else:
                    rows.append({"symbol": text, "exchange": ""})
        picked = pd.DataFrame(rows)
        if picked["exchange"].eq("").any():
            filled = []
            for _, row in picked.iterrows():
                if row["exchange"]:
                    filled.append(row.to_dict())
                    continue
                match = snapshot[snapshot["symbol"] == row["symbol"]]
                if len(match) != 1:
                    nse = match[match["exchange"] == "NSE"] if "exchange" in match.columns else match
                    if len(nse) == 1:
                        match = nse
                    else:
                        raise QueryError(f"Symbol {row['symbol']} is not unique without an exchange.")
                filled.append({"symbol": row["symbol"], "exchange": str(match.iloc[0]["exchange"])})
            picked = pd.DataFrame(filled)
        return picked
    uid = universe["set"]
    subset = members.loc[members["universe_id"] == uid, ["symbol", "exchange"]]
    if subset.empty:
        raise QueryError(f"Universe {uid!r} has no members in the warehouse.")
    return subset.drop_duplicates()


def _rank(
    frame: pd.DataFrame,
    rank: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    warnings: list[str],
) -> pd.DataFrame:
    clauses = rank.get("by") or []
    if not clauses:
        return frame.reset_index(drop=True)
    if len(clauses) == 1:
        item = clauses[0]
        metric = item["metric"]
        window = item.get("window")
        col = column_key(metric, parse_window(window)) if (metric in PARAMETRIC_METRICS and window) else metric
        ascending = item.get("dir") == "asc"
        if col not in frame.columns:
            return frame.reset_index(drop=True)
        return frame.sort_values(by=col, ascending=ascending, na_position="last", kind="mergesort").reset_index(drop=True)
    weights = [float(item.get("weight") or 0.0) for item in clauses]
    total = sum(weights)
    if total <= 0:
        raise QueryError("Rank weights must sum to a positive number.")
    if abs(total - 1.0) > 1e-9:
        weights = [w / total for w in weights]
        warnings.append("Rank weights did not sum to 1 and were normalised.")
    scored = frame.copy()
    scored["_score"] = 0.0
    for item, weight in zip(clauses, weights):
        metric = item["metric"]
        window = item.get("window")
        col = column_key(metric, parse_window(window)) if (metric in PARAMETRIC_METRICS and window) else metric
        if col not in scored.columns:
            continue
        series = pd.to_numeric(scored[col], errors="coerce")
        pct = series.rank(method="average", pct=True, ascending=True)
        if item.get("dir") == "asc":
            pct = 1.0 - pct
        scored["_score"] = scored["_score"] + weight * pct.fillna(0.0)
        scored.loc[series.isna(), "_score"] = pd.NA
    return scored.sort_values(by="_score", ascending=False, na_position="last", kind="mergesort").drop(columns=["_score"]).reset_index(drop=True)


def run_query(
    query: dict[str, Any],
    snapshot: pd.DataFrame,
    members: pd.DataFrame,
    catalogue: list[dict[str, Any]],
    universes: pd.DataFrame,
    prices: pd.DataFrame | None = None,
) -> QueryResult:
    if snapshot.empty:
        raise QueryError("scan_snapshot is empty. Build the snapshot from prices first.")
    universe_ids = set(universes["universe_id"].astype(str)) if not universes.empty else set()
    validate_query(query, catalogue, universe_ids)
    as_of = str(snapshot["as_of"].iloc[0])
    requested = query.get("as_of", "latest")
    if requested not in {"latest", as_of}:
        raise QueryError(f"The snapshot is as of {as_of}. Historical as-of is not built yet.")
    universe = _universe_frame(query, members, snapshot)
    work = universe.merge(snapshot, on=["symbol", "exchange"], how="left")
    if "name" not in work.columns:
        work["name"] = pd.NA

    # Compute dynamic (parametric) metrics from prices_daily and merge in.
    dynamic_requests: list[tuple[str, WindowSpec]] = []
    seen: set[tuple[str, str]] = set()
    filt = query.get("filter")
    if filt:
        _collect_dynamic_requests(filt, seen, dynamic_requests)
    for item in (query.get("rank") or {}).get("by") or []:
        metric = str(item.get("metric") or "")
        raw_window = item.get("window")
        if metric in PARAMETRIC_METRICS and raw_window is not None:
            spec = parse_window(raw_window)
            key = (metric, spec.label())
            if key not in seen:
                seen.add(key)
                dynamic_requests.append((metric, spec))
    if dynamic_requests:
        if prices is None or prices.empty:
            raise QueryError(
                "This query uses a dynamic metric (return or sma with a window) "
                "but no price data is available. Rebuild the snapshot first."
            )
        dyn = compute_dynamic_columns(prices, as_of, dynamic_requests)
        if not dyn.empty:
            work = work.merge(dyn, on=["symbol", "exchange"], how="left")

    by_id = catalogue_by_id(catalogue)
    attribution_index: dict[str, dict[str, Any]] = {}
    if filt:
        normalise_units(filt)
        _annotate(filt, "filter", [0])

        def remember(node: dict[str, Any]) -> None:
            if "_id" in node:
                attribution_index[node["_id"]] = {
                    "id": node["_id"],
                    "label": node.get("_label", node["_id"]),
                    "removed": 0,
                    "had_no_value": 0,
                }
            for child in node.get("args") or []:
                remember(child)

        remember(filt)

    passed_flags: list[bool] = []
    unknown_flags: list[bool] = []
    for _, row in work.iterrows():
        if not filt:
            passed_flags.append(True)
            unknown_flags.append(False)
            continue
        outcome, attr = _eval(filt, row)
        if outcome == TRUE:
            passed_flags.append(True)
            unknown_flags.append(False)
        elif outcome == UNKNOWN:
            passed_flags.append(False)
            unknown_flags.append(True)
            if attr and attr in attribution_index:
                attribution_index[attr]["had_no_value"] += 1
        else:
            passed_flags.append(False)
            unknown_flags.append(False)
            if attr and attr in attribution_index:
                attribution_index[attr]["removed"] += 1

    work["_pass"] = passed_flags
    work["_unknown"] = unknown_flags
    survivors = work.loc[work["_pass"]].drop(columns=["_pass", "_unknown"])
    warnings: list[str] = []
    ranked = _rank(survivors, query.get("rank") or {}, by_id, warnings)
    top_n = (query.get("rank") or {}).get("top_n")
    if top_n is not None:
        ranked = ranked.head(int(top_n))

    # Collect used metric column names (including dynamic).
    used = []
    if filt:
        def collect(node: dict[str, Any]) -> None:
            if node.get("enabled") is False:
                return
            if "metric" in node:
                metric = str(node["metric"])
                window = node.get("window")
                col = column_key(metric, parse_window(window)) if (metric in PARAMETRIC_METRICS and window) else metric
                used.append(col)
                if node.get("other_metric"):
                    other = str(node["other_metric"])
                    other_window = node.get("other_window")
                    other_col = column_key(other, parse_window(other_window)) if (other in PARAMETRIC_METRICS and other_window) else other
                    used.append(other_col)
            for child in node.get("args") or []:
                collect(child)
        collect(filt)
    for item in (query.get("rank") or {}).get("by") or []:
        metric = str(item.get("metric") or "")
        window = item.get("window")
        col = column_key(metric, parse_window(window)) if (metric in PARAMETRIC_METRICS and window) else metric
        used.append(col)
    used_unique = list(dict.fromkeys(used))
    anchor_columns = [
        col for col in ("close",)
        if col in ranked.columns and col not in used_unique
    ]
    used_unique = anchor_columns + used_unique
    display_cols = ["symbol", "exchange", "name"] + [m for m in used_unique if m in ranked.columns]
    rows = []
    for position, (_, row) in enumerate(ranked.iterrows(), start=1):
        item: dict[str, Any] = {"rank": position}
        shown: dict[str, str | None] = {}
        for col in display_cols:
            value = row[col]
            item[col] = None if _is_na(value) else value
            if col in by_id:
                shown[col] = display_value(value, str(by_id[col]["unit"]))
            elif col.startswith("_dyn_return_"):
                shown[col] = display_value(value, "ratio")
            elif col.startswith("_dyn_sma_"):
                shown[col] = display_value(value, "INR")
        item["display"] = shown
        rows.append(item)
    universe_name = "a custom list"
    uid = (query.get("universe") or {}).get("set")
    if uid and not universes.empty:
        match = universes.loc[universes["universe_id"] == uid, "name"]
        if not match.empty:
            universe_name = str(match.iloc[0])
    return QueryResult(
        as_of=as_of,
        read_back=read_back(query, catalogue, universe_name),
        passed=int(work["_pass"].sum()),
        had_no_value=int(work["_unknown"].sum()),
        removed=int((~work["_pass"] & ~work["_unknown"]).sum()),
        universe_size=len(work),
        rows=rows,
        used_metrics=used_unique,
        attribution=list(attribution_index.values()),
        warnings=warnings,
    )
