# Project Setup: Azure Architecture Sentinel

## Phase 1: Local Development & SpecKit (Completed)
- [x] Rename existing `MyHobbyAgent` to `AdvisorTrigger`
- [x] Implement `src/agents/arch_advisor.py`
- [x] Implement `src/utils/agent_factory.py`
- [x] Implement `src/utils/ingestion.py`
- [x] Implement `src/utils/search_helpers.py`
- [x] Implement `src/utils/tools.py`
- [x] Write Unit Tests

## Phase 1.5: Frontend Validation (MVA) — Completed
- [x] Architecture doc `001_mva_local_setup.md`
- [x] Implement `src/ui/app.py` (Streamlit)
- [x] `.devcontainer/Dockerfile`
- [x] Pytest 5/5 passed

## Dev Environment Modernization — Completed
- [x] Analyze project structure, challenge `.devcontainer`
- [x] Configure workspace interpreter → `.venv/Scripts/python.exe`
- [x] Modify `Dockerfile` (add `PYTHONDONTWRITEBYTECODE`)
- [x] Update `entrypoint.sh` with `--server.runOnSave`
- [x] Create `docker-compose.dev.yml`
- [x] Create `.env.example` and `.env`
- [x] Remove stale `requirements.txt`
- [x] Update `.dockerignore` and `.gitignore`
- [x] Rewrite `README.md` (native + container workflows)
- [x] Create `.agents/workflows/dev.md` and `docker-validate.md`
- [x] Verify: `uv run pytest` passes (5/5 ✓)
- [ ] Verify: Docker live-reload (requires Rancher Desktop — manual)

## Phase 2: Infrastructure Provisioning
- [ ] `infra/main.tf` — AI Search, Capability Host, AI Foundry (Entra ID)
- [ ] VNet and Private endpoints in Terraform

## Phase 3: Containerization & Deployment
- [x] Build `Dockerfile` utilizing UV
- [ ] Enforce `DefaultAzureCredential` across all clients

## Phase 4: Continuous Evaluation
- [ ] Application Insights hooks
- [ ] Semantic Chunking tuning scripts
