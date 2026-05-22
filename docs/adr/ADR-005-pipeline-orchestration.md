---
name: ADR-005-pipeline-orchestration
description: Use when evaluating data pipeline orchestration beyond a script entrypoint — scheduling, declarative asset management, partitioned backfills, or built-in lineage requirements
applies_to: "project_type: ml, project_type: agent (data-intensive)"
---

# ADR-005: Data Pipeline Orchestration

> **Applies to:** `project_type: ml` (Medallion pipelines) and `project_type: agent` when the agent consumes or produces structured datasets requiring scheduling or lineage. Not applicable to `project_type: application`.

## Status
Proposed

## Context and Problem Statement

The default Medallion pipeline runs via a simple script entrypoint (`uv run main.py`). As the number of pipelines grows, the need for declarative asset management, built-in lineage, partitioning, and scheduling becomes apparent. The decision is whether and when to adopt a dedicated orchestration framework.

## Considered Options

* Dagster (Software-Defined Assets)
* Airflow
* dbt (SQL-centric teams)

## Decision Outcome

Chosen: **Dagster when adoption criteria are met** — adopt when multiple Medallion pipelines are in production, partitioned backfills are needed, or observability into asset staleness is a primary concern.

**Choose Dagster when:** multiple Medallion pipelines are in production, partitioned backfills are needed, or observability into asset staleness is a primary concern.

```python
from dagster import asset, AssetIn
import polars as pl

@asset
def bronze_sick_leave(context) -> pl.DataFrame:
    return load_raw_files(RAW_PATH)

@asset(ins={"bronze": AssetIn("bronze_sick_leave")})
def silver_sick_leave(bronze: pl.DataFrame) -> pl.DataFrame:
    return transform_to_silver(bronze)

@asset(ins={"silver": AssetIn("silver_sick_leave")})
def gold_sick_leave(silver: pl.DataFrame) -> pl.DataFrame:
    return build_gold(silver)
```

### Confirmation

* Confirm adoption criteria are met before introducing Dagster: multiple production pipelines, or backfill/scheduling requirements that the script entrypoint cannot satisfy
* Confirm each Medallion tier is declared as a Dagster asset — no raw `uv run` entrypoints bypassing the asset graph
* Confirm `uv run main.py` is replaced or wrapped by the Dagster job entrypoint after adoption
* Confirm dbt models, if present, are declared as Dagster assets rather than run separately

## Pros and Cons of the Options

### Dagster (Software-Defined Assets)

| | |
|---|---|
| **Good** | Declarative assets — asset dependency graph IS the lineage graph; no separate OpenLineage emission needed |
| **Good** | Built-in partitioning and backfills — time-partitioned assets are first-class |
| **Good** | Python-native — same language as the rest of the stack |
| **Good** | Environment agnosticism — same asset definitions run in dev and production |
| **Bad** | Significant complexity overhead for simple pipelines |
| **Bad** | Adoption requires restructuring pipeline code into asset definitions |

### Airflow

| | |
|---|---|
| **Good** | Broad ecosystem — supports multi-system orchestration |
| **Bad** | Task-centric, not asset-centric — no built-in lineage |
| **Bad** | Heavier infrastructure footprint |

### dbt

| | |
|---|---|
| **Good** | Natural for SQL-centric teams |
| **Bad** | SQL-only — limits expressiveness for complex Python transformations |
