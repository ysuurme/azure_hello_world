---
name: ADR-001-data-science
description: Use when selecting data science tooling — notebook format, EDA library, or ML framework for tabular data
applies_to: "project_type: ml"
---

# ADR-001: Data Science Tooling Selection

> **Applies to:** `project_type: ml` — skip for `application` and `agent` projects.

## Status
Accepted

## Context and Problem Statement

A data science workflow requires tooling for exploratory analysis, model prototyping, and experiment tracking. The choice of notebook format, transformation library, and ML framework has downstream implications for reproducibility, agent-readability, and production handoff quality.

## Considered Options

* Marimo (`.py`) vs Jupyter (`.ipynb`) as notebook format
* Pandas vs Polars as the EDA and prototyping library
* scikit-learn vs PyTorch as the primary ML framework for tabular data

## Decision Outcome

Chosen: **Marimo + Pandas + scikit-learn**, because Marimo notebooks are plain Python files (Git-diffable, agent-readable, `uv run`-compatible), Pandas is optimal for interactive EDA at single-machine scale, and scikit-learn covers the tabular ML use case without heavy framework overhead.

### Confirmation

* Check notebooks directory — all notebooks use `.py` extension and follow the `nb_<purpose>.py` naming convention
* Confirm no inline redefinition of constants from `config.py` inside notebook files
* Confirm `pyproject.toml` — Pandas and scikit-learn present; no direct PyTorch dependency for tabular models
* Review at model handoff — graduation threshold met: runs clean on a fresh environment (`uv run`), validated on a held-out set, results reproducible within ±1% metric variance

## Pros and Cons of the Options

### Marimo (`.py`)

| | |
|---|---|
| **Good** | Plain Python file — Git-diffable, no JSON noise, no merge conflicts on re-executed output cells |
| **Good** | Agent-readable — Claude and Gemini can read and reason about notebook content directly |
| **Good** | Runs headless via `uv run marimo run` — no Jupyter server required |
| **Bad** | Smaller ecosystem than Jupyter — fewer pre-built extensions |
| **Bad** | Less familiar to stakeholders who expect `.ipynb` output |

### Jupyter (`.ipynb`)

| | |
|---|---|
| **Good** | Industry standard — universally familiar; broadest ecosystem support |
| **Good** | Rich inline outputs: plots, widgets, table renderers |
| **Bad** | JSON format — creates noisy Git diffs when cells are re-executed |
| **Bad** | Not importable as a module; agents cannot read cell structure without conversion |
| **Bad** | Requires a Jupyter server; incompatible with `uv run` headless execution |

### Pandas (EDA and prototyping)

| | |
|---|---|
| **Good** | Familiar interactive API — fast to iterate at notebook scale |
| **Good** | Native integration with scikit-learn — no conversion step at model fit time |
| **Bad** | Single-threaded; memory-heavy on large datasets |

### Polars (EDA and prototyping)

| | |
|---|---|
| **Good** | Multi-threaded, Arrow-native — fast on large datasets |
| **Bad** | Less natural for interactive exploration; lazy evaluation API requires planning ahead |
| **Bad** | Requires explicit `.to_pandas()` conversion for scikit-learn |
