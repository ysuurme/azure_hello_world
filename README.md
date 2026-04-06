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

To run this application locally, you must satisfy the following environment and identity requirements:

1.  **Python 3.10+** installed on your Windows Host.
2.  **UV** package manager (`pip install uv`).
3.  **Azure CLI** installed and authenticated via `az login`.
4.  **Azure RBAC Role**: Your user account must have the **"Cognitive Services OpenAI User"** role assigned on the Azure AI Foundry project or its parent Resource Group.
5.  **Environment Variables**: Create a `.env` file in the project root with:
    - `AZURE_AAIF_PROJECT_ENDPOINT`: The endpoint for your AI Foundry project (e.g., `https://<REGION>.api.azureml.ms`).
    - (Optional) `AZURE_AUTH_MODE`: Set to `cli` (default) for `az login` or `sp` for Service Principal.
    - (Optional) `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`: Required if `AZURE_AUTH_MODE=sp`.
6.  **Model Deployments**: Ensure the following models are deployed in your AI Foundry project with names matching `config.py`:
    - `gpt-5-mini` (Intake Reviewer)
    - `DeepSeek-V3.1` (Architecture Composer)

Verify your setup by running:
```powershell
task agent:check
```

### 1. Execution (Single Command)
Because we migrated into a Lean MVP architecture, startup is completely streamlined via Task:

```powershell
task dev
```
*(Access the UI immediately via `http://localhost:8501`)*

### 2. Start the MCP Bridge (Local Coding Specialist)
To enable the agent to perform local code-writing and refactoring (the "Coding Specialist" role), you must start the MCP bridge in a separate terminal:

```powershell
task agent:local
```
*(This bridges the cloud-based Thinking Engine with your local environment securely. Note: This process remains running while you are developing.)*

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
task test
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

## 🤖 Agentic Development (GitHub Issues → PR)

Development tasks execute through a headless "Director Workflow" — create an issue from your phone, and a local agent listener builds, tests, and delivers a PR for your review.

### Full Validated Workflow

```
📱 Phone: Create issue + label 'agent:dev'
    │
    ▼
🤖 Listener picks up issue → label: agent:in-progress
    │
    ├─ Phase A: Refine
    │   Read raw issue → formalize into Goal/Description/Requirements/AC
    │   Post refinement comment on issue
    │
    ├─ Phase B: Develop
    │   git checkout main → git pull → git checkout -b feature/issue-N
    │   Gemini CLI reads issue, follows GEMINI.md + .agents/skills/
    │   Implements changes → runs task test && task lint
    │
    ├─ Commit & PR
    │   git commit -m "feat(#N): Title" → git push origin HEAD
    │   gh pr create --reviewer ysuurme --project @hello_architect
    │   PR body: summary, validation status, Closes #N
    │
    ├─ Agent Self-Review
    │   gh pr review --comment (diff stats + quality checklist)
    │   All agent notes posted on PR for full transparency
    │
    └─ Handoff
        Label: agent:review → issue moves to Review lane
        GitHub Action pr-checks.yml runs lint + test (Critic)
        │
        ▼
📱 Phone: Review PR → Approve → Merge → Branch auto-deleted
```

### Label Lifecycle

| Label | Meaning |
|-------|---------|
| `agent:dev` | Queued for agent pickup |
| `agent:in-progress` | Agent is working (refine + develop) |
| `agent:review` | PR created, agent review posted, awaiting human approval |
| `agent:completed` | Human approved and merged |
| `agent:failed` | Agent error (see issue comments) |

### Running the Listener

```powershell
task agent:listen
```

> **⚠️ Temporary Architecture**: Laptop-based polling listener. If laptop sleeps, tasks are silently dropped. Future target: event-driven GitHub Codespaces.

### Key Design Decisions

- **Gemini CLI** is the Builder (writes code). **GitHub Actions** is the Critic (validates PRs). `gh` CLI handles plumbing (branches, labels, PRs).
- **Branch naming**: `feature/issue-N` — consistent, grep-friendly, auto-cleaned on merge.
- **Commit format**: `feat(#N): Title` — conventional commits, machine-parseable.
- **Agent reviews its own PR** with diff stats and a checklist. Human approval is always required.
- **`@hello_architect` project** receives all PRs. Issues move to the Review lane automatically.

### MCP Bridge Architecture (Local Code Generation)

The headless agent uses a local LM Studio model for code generation via the MCP (Model Context Protocol) bridge. This offloads routine code-writing from premium cloud models to a local GPU-resident model, reducing API costs while maintaining code quality.

**The Problem:** The Gemini CLI spawns MCP servers as child processes using Node.js `child_process.spawn()` with stdio pipes for JSON-RPC communication. On Windows, this creates two fatal issues:
1. **Batch file pipe closure**: `npx.cmd` is a Windows batch wrapper. When Node spawns `.cmd` files, the stdio pipe handles are destroyed by the intermediate `cmd.exe` shell, severing the MCP connection instantly (`MCP error -32000: Connection closed`).
2. **stdout pollution**: The bridge package (`@intelligentinternet/gemini-cli-mcp-openai-bridge`) writes startup logs and ANSI escape codes to `stdout` via `console.log()`. MCP JSON-RPC mandates that stdout carry exclusively JSON messages. Any non-JSON text on stdout causes the Gemini CLI to interpret it as a malformed RPC response and kill the connection.

**The Solution: SSE HTTP Transport.** Instead of stdio, the bridge runs as a persistent background HTTP server managed by `agent-listener.ps1`:

```
agent-listener.ps1 → Start-Process node [..., --port 3100] → bridge HTTP server
Gemini CLI → settings.json: { "url": "http://localhost:3100/mcp" } → clean HTTP JSON-RPC
```

Key implementation details:
- **`Invoke-EnvironmentBootstrap`** resolves the bridge's JS entry point via `npm root -g`, starts it as a background process on port 3100, and tracks the PID for lifecycle management.
- **`settings.json`** is generated dynamically with UTF-8 No-BOM encoding (PowerShell's `Set-Content -Encoding UTF8` injects a BOM that crashes JSON parsers) using `[System.IO.File]::WriteAllText()`.
- **Validation gates**: Before the listener enters its polling loop, it sequentially validates: (1) LM Studio REST API connectivity, (2) target model loaded in VRAM via `/v1/models`, (3) live inference via a hello-world `chat/completions` call, (4) bridge process is alive on port 3100. If any check fails, MCP is gracefully disabled and the pipeline falls back to pure cloud models.
- **`Invoke-EnvironmentTeardown`** kills the bridge process, ejects the model from VRAM (`lms unload --all`), and stops the LM Studio server.
- **Debug mode** (`task agent:listen:debug`) sets `KEEP_MODELS_LOADED=true`, skipping VRAM load/unload cycles during rapid iteration.

**Configuration** (`.env`):
```env
LOCAL_AI_MODEL=nerdsking-python-coder-3b-i
```

---

## 📚 Project Governance

> **All agents (Gemini, Claude, or other) must read `AI.md` on startup.** It is the single source of truth for project rules, architecture, coding standards, and driver-specific delegation behaviour.

| File | Role |
|------|------|
| `AI.md` | **Primary agent instruction file.** Rules, architecture, model delegation (Gemini + Claude drivers), safety boundaries. Read this first. |
| `CLAUDE.md` | Redirect to `AI.md` — exists so Claude Code picks it up automatically. |
| `.agents/skills/` | Coding enforcement protocols (`review-code`, `design-architecture`, `design-infrastructure`, `git-workflow`). |
| `Taskfile.yml` | Single source of truth for all commands. `task --list` to discover. |
| `ISSUES.md` | **Single source of truth for the project roadmap.** All future improvements, features, and bugs are written here. |

### Adding Improvements

All future work — features, bugs, refactors — must be captured as `ISSUE:…END_ISSUE` blocks in `ISSUES.md`. This replaces any standalone implementation plans or task trackers.

```
1. Write the issue in ISSUES.md (Goal / Description / Requirements / Acceptance Criteria)
2. Run `task sync` to push to GitHub and the @hello_architect project
3. Label with `agent:dev` for automated execution, or work it manually
```

This ensures every improvement is tracked in GitHub, reviewable from mobile, and executable by the agent listener.
