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

---

## 📚 Project Governance

| File | Role |
|------|------|
| `GEMINI.md` | Thin structural map — repository layout, rules. Auto-consumed by Gemini CLI. |
| `agents.md` | Deep architecture — design philosophy, learning goals, session instructions. |
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
