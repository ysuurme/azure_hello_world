# AGENTS.md — Agent Standing Instructions & Project Context

> **Governance:** Comprehensive ruleset and standing instructions for any agent interacting with this repository. Coding enforcement protocols are explicitly detailed in `.agents/skills/`.

## Project Identity

| Key | Value |
|-----|-------|
| Stack | Python + UV |
| Entry point | `src/main.py` |
| Config | `src/config.py` (pydantic-settings, loads `.env`) |

## Session Initialisation

Load in this order at the start of every session:

1. `CONTEXT.md` — domain glossary, bounded contexts, Module Map, Issue-Type Index, and architectural constraints
2. `AGENTS.md` — this file; standing instructions and skill index
3. `docs/adr/ADR_STRUCTURE.md` — master ADR index; filter by `applies_to` for the current `project_type` and load only the relevant ADR files
4. Task-specific context — issue description, PR diff, or user prompt

Never begin a task without reading `CONTEXT.md` first. An agent that skips this will hallucinate boundaries. 
After reading `ADR_STRUCTURE.md`, load only the ADRs that match the current `project_type` (default: application - ADR-003, ADR-004, ADR-007, ADR-008, ADR-009). Do not load ADRs scoped to other project types.

### Context Protocol

Mandatory before opening any source file. See ADR-009.
1. Read `CONTEXT.md` fully. Do not open any `.py` / `.ps1` / `.yml` file yet.
2. From the Module Map and Issue-Type Index, identify the 3–5 files relevant to this task. Write them down explicitly in your first user-facing message before reading them.
3. Read only those files. If you feel the urge to read more, ask: *does CONTEXT.md tell me this file is in scope for this issue type?* If no — stop. Work with what you have.
4. If implementation reveals a dependency not on the Map, read that file, and update the Module Map in `CONTEXT.md` in the same PR.
5. Never `Grep` `**/*.py` to orient yourself. Keep the Map accurate.

## Agentic Development Workflow

The `agent-listener.ps1` polls for `agent:dev`-labeled issues. Phase A refines raw issues into structured format. Phase B runs the agent CLI (`task start ISSUE=N`) to implement. Labels track state: `agent:dev` → `agent:implementing` → `agent:review` → `agent:merged`. All PRs route to the `@hello_architect` project for human review.

### Skills

Invoke the relevant skill in `.agents/skills/` before implementing manually.
- **Workflow:** `refine` → `architecture` → `plan` → `tdd` → `harness` → `review` → `ship`
- **Meta:** `version-control`, `write-skills`
- **Domain:** `application-engineering` (AI-backed APIs), `data-engineering`, `agentic-engineering`. Load exactly one domain skill per session.

## Repository Layout

| Path | Purpose |
|------|---------|
| `src/main.py` | Entry point |
| `src/config.py` | Centralised config (loads `.env`) |
| `src/utils/` | Generic transferable modules (`m_*.py`) |
| `src/<domain>/` | Domain-specific logic |
| `src/tools/` | Developer utilities |
| `tests/` | Pytest suite, mirrors `src/` and `tools/` hierarchy |
| `.agents/skills/` | Skill system instructions |
| `infra/` | Terraform IaC for the Azure cloud backend (ACR + UAMI + Container Apps + Foundry). azurerm `~> 4.0`; remote state in the shared platform account `stplatformydev` (ADR-015). |
| `docs/adr/` | Architecture Decision Records |
| `CONTEXT.md` | Repo-structure doc — domain glossary, Module Map, architectural constraints |
| `.github/workflows/` | CI: lint + test |

## Rules

1. **UV only.** `uv add`, `uv sync`, `uv run` — never `pip install`.
2. **No hardcoded secrets.** All Azure connections use `DefaultAzureCredential`. All config via `.env` + `src/config.py`.
3. **Test parity.** Every `src/**/*.py` and `tools/*.py` must have a matching test file in `/tests`.
4. **Lint must pass.** `uv run ruff check` + `uv run ruff format --check` before commit.
5. **Code geometry.** <30-line functions, 2-level indent max, type hints, guard clauses (`.agents/skills/review-code`).
6. **Standard library first.** Prefer stdlib over third-party packages. Keep `src/utils/` generic (`m_*.py`).
7. **Never modify `AGENTS.md` or `CONTEXT.md` during implementation.** Changes go through a `refine` session. *Exception*: Updating the Module Map and Issue-Type Index mid-implementation when a new file/domain is discovered.
8. **Git operations.** Use `feature/issue-N` branches, conventional commits, no auto-merge (`.agents/skills/git-workflow`).
9. **Sizing and Priority.** Fibonacci estimate anchor, scale, and priority definitions are defined in the `ISSUES.md` header.

## Model Delegation & Handoff Rules (MANDATORY)

The active driver is set via `AGENT_DRIVER` in `.env` (`gemini` or `claude`).
- **Cloud Model (Gemini/Claude):** Architecture, planning, complex reasoning, multi-step decision-making, web research, code review analysis, multi-file refactors.
- **Local Model (GPU-resident, LM Studio):** ALL routine code generation, file writing/editing, refactoring, boilerplate, test scaffolding.

### Driver Mechanisms
- **Gemini:** Uses the `lm-local` MCP server (port 3100) for routine work (`mcp_lm-local_*` tools).
- **Claude:** Uses HTTP call to LM Studio (`uv run python .github/scripts/local_lm_coder.py`).

## Safety & Boundaries

- **STRICT PROJECT ROOT BOUNDARY:** Never modify files or run commands that affect files outside this project root directory.
- **SYSTEM HARM:** When in doubt, do NOT run commands that could potentially harm the host system. Fall back to safely failing.
- **NO DESTRUCTIVE GLOBAL COMMANDS:** Global state changes are strictly prohibited.
- **Tooling Policy:** Allowed shell commands: `gh`, `task`, `git`, `ruff`, `uv run`, `terraform` (scoped to `infra/`).

## Personal Learning Goals

1. **Master Agentic Workflows**: Build non-deterministic, reasoning-based AI systems via Azure AI Foundry.
2. **Context-Aware Search**: Move past basic RAG into multi-query planning via Azure AI Search (`knowledge_base_retrieve`).
3. **IaC and Managed Identities**: Deepen proficiency with Terraform and Entra ID (`authType = "ProjectManagedIdentity"`).
4. **Agent Observability**: Track AI reasoning traces using Azure Application Insights.
