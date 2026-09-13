---
name: woong-ingest
description: Build or change a Woong ingest pipe. Use when harvesting data into the warehouse, adding an endpoint, fixing a resumable harvest, or handling rate limits, checkpoints and idempotent upserts.
---

# Ingest

An ingest module fetches and stores. It computes nothing.

## Order of work

1. Write the raw payload to `data/raw/<pipe>/<endpoint>/<fetch-date>/` exactly as
   received. A parse bug must never cost a re-fetch.
2. Parse into the canonical table with Woong column names and a generic
   `source` tag.
3. Upsert on the natural key.
4. Update the checkpoint in `ingest_jobs`.

## Checkpointing

Every pipe writes one `ingest_jobs` row per endpoint holding a watermark, a
cursor and the last error.

- Checkpoint after each symbol or page, not at the end of the run.
- On start, read the checkpoint and skip completed work.
- A crash resumes. It never restarts the harvest.

## Idempotence

Upsert on the natural key so a second run adds nothing. State the natural key in
the module docstring.

## Coverage

Harvest the full symbol master and every index. Nulls are fine. A symbol missing
because ingest never asked is not fine, because nothing downstream can tell that
apart from a symbol with no data.

## Failure

- Bound retries, with a delay that grows. Respect rate limits.
- Collect failures, print them at the end, exit non-zero.
- Never return an empty result on error. A run that half-worked must not look
  like a run that worked.

## Forbidden

- Computing a metric here.
- Naming a provider anywhere, including log lines and raw directory names.
- Hard-coding a base URL or token. Read `woong/config.py`.
- Re-downloading data already on disk. Check the store first.
