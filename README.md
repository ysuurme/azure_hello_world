# Azure Architecture Agent

The **Azure Architecture Agent** is a Technical Design Authority (TDA) Agent. It moves past simple "Chat-over-PDF" patterns into Agentic Retrieval-Augmented Generation (RAG). The system actively reasons across the Microsoft Well-Architected Framework (WAF) and private repository notes to balance structural resiliency with cost-efficiency.

## Project Structure & Focus
This project utilizes **Azure AI Foundry** (for Agent Orchestration) and **Azure AI Search** (for Vector Store tracking). It serves as a multi-week roadmap aimed at mastering the transition from deterministic procedural logic to the non-deterministic reasoning flows of the 2026 AI-native ecosystem.

### Implementation Roadmap
1. **Phase 1: Local Development and "SpecKit"**
   - Focus: Python utilities, Tool definition (Cost APIs), Ingestion pipelines, Maker-Checker prompts.
2. **Phase 2: Infrastructure Provisioning**
   - Focus: Terraform integration, Entra ID Managed Identities, AI Search & Hub linkages via `azapi`.
3. **Phase 3: Containerization and Deployment**
   - Focus: Dockerizing Python with UV, deploying to Azure Container Apps (ACA) using `DefaultAzureCredential`.
4. **Phase 4: Continuous Evaluation and Refinement**
   - Focus: Application Insights telemetry, tuning Semantic Chunking logic, managing agent evaluation accuracy.

## Key Technical Decisions
- **Standard Library First**: Logic favors standard parsing before 3rd party toolkits.
- **Idempotency**: Ingestion enforces SHA-256 hash checks with Azure AI Document Intelligence before vector mapping.
- **Agentic RAG**: Multi-query pipelines via `azure-ai-projects` rather than single-vector retrieval.

## Local Development

### Prerequisites
- **Python 3.10+** installed on your Windows host
- **UV** package manager (`pip install uv` or [standalone installer](https://docs.astral.sh/uv/getting-started/installation/))
- **Rancher Desktop** (optional, for container validation) — set to **dockerd (moby)** engine

### Native Development (Daily Workflow)

Run everything from your host `.venv` via UV. No containers needed.

```powershell
# 1. Install / sync dependencies
uv sync --frozen

# 2. Start the Streamlit UI (port 8501)
uv run streamlit run src/ui/app.py --server.port 8501

# 3. In a second terminal — start the Azure Functions host (port 7071)
cd src; $env:PYTHONPATH=".."; uv run func start --port 7071

# 4. Run tests
uv run pytest tests/ -v
```

### Container Validation (Rancher Desktop)

Validate the production-parity Docker image locally with live-reload.

```powershell
# 1. Copy the environment template and fill in your values
cp .env.example .env

# 2. Build and run with live-reload volume mounts
docker compose -f docker-compose.dev.yml up --build
```

- **Streamlit UI**: http://localhost:8501
- **Azure Functions**: http://localhost:7071/api/ArchitectureAdvisorTrigger
- Edit files under `src/` — changes appear in the container automatically.

> **Note:** A `.devcontainer/` configuration is included for contributors who prefer a fully containerised IDE experience. It is not required for daily development.
