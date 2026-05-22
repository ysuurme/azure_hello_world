# System Context & Domain Glossary

This file serves as the system prompt and architectural glossary for AI agents. Use this document to understand the fundamental architecture, data flow, and codebase topography so you can navigate the repository effectively without exhausting context limits.

## Project Identity

**Azure Architecture Sentinel** — A Technical Design Authority (TDA) agent running on Azure AI Foundry. It ingests requirements against the Azure Well-Architected Framework (WAF), queries a capability RAG repository, and generates architecture documents with D2 diagrams.

## Architectural Context

### 1. The Sentinel Concept (Technical Design Authority)
The agent acts as a TDA. It operates using a **"Maker-Checker"** loop:
- **Maker**: Formulate proposals retrieving from internal GitHub markdown notes and WAF guidance.
- **Checker**: Critique proposals specifically on "Security" and "Cost."
- **Refinement**: Fallback to "Value" alternatives based on estimated budgets evaluated via live API Tooling.

### 2. Ingestion Pipeline & Identity
The Sentinel uses advanced methods for data processing (`src/utils/m_ingest.py`):
- **Idempotency**: Avoids duplicative compute by calculating `H(x) = SHA256(Content_{raw} + Metadata_{source})`. Compares against the AI Search Index metadata; only upload/embed if the hash drifts (using `mergeOrUpload`).
- **Document Intelligence**: Uses the Azure Document Intelligence (Layout Model) to strictly preserve complex tables via structured Markdown, enabling "Document-Aware Recursive Chunking" on natural headers instead of arbitrary 1000-token breaks.

### 3. The Tool Layer ("Cost vs Resiliency")
The Agent is equipped with explicitly defined tools such as `calculate_cost()` located in `src/utils/m_tools.py`.
- **Function**: Queries the Azure Retail Prices API.
- **Goal**: Elevates the agent from "Searchbot" to "Financial Architect," directly exposing the real-world financial cost (e.g., $35/mo Front Door) incurred by its WAF resiliency recommendations across a presented "Trade-off Matrix."

### 4. Code & Directory Architecture Standards
- Python logic utilizes **UV** package management inside `.venv`.
- Follows strict **Single Responsibility**, **Object-Oriented Clarity**, and **PEP-8 Meaningful Naming**.
- The `src/` directory rigidly abstracts Trigger boundaries from the business logic encapsulated cleanly within the `utils/` directory. Connections utilize `DefaultAzureCredential` to ensure seamless transition from local `az login` to production environments on Azure Container Apps.
- **Native Secret Management**: Uses a local vault named 'LocalStore' for secret management.

---

## Codebase Map & Topography

Use this module map to pinpoint the relevant files for your task and avoid loading unnecessary files into context.

### Module Fan-in/Fan-out Summary

| Module | Fan-in | Fan-out | Classification | Purpose / Responsibility |
|--------|--------|---------|----------------|--------------------------|
| `agents.architecture_composer` | 0 | 6 | deep module | Orchestrates capability retrieval, decision-making, and architecture generation. |
| `agents.intake_reviewer` | 0 | 5 | deep module | Refines user intake, extracts requirements, and evaluates feasibility against constraints. |
| `config` | 0 | 1 | deep module | Centralized configuration via pydantic-settings; loads from `.env`. |
| `ui.app` | 0 | 9 | deep module | Streamlit frontend for the Maker-Checker conversation loop. |
| `utils.m_ai_client` | 0 | 4 | deep module | Manages `DefaultAzureCredential` and instantiates connections to Azure AI Foundry models. |
| `utils.m_capability_repo` | 0 | 4 | deep module | Parses markdown/YAML capability records from local storage. |
| `utils.m_diagram_engine` | 0 | 5 | deep module | Bridges Composer markdown to D2 diagram syntax and SVGs. |
| `utils.m_health_check` | 0 | 4 | deep module | Validates environment, credentials, and API readiness. |
| `utils.m_ingest` | 0 | 2 | deep module | Idempotent RAG ingestion pipeline via Azure AI Search. |
| `utils.m_log` | 0 | 4 | deep module | Centralized logging and telemetry wrapping. |
| `utils.m_orchestrator` | 0 | 4 | deep module | The state machine governing Maker-Checker loop transitions. |
| `utils.m_persist_design` | 0 | 4 | deep module | Persists approved markdown and SVG deliverables to the `designs/` directory. |
| `utils.m_search` | 0 | 1 | deep module | Abstraction for executing semantic queries against AI Search. |
| `utils.m_tools` | 0 | 2 | deep module | Function calling capabilities for agents (e.g., `calculate_cost`). |

### Legend

| Term | Meaning |
|------|---------|
| Fan-in  | Number of modules that import this module — high fan-in = wide blast radius |
| Fan-out | Number of modules this module imports |
| Deep module    | Large implementation, small interface — target state |
| Shallow module | Interface ≈ implementation complexity — refactoring trigger |
| High fan-in    | Risk: a change here propagates to many callers |

> **Navigation Tip:** When tasked with modifying business logic, always scope your file reads (`view_file`) exclusively to the target module and its direct dependencies in `src/utils/`. Do not greedily read files outside the blast radius.
