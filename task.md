# Project Setup: Azure Architecture Sentinel

## Phase 1: Local Development & SpecKit (Completed)
- [x] Rename existing `MyHobbyAgent` to `AdvisorTrigger`
- [x] Implement `src/agents/arch_advisor.py`
- [x] Implement `src/utils/agent_factory.py`
- [x] Implement `src/utils/ingestion.py`
- [x] Implement `src/utils/search_helpers.py`
- [x] Implement `src/utils/tools.py`
- [x] Write Unit Tests
- [x] **[Sentinel Audit]** Atomize `calculate_cost` in `tools.py` to `<30 lines`
- [x] **[Sentinel Audit]** Implement Unified Telemetry Facade (`m_log.py`) and delete fragmented `import logging`.

## Phase 1.5: Frontend Validation (MVA) — Completed
- [x] Architecture doc `001_mva_local_setup.md`
- [x] Implement `src/ui/app.py` (Streamlit)
- [x] **[Sentinel Audit]** Flatten Code Geometry in `app.py` via Guard Clauses & Type Hints.
- [x] **[Sentinel Audit]** Implement the Thin Mediator (`api_adapter.py`) to decouple the UI from HTTP operations.

## Dev Environment Modernization — Completed
- [x] Configure workspace interpreter → `.venv/Scripts/python.exe`
- [x] Update `entrypoint.sh` with `exec` to manage container lifecycles securely.
- [x] Create `docker-compose.dev.yml` and `.env`
- [x] Remove stale `requirements.txt` / Configure `pyproject.toml`
- [x] Rewrite `README.md` (Agentic `.agents/skills` framework integration)
- [x] Update `implementation_plan.md` to guarantee structural reproducibility.

## Phase 2: Infrastructure Provisioning
- [ ] `infra/main.tf` — AI Search, Capability Host, AI Foundry (Entra ID)
- [ ] Enforce **Azure Blob Storage** as the locked Terraform remote backend.
- [ ] VNet and Private endpoints (Private Link) in Terraform for PaaS Isolation.
- [ ] Enforce `terraform plan -detailed-exitcode` drift detection CI/CD gates.

## Phase 3: Containerization & Deployment
- [x] Standardize Local Docker tooling around `uv`.
- [x] **[Sentinel Audit]** Rewrite `Dockerfile` to enforce **Multi-Stage Rootless** execution minimizing Blast Radius.
- [x] **[Sentinel Audit]** Implement Standard Library `HEALTHCHECK`.
- [ ] Implement Trivy security scans prior to image registry push.
- [ ] Enforce `DefaultAzureCredential` across all clients to assume ACA Managed Identity.

## Phase 4: Continuous Evaluation
- [ ] Application Insights hooks wrapped around Maker-Checker logic.
- [ ] Semantic Chunking tuning scripts based on hallucination thresholds.
