"""Broker-pipe harvest: instrument map and full-history daily OHLCV.

Fetches and stores. Computes nothing.

Natural keys:
- broker_instruments: (symbol, exchange)
- prices_daily: (symbol, exchange, date, source) with source = broker

Refuses to start without broker settings. Refuses to name a provider. Refuses
to re-download a raw payload that is already on disk for today's fetch date.
Refuses to invent open/high/low/volume. A second run upserts and adds nothing
when the payload is unchanged.

Bars are the broker's continuous adjusted session series. That contract is
stated in docs/DATA.md.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from woong.config import Settings, load_settings, require_broker
from woong.ingest.broker_http import BrokerError, BrokerSession, create_session
from woong.ingest.broker_parse import SOURCE, parse_broker_instruments, parse_daily_candles
from woong.warehouse.schema import BROKER_INSTRUMENTS, INGEST_JOBS, INSTRUMENTS, PRICES_DAILY
from woong.warehouse.store import Warehouse

FETCH_DATE = date.today().isoformat()
HISTORY_START = date(1980, 1, 1)
# Day candles are requested in chunks so a single call cannot hit a broker
# window limit and look like an empty history.
CHUNK_DAYS = 2000


def raw_path(warehouse: Warehouse, endpoint: str, unit: str) -> Path:
    return warehouse.raw_dir / SOURCE / endpoint / FETCH_DATE / f"{unit}.json"


def write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def record_job(
    warehouse: Warehouse,
    endpoint: str,
    unit: str,
    status: str,
    http_status: int | None = None,
    byte_count: int | None = None,
    error: str = "",
    watermark: str = "",
) -> None:
    warehouse.upsert(
        INGEST_JOBS,
        pd.DataFrame(
            [
                {
                    "pipe": SOURCE,
                    "endpoint": endpoint,
                    "unit": unit,
                    "status": status,
                    "watermark": watermark or FETCH_DATE,
                    "http_status": http_status,
                    "byte_count": byte_count,
                    "last_error": error,
                    "updated_at": pd.Timestamp.utcnow().isoformat(),
                }
            ]
        ),
    )


def _wanted_listings(warehouse: Warehouse) -> dict[tuple[str, str], str]:
    instruments = warehouse.read(INSTRUMENTS)
    if instruments.empty:
        raise RuntimeError(
            "instruments is empty. Load the symbol master before the broker harvest."
        )
    targets = instruments[instruments["instrument_kind"].isin(["stock", "etf"])]
    wanted: dict[tuple[str, str], str] = {}
    for _, row in targets.iterrows():
        key = (str(row["symbol"]).upper(), str(row["exchange"]).upper())
        wanted[key] = str(row["instrument_kind"])
    return wanted


def harvest_instrument_master(settings: Settings, session: BrokerSession) -> int:
    """Download the broker instrument dump and map tokens for our listings."""
    warehouse = Warehouse(settings.data_dir)
    warehouse.create_empty_tables()
    wanted = _wanted_listings(warehouse)
    dest = warehouse.raw_dir / SOURCE / "instruments" / FETCH_DATE / "instruments.csv"
    if not dest.exists():
        payload = session.get_bytes("instruments")
        write_bytes(dest, payload)
    else:
        payload = dest.read_bytes()
    frame = parse_broker_instruments(payload.decode("utf-8"), wanted, FETCH_DATE)
    warehouse.replace(BROKER_INSTRUMENTS, frame)
    record_job(
        warehouse,
        "instruments",
        "all",
        "done",
        200,
        dest.stat().st_size,
        watermark=FETCH_DATE,
    )
    missing = len(wanted) - len(frame)
    if missing:
        print(f"broker map: {len(frame)} matched, {missing} warehouse listings had no token", file=sys.stderr)
    return len(frame)


def _year_chunks(start: date, end: date) -> list[tuple[date, date]]:
    chunks: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS - 1), end)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + timedelta(days=1)
    return chunks


def harvest_ohlcv(
    settings: Settings,
    session: BrokerSession,
    pause_s: float = 0.35,
) -> int:
    """Fetch full daily OHLCV history for every mapped listing.

    Writes raw JSON per symbol, then upserts into prices_daily. Skips a unit
    whose raw file for today already exists and is marked done.
    """
    warehouse = Warehouse(settings.data_dir)
    mapping = warehouse.read(BROKER_INSTRUMENTS)
    if mapping.empty:
        raise RuntimeError("broker_instruments is empty. Run harvest-instruments first.")

    jobs = warehouse.read(INGEST_JOBS)
    done: set[str] = set()
    if not jobs.empty:
        done = set(
            jobs.loc[
                (jobs["pipe"] == SOURCE)
                & (jobs["endpoint"] == "ohlcv")
                & (jobs["status"] == "done"),
                "unit",
            ].astype(str)
        )

    end = date.today()
    fetched = 0
    failures: list[str] = []
    for _, row in mapping.iterrows():
        symbol = str(row["symbol"])
        exchange = str(row["exchange"])
        unit = f"{exchange}:{symbol}"
        dest = raw_path(warehouse, "ohlcv", unit.replace(":", "__"))
        if dest.exists() and unit in done:
            continue
        if dest.exists() and unit not in done:
            try:
                prices = parse_daily_candles(read_json(dest), symbol, exchange, FETCH_DATE)
                if not prices.empty:
                    warehouse.upsert(PRICES_DAILY, prices)
                record_job(warehouse, "ohlcv", unit, "done", 200, dest.stat().st_size)
            except (ValueError, KeyError) as exc:
                record_job(warehouse, "ohlcv", unit, "error", error=str(exc))
                failures.append(f"{unit}: {exc}")
            continue

        token = int(row["broker_token"])
        candles: list = []
        try:
            for start, stop in _year_chunks(HISTORY_START, end):
                payload = session.get_json(
                    f"instruments/historical/{token}/day",
                    {"from": start.isoformat(), "to": stop.isoformat()},
                )
                chunk = (payload.get("data") or {}).get("candles") or []
                candles.extend(chunk)
                time.sleep(pause_s)
            combined = {"status": "success", "data": {"candles": candles}}
            write_json(dest, combined)
            prices = parse_daily_candles(combined, symbol, exchange, FETCH_DATE)
            if not prices.empty:
                warehouse.upsert(PRICES_DAILY, prices)
            record_job(warehouse, "ohlcv", unit, "done", 200, dest.stat().st_size)
            fetched += 1
        except (BrokerError, ValueError, KeyError) as exc:
            status = getattr(exc, "status", None)
            record_job(warehouse, "ohlcv", unit, "error", status, error=str(exc))
            failures.append(f"{unit}: {exc}")
            if isinstance(exc, BrokerError) and exc.status in {401, 403}:
                raise RuntimeError(
                    f"Broker credential failed on {unit} after {fetched} fetches. "
                    "Refresh WOONG_BROKER_ACCESS_TOKEN (or login fields) and re-run; "
                    "completed symbols stay done."
                ) from exc
        time.sleep(pause_s)

    if failures:
        print(f"broker ohlcv failures {len(failures)}", file=sys.stderr)
        for line in failures[:20]:
            print(line, file=sys.stderr)
        raise RuntimeError(f"{len(failures)} symbols failed the broker OHLCV harvest")
    return fetched


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    settings = load_settings()
    require_broker(settings)
    if not args:
        raise SystemExit(
            "usage: python -m woong.ingest.broker "
            "[harvest-instruments|harvest-ohlcv|harvest-all]"
        )
    command = args[0]
    session = create_session(settings)
    if command == "harvest-instruments":
        count = harvest_instrument_master(settings, session)
        print(f"broker_instruments {count} rows")
        return 0
    if command == "harvest-ohlcv":
        fetched = harvest_ohlcv(settings, session)
        print(f"fetched {fetched} new broker OHLCV series")
        return 0
    if command == "harvest-all":
        count = harvest_instrument_master(settings, session)
        print(f"broker_instruments {count} rows")
        fetched = harvest_ohlcv(settings, session)
        print(f"fetched {fetched} new broker OHLCV series")
        return 0
    raise SystemExit(
        "usage: python -m woong.ingest.broker "
        "[harvest-instruments|harvest-ohlcv|harvest-all]"
    )


if __name__ == "__main__":
    raise SystemExit(main())
