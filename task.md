# Project Setup: Azure Architecture Sentinel

## Phase 1: Local Development & SpecKit (Completed)
- [x] Rename existing `MyHobbyAgent` to `AdvisorTrigger`.
- [x] Implement `src/agents/arch_advisor.py` (Maker-Checker prompts, Tool Binding).
- [x] Implement `src/utils/agent_factory.py` (Local Client initialization).
- [x] Implement `src/utils/ingestion.py` (Document ID hashing, Azure Document Intelligence structure).
- [x] Implement `src/utils/search_helpers.py` (`knowledge_base_retrieve` logic).
- [x] Implement `src/utils/tools.py` (Live Azure Retail Prices API logic for `calculate_cost`).
- [x] Write Unit Tests for tools mirroring local expected outputs.

## Phase 2: Infrastructure Provisioning & Environment Setup
- [x] Configure `.devcontainer/devcontainer.json` for reproducible Azure Functions and Terraform execution.
- [ ] Outline `infra/main.tf` logic for AI Search, Capability Host, and AI Foundry connections (Entra ID).
- [ ] Provision VNet and Private endpoints configurations in Terraform.

## Phase 3: Containerization & Deployment
- [ ] Build `Dockerfile` utilizing UV.
- [ ] Enforce `DefaultAzureCredential` across all python connection clients.

## Phase 4: Continuous Evaluation
- [ ] Wrap Foundry calls in Azure Application Insights hooks.
- [ ] Prepare scripts to tune Semantic Chunking heuristics.
