---
name: ADR_STRUCTURE
description: Master index of all Architecture Decision Records — load this at session start to filter which ADRs apply to the current project_type without reading every file
---

# ADR Structure

Master index for all Architecture Decision Records in this project. Load this file at session
start instead of reading individual ADRs. Use the **Applies To** column to filter which ADRs are
relevant to the current `project_type`. Load the full ADR only when you need the rationale,
full option analysis, or confirmation checklist.

---

## How to Use

1. Read this index at session start alongside `CONTEXT.md` and `AGENTS.md`.
2. Filter by **Applies To** — skip ADRs that do not match the current `project_type`.
3. Load the individual ADR file only when you need the full context, considered options, or
   confirmation steps.
4. When making a decision that contradicts or extends an existing ADR, load the full ADR before
   proposing a change.

**Maintenance:** Updated by `ship` after every ADR merge. When adding a new ADR, add a row here
at the same time — never merge an ADR without a corresponding index update.

---

## Index

| ADR | Title | Status | Applies To | Decision |
|---|---|---|---|---|
| [ADR-000](ADR-000-template-architecture-decision.md) | Template Architecture Decision | Template | all | MADR format — use this template for every new ADR in this project |
| [ADR-001](ADR-001-data-science.md) | Data Science Tooling Selection | Accepted | `project_type: ml` | Marimo (`.py`) + Pandas + scikit-learn — Git-diffable notebooks, interactive EDA, tabular ML |
| [ADR-002](ADR-002-mlops.md) | Experiment Tracking and AI Model Delivery Maturity | Accepted | `project_type: ml` | MLflow targeting Google AI Engineering Level 1 — self-hostable, tracking URI swap for Level 0→1 migration |
| [ADR-003](ADR-003-observability.md) | Observability Stack Selection | Accepted | all | OpenTelemetry + OpenLineage — no proprietary cloud SDK in instrumentation paths; exporter target via env var |
| [ADR-004](ADR-004-iam-provider-selection.md) | IAM Provider Selection | Proposed | `project_type: application`, `project_type: agent` | Keycloak (internal employees / LDAP) or Zitadel (external customers / B2B) — context-dependent; FastAPI via `OAuth2AuthorizationCodeBearer` |
| [ADR-005](ADR-005-pipeline-orchestration.md) | Data Pipeline Orchestration | Proposed | `project_type: ml`, `project_type: agent` (data-intensive) | Dagster (Software-Defined Assets) when multiple production pipelines or backfill requirements emerge — not applicable to `application` |
| [ADR-006](ADR-006-agent-observability.md) | Agent Observability Tooling | Accepted | `project_type: agent` | Vertex AI Service Runtime (GCP + Gemini) or LangSmith (provider-agnostic) — context-dependent; extends ADR-003, does not replace OTel span emission |
| [ADR-007](ADR-007-project-type-selection.md) | Project Type Selection | Accepted | all | `{{ project_type }}` — determines relevant domain ADRs and the domain skill to invoke during `tdd` REFACTOR |
| [ADR-008](ADR-008-secrets-management.md) | Secrets Management | Accepted | all | GitHub Secrets for dev/CI; Azure Key Vault (corporate) / GCP Secret Manager (personal) for production |
| [ADR-009](ADR-009-context-strategy.md) | Context Strategy | Accepted | all | Module Map + Issue-Type Index in CONTEXT.md, Context Protocol in AGENTS.md, blocking ship gate on Module Map updates |
| [ADR-010](ADR-010-workflow-dispatcher.md) | Workflow Dispatcher Architecture | Accepted | `project_type: application`, `project_type: agent` | Slash-command dispatcher routes the main chat to capability modules; existing AgenticOrchestrator extracted as `DesignArchitectureModule` |
| [ADR-011](ADR-011-diagram-studio-sketch.md) | Diagram Studio Module with Native D2 Sketch Rendering | Accepted | `project_type: application`, `project_type: agent` | First capability module — refine-pattern grill loop produces a DiagramBrief; sketch enforced via `--sketch` at engine level; persist brief + D2 + SVG trio |
| [ADR-012](ADR-012-fastapi-backend.md) | Adopt FastAPI for the Application Backend | Accepted | `project_type: application` | FastAPI + Uvicorn — request validation, auto OpenAPI schema, async-native; supersedes stdlib-only rejection scoped to hello-world starter |

---

## Project-Type Quick Filter

Use this to determine which ADRs to load at session start. ADR-000 is always a template
reference — load it only when creating a new ADR.

### `project_type: application` (default)
Load: **ADR-003**, **ADR-004**, **ADR-007**, **ADR-008**, **ADR-009**, **ADR-010**, **ADR-011**, **ADR-012**

### `project_type: agent`
Load: **ADR-003**, **ADR-004**, **ADR-006**, **ADR-007**, **ADR-008**, **ADR-009**, **ADR-010**, **ADR-011**

### `project_type: ml`
Load: **ADR-001**, **ADR-002**, **ADR-003**, **ADR-005**, **ADR-007**, **ADR-008**, **ADR-009**
