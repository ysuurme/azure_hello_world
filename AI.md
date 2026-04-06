# AI.md — Project Context for AI Agents

> **Governance:** Comprehensive structural map, ruleset, and deep architecture. Coding enforcement in [`.agents/skills/`](.agents/skills/).

## Project Identity

**Azure Architecture Sentinel** — A TDA agent on Azure AI Foundry. Ingests requirements against the Well-Architected Framework, queries a capability RAG repository, generates architecture documents with D2 diagrams.

## Repository Layout

| Directory | Purpose |
|-----------|---------|
| `src/agents/` | Agent definitions (Intake Reviewer, Architecture Composer) |
| `src/utils/` | Business logic: orchestrator, tools, ingestion, logging, persistence |
| `src/ui/` | Streamlit frontend |
| `src/config.py` | Centralized configuration management |
| `tests/` | Unit and integration tests (pytest) |
| `capabilities/` | Git-backed Markdown RAG repository with YAML frontmatter |
| `designs/` | Persisted AI-generated SVG and MD deliverables |
| `infra/` | Terraform IaC modules |
| `.agents/skills/` | Agent skill protocols: `design-architecture`, `design-infrastructure`, `review-code`, `git-workflow`, `write-skills` |
| `.github/scripts/` | `sync-issues.ps1` (issue sync), `agent-listener.ps1` (headless builder) |
| `.github/workflows/` | `pr-checks.yml` (lint + test on PR) |

## Git Workflow

Branches: `feature/issue-N` from `master`. Commits: `feat(#N): Title`. PRs target `master` with `Closes #N`. Agent self-reviews every PR. Human approval required. Branch auto-deleted on merge. Full protocol in `.agents/skills/git-workflow/SKILL.md`.

## Agentic Development

The `agent-listener.ps1` polls for `agent:dev`-labeled issues. Phase A refines raw issues into structured format. Phase B runs Gemini CLI (`task agent:dev ISSUE=N`) to implement. Labels track state: `agent:dev` → `agent:in-progress` → `agent:review` → `agent:completed`. All PRs route to the `@hello_architect` project for human review.

## Rules

1. **Every PR must include a test file** in `/tests`.
2. **Check `Taskfile.yml` first** before writing new scripts. `task --list` to discover.
3. **No hardcoded API keys.** All Azure connections use `DefaultAzureCredential`.
4. **UV is the package manager.** `uv add`, `uv sync`, `uv run` — never `pip install`.
5. **Code geometry** enforced via `.agents/skills/review-code`: <30-line functions, 2-level indent max, type hints, guard clauses.
6. **Standard Library First.** Prefer builtins and stdlib over third-party packages.
7. **Git operations** follow `.agents/skills/git-workflow`: `feature/issue-N` branches, conventional commits, agent self-review, no auto-merge.
8. **Lint must pass** before any commit: `task lint` (ruff with E, F, I, N, UP rules).

## Tooling Policy
- **Primary Tool:** You MUST use `run_shell_command` or similar capability limits for all environment interactions.
- **Allowed Binaries:** `gh`, `task`, `ruff`, `git`.
- **Constraint:** Do not use raw `pip`, `npm`, or `rm -rf`; always use the project `task` runner or native operations to ensure state protection.

## Model Delegation & Handoff Rules (MANDATORY)

The active driver is set via `AGENT_DRIVER` in `.env` (`gemini` or `claude`). Both drivers share the same delegation principle: the cloud model reasons and plans; the local model generates code.

### Role Definitions
- **Cloud Model (Gemini or Claude, per `AGENT_DRIVER`):** Architecture, planning, complex reasoning, multi-step decision-making, web research, code review analysis.
- **Local Model (GPU-resident, via LM Studio):** ALL routine code generation, file writing, file editing, refactoring, boilerplate, test scaffolding.

### Decision Heuristic (applies to both drivers)
- **One sentence to describe the change** → delegate to local model.
- **Multi-step reasoning or cross-file coordination required** → use cloud model tools directly.

**Delegate to local model for:** new files, single-file edits, test files, config files, boilerplate, small refactors.
**Keep in cloud model for:** multi-file coordinated refactors, security-critical code (auth, credentials, encryption), fixing local model errors, files >200 lines requiring coherence.

### Gemini Driver — MCP-First Enforcement

When `AGENT_DRIVER=gemini`, the `lm-local` MCP server (bridge on port 3100) is the delegation mechanism. Default to it for all routine code-writing operations.

**Use `mcp_lm-local_*` tools for all routine work.** Available tools: `write_file`, `read_file`, `replace`, `glob`, `list_directory`, `read_many_files`, `search_file_content`, `google_web_search`, `web_fetch`.

If `lm-local` is disconnected, fall back to cloud model file tools and log the fallback in the issue comments.

### Claude Driver — Local LM via HTTP

When `AGENT_DRIVER=claude`, delegation uses a direct HTTP call to LM Studio's Anthropic-compatible endpoint. No MCP bridge is involved.

For all routine code generation, call:
```bash
uv run python .github/scripts/local_lm_coder.py \
  --task "precise description of what to generate" \
  --context "$(cat path/to/relevant/file.py)"
```
Capture stdout and write it to the target file using Write/Edit tools. Do not generate code directly when this rule applies.

Allowed shell commands: `gh`, `task`, `git`, `ruff`, `uv run`, `lms` — see `.claude/settings.json`.

### Cloud Model — Permitted Uses (both drivers)
1. **Planning**: Deciding what to build, reading issues, analyzing requirements.
2. **Architecture**: Designing module boundaries, data flow, API contracts.
3. **Research**: Web search and page fetching for documentation and APIs.
4. **Complex Reasoning**: Debugging multi-file interactions, resolving ambiguous requirements.
5. **Shell Commands**: Running `gh`, `task`, `git`, `ruff`.
6. **Code Review**: Analyzing diffs, posting PR review comments.
7. **Complex Code**: Multi-file refactors, security-critical implementations, correcting local model errors.

## Safety & Boundaries (CRITICAL for Headless Agents)
- **STRICT PROJECT ROOT BOUNDARY:** You must NEVER modify any files, or run any commands that affect files, outside of this project root directory.
- **SYSTEM HARM:** When in doubt, do NOT run any commands that could potentially harm the host system. Fall back to safely failing the task.
- **NO DESTRUCTIVE GLOBAL COMMANDS:** Global state changes (e.g., modifying global Git configs, installing global software) are strictly prohibited.
- **VERSION CONTROL FREEDOM:** Because the project is under Git version control and the listener orchestrates feature branches, you are free to heavily modify, refactor, and create files *within* the project root. Git provides the safety net.

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
