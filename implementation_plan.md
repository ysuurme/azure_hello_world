# Project Roadmap & Implementation Plan

The objective is to architect and deploy the "**Azure Architecture Sentinel**" - an "Architect's Architect" Technical Design Authority (TDA) Agent on Azure Container Apps (ACA). 

This system leverages **Azure AI Search** as the vector store alongside the **Azure AI Foundry Agent Service**. The project is structured into targeted learning phases, governed by the stringent `.agents/skills` framework (Clean Architecture, Rootless Containers, Maker-Checker Loops).

## Reproducibility Guidelines
To successfully reproduce and extend this architecture, developers or AI Agents must execute a "Full Project Sentinel Audit" against the codebase using the three core protocols:
1. `review-code.md`: Ensure all new Python scripts adhere to the $<30$-line limit, 2-level indentation max, and utilize the Unified Telemetry facade (`m_log.py`).
2. `design-architecture.md`: Ensure the Domain Model does not leak into the UI Adapters.
3. `design-infrastructure.md`: Ensure any new container definitions use Multi-Stage builders and Trivy scans.

---

## Proposed Changes: Implementation Roadmap

### Phase 1: Local Development and "SpecKit" 
*Status: Completed. Focus: Agent logic, tooling, boundary enforcement.*

#### `src/agents/arch_advisor.py` (Implemented)
- *Object-Oriented Clarity*: `class ArchitectureAdvisorAgent` manages the state of the TDA.
- *Context-Aware Query Planning:* The core system prompt explicitly enforces a **"Maker-Checker" loop**. The agent is instructed to prioritize internal docs via the `knowledge_base_retrieve` tool, critique against WAF "Security/Cost" pillars, and selectively trigger `calculate_cost`.

#### `src/utils/m_log.py` (Implemented)
- *Unified Telemetry Facade*: Centralized log routing acting as the exclusive observable pipeline. Fragments of native `logging` arrays have been purged.

#### `src/utils/api_adapter.py` & `src/ui/app.py` (Implemented)
- *The Thin Mediator*: Streamlit UI has been stripped of raw HTTP and JSON parsing. It delegates all logic to the structural adapter boundary.

#### `src/utils/tools.py` (Implemented)
- Queries the live **Azure Retail Prices API** using `requests`. Logic was atomized to satisfy Code Geometry constraints.

---

### Phase 1.5: Headless Agentic Ecosystem
*Status: Completed. Focus: GitHub-driven development loop, governance, automation.*

#### Governance (Implemented)
- `GEMINI.md`: Thin structural map consumed by Gemini CLI. Layout, rules, git workflow, agentic dev summary.
- `agents.md`: Deep architecture — design philosophy, learning goals, session operating instructions.
- `Taskfile.yml`: Single command authority. 11 tasks covering dev, test, lint, docker, sync, agent operations.

#### Validated Agent Pipeline (Implemented)
End-to-end flow: `agent:dev` label → listener pickup → refine → `feature/issue-N` branch → Gemini CLI builder → `feat(#N): Title` commit → PR with `Closes #N` → agent self-review on PR → `agent:review` label → human approval → merge → branch auto-deleted.

- **Builder**: Gemini CLI via `task agent:dev ISSUE=N`. Reads issue, follows `GEMINI.md`, implements, validates with `task test && task lint`.
- **Critic**: GitHub Action `pr-checks.yml` runs `ruff check` + `pytest` on every PR to `main`.
- **Plumbing**: `gh` CLI manages labels, branches, PRs, issue comments throughout.

#### Automation Scripts (Implemented)
- `sync-issues.ps1`: Parses `ISSUES.md` `ISSUE:…END_ISSUE` blocks → `gh issue create`. Auto-removes synced issues. Parameterized `$ProjectName`.
- `agent-listener.ps1`: Polls for `agent:dev` issues. Phase A refines raw issues. Phase B creates `feature/issue-N` branch, runs Gemini CLI, commits, creates PR, posts agent self-review, hands off to Review lane.
- `pr-checks.yml`: `ruff check src/ tests/` + `pytest tests/ -v` on every PR to `main`.

#### Code Quality (Implemented)
- `ruff` (dev dependency): E, F, I, N, UP rules. Line length 120. `task lint` / `task lint:fix`.
- `git-workflow` skill: TDD-validated protocol documenting 6 baseline hallucination patterns and their fixes.

---

### Phase 2: Infrastructure Provisioning 
*Status: Pending. Focus: Security, Network mapping, and Terraform Blueprints.*

#### `infra/main.tf`
- Provision `azurerm_search_service` (Basic SKU, Free Semantic Search).
- Add `azapi_resource` (`search_connection`) linking Search to the AI Hub via `authType = "ProjectManagedIdentity"` (Entra ID).
- Introduce the explicit `capability_host` for the Agent Service to execute local MCP/Python tools.
- *Constraint Check*: All deployed pipelines must execute `terraform plan -detailed-exitcode` to catch architectural drift.

---

### Phase 3: Containerization and Deployment
*Status: Completed (Local). Focus: Translating into ACA production environments.*

#### `Dockerfile` (Implemented)
- Multi-Stage Rootless Pattern. Builder layer uses `uv` for frozen `.venv`. Runtime layer runs under `USER appuser` with Standard Library `HEALTHCHECK`.

#### Identity Frameworks
- All Azure SDK clients route through `ClientManager` using `DefaultAzureCredential`. Swaps from local `az login` to ACA Managed Identity automatically.

---

### Phase 4: Continuous Evaluation and Refinement
*Status: Pending. Focus: Day-2 Operations and Observability.*

- Application Insights tracing around Maker-Checker loop via `azure-monitor-opentelemetry`.
- Semantic chunking tuning based on observed hallucination rates (vector chunk sizes, BM25 coefficients).

## Verification Plan

- **Phase 1:** Tests confirm MCP tools calculate costs correctly. `m_log` records semantic reasoning paths.
- **Phase 1.5:** `task --list` shows 11 tasks. `task lint` passes clean. `task sync:dry` parses 4 issues. `agent-listener.ps1` creates `feature/issue-N` branches, commits `feat(#N)`, creates PRs with agent self-review, moves issues to Review lane. `pr-checks.yml` triggers on PR.
- **Phase 2:** `terraform apply` succeeds cleanly. Search Service connected via Entra ID. Zero hardcoded secrets.
- **Phase 3:** ACA URL returns valid response. Trivy scans pass. Managed Identity acts as Sentinel.
