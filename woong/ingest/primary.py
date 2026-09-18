"""Primary-pipe harvest and load.

Natural keys are stated on each warehouse table. A second run upserts on those
keys and adds nothing new when the payload is unchanged.

Refuses to compute a metric, to re-download a payload that is already on disk,
and to request the insider-trades HTTP path. That file is loaded from the
local dump only.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from woong.config import Settings, load_settings
from woong.ingest.http import FetchError, get_json
from woong.ingest.parse import (
    SOURCE,
    default_universes,
    parse_breadth,
    parse_events,
    parse_factors,
    parse_flows,
    parse_insider,
    parse_seasonality,
    parse_stock_series,
    parse_symbols,
)
from woong.metrics.catalogue import CATALOGUE_ROWS
from woong.warehouse.schema import (
    FACTORS_DAILY,
    INGEST_JOBS,
    INSIDER_TRADES,
    INSTRUMENTS,
    MARKET_BREADTH,
    MARKET_EVENTS,
    MARKET_FLOWS,
    METRIC_CATALOG,
    PRICE_METRICS_DAILY,
    PRICES_DAILY,
    SEASONALITY,
    UNIVERSE_MEMBERS,
    UNIVERSES,
)
from woong.warehouse.store import Warehouse

PRICE_COLUMNS = "close,return1D,return1W,return1M,return3M,return1Y,return3Y,return5Y"
FETCH_DATE = date.today().isoformat()


def raw_path(warehouse: Warehouse, endpoint: str, unit: str = "payload") -> Path:
    return warehouse.raw_dir / SOURCE / endpoint / FETCH_DATE / f"{unit}.json"


def write_raw(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def read_raw(path: Path) -> dict:
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


def load_catalogue(warehouse: Warehouse) -> int:
    return warehouse.upsert(METRIC_CATALOG, pd.DataFrame(list(CATALOGUE_ROWS)))


def load_symbols(warehouse: Warehouse, payload: dict) -> pd.DataFrame:
    instruments = parse_symbols(payload)
    warehouse.upsert(INSTRUMENTS, instruments)
    as_of = instruments["as_of"].iloc[0]
    universes, members = default_universes(instruments, as_of)
    warehouse.upsert(UNIVERSES, universes)
    warehouse.upsert(UNIVERSE_MEMBERS, members)
    return instruments


def exchange_for(instruments: pd.DataFrame, symbol: str) -> str:
    matches = instruments[instruments["symbol"] == symbol]
    if matches.empty:
        raise ValueError(f"Symbol {symbol} is not in the master")
    nse = matches[matches["exchange"] == "NSE"]
    if len(nse) == 1:
        return "NSE"
    if len(matches) == 1:
        return str(matches.iloc[0]["exchange"])
    # Two different companies share a ticker. The price path has no listing
    # field, so we refuse to attach the series to the wrong row.
    raise ValueError(f"Symbol {symbol} is listed on more than one exchange")


def load_existing(settings: Settings) -> None:
    warehouse = Warehouse(settings.data_dir)
    warehouse.create_empty_tables()
    load_catalogue(warehouse)
    raw = warehouse.raw_dir / SOURCE
    failures: list[str] = []

    symbols_file = raw / "symbols" / FETCH_DATE / "payload.json"
    if not symbols_file.exists():
        raise RuntimeError("Symbols payload is missing. Fetch the master first.")
    instruments = load_symbols(warehouse, read_raw(symbols_file))
    record_job(warehouse, "symbols", "all", "done", 200, symbols_file.stat().st_size)

    mapping = [
        ("market-flows", parse_flows, MARKET_FLOWS),
        ("market-breadth", parse_breadth, MARKET_BREADTH),
        ("stocks-factors-latest-NETWEB", parse_factors, FACTORS_DAILY),
        ("seasonality-NIFTY", parse_seasonality, SEASONALITY),
        ("seasonality-CNXIT", parse_seasonality, SEASONALITY),
        ("market-events-NETWEB", parse_events, MARKET_EVENTS),
    ]
    for name, parser, spec in mapping:
        path = raw / name / FETCH_DATE / "payload.json"
        if not path.exists():
            failures.append(f"{name}: raw file missing")
            continue
        warehouse.upsert(spec, parser(read_raw(path)))
        record_job(warehouse, name, "payload", "done", 200, path.stat().st_size)

    prices_file = raw / "stocks-data-NETWEB" / FETCH_DATE / "payload.json"
    if prices_file.exists():
        try:
            exchange = exchange_for(instruments, "NETWEB")
            prices, metrics = parse_stock_series(read_raw(prices_file), exchange)
            warehouse.upsert(PRICES_DAILY, prices)
            warehouse.upsert(PRICE_METRICS_DAILY, metrics)
            record_job(warehouse, "stocks/data", "NETWEB", "done", 200, prices_file.stat().st_size)
        except ValueError as exc:
            failures.append(f"stocks-data-NETWEB: {exc}")

    insider_file = raw / "insider-trades" / FETCH_DATE / "payload.json"
    if insider_file.exists():
        warehouse.upsert(INSIDER_TRADES, parse_insider(read_raw(insider_file)))
        record_job(warehouse, "insider-trades", "local-dump", "done", 200, insider_file.stat().st_size)

    if failures:
        raise RuntimeError("Load finished with failures: " + "; ".join(failures))


def harvest_price_series(settings: Settings, pause_s: float = 0.2) -> int:
    """Fetch the daily series for every stock and exchange-traded fund (ETF).

    This step only writes raw payloads and a checkpoint per symbol. Parsing into
    the warehouse is `load_price_series`, because upserting one symbol at a time
    rewrites the whole price table and turns a linear harvest into a quadratic
    one.
    """
    import time

    warehouse = Warehouse(settings.data_dir)
    instruments = warehouse.read(INSTRUMENTS)
    if instruments.empty:
        raise RuntimeError("instruments is empty. Run load-existing first.")
    targets = instruments[instruments["instrument_kind"].isin(["stock", "etf"])]
    failures: list[str] = []
    fetched = 0
    for _, row in targets.iterrows():
        symbol = row["symbol"]
        dest = raw_path(warehouse, "stocks-data", symbol)
        if dest.exists():
            continue
        try:
            exchange_for(instruments, symbol)
        except ValueError as exc:
            record_job(warehouse, "stocks/data", symbol, "skipped", error=str(exc))
            continue
        try:
            status, payload = get_json(
                settings,
                f"stocks/data/{symbol}",
                {"columns": PRICE_COLUMNS},
            )
            write_raw(dest, payload)
            record_job(warehouse, "stocks/data", symbol, "fetched", status, dest.stat().st_size)
            fetched += 1
        except (FetchError, ValueError, KeyError) as exc:
            record_job(warehouse, "stocks/data", symbol, "error", error=str(exc))
            failures.append(f"{symbol}: {exc}")
        time.sleep(pause_s)
    if failures:
        print(f"price harvest failures {len(failures)}", file=sys.stderr)
        for line in failures[:20]:
            print(line, file=sys.stderr)
        raise RuntimeError(f"{len(failures)} symbols failed the price harvest")
    return fetched


def load_price_series(settings: Settings, chunk_size: int = 900) -> int:
    """Parse every raw daily series on disk into the warehouse.

    Idempotent: the natural key is the same on a second run, so nothing is
    duplicated. Writes in chunks so one bad chunk cannot lose the whole load.
    """
    warehouse = Warehouse(settings.data_dir)
    instruments = warehouse.read(INSTRUMENTS)
    if instruments.empty:
        raise RuntimeError("instruments is empty. Run load-existing first.")
    raw_dir = raw_path(warehouse, "stocks-data", "any").parent
    if not raw_dir.exists():
        raise RuntimeError("No raw daily series on disk. Run harvest-prices first.")
    files = sorted(raw_dir.glob("*.json"))
    if not files:
        raise RuntimeError("No raw daily series on disk. Run harvest-prices first.")
    failures: list[str] = []
    loaded = 0
    price_chunk: list[pd.DataFrame] = []
    metric_chunk: list[pd.DataFrame] = []
    done_units: list[str] = []

    def flush() -> None:
        if not price_chunk:
            return
        warehouse.upsert(PRICES_DAILY, pd.concat(price_chunk, ignore_index=True))
        warehouse.upsert(PRICE_METRICS_DAILY, pd.concat(metric_chunk, ignore_index=True))
        for unit in done_units:
            record_job(warehouse, "stocks/data", unit, "done", 200)
        price_chunk.clear()
        metric_chunk.clear()
        done_units.clear()

    for path in files:
        symbol = path.stem
        try:
            exchange = exchange_for(instruments, symbol)
            prices, metrics = parse_stock_series(read_raw(path), exchange)
        except (ValueError, KeyError) as exc:
            failures.append(f"{symbol}: {exc}")
            continue
        price_chunk.append(prices)
        metric_chunk.append(metrics)
        done_units.append(symbol)
        loaded += 1
        if len(price_chunk) >= chunk_size:
            flush()
    flush()
    if failures:
        print(f"price load failures {len(failures)}", file=sys.stderr)
        for line in failures[:20]:
            print(line, file=sys.stderr)
        raise RuntimeError(f"{len(failures)} raw series failed to load")
    return loaded


SEASONALITY_KINDS = ("stock", "etf", "index")


def harvest_seasonality(
    settings: Settings,
    kinds: tuple[str, ...] = SEASONALITY_KINDS,
    pause_s: float = 0.2,
) -> int:
    """Fetch monthly seasonality for every instrument of the given kinds.

    The path needs a bearer token. Without one it answers HTTP 400 for a stock,
    which is indistinguishable from a symbol that has no seasonality. So an
    unauthorised answer stops the run instead of being recorded thousands of
    times as a refusal.

    Seasonality is keyed on symbol alone, so a symbol listed on two exchanges is
    fetched once.
    """
    import time

    warehouse = Warehouse(settings.data_dir)
    instruments = warehouse.read(INSTRUMENTS)
    if instruments.empty:
        raise RuntimeError("instruments is empty. Run load-existing first.")
    wanted = instruments[instruments["instrument_kind"].isin(list(kinds))].copy()
    # National Stock Exchange (NSE) names go first. The credential can expire
    # mid-run, so the order decides what we end up holding, and the scanner's
    # universes are NSE.
    wanted["_nse_first"] = (wanted["exchange"].astype(str) != "NSE").astype(int)
    wanted = wanted.sort_values(["_nse_first", "symbol"], kind="mergesort")
    symbols = list(dict.fromkeys(wanted["symbol"].astype(str)))
    fetched = 0
    refused: list[str] = []
    for symbol in symbols:
        dest = raw_path(warehouse, "seasonality", symbol)
        if dest.exists():
            continue
        try:
            status, payload = get_json(settings, f"seasonality/{symbol}")
            write_raw(dest, payload)
            record_job(warehouse, "seasonality", symbol, "fetched", status, dest.stat().st_size)
            fetched += 1
        except FetchError as exc:
            record_job(warehouse, "seasonality", symbol, "refused", exc.status, error=str(exc))
            if exc.status in {401, 403}:
                raise RuntimeError(
                    "The primary pipe refused the credential on "
                    f"{symbol} after {fetched} fetches. WOONG_PRIMARY_API_TOKEN is "
                    "missing or expired. Refresh it and run this command again: "
                    "everything already on disk is kept."
                ) from exc
            refused.append(f"{symbol}: HTTP {exc.status}")
        except (ValueError, KeyError) as exc:
            record_job(warehouse, "seasonality", symbol, "error", error=str(exc))
            refused.append(f"{symbol}: {exc}")
        time.sleep(pause_s)
    if refused:
        print(f"seasonality refusals {len(refused)}", file=sys.stderr)
        for line in refused[:20]:
            print(line, file=sys.stderr)
    return fetched


def load_seasonality(settings: Settings) -> int:
    """Parse every raw seasonality payload on disk into the warehouse."""
    warehouse = Warehouse(settings.data_dir)
    raw_dir = raw_path(warehouse, "seasonality", "any").parent
    files = sorted(raw_dir.glob("*.json")) if raw_dir.exists() else []
    legacy = [
        path
        for name in ("seasonality-NIFTY", "seasonality-CNXIT")
        for path in [warehouse.raw_dir / SOURCE / name / FETCH_DATE / "payload.json"]
        if path.exists()
    ]
    files = files + legacy
    if not files:
        raise RuntimeError("No raw seasonality on disk. Run harvest-seasonality first.")
    frames: list[pd.DataFrame] = []
    failures: list[str] = []
    for path in files:
        try:
            frames.append(parse_seasonality(read_raw(path)))
        except (ValueError, KeyError) as exc:
            failures.append(f"{path.stem}: {exc}")
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        combined = combined.drop_duplicates(subset=["symbol", "month"], keep="last")
        warehouse.upsert(SEASONALITY, combined)
        for symbol in sorted(set(combined["symbol"])):
            record_job(warehouse, "seasonality", symbol, "done", 200)
    if failures:
        print(f"seasonality load failures {len(failures)}", file=sys.stderr)
        raise RuntimeError(f"{len(failures)} raw seasonality payloads failed to load")
    return 0 if not frames else int(combined["symbol"].nunique())


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    settings = load_settings()
    if not args or args[0] == "load-existing":
        load_existing(settings)
        print("loaded existing raw payloads into the warehouse")
        return 0
    if args[0] == "harvest-prices":
        fetched = harvest_price_series(settings)
        print(f"fetched {fetched} new price series")
        return 0
    if args[0] == "load-prices":
        loaded = load_price_series(settings)
        print(f"loaded {loaded} raw price series into the warehouse")
        return 0
    if args[0] == "harvest-seasonality":
        kinds = tuple(args[1].split(",")) if len(args) > 1 else SEASONALITY_KINDS
        fetched = harvest_seasonality(settings, kinds)
        print(f"fetched {fetched} new seasonality series")
        return 0
    if args[0] == "load-seasonality":
        symbols = load_seasonality(settings)
        print(f"loaded seasonality for {symbols} symbols")
        return 0
    raise SystemExit(
        "usage: python -m woong.ingest.primary [load-existing|harvest-prices|"
        "load-prices|harvest-seasonality|load-seasonality]"
    )


if __name__ == "__main__":
    raise SystemExit(main())
