"""Serve the desktop page and the query endpoint.

The browser posts a query and renders the response. This module does not
compute a number.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from woong.config import load_settings
from woong.engine.run import run_query
from woong.engine.types import QueryError
from woong.metrics.catalogue import CATALOGUE_ROWS
from woong.metrics.snapshot import build_snapshot
from woong.metrics.studies import STUDY_ROWS
from woong.api.instrument import InstrumentNotFound, instrument_page, lookup_instruments
from woong.api.present import to_display_query
from woong.warehouse.schema import PRICES_DAILY, SCAN_SNAPSHOT, UNIVERSE_MEMBERS, UNIVERSES
from woong.warehouse.store import Warehouse

WEB_DIR = Path(__file__).resolve().parents[1] / "web"


def _json(payload: Any) -> bytes:
    return json.dumps(payload, default=str).encode("utf-8")


class ScannerHandler(BaseHTTPRequestHandler):
    warehouse: Warehouse

    def log_message(self, format: str, *args: object) -> None:
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: Any) -> None:
        self._send(status, _json(payload), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            page = WEB_DIR / "index.html"
            self._send(200, page.read_bytes(), "text/html; charset=utf-8")
            return
        if path == "/style.css":
            self._send(200, (WEB_DIR / "style.css").read_bytes(), "text/css; charset=utf-8")
            return
        if path == "/basket-data.js":
            self._send(200, (WEB_DIR / "basket-data.js").read_bytes(), "text/javascript; charset=utf-8")
            return
        if path == "/baskets":
            self._send(200, (WEB_DIR / "baskets.html").read_bytes(), "text/html; charset=utf-8")
            return
        if path.startswith("/basket/"):
            self._send(200, (WEB_DIR / "basket.html").read_bytes(), "text/html; charset=utf-8")
            return
        if path.startswith("/instrument/"):
            page = WEB_DIR / "instrument.html"
            self._send(200, page.read_bytes(), "text/html; charset=utf-8")
            return
        if path == "/api/lookup":
            query = parse_qs(urlparse(self.path).query)
            q = (query.get("q") or [""])[0]
            self._send_json(200, {"matches": lookup_instruments(self.warehouse, q)})
            return
        if path == "/api/instrument":
            query = parse_qs(urlparse(self.path).query)
            symbol = unquote((query.get("symbol") or [""])[0])
            exchange = unquote((query.get("exchange") or [""])[0])
            try:
                self._send_json(200, instrument_page(self.warehouse, symbol, exchange))
            except InstrumentNotFound as exc:
                self._send_json(404, {"error": str(exc)})
            return
        if path == "/api/meta":
            universes = self.warehouse.read(UNIVERSES)
            snapshot = self.warehouse.read(SCAN_SNAPSHOT)
            as_of = "" if snapshot.empty else str(snapshot["as_of"].iloc[0])
            self._send_json(
                200,
                {
                    "as_of": as_of,
                    "snapshot_rows": int(len(snapshot)),
                    "studies": [
                        {
                            "study_id": row["study_id"],
                            "title": row["title"],
                            "shelf": row["shelf"],
                            "author": row["author"],
                            "idea": row["idea"],
                            "query": to_display_query(row["query"], list(CATALOGUE_ROWS)),
                        }
                        for row in STUDY_ROWS
                    ],
                    # A per-index universe is a membership list with no members
                    # loaded. The index_list universes are the scannable ones.
                    "universes": [
                        {
                            "universe_id": rec["universe_id"],
                            "name": rec["name"],
                            "kind": rec["kind"],
                        }
                        for rec in universes.to_dict(orient="records")
                        if rec["kind"] != "index"
                    ],
                    "catalogue": list(CATALOGUE_ROWS),
                },
            )
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Body is not JSON."})
            return
        if path == "/api/query":
            try:
                result = run_query(
                    payload,
                    self.warehouse.read(SCAN_SNAPSHOT),
                    self.warehouse.read(UNIVERSE_MEMBERS),
                    list(CATALOGUE_ROWS),
                    self.warehouse.read(UNIVERSES),
                    prices=self.warehouse.read(PRICES_DAILY),
                )
            except QueryError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(
                200,
                {
                    "as_of": result.as_of,
                    "read_back": result.read_back,
                    "disclaimer": result.disclaimer,
                    "passed": result.passed,
                    "had_no_value": result.had_no_value,
                    "removed": result.removed,
                    "universe_size": result.universe_size,
                    "used_metrics": result.used_metrics,
                    "attribution": result.attribution,
                    "warnings": result.warnings,
                    "rows": result.rows,
                },
            )
            return
        if path == "/api/snapshot":
            try:
                count, as_of = build_snapshot(self.warehouse)
            except RuntimeError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, {"snapshot_rows": count, "as_of": as_of})
            return
        self._send_json(404, {"error": "Not found"})


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    settings = load_settings()
    warehouse = Warehouse(settings.data_dir)
    snapshot = warehouse.read(SCAN_SNAPSHOT)
    if snapshot.empty:
        build_snapshot(warehouse)
    ScannerHandler.warehouse = warehouse
    server = ThreadingHTTPServer((host, port), ScannerHandler)
    print(f"scanner on http://{host}:{port}", flush=True)
    server.serve_forever()
