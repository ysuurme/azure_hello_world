---
name: ADR-003-observability
description: Use when selecting an observability stack — telemetry instrumentation, tracing, metrics, or data lineage tracking across services or pipelines
applies_to: "all project types"
---

# ADR-003: Observability Stack Selection

> **Applies to:** All project types — instrument every service and agent loop with OTel from day one.

## Status
Accepted

## Context and Problem Statement

Services and pipelines need consistent telemetry (logs, traces, metrics) and data lineage tracking. The choice of observability stack determines vendor portability: a proprietary SDK ties instrumentation to a specific cloud provider, while a vendor-neutral standard decouples instrumentation from the export target and allows the cloud target to change without re-instrumentation.

## Considered Options

* OpenTelemetry (vendor-neutral SDK with pluggable exporters) + OpenLineage for data lineage
* Proprietary cloud SDKs (Azure Application Insights SDK, Google Cloud Logging / Monitoring client)

## Decision Outcome

Chosen: **OpenTelemetry + OpenLineage**, because instrumentation code is written once and exporters are swapped without touching application code. Changing cloud targets (Azure → GCP or vice versa) requires only an exporter swap. OpenLineage (with Marquez as the reference backend) provides data lineage metadata complementary to OTel telemetry.

### Confirmation

* Check service code — no direct `azure-monitor` or `google-cloud-logging` SDK calls in instrumentation paths; all telemetry emitted through the OTel SDK
* Confirm `trace_id` and `span_id` present on all structured log records
* Confirm one span per logical pipeline step — not one root span covering the full run
* Confirm exporter target (`OTEL_EXPORTER_OTLP_ENDPOINT` or equivalent) set via environment variable — no hardcoded endpoints

## Pros and Cons of the Options

### OpenTelemetry

| | |
|---|---|
| **Good** | Vendor-neutral — swap exporters (Azure Monitor, GCP Cloud Monitoring, console) without changing instrumentation |
| **Good** | Industry standard — broad SDK support across languages and frameworks |
| **Good** | Three-pillar correlation: logs, traces, and metrics share a single `trace_id` |
| **Bad** | More initial setup than a proprietary SDK — requires provider, processor, and exporter configuration |
| **Bad** | Auto-instrumentation quality varies across frameworks |

### Proprietary Cloud SDKs

| | |
|---|---|
| **Good** | Minimal setup — one configure call (e.g., `configure_azure_monitor()`) |
| **Good** | Deep integration with cloud-native dashboards out of the box |
| **Bad** | Vendor lock-in — migrating clouds requires re-instrumenting every service |
| **Bad** | Each SDK has a different API — inconsistent patterns when services target different clouds |
