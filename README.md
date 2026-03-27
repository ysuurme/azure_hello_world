# Azure Architecture Agent

The **Azure Architecture Agent** is a Technical Design Authority (TDA) Agent. It moves past simple "Chat-over-PDF" patterns into Agentic Retrieval-Augmented Generation (RAG). The system actively reasons across the Microsoft Well-Architected Framework (WAF) and private repository notes to balance structural resiliency with cost-efficiency.

## 🛡️ The AI Sentinel Framework (`.agents/skills/`)
This repository enforces strict engineering standards through a custom **Agentic Skills Framework**. AI Agents operating in this workspace act as the "Senior Educational Software Architect" and are bound by three mutually exclusive protocols:

1. **`design-architecture`**: Governs Domain logic, Hexagonal bounding, and the Maker/Checker reasoning loop. Forbids "Architectural Drift" and temporary CSV/JSON artifacts.
2. **`design-infrastructure`**: Governs Delivery mechanisms and Cloud Orchestration. Forces Docker blast-radius minimization, rootless configuration, and Azure native Identity/Networking limits.
3. **`review-code`**: Governs Micro-Syntax and Geometry. Enforces 100% Type Hints, inverted Guard Clauses, and strict `<30`-line function ceilings.

## Key Technical Decisions
- **Thin UI Mediator**: The Streamlit application (`src/ui/app.py`) is completely decoupled from HTTP via a custom API adapter, maintaining Clean Architecture boundaries.
- **Unified Telemetry**: Fragmented native logging is banned. All project observability routes exclusively through `src/utils/m_log.py`.
- **Rootless Multi-Stage Containers**: The `Dockerfile` natively builds via `uv` in a `builder` layer, and strips massive vulnerability vectors (like shells/compilers) from the final execution layer.
- **Standard Library First**: External SDKs are heavily scrutinized. Code favors standard parsing (like `urllib` Healthchecks) over 3rd party toolkits.
- **Idempotency**: Ingestion enforces SHA-256 hash checks with Azure AI Document Intelligence before vector mapping.

## Local Development

### Prerequisites
- **Python 3.10+** installed on your Windows host
- **UV** package manager (`pip install uv` or [standalone installer](https://docs.astral.sh/uv/getting-started/installation/))
- **Docker / Rancher Desktop** (optional, for container validation) 

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

### Container Validation (Reproducing Production)

Validate the production-parity Docker image using our Rootless Multi-Stage build.

```powershell
# 1. Copy the environment template and fill in your values
cp .env.example .env

# 2. Build and run the hardened container
docker compose -f docker-compose.dev.yml up --build
```

- **Streamlit UI**: http://localhost:8501
- **Azure Functions**: http://localhost:7071/api/ArchitectureAdvisorTrigger
