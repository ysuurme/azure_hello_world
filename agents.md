# Sentinel Technical Reference (agents.md)

This file serves as a reference log capturing the extensive architectural context, personal learning goals, and design philosophy discussed during the creation of the Azure Architecture Sentinel. It ensures future Agent sessions understand the complex rationale behind the codebase.

## Future Session Operating Instructions
1. **Always read the `README.md`** for context when starting a new session.
2. **Always read the `implementation_plan.md`**. When explicit new instructions are received, update the `implementation_plan.md` or add relevant details to it.
3. **After implementing any steps, always update `task.md`** to track progress accurately.

## Personal Learning Goals
1. **Master Agentic Workflows**: Move past functional programming toward building non-deterministic, reasoning-based AI systems via Azure AI Foundry.
2. **Understanding Context-Aware Search**: Move past basic RAG into multi-query planning. Use Semantic Rankers alongside Hybrid Vector/BM25 retrievals via Azure AI Search (`knowledge_base_retrieve`).
3. **IaC and Managed Identities**: Deepen proficiency with Terraform, specifically configuring connections governed by Entra ID (`authType = "ProjectManagedIdentity"`) and understanding underlying requirements like the `capability_host` for AI Hub execution.
4. **Agent Observability**: Track AI reasoning traces using Azure Application Insights explicitly layered onto Foundry Agent Services.

## Architectural Context Provided

### 1. The Sentinel Concept (Technical Design Authority)
The agent acts as a TDA. It operates using a **"Maker-Checker"** loop:
- **Maker**: Formulate proposals retrieving from internal GitHub markdown notes and WAF guidance.
- **Checker**: Critique proposals specifically on "Security" and "Cost."
- **Refinement**: Fallback to "Value" alternatives based on estimated budgets evaluated via live API Tooling.

### 2. Ingestion Pipeline & Identity
The Sentinel uses advanced methods for data processing (`utils/ingestion.py`):
- **Idempotency**: Avoid duplicative compute. Calculate `H(x) = SHA256(Content_{raw} + Metadata_{source})`. Compare against the AI Search Index metadata; only upload/embed if the hash drifts (using `mergeOrUpload`).
- **Document Intelligence**: Use the Azure Document Intelligence (Layout Model) to strictly preserve complex tables (such as architectural comparisons) via structured Markdown, enabling "Document-Aware Recursive Chunking" on natural headers instead of arbitrary 1000-token breaks.

### 3. The Tool Layer ("Cost vs Resiliency")
The Agent is equipped with explicitly defined tools such as `calculate_cost()` located in `utils/tools.py`.
- **Function**: Queries the Azure Retail Prices API.
- **Goal**: Elevates the agent from "Searchbot" to "Financial Architect," directly exposing the real-world financial cost (e.g., $35/mo Front Door) incurred by its WAF resiliency recommendations across a presented "Trade-off Matrix."

### 4. Code & Directory Architecture Standards
- Python logic utilizes **UV** package management inside `.venv`.
- Follows strict **Single Responsibility**, **Object-Oriented Clarity**, and **PEP-8 Meaningful Naming**.
- The `src/` directory rigidly abstracts Trigger boundaries from the business logic encapsulated cleanly within the `utils/` directory. Connections utilize `DefaultAzureCredential` to ensure seamless transition from local `az login` to production environments on Azure Container Apps.
