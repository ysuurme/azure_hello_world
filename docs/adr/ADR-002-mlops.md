---
name: ADR-002-mlops
description: Use when selecting experiment tracking tooling or defining AI model delivery maturity for a machine learning project
applies_to: "project_type: ml"
---

# ADR-002: Experiment Tracking and AI Model Delivery Maturity

> **Applies to:** `project_type: ml` — skip for `application` and `agent` projects.

## Status
Accepted

## Context and Problem Statement

A machine learning project needs experiment tracking, model versioning, and a path to automated continuous training (CT). The choice of tooling and target maturity level determines the operational overhead and the level of automation achievable without significant re-architecture.

Current state: **Level 0** — MLflow logs to a local SQLite database (`data/4_eval/eval_data.db`), training runs via `uv run main.py`, execution is manual. Target: **Google AI Engineering Level 1** — automated CT pipeline, remote tracking server, governed model registry.

## Considered Options

* MLflow (local SQLite → remote tracking server + model registry)
* Weights & Biases (W&B)
* Neptune.ai

## Decision Outcome

Chosen: **MLflow targeting Google MLOps Level 1**, because MLflow is open-source and self-hostable with no SaaS dependency at Level 0, and the Level 0 → Level 1 migration path requires only a tracking URI swap — same instrumentation code throughout.

### Confirmation

* Check `pyproject.toml` — `mlflow` present; W&B or Neptune absent
* Confirm all MLflow runs set `run_name = f"{model_name}_{feature_set}"` — no auto-generated UUIDs
* Verify required params logged per run: `model`, `features`, `target`, `n_train`, `random_seed`, `data_version`
* At Level 1 transition: `MLFLOW_TRACKING_URI` env var points to remote server; local SQLite path no longer referenced in pipeline code

## Pros and Cons of the Options

### MLflow

| | |
|---|---|
| **Good** | Open-source and self-hostable — no SaaS dependency at Level 0 |
| **Good** | Smooth Level 0 → Level 1 migration: same API, swap tracking URI via env var |
| **Good** | Native model registry with `staging` / `production` / `archived` promotion stages |
| **Good** | ONNX integration — `mlflow.onnx.log_model()` for framework-agnostic model artifacts |
| **Bad** | UI is functional but not as polished as W&B or Neptune for experiment comparison |
| **Bad** | Remote tracking server adds infrastructure overhead at Level 1 |

### Weights & Biases (W&B)

| | |
|---|---|
| **Good** | Best-in-class UI for experiment comparison and run visualisation |
| **Good** | SaaS — zero infrastructure overhead |
| **Bad** | Proprietary SaaS — data leaves the environment; self-hosting requires enterprise plan |
| **Bad** | Additional cost at scale |

### Neptune.ai

| | |
|---|---|
| **Good** | Strong metadata management and run comparison |
| **Bad** | Smaller community; less ecosystem integration than MLflow or W&B |
| **Bad** | SaaS-first model — same residency concerns as W&B |
