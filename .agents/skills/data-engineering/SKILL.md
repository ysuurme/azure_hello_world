---
name: data-engineering
description: Use when designing or implementing data pipelines, structuring Medallion architecture tiers, defining data quality gates, schema validation with Pydantic, writing SQLAlchemy or Polars transformations, configuring DuckLake storage, or building feature pipelines for ML consumption
---

# Data Engineering

## Overview

ELT pipelines following a Mini-Medallion architecture (Raw → Bronze → Silver → Gold). Two storage backends: **SQLite + SQLAlchemy** for local/prototype; **DuckLake (PostgreSQL catalog + Parquet + DuckDB)** for production scale. **Polars** is the default transformation library. Primary output: Gold tables or Parquet datasets that are ML-ready, null-free, and correctly shaped.

**Primary artifact:** Validated, query-ready datasets produced by a layered Medallion pipeline.

## Scope

**Owns:** ELT pipeline design and implementation, Medallion tier definitions and boundaries, SQLAlchemy Core (Bronze bulk inserts) and ORM (Silver/Gold transformations), Polars for pipeline data transformations, DuckLake storage backend configuration, storage backend selection (SQLite vs DuckLake), Pydantic boundary validation (the Sandwich), upsert logic, data quality gates, schema contracts, feature pipeline implementation (computing features at scale — not designing them), lineage event emission from pipeline steps (OpenLineage).

**Does not own:** Feature design — which features to compute and why (→ `refine`), model training pipelines (→ `agentic-engineering`), general telemetry instrumentation (→ `harness`).

**Interfaces with:** `refine` — feature requirements and domain boundaries are specified there; data-engineering implements the Gold pipeline against those specs. `tdd` — integration tests for each pipeline stage drive the RED phase. `application-engineering` — Gold tables / Parquet datasets are the contract for downstream APIs.

## When to Use

- **Trigger:** Designing or building any layer of the Medallion pipeline
- **Trigger:** Writing SQLAlchemy models, Core inserts, or ORM transformations
- **Trigger:** Writing Polars transformation logic for pipeline stages
- **Trigger:** Configuring or querying a DuckLake storage backend
- **Trigger:** Deciding storage backend — SQLite vs DuckLake
- **Trigger:** Adding or modifying data quality gates or schema validation
- **Trigger:** Implementing a feature pipeline from a `refine` specification

**Do NOT use for:**
- Deciding which features to engineer (→ `refine`)
- Model training pipelines (→ `agentic-engineering`)

## Required Inputs

- Feature specification from `refine` (which features to compute and why)
- Source data schema (raw input format)
- Storage backend decision (SQLite vs DuckLake)
- Acceptance criteria from Lean PRD testing decisions (from `plan`)

## Primary Outputs

- Medallion pipeline (Raw → Bronze → Silver → Gold)
- SQLAlchemy models and Polars transformation functions
- Data quality gate checks (row count, type contract, Zero-Null policy)
- Integration tests covering each pipeline stage output

## tdd REFACTOR Phase Patterns

When the GREEN phase is complete, extend the REFACTOR phase with these data-engineering patterns:

- **Medallion boundary enforcement:** Each tier function must read only from the tier below and write only to its own tier. If Bronze logic appears in Silver, extract it back to Bronze.
- **Polars over Pandas:** If Pandas appears in pipeline code after GREEN, replace with Polars equivalents. Exception: boundary conversion for downstream libraries that strictly require `pd.DataFrame`.
- **Pydantic Sandwich tightening:** All data entering a SQLAlchemy session or Polars write must pass through a Pydantic model. If raw dict access appears after GREEN, extract a validator.
- **Zero-Null gate completeness:** The Gold layer must enforce null-free output. If `test_gold_no_nulls` passes but the interpolation logic is fragile, refactor the interpolation to be explicit and idempotent.
- **Upsert idempotency:** Bronze upsert logic must be safe to run multiple times on the same source file. If the test suite doesn't cover duplicate ingestion, add a test and fix the logic if it fails.
- **Lineage event coverage:** Every pipeline stage boundary should emit an OpenLineage event. If missing after GREEN, add it in REFACTOR.

---

## Core Pattern

### Medallion Architecture (ELT)

Load first, transform in-place. Never write intermediate files to disk — all state lives in the database or object storage.

**Raw** — Source Zone
- Local files exactly as received — source of truth for reprocessing
- Excluded from version control (`.gitignore`)
- No transformation — read-only input layer

**Bronze** — Landing Zone
- Technology: **SQLAlchemy Core** (bulk inserts, speed-optimised)
- Structure: Star Schema — Fact tables + Dimension tables
- Upsert logic: process only new files in Raw; never reprocess the entire dataset

**Silver** — Clean Zone
- Technology: **SQLAlchemy ORM** (complex joins) or **Polars** (large-scale transformation)
- Flatten nested structures, cast types, standardise strings
- JOIN Fact + Dimension tables to replace codes with human-readable values

**Gold** — ML Zone
- Technology: **SQLAlchemy ORM** (SQLite backend) or **Polars → Parquet** (DuckLake backend)
- **Target datasets (Fact):** preserve composite key (e.g., `Quarter + Branch`) — **NEVER pivot**
- **Feature datasets (Dimension):** pivot/flatten to exactly 1 row per `Quarter` for clean `LEFT JOIN`
- Zero-Null policy: enforce via interpolation before the ML handoff gate

### Polars as Default Processing Library

```python
import polars as pl

# ✅ Polars pipeline transformation
df = pl.read_database("SELECT * FROM silver_sick_leave", connection)
df_gold = (
    df
    .filter(pl.col("value").is_not_null())
    .with_columns(pl.col("period").str.to_date())
    .group_by("quarter", "branch")
    .agg(pl.col("value").mean().alias("avg_value"))
)
df_gold.write_parquet("data/gold/sick_leave/2024Q1.parquet")

# ❌ Pandas in pipelines — single-threaded, eager, memory-heavy
import pandas as pd
```

Exception: Pandas is acceptable as a boundary conversion when a downstream library strictly requires `pd.DataFrame`. Convert at the boundary: `df.to_pandas()`.

### The Pydantic Sandwich

Validate at the boundary — before data touches a SQLAlchemy session or Polars write. Use **SQLModel** (unifies SQLAlchemy + Pydantic in one class) when validation and storage shapes are identical.

```python
from sqlmodel import SQLModel, Field, Session

class SickLeaveRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    period: str = Field(pattern=r'^\d{4}Q[1-4]$')
    value: float

record = SickLeaveRecord.model_validate(raw_data)  # Raises ValidationError if invalid
with Session(engine) as session:
    session.add(record)
    session.commit()
```

Use separate `Pydantic(BaseModel)` + `SQLAlchemy(Base)` only when the validation and storage shapes genuinely diverge between tiers.

## Quick Reference

### Technology Tiers

#### Must-Have (Every Project)

| Task | Tool |
|---|---|
| Dependency management | `uv` |
| Pipeline transformation | `polars` |
| ORM / SQL abstraction | SQLAlchemy Core (Bronze) + ORM (Silver/Gold) |
| Boundary validation | Pydantic (Sandwich / SQLModel) |
| Data lake query engine | `duckdb` |
| Storage backend | SQLite (local/prototype) |
| Architecture | Medallion (Raw → Bronze → Silver → Gold) |

#### Optional (Mature / Production Setup)

| Tool | Adopt when |
|---|---|
| **DuckLake** | Production data lake with multi-consumer access (PostgreSQL catalog + Parquet) |
| **PySpark** | Data exceeds single-machine capacity; Databricks environment |
| **Dagster** | Mature orchestration with Software-Defined Assets, built-in lineage, scheduling |
| **OpenLineage + Marquez** | Data lineage tracking at scale across pipeline stages |
| **dbt** | Team is strongly SQL-heavy and Python transformations are not preferred |

### Storage Backend Selection

| Backend | When | Catalog | Storage | Query |
|---|---|---|---|---|
| SQLite + SQLAlchemy | Local dev, prototype, portable | Embedded `.db` | `.db` file | SQLAlchemy / DuckDB |
| DuckLake | Production scale, cloud, multi-consumer | PostgreSQL | Parquet on object storage | DuckDB |

### SQLAlchemy API Selection

| Tier | API | Reason |
|---|---|---|
| Bronze | Core | Bulk inserts, speed-critical |
| Silver | ORM or Polars | ORM for joins; Polars for large-scale transformation |
| Gold | ORM or Polars → Parquet | ORM for SQLite backend; Polars for DuckLake backend |

### Medallion Tier Responsibilities

| Tier | Transformation | Quality Gate |
|---|---|---|
| Raw | None | None — source of truth |
| Bronze | None — load only (Star Schema) | Upsert deduplication |
| Silver | Flatten, cast types, JOIN, standardise | Type contract compliance |
| Gold | Feature engineering, pivot rules, interpolation | Zero-Null policy, ML shape contract |

### Pipeline Entrypoint Pattern

```bash
uv run main.py                 # ML pipeline only — runs on existing Gold tables
uv run main.py --refresh-data  # Full pipeline — Raw → Gold → ML
```

## Implementation

### Project Structure

```
src/
  data_engineering/     # Medallion pipeline (Raw, Bronze, Silver, Gold)
  utils/                # Shared SQLAlchemy session handlers, DB utilities
  config.py             # Pipeline configuration (metrics enabled, paths, backend)
data/
  0_Raw/                # Source files — excluded from Git
  *.db                  # SQLite databases — excluded from Git
  gold/                 # Parquet files (DuckLake backend) — excluded from Git
```

### DuckLake Setup and Usage

```python
import duckdb
import polars as pl

conn = duckdb.connect()
conn.execute("INSTALL ducklake; LOAD ducklake;")
conn.execute("""
    ATTACH 'ducklake:postgresql://user:pass@host/catalog_db'
    AS lake (DATA_PATH 's3://bucket/data/')
""")

df_gold.write_parquet("s3://bucket/data/gold/sick_leave/2024Q1.parquet")
result = conn.execute("SELECT * FROM lake.gold.sick_leave").pl()
```

### Upsert Pattern (Bronze / SQLite)

```python
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

stmt = sqlite_insert(BronzeTable).values(records)
stmt = stmt.on_conflict_do_nothing(index_elements=["source_file", "record_id"])
session.execute(stmt)
session.commit()
```

### Gold Layer Shape Rules

1. **Target tables:** rows indexed on composite key `(Quarter, Branch)` — one row per prediction unit
2. **Feature tables:** rows indexed on `(Quarter,)` — exactly one row per time period
3. **Structural join:** `LEFT JOIN feature ON target.quarter = feature.quarter`
4. **Zero-Null gate:** run interpolation before exposing Gold to downstream — no nulls may pass

### Data Lineage (OpenLineage)

Emit OpenLineage events from each Medallion tier for machine-readable lineage:

```python
from openlineage.client import OpenLineageClient, RunEvent, RunState

client = OpenLineageClient.from_environment()
client.emit(RunEvent(
    eventType=RunState.COMPLETE,
    job=Job(namespace="pipeline", name="silver_transformation"),
    inputs=[Dataset(namespace="sqlite", name="bronze_sick_leave")],
    outputs=[Dataset(namespace="sqlite", name="silver_sick_leave")],
))
```

Compatible with OpenMetadata, Apache Atlas, and Marquez.

### Integration Testing for ETL Pipelines

Integration tests — not unit tests — are the primary test type. Test the output of each stage, not the transformation logic.

```python
def test_silver_row_count(session: Session) -> None:
    count = session.execute(select(func.count()).select_from(SilverSickLeave)).scalar()
    assert count > 0

def test_gold_no_nulls(session: Session) -> None:
    nulls = session.execute(
        select(func.count()).select_from(GoldSickLeave).where(GoldSickLeave.avg_value.is_(None))
    ).scalar()
    assert nulls == 0, "Gold Zero-Null policy violated"
```

Standard checks per stage: row count, unique IDs, date range, Zero-Null (Gold only).

## Common Mistakes

**Using Pandas for pipeline transformations.**
Pandas is not used in data-engineering pipelines. Polars is the default. The only exception is a boundary conversion when a downstream library strictly requires `pd.DataFrame`.

**Using SQLAlchemy ORM at Bronze for bulk inserts.**
ORM overhead is unnecessary at the loading stage. Use SQLAlchemy Core for Bronze.

**Validating data inside SQLAlchemy models.**
`@validates` fires at flush time. Use the Pydantic Sandwich: validate at the boundary, store with SQLAlchemy.

**Pivoting target (Fact) tables in Gold.**
Target datasets must preserve the composite key. Pivoting creates Cartesian explosions.

**Writing intermediate files to disk.**
Zero-Artifact policy is absolute. State lives in the database or registered Parquet files. No temporary CSVs or JSONs between tiers.

**Running `python` directly instead of `uv run`.**
Always use `uv run` — correct environment and interpreter are guaranteed.

**Reprocessing all Raw files on every pipeline run.**
Upsert logic exists to prevent this. Processing only new files is a core efficiency constraint.
