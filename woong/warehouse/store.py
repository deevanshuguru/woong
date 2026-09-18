"""Read and write parquet tables under the data directory.

Refuses to write a row that is missing its natural key, and refuses to create a
table that is not in the schema.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from woong.warehouse.schema import TABLE_SPECS, TableSpec


class Warehouse:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.warehouse_dir = self.data_dir / "warehouse"
        self.raw_dir = self.data_dir / "raw"
        self.warehouse_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, spec: TableSpec) -> Path:
        return self.warehouse_dir / f"{spec.name}.parquet"

    def _write(self, spec: TableSpec, frame: pd.DataFrame) -> None:
        """Write through a temporary file and rename it into place.

        Writing straight to the destination leaves a window where the file on
        disk is a truncated parquet. A reader in another process does not get a
        stale table then, it gets an unreadable one, and the run that was meant
        to be resumable is the run that destroyed its own checkpoint.

        This makes a write atomic. It does not make two concurrent writers safe:
        the last rename wins and the other writer's rows are lost. Two harvests
        must not run against one warehouse at the same time.
        """
        final = self.path_for(spec)
        staging = final.with_name(f".{final.name}.{os.getpid()}.tmp")
        try:
            frame.to_parquet(staging, index=False)
            os.replace(staging, final)
        finally:
            if staging.exists():
                staging.unlink()

    def read(self, spec: TableSpec) -> pd.DataFrame:
        path = self.path_for(spec)
        if not path.exists():
            return pd.DataFrame(columns=list(spec.columns))
        frame = pd.read_parquet(path)
        return frame.reindex(columns=list(spec.columns))

    def upsert(self, spec: TableSpec, rows: pd.DataFrame) -> int:
        if rows.empty:
            return 0
        missing = [column for column in spec.columns if column not in rows.columns]
        if missing:
            raise ValueError(f"{spec.name} is missing columns: {missing}")
        incoming = rows.loc[:, list(spec.columns)].copy()
        key = list(spec.natural_key)
        if incoming[key].isna().any().any():
            raise ValueError(f"{spec.name} has a null in the natural key {key}")
        existing = self.read(spec)
        if existing.empty:
            combined = incoming
        else:
            existing = existing.set_index(key, drop=False)
            incoming_idx = incoming.set_index(key, drop=False)
            existing = existing.drop(index=incoming_idx.index, errors="ignore")
            kept = existing.reset_index(drop=True)
            # A column that is entirely null on one side has no dtype of its own to
            # contribute. Borrowing the other side's dtype keeps a numeric column
            # numeric instead of letting it widen to object.
            for column in incoming.columns:
                if column not in kept.columns:
                    continue
                if incoming[column].isna().all() and not kept[column].isna().all():
                    incoming[column] = incoming[column].astype(kept[column].dtype)
                elif kept[column].isna().all() and not incoming[column].isna().all():
                    kept[column] = kept[column].astype(incoming[column].dtype)
            combined = incoming if kept.empty else pd.concat([kept, incoming], ignore_index=True)
        self._write(spec, combined)
        return len(incoming)

    def replace(self, spec: TableSpec, rows: pd.DataFrame) -> int:
        """Overwrite a derived table. Snapshot and study seeds are not upserts."""
        incoming = rows.reindex(columns=list(spec.columns))
        self._write(spec, incoming)
        return len(incoming)

    def create_empty_tables(self) -> None:
        for spec in TABLE_SPECS:
            if not self.path_for(spec).exists():
                self._write(spec, pd.DataFrame(columns=list(spec.columns)))
