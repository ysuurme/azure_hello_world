# Project Setup: Azure Architecture Sentinel

## Phase 1: Local Development & SpecKit — Completed
- [x] `src/agents/arch_advisor.py` — TDA agent with Maker-Checker loop
- [x] `src/utils/` — agent factory, ingestion, search, tools, logging
- [x] Unit tests covering cost calculation and telemetry paths
- [x] Sentinel Audit: atomized `calculate_cost` (<30 lines), unified `m_log.py`

## Phase 1.5a: Frontend Validation (MVA) — Completed
- [x] `src/ui/app.py` — Streamlit with Guard Clauses, Thin Mediator (`api_adapter.py`)
- [x] Dev environment: `docker-compose.dev.yml`, `pyproject.toml`, workspace interpreter

## Phase 1.5b: Headless Agentic Ecosystem — Completed
- [x] `GEMINI.md` — structural map (layout, rules, git workflow, agentic dev)
- [x] `Taskfile.yml` — 11 tasks: dev, test, lint, lint:fix, docker:build/down, sync/sync:dry, agent:dev/listen, status
- [x] `ruff` — E, F, I, N, UP rules, line-length 120, lint passes clean (0 errors)
- [x] `ISSUES.md` — 4 seed issues, ISSUE/END_ISSUE block format
- [x] `sync-issues.ps1` — parameterized project name, auto-removes synced issues
- [x] `agent-listener.ps1` — two-phase Refine → Develop, validated workflow:
  - `feature/issue-N` branches, `feat(#N): Title` commits
  - Gemini CLI builder, agent self-review on PR
  - `agent:review` label handoff, `@hello_architect` project routing
- [x] `pr-checks.yml` — ruff + pytest on every PR to main
- [x] `git-workflow` skill — TDD-validated, 6 baseline hallucination patterns documented
- [x] Deleted `.agents/workflows/` (Taskfile subsumes), `sync-todo.ps1` (replaced)
- [x] README.md — full validated workflow diagram, governance table

## Phase 2: Infrastructure Provisioning
- [ ] `infra/main.tf` — AI Search (Basic SKU), Capability Host, AI Foundry (Entra ID)
- [ ] Terraform remote backend on Azure Blob Storage
- [ ] VNet + Private Link for PaaS isolation
- [ ] `terraform plan -detailed-exitcode` drift detection in CI

## Phase 3: Containerization & Deployment
- [x] Multi-Stage Rootless Dockerfile, Standard Library HEALTHCHECK
- [ ] Trivy security scans gating image push
- [ ] `DefaultAzureCredential` audit across all SDK clients

## Phase 4: Continuous Evaluation
- [ ] Application Insights via `azure-monitor-opentelemetry` on Maker-Checker loop
- [ ] Semantic chunking tuning (vector sizes, BM25 coefficients)

## Pending Manual Actions
- [x] Run `gh repo edit --delete-branch-on-merge` to enable auto-branch cleanup
