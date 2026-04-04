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
*Status: Completed. Focus: GitHub-driven development loop, automation scaffolding, governance.*

#### Project Governance Model (Implemented)
- `GEMINI.md`: Thin structural map for Gemini CLI (repository layout, rules, cross-references).
- `agents.md`: Deep architectural context (design philosophy, learning goals, session instructions).
- `Taskfile.yml`: Single source of truth for all automation commands (`task --list`).

#### Automation Infrastructure (Implemented)
- `Taskfile.yml`: Expanded with `dev`, `test`, `lint`, `lint:fix`, `docker:build`, `docker:down`, `sync`, `sync:dry`, `agent:dev`, `agent:listen` tasks. Parameterized `GITHUB_PROJECT` variable for cross-repo reuse.
- `.github/scripts/sync-issues.ps1`: Parses `ISSUES.md` into GitHub Issues (parameterized project name, replaces `sync-todo.ps1`).
- `.github/scripts/agent-listener.ps1`: Two-phase local listener (Refine → Develop) with error recovery. **Temporary architecture** — future target is GitHub Codespaces.
- `.github/workflows/pr-checks.yml`: MVP CI running `ruff check` + `pytest` on every PR to `main`.
- `ISSUES.md`: Agile issue tracking manifest using `ISSUE:…END_ISSUE` block format.

#### Code Quality (Implemented)
- `ruff` added as dev dependency via `uv add --dev ruff`. Configured in `pyproject.toml` with `E, F, I, N, UP` rule sets.

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
- Complete implementation of the **Multi-Stage Rootless Pattern**.
- *Layer 1 (Builder)*: Secures OS packages, utilizes `uv` to build the frozen Python `.venv`.
- *Layer 2 (Runtime)*: Distroless/Slim equivalent execution under `USER appuser`. Stripped of all `curl`/`gpg` risk vectors. Natively exposes Standard Library ping `HEALTHCHECK`.

#### Update Identity Frameworks
- Ensure all connections inside `agent_factory.py`, `ingestion.py`, and `tools.py` explicitly default to `DefaultAzureCredential` from `azure-identity`. This automatically swaps from local `az login` to the Managed System-Assigned Identity of the Azure Container App.

---

### Phase 4: Continuous Evaluation and Refinement
*Status: Pending. Focus: Day-2 Operations and Observability.*

#### `src/utils/evaluation.py`
- Implementing Application Insights tracing wrapped around the Agent Foundry calls to monitor the "Maker-Checker" loop paths.
- Scripts to fine-tune semantic configuration in AI search (e.g., adjusting vector chunk sizes or BM25 coefficients based on observed agent hallucination rates).

## Verification Plan

Because this is an evolving architecture, validation is codified in the deployment layers:
- **Phase 1 Validation:** Local tests confirm the agent's MCP tools calculate costs correctly and `m_log` records semantic reasoning paths.
- **Phase 1.5 Validation:** `task --list` displays all tasks. `task sync:dry` parses `ISSUES.md` correctly. `pr-checks.yml` triggers on PR. Agent listener handles label lifecycle (visible from mobile).
- **Phase 2 Validation:** `terraform apply` succeeds cleanly; the Foundry project is connected to the Search Index via Entra ID without hardcoded secrets.
- **Phase 3 Validation:** ACA URL returns a valid response asserting the Managed Identity natively acts as the Sentinel. Trivy container scans pass successfully.
