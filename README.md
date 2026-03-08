# Azure Architecture Sentinel

The **Azure Architecture Sentinel** is a Technical Design Authority (TDA) Agent. It moves past simple "Chat-over-PDF" patterns into Agentic Retrieval-Augmented Generation (RAG). The system actively reasons across the Microsoft Well-Architected Framework (WAF) and private repository notes to balance structural resiliency with cost-efficiency.

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

## Local Development Requirements (Rancher Desktop + WSL)
Instead of installing complex Python and Azure dependencies on your host Windows machine, this project uses a fully isolated **VS Code Devcontainer**.

### Prerequisites
1. **Rancher Desktop**: Installed and running on your Windows machine.
   - Go to *Preferences > Container Engine* and ensure **dockerd (moby)** is selected (not containerd).
   - Ensure the WSL integration is enabled for your default WSL distro.
2. **VS Code**: Installed with the `Dev Containers` extension (by Microsoft).

### Running Locally
1. Clone the repository and open the folder in VS Code.
2. VS Code should prompt you to "Reopen in Container". If not, press `Ctrl+Shift+P`, type `Dev Containers: Reopen in Container`, and select it.
3. The container will build (downloading Python, Azure CLI, Azure Functions Core Tools, and Terraform).
4. **Validation**: Once inside the container, open a new VS Code terminal. The `uv venv` and `uv sync` commands will have run automatically. 
   - Start the local Azure Functions server:
     ```bash
     cd src && PYTHONPATH=".." func start
     ```
   - In a second terminal, trigger the Sentinel Agent with a dummy payload:
     ```bash
     curl -X POST http://localhost:7071/api/AdvisorTrigger \
          -H "Content-Type: application/json" \
          -d '{"query": "Evaluating the cost impact of moving to a multi-region App Service with Azure Front Door."}'
     ```
   - You should see the HTTP 200 response with the calculated Trade-off Matrix!
