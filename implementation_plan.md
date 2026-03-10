# Goal Description
The objective is to architect and deploy the "**Azure Architecture Sentinel**" - an "Architect's Architect" Technical Design Authority (TDA) Agent on Azure Container Apps (ACA). 

This system leverages **Azure AI Search** as the vector store alongside the **Azure AI Foundry Agent Service**. The project is explicitly structured into four high-level learning phases, allowing for incremental building, testing, and continuous deployment over several weeks.

The design adheres to the provided rules:
1. **Standard Library First**
2. **Object-Oriented Clarity**
3. **Meaningful Naming (PEP 8+)**
4. **Single Responsibility**
5. **Implementation-First Communication Plan Gate** (This document)

## Proposed Changes: Implementation Roadmap

### Phase 1: Local Development and "SpecKit" 
*Status: Completed. Focus: Agent logic, tooling, and ingestion primitives.*

#### `src/agents/arch_advisor.py` (Implemented)
- *Object-Oriented Clarity*: `class ArchitectureAdvisorAgent` manages the state of the TDA.
- *Context-Aware Query Planning:* The core system prompt explicitly enforces a **"Maker-Checker" loop**. The agent is instructed to act as an elite Technical Design Authority, prioritizing internal docs via the `knowledge_base_retrieve` tool, critiquing against WAF "Security/Cost" pillars, and triggering the `calculate_cost` tool to evaluate the layout.
- *Future Improvement*: Hardcode an explicit Fallback route in the prompt if `calculate_cost` API times out.

#### `src/utils/agent_factory.py` (Implemented)
- Boilerplate setting up the `AIProjectClient`.
- *Future Improvement*: In Phase 3, this file needs refactoring to explicitly use `DefaultAzureCredential` from `azure-identity`.

#### `src/utils/ingestion.py` (Implemented)
- Unit tests in `tests/` for `ingestion.py`: (Implemented)
- *Idempotency & Integrity*: Implemented $H(x) = \text{SHA256}(Content_{raw} + Metadata_{source})$ hashing to verify document differences before incurring vector mapping costs.
- Integrates mock connections ready for **Azure Document Intelligence (Layout model)** to extract structured markdown and preserve table cells natively.
- *Future Improvement*: Connect the mock chunks directly into the `azure-search-documents` SDK `upload_documents` push method once TF is applied.

#### `src/utils/search_helpers.py` (Implemented)
- Mocked the `knowledge_base_retrieve` method to prepare for Hybrid Vector + BM25 querying.

#### `src/utils/tools.py` (Implemented)
- *Standard Library First*: Engineered `calculate_cost(resources: list[str])`.
- Queries the live **Azure Retail Prices API** using `requests` to fetch accurate USD consumption estimates and returns a structured "Trade-off Matrix". Includes a static failover dictionary.

#### `src/AdvisorTrigger/__init__.py` (Implemented)
- Cleanly orchestrates the incoming HTTP request directly into the `ArchitectureAdvisorAgent.process_query()`.

---

### Phase 1.5: Frontend Validation (MVA)
*Status: In Progress. Focus: Visualizing the Agent output locally.*

#### [NEW] `src/ui/`
- **Architecture**: Documented in `docs/architectures/local/001_mva_local_setup.md`.
- **Implementation**: A lightweight Streamlit app (`src/ui/app.py`) running within the unified container to validate the end-to-end flow visually.

### Phase 2: Infrastructure Provisioning 
*Focus: Security, Network mapping, and Terraform Enterprise Blueprints.*

#### [MODIFY] `infra/main.tf`
- Provision `azurerm_search_service` (Basic SKU, Free Semantic Search).
- Add `azapi_resource` (`search_connection`) linking Search to the AI Hub via `authType = "ProjectManagedIdentity"` (Entra ID).
- Introduce the explicit `capability_host` for the Agent Service to execute local MCP/Python tools.
- Set up VNet and potentially Private Endpoints if high security is desired for the learning roadmap.

#### [MODIFY] `infra/variables.tf` & `infra/outputs.tf`
- Ensure all resources clearly export their endpoints to pipeline environments.

---

### Phase 3: Containerization and Deployment
*Focus: Translating local code into production-ready Azure Container Apps running on Entra ID.*

#### [NEW] `Dockerfile`
- Standard Python 3.10+ image utilizing UV to map `pyproject.toml` into a containerized runtime.

#### Update Identity Frameworks
- Ensure all connections inside `agent_factory.py`, `ingestion.py`, and `tools.py` explicitly default to `DefaultAzureCredential` from `azure-identity`. This automatically swaps from local `az login` to the Managed Identity of the Azure Container App.

---

### Phase 4: Continuous Evaluation and Refinement
*Focus: Day-2 Operations, observability, and fine-tuning reasoning.*

#### [NEW] `src/utils/evaluation.py`
- Implementing Application Insights tracing wrapped around the Agent Foundry calls to monitor the "Maker-Checker" loop reasoning paths.
- Scripts to fine-tune semantic configuration in AI search (e.g., adjusting vector chunk sizes or BM25 coefficients based on observed agent hallucination rates).

## Verification Plan

Because this is a multi-week initiative, validation occurs per phase:
- **Phase 1 Validation:** Local `uv run pytest` confirms the agent's MCP tools calculate costs correctly and the ingestion pipeline generates idempotent hashes.
- **Phase 2 Validation:** `terraform apply` succeeds cleanly, demonstrating the Foundry project is connected to the Search Index via Entra ID in the portal.
- **Phase 3 Validation:** ACA URL returns a valid response asserting the Managed Identity correctly assumed the role of the Architect Sentinel.
- **Phase 4 Validation:** Telemetry appears natively within Azure Application Insights without complex manual logging overrides.
