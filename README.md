# Azure Architecture Agent

**The Technical Design Authority (TDA) Agent**

This system is a mature, stateful "Solution Architecture Composer". Moving past single-prompt Chat-over-PDF patterns, it utilizes a cyclical agentic routing loop (inspired by Microsoft Agent Framework concepts) to stringently intake user requirements against the Microsoft Well-Architected Framework, query a structured Capability RAG repository, and finally generate both a formal 5-point architecture document and a raw **D2 Visual diagram** mapped securely via Python subprocesses!

---

## 🛡️ Core Architecture Updates (Live MVP)

1. **Lean Boundary Mediation**: For the active MVP, the Azure Function trigger overhead has been decoupled. Streamlit natively invokes the `AgenticOrchestrator` synchronously. This allows for rapid, unified local development testing without Docker network proxy complexity.
2. **Secure Entra ID AI Identity**: Hardcoded API keys (`OPENAI_API_KEY`) are completely banned in this repository. Our factory (`m_agentfactory.py`) natively leverages `azure-ai-projects` and `azure-identity` (`DefaultAzureCredential`). Your underlying OS terminal login (`az login`) automatically issues temporary tokens over the data-plane using RBAC.
3. **D2 Diagram Visual Engine**: Using isolated Python `subprocess` bindings executing a static GO compilation of [D2](https://d2lang.com/), the LLM physically drafts SVG architectural diagrams rendered natively dynamically directly into the Streamlit Chat state.
4. **Structured RAG Repository**: The `/capabilities/` directory operates as a Git-backed Document Intelligence engine. It stores Markdown definitions enhanced with exact YAML Frontmatter targeting system constraints dynamically.
5. **Continuous Persistence**: The `ArchitecturePersister` (`src/utils/m_persist_design.py`) caches all successfully approved AI-generated SVG and MD deliverables securely onto timestamped local directories for history.

---

## 🧠 Agentic Application Architecture

The system achieves "Solution Architecture" reasoning not by using massive unmanageable monolithic prompts, but by stringing specialized agents together using a finite state machine loop called the **Agentic Orchestrator**:

```mermaid
graph TD
    UI[🖥️ Streamlit UI] -->|User Input| AO[⚙️ Agentic Orchestrator]
    
    %% INTAKE PHASE
    AO -->|State: INTAKE| IR(🕵️ Intake Reviewer)
    IR -->|Azure Foundry Inference| AO
    
    %% GENERATION PHASE
    AO -->|State: GENERATION| AC(👷 Architecture Composer)
    AC -->|Search Vector RAG| RAG[(📁 /capabilities/ MDs)]
    AC -->|Extracts Pricing| CALC(💲 Retail Cost Sync Tool)
    AC -->|Azure Foundry Inference| SVG(🖨️ D2 Engine)
    SVG -->|Renders Visuals| UI
    
    classDef agent fill:#0a5a9c,color:#fff,stroke:#fff,stroke-width:2px,rx:10px,ry:10px;
    classDef sys fill:#333,color:#fff,stroke:#fff,stroke-width:1px,rx:5px,ry:5px;
    class IR,AC agent;
    class UI,AO,RAG,CALC,SVG sys;
```

---

## 🚀 Native Local Deployment

### Prerequisites
- **Python 3.10+** installed on your Windows Host.
- **UV** package manager (`pip install uv`).
- **Azure CLI** installed and authenticated via `az login` to a tenant holding **"Cognitive Services OpenAI User"** data-plane permissions over an active AI Foundry project.

### 1. Execution (Single Command)
Because we migrated into a Lean MVP architecture, startup is completely streamlined via UV:

```powershell
uv sync --frozen
uv run streamlit run src/ui/app.py
```
*(Access the UI immediately via `http://localhost:8501`)*

### Bootstrap: single shared ClientManager

Create one `ClientManager` at application startup and pass it to the `AgenticOrchestrator` so every agent shares the same authenticated clients and credentials lifecycle:

```python
from src.utils.m_ai_client import ClientManager
from src.utils.m_orchestrator import AgenticOrchestrator

cm = ClientManager()  # uses DefaultAzureCredential (az login or service principal env vars)
orchestrator = AgenticOrchestrator(client_manager=cm)
```

Set `AZURE_AAIF_PROJECT_ENDPOINT` and optionally `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET` in your `.env` or environment before running.

## Code Validation
```powershell
python -m pytest -v tests
```

## 🐳 Container Validation (Production Parity)
Our Container respects strictly hardened Rootless Multi-Stage paradigms. 
The D2 engine `.tar.gz` is safely pulled within an isolated builder container, and only the raw static binary mapped directly into an `appuser` distroless linux runtime layer to eliminate arbitrary system vulnerability vectors.

```env
# No passwords or API keys needed. Your CLI token handles auth!
AIPROJECT_CONNECTION_STRING=endpoint=https://<REGION>.api.azureml.ms;subscription_id=<YOUR_SUB>;resource_group_name=<YOUR_RG>;workspace_name=<YOUR_HUB_PROJECT>

# Alternate raw endpoint parsing is also supported directly:
# AIFOUNDRY_CONNECTION_STRING=endpoint=...

# (Optional) Control pricing/performance via specific Models
AZURE_AI_MODEL=gpt-4o
```

```powershell
docker compose -f docker-compose.dev.yml up --build
```

---

## 📜 Agent Skills Framework (`.agents/skills/`)
AI Agents operating in this workspace act as the "Senior Educational Software Architect" and evaluate code geometry via three exclusive protocols:

1. **`design-architecture`**: Dictates component Single Responsibility and State routing logic. Enforces "Standard Library First".
2. **`design-infrastructure`**: Controls strict blast-radius isolation (Entra ID, Docker rootless constraints, Azure Networking limits).
3. **`review-code`**: Manages explicit code limits (`<30`-line function ceilings, 2-level indent limits, mandatory Type Hinting, & Guard Clauses).

---

## 🤖 Agentic Development (GitHub Issues)

This project supports a headless "Director Workflow" where development tasks are triggered remotely via GitHub Issues and executed by a local agent listener.

### The Director Workflow (Mobile Mode)

```
Detect → Task → Monitor → Approve
```

1. **Detect**: You spot a bug or feature idea while away from your desk.
2. **Task**: Open the GitHub App → Create Issue → Apply the `agent:dev` label.
3. **Monitor**: Watch label transitions and agent comments from the GitHub App. The PR Checks Action (`pr-checks.yml`) provides test/lint results in the Actions tab.
4. **Approve**: Receive a PR notification → Review → Merge.

### Label Lifecycle

| Label | Meaning |
|-------|---------|
| `agent:dev` | Issue is queued for agent pickup |
| `agent:in-progress` | Agent has claimed and is working on the issue |
| `agent:completed` | Agent finished successfully, PR created |
| `agent:failed` | Agent encountered an error (see issue comments for details) |

### Two-Phase Agent Loop

The agent listener (`.github/scripts/agent-listener.ps1`) implements a deliberate two-phase process:

- **Phase A — Refine**: Reads the raw issue body and enriches it into a structured format (Goal / Description / Requirements / Acceptance Criteria). This means you can write rough issues from your phone — the agent formalizes them before coding.
- **Phase B — Develop**: Creates a linked branch via `gh issue develop`, executes the development task, and creates a PR on success.

### Running the Listener

```powershell
task agent:listen
```

> **⚠️ Temporary Architecture**: The listener currently runs on your laptop. If the laptop sleeps or loses network, tasks are silently dropped. The future target is GitHub Codespaces with event-driven spin-up/down. This is explicitly accepted as a Phase 1 scaffold.

---

## 📚 Project Governance

| File | Role |
|------|------|
| `GEMINI.md` | **Thin structural map** — repository layout, rules, and cross-references. Consumed automatically by Gemini CLI and VS Code extension. |
| `agents.md` | **Deep architecture** — design philosophy, learning goals, architectural context, session operating instructions. |
| `.agents/skills/` | **Coding enforcement** — deterministic behavioral protocols for AI agents. |
| `Taskfile.yml` | **Single source of truth** for all automation commands. Run `task --list` to discover available tasks. |

