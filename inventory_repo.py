#!/usr/bin/env python3
"""One-shot repository inventory.

Produces repo_inventory.md: sizes, files missing from the shared zip,
JSON structures with sample elements, CSV headers, and presence (never
contents) of secret files. Standard library only.

usage: python3 inventory_repo.py [repo_root]   (default: current directory)
"""

import csv
import io
import json
import os
import sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT = "repo_inventory.md"
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".cursor"}
BIG_JSON = 5 * 1024 * 1024
SECRET_HINTS = ("token", "password", "secret", "api_key", "apikey", "authorization")

KNOWN_FROM_ZIP = set(""".cursor/agents/business-strategist.md
.cursor/agents/data-analyst.md
.cursor/agents/data-engineer.md
.cursor/agents/product-manager.md
.cursor/agents/qa-reviewer.md
.cursor/agents/senior-engineer.md
.cursor/rules/woong.mdc
.cursor/skills/woong-git/SKILL.md
.cursor/skills/woong-ingest/SKILL.md
.cursor/skills/woong-metrics/SKILL.md
.cursor/skills/woong-query/SKILL.md
.cursor/skills/woong-scanner-ui/SKILL.md
.env.example
.github/ISSUE_TEMPLATE/work-item.md
.github/pull_request_template.md
.github/workflows/ci.yml
.gitignore
AGENTS.md
CLAUDE.md
README.md
SHARE_PACK.md
STATUS.md
docs/ARCHITECTURE.md
docs/CONTRIBUTING.md
docs/DATA.md
docs/DESIGN.md
docs/PRODUCT.md
docs/QUERY.md
docs/SEASONALITY.md
docs/metric-ideas.md
manually_added_data/category_columns.md
manually_added_data/insider_trades.md
manually_added_data/seasonality.md
mvp/tasks.json
pyproject.toml
requirements.txt
tests/fixtures/broker/candles.json
tests/fixtures/broker/instruments.csv
tests/fixtures/primary/stock_series.json
tests/fixtures/primary/symbols.json
tests/test_broker_ingest.py
tests/test_chart.py
tests/test_compute.py
tests/test_engine.py
tests/test_foundation.py
tests/test_instrument.py
tests/test_repository_guards.py
tests/test_seasonality.py
tests/test_warehouse.py
woong/__init__.py
woong/api/__init__.py
woong/api/__main__.py
woong/api/chart.py
woong/api/instrument.py
woong/api/present.py
woong/api/server.py
woong/config.py
woong/engine/__init__.py
woong/engine/__main__.py
woong/engine/readback.py
woong/engine/run.py
woong/engine/types.py
woong/engine/validate.py
woong/ingest/__init__.py
woong/ingest/__main__.py
woong/ingest/broker.py
woong/ingest/broker_auth.py
woong/ingest/broker_http.py
woong/ingest/broker_parse.py
woong/ingest/http.py
woong/ingest/parse.py
woong/ingest/primary.py
woong/metrics/__init__.py
woong/metrics/__main__.py
woong/metrics/catalogue.py
woong/metrics/compute.py
woong/metrics/display.py
woong/metrics/seasonality.py
woong/metrics/snapshot.py
woong/metrics/studies.py
woong/warehouse/__init__.py
woong/warehouse/schema.py
woong/warehouse/store.py
woong/web/index.html
woong/web/instrument.html
woong/web/style.css""".split())

def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%.1f %s" % (n, unit)
        n /= 1024.0

def walk_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield os.path.join(dirpath, name)

def redact_value(key, value):
    k = str(key).lower()
    if any(h in k for h in SECRET_HINTS):
        return "<redacted>"
    text = json.dumps(value) if not isinstance(value, str) else value
    text = str(text)
    return text[:80] + ("..." if len(text) > 80 else "")

def schema_of(obj, depth=0, max_depth=4):
    """Type map with one sample per leaf."""
    pad = "  " * depth
    lines = []
    if depth >= max_depth:
        return [pad + "... (deeper)"]
    if isinstance(obj, dict):
        lines.append(pad + "object with %d keys" % len(obj))
        for i, (k, v) in enumerate(obj.items()):
            if i >= 25:
                lines.append(pad + "  ... %d more keys" % (len(obj) - 25))
                break
            lines.append(pad + "  %s: %s" % (k, type(v).__name__))
            lines.extend(schema_of(v, depth + 2, max_depth))
            if isinstance(v, (dict, list)):
                continue
    elif isinstance(obj, list):
        lines.append(pad + "array with %d items" % len(obj))
        if obj:
            lines.append(pad + "  first item:")
            lines.extend(schema_of(obj[0], depth + 2, max_depth))
            if len(obj) > 1:
                lines.append(pad + "  last item:")
                lines.extend(schema_of(obj[-1], depth + 2, max_depth))
    else:
        lines.append(pad + "sample: %s" % redact_value("", obj))
    return lines

def describe_json(path):
    size = os.path.getsize(path)
    out = ["### `%s` (%s)" % (os.path.relpath(path, ROOT), human(size))]
    try:
        if size <= BIG_JSON:
            with open(path, encoding="utf-8", errors="replace") as fh:
                data = json.load(fh)
        else:
            with open(path, encoding="utf-8", errors="replace") as fh:
                head = fh.read(200_000)
            data = None
            dec = json.JSONDecoder()
            pos = 0
            while pos < len(head):
                try:
                    data, end = dec.raw_decode(head, pos)
                    break
                except json.JSONDecodeError:
                    pos = head.find(chr(10), pos)
                    if pos == -1:
                        break
                    pos += 1
            if data is None:
                out.append("- too large and not partially parseable; head: `%s`" % head[:200].replace(chr(10), " "))
                return chr(10).join(out)
            out.append("- large file; structure from first 200KB")
        out.append("- root type: %s" % type(data).__name__)
        if isinstance(data, dict):
            out.append("- top-level keys: %s" % ", ".join("`%s`" % k for k in list(data.keys())[:30]))
            out.append("- structure and samples:")
            out.extend("    " + l.strip() for l in schema_of(data, 1))
        elif isinstance(data, list):
            out.append("- %d items at root" % len(data))
            if data:
                out.append("- structure and samples:")
                out.extend("    " + l.strip() for l in schema_of(data, 1))
    except Exception as exc:
        out.append("- could not parse: %s" % exc)
    return chr(10).join(out) + chr(10)

def describe_csv(path):
    size = os.path.getsize(path)
    out = ["### `%s` (%s)" % (os.path.relpath(path, ROOT), human(size))]
    try:
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            count = sum(1 for _ in reader)
        out.append("- columns (%d): %s" % (len(header or []), ", ".join(header or [])))
        out.append("- data rows: %d" % count)
    except Exception as exc:
        out.append("- could not read: %s" % exc)
    return chr(10).join(out) + chr(10)

def describe_parquet(path):
    out = ["### `%s` (%s)" % (os.path.relpath(path, ROOT), human(os.path.getsize(path)))]
    try:
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(path)
        out.append("- rows: %s" % pf.metadata.num_rows)
        out.append("- columns: %s" % ", ".join(n.name for n in pf.schema))
    except Exception as exc:
        out.append("- pyarrow unavailable or unreadable: %s" % exc)
    return chr(10).join(out) + chr(10)

def main():
    if not os.path.isdir(ROOT):
        raise SystemExit("not a directory: " + ROOT)
    all_files = list(walk_files(ROOT))
    rows = []
    for p in all_files:
        try:
            rows.append((os.path.relpath(p, ROOT), os.path.getsize(p)))
        except OSError:
            pass
    total = sum(s for _, s in rows)

    by_ext = {}
    for _, s in rows:
        ext = os.path.splitext(_)[1].lower() or "(none)"
        by_ext[ext] = by_ext.get(ext, [0, 0])
        by_ext[ext][0] += 1
        by_ext[ext][1] += s

    # directory aggregation
    dir_size = {}
    for rel, s in rows:
        top = rel.split(os.sep)[0] if os.sep in rel else "(root)"
        dir_size[top] = dir_size.get(top, 0) + s

    # not in shared zip
    missing = sorted(
        rel for rel, _ in rows
        if rel.replace(os.sep, "/") not in KNOWN_FROM_ZIP
    )

    L = []
    L.append("# Repository inventory")
    L.append("")
    L.append("Root: `%s`" % ROOT)
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append("- files: %d" % len(rows))
    L.append("- total size: %s" % human(total))
    L.append("")
    L.append("| ext | files | size |")
    L.append("|---|---|---|")
    for ext, (c, s) in sorted(by_ext.items(), key=lambda kv: -kv[1][1]):
        L.append("| %s | %d | %s |" % (ext, c, human(s)))
    L.append("")
    L.append("## Size by top-level directory")
    L.append("")
    L.append("| dir | size |")
    L.append("|---|---|")
    for d, s in sorted(dir_size.items(), key=lambda kv: -kv[1]):
        L.append("| %s | %s |" % (d, human(s)))
    L.append("")
    L.append("## 25 largest files")
    L.append("")
    L.append("| file | size |")
    L.append("|---|---|")
    for rel, s in sorted(rows, key=lambda r: -r[1])[:25]:
        L.append("| %s | %s |" % (rel, human(s)))
    L.append("")
    L.append("## Files NOT in the zip I shared (%d)" % len(missing))
    L.append("")
    if missing:
        L.extend("- `%s`" % m for m in missing[:200])
        if len(missing) > 200:
            L.append("- ... and %d more" % (len(missing) - 200))
    else:
        L.append("- none")
    L.append("")

    jsons = sorted(p for p in all_files if p.lower().endswith(".json"))
    L.append("## JSON files (%d)" % len(jsons))
    L.append("")
    for p in jsons:
        L.append(describe_json(p))

    csvs = sorted(p for p in all_files if p.lower().endswith(".csv"))
    if csvs:
        L.append("## CSV files (%d)" % len(csvs))
        L.append("")
        for p in csvs:
            L.append(describe_csv(p))

    pqs = sorted(p for p in all_files if p.lower().endswith(".parquet"))
    if pqs:
        L.append("## Parquet files (%d)" % len(pqs))
        L.append("")
        for p in pqs:
            L.append(describe_parquet(p))

    L.append("## Secret files (presence only, never contents)")
    L.append("")
    for name in (".env", "data/.broker_token"):
        p = os.path.join(ROOT, name)
        L.append("- `%s`: %s" % (name, "present (%s)" % human(os.path.getsize(p)) if os.path.exists(p) else "absent"))
    L.append("")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(chr(10).join(L))
    print("wrote %s (%d files scanned)" % (OUT, len(rows)))

if __name__ == "__main__":
    main()
