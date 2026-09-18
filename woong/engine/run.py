"""Run a validated scanner query against a snapshot.

A missing value is unknown: it never passes and never counts as a failure.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from woong.engine.readback import read_back
from woong.engine.types import QueryError, QueryResult
from woong.engine.validate import catalogue_by_id, validate_query
from woong.metrics.display import display_value

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


def _cell(row: pd.Series, metric: str) -> Any:
    if metric not in row.index:
        return None
    return row[metric]


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
    """Convert a percent value to the ratio the metric is stored in.

    The screen lets a user type 20 for twenty percent. The division happens
    here, in Python, for the same reason every other number does.
    """
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
    if node.get("other_metric"):
        node["_label"] = f"{metric} {cmp} {node['other_metric']}"
    else:
        node["_label"] = f"{metric} {cmp} {node.get('value')}"


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
    left = _cell(row, str(node["metric"]))
    if node.get("other_metric"):
        right = _cell(row, str(node["other_metric"]))
    else:
        right = node.get("value")
    outcome = _compare(left, str(node["cmp"]), right)
    return outcome, str(node["_id"])


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
            # A ticker without an exchange uses the snapshot row when unique.
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
                        raise QueryError(
                            f"Symbol {row['symbol']} is not unique without an exchange."
                        )
                filled.append(
                    {"symbol": row["symbol"], "exchange": str(match.iloc[0]["exchange"])}
                )
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
        metric = clauses[0]["metric"]
        ascending = clauses[0].get("dir") == "asc"
        ordered = frame.sort_values(
            by=metric,
            ascending=ascending,
            na_position="last",
            kind="mergesort",
        )
        return ordered.reset_index(drop=True)
    weights = []
    for item in clauses:
        weights.append(float(item.get("weight") or 0.0))
    total = sum(weights)
    if total <= 0:
        raise QueryError("Rank weights must sum to a positive number.")
    if abs(total - 1.0) > 1e-9:
        weights = [weight / total for weight in weights]
        warnings.append("Rank weights did not sum to 1 and were normalised.")
    scored = frame.copy()
    scored["_score"] = 0.0
    for item, weight in zip(clauses, weights):
        metric = item["metric"]
        series = pd.to_numeric(scored[metric], errors="coerce")
        pct = series.rank(method="average", pct=True, ascending=True)
        if item.get("dir") == "asc":
            pct = 1.0 - pct
        scored["_score"] = scored["_score"] + weight * pct.fillna(0.0)
        # Missing rank inputs stay last, not zero-scored into the middle.
        scored.loc[series.isna(), "_score"] = pd.NA
    ordered = scored.sort_values(
        by="_score",
        ascending=False,
        na_position="last",
        kind="mergesort",
    )
    return ordered.drop(columns=["_score"]).reset_index(drop=True)


def run_query(
    query: dict[str, Any],
    snapshot: pd.DataFrame,
    members: pd.DataFrame,
    catalogue: list[dict[str, Any]],
    universes: pd.DataFrame,
) -> QueryResult:
    if snapshot.empty:
        raise QueryError("scan_snapshot is empty. Build the snapshot from prices first.")
    universe_ids = set(universes["universe_id"].astype(str)) if not universes.empty else set()
    validate_query(query, catalogue, universe_ids)
    as_of = str(snapshot["as_of"].iloc[0])
    requested = query.get("as_of", "latest")
    if requested not in {"latest", as_of}:
        raise QueryError(
            f"The snapshot is as of {as_of}. Historical as-of is not built yet."
        )
    universe = _universe_frame(query, members, snapshot)
    work = universe.merge(snapshot, on=["symbol", "exchange"], how="left")
    if "name" not in work.columns:
        work["name"] = pd.NA
    filt = query.get("filter")
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
    by_id = catalogue_by_id(catalogue)
    ranked = _rank(survivors, query.get("rank") or {}, by_id, warnings)
    top_n = (query.get("rank") or {}).get("top_n")
    if top_n is not None:
        ranked = ranked.head(int(top_n))
    used = []
    if filt:

        def collect(node: dict[str, Any]) -> None:
            if node.get("enabled") is False:
                return
            if "metric" in node:
                used.append(str(node["metric"]))
                if node.get("other_metric"):
                    used.append(str(node["other_metric"]))
            for child in node.get("args") or []:
                collect(child)

        collect(filt)
    for item in (query.get("rank") or {}).get("by") or []:
        used.append(str(item["metric"]))
    used_unique = list(dict.fromkeys(used))
    # Anchor columns ride along on every result: a stranger's stock needs a
    # price and two short returns before any rule metric means anything.
    anchor_columns = [
        column
        for column in ("close", "return_1m", "return_3m")
        if column in ranked.columns and column not in used_unique
    ]
    used_unique = anchor_columns + used_unique
    display_cols = ["symbol", "exchange", "name"] + [
        metric for metric in used_unique if metric in ranked.columns
    ]
    rows = []
    for position, (_, row) in enumerate(ranked.iterrows(), start=1):
        item: dict[str, Any] = {"rank": position}
        shown: dict[str, str | None] = {}
        for col in display_cols:
            value = row[col]
            item[col] = None if _is_na(value) else value
            if col in by_id:
                shown[col] = display_value(value, str(by_id[col]["unit"]))
        # The screen prints these strings. It is not allowed to turn a ratio into
        # a percent itself, so the conversion happens here.
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
