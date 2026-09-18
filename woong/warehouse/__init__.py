"""Canonical warehouse tables and the parquet store.

Refuses to hold an upstream provider name, a picture URL, or a computed metric.
Fetching lives in `woong.ingest`.
"""

from woong.warehouse.schema import TABLE_SPECS, TableSpec
from woong.warehouse.store import Warehouse

__all__ = ["TABLE_SPECS", "TableSpec", "Warehouse"]
