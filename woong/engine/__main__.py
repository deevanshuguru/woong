"""Run a study or a query file against the local warehouse."""

from __future__ import annotations

import json
import sys

import pandas as pd

from woong.config import load_settings
from woong.engine.run import run_query
from woong.engine.types import QueryError
from woong.metrics.catalogue import CATALOGUE_ROWS
from woong.metrics.studies import STUDY_ROWS
from woong.warehouse.schema import SCAN_SNAPSHOT, UNIVERSE_MEMBERS, UNIVERSES
from woong.warehouse.store import Warehouse


def _load_query(args: list[str]) -> dict:
    if not args or args[0] in {"--study", "study"}:
        study_id = args[1] if len(args) > 1 else STUDY_ROWS[0]["study_id"]
        for row in STUDY_ROWS:
            if row["study_id"] == study_id:
                return row["query"]
        raise SystemExit(f"Unknown study {study_id}")
    if args[0] in {"--query-file", "query-file"}:
        return json.loads(open(args[1], encoding="utf-8").read())
    raise SystemExit("usage: python -m woong.engine --study <id> | --query-file <path>")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    query = _load_query(args)
    settings = load_settings()
    warehouse = Warehouse(settings.data_dir)
    try:
        result = run_query(
            query,
            warehouse.read(SCAN_SNAPSHOT),
            warehouse.read(UNIVERSE_MEMBERS),
            list(CATALOGUE_ROWS),
            warehouse.read(UNIVERSES),
        )
    except QueryError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(result.read_back)
    print(result.disclaimer)
    print(
        f"as of {result.as_of}  passed {result.passed}  "
        f"had no value {result.had_no_value}  removed {result.removed}  "
        f"universe {result.universe_size}"
    )
    for item in result.attribution:
        print(
            f"  {item['label']}: removed {item['removed']}, "
            f"had no value {item['had_no_value']}"
        )
    if result.rows:
        print(pd.DataFrame(result.rows).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
