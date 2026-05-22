---
name: ADR-006-agent-observability
description: Use when selecting an agent-specific observability tool for loop replay and failure analysis beyond raw OpenTelemetry spans
applies_to: "project_type: agent"
---

# ADR-006: Agent Observability Tooling

> **Applies to:** `project_type: agent` — extends ADR-003 (OTel baseline) with agent-specific loop replay and failure analysis. Review ADR-003 first.

## Status
Accepted

## Context and Problem Statement

Agent loops emit OpenTelemetry spans (one per iteration) as the primary observability layer. Beyond raw OTel, a dedicated agent visualisation tool enables full loop replay and failure analysis. The decision is which tool to adopt for agent-specific tracing.

## Considered Options

* Vertex AI Service Runtime (GCP-native)
* LangSmith

## Decision Outcome

Chosen: **Context-dependent** — see decision drivers below.

**Choose Vertex AI Service Runtime when:** agents are deployed on GCP and Gemini is the primary LLM provider.
**Choose LangSmith when:** provider-agnostic observability is needed, or the codebase uses LangChain patterns.

Both are compatible with the OTel span emission pattern in `agentic-engineering`. General OTel setup follows `harness`.

### Confirmation

* Confirm chosen tool matches the deployment target (GCP vs provider-agnostic)
* Confirm OTel spans are emitted per loop iteration regardless of which visualisation tool is chosen — OTel is not replaced by the visualisation layer
* Confirm no LangChain dependency is introduced if LangSmith is adopted only for its tracing UI

## Pros and Cons of the Options

### Vertex AI Service Runtime

| | |
|---|---|
| **Good** | GCP-native — zero additional infrastructure if already on GCP |
| **Good** | Integrated with Gemini API for full end-to-end agent tracing |
| **Bad** | GCP lock-in — not portable to other providers |
| **Bad** | Limited to Vertex AI-deployed agents |

### LangSmith

| | |
|---|---|
| **Good** | Provider-agnostic — works with Claude, Gemini, OpenAI |
| **Good** | Full loop replay, prompt versioning, evaluation datasets |
| **Good** | Integrates with the LangChain ecosystem |
| **Bad** | Additional SaaS dependency |
| **Bad** | LangChain coupling if using LangSmith's native integrations rather than the OTel bridge |
