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

### Role Definitions
- **Cloud Model (Gemini Pro):** Architecture, planning, complex reasoning, multi-step decision-making, code review analysis.
- **Local Model (`lm-local` MCP):** ALL code generation, file writing, file editing, refactoring, boilerplate, test scaffolding.

### MCP-First Enforcement (Non-Negotiable)

When the `lm-local` MCP server is connected and available, **default to it for all routine code-writing operations**. Cloud token budget should be reserved for reasoning and complex tasks.

**Use `lm-local` MCP tools for (routine work):**
- Creating new files with well-defined structure (Python, YAML, TOML, Markdown, JSON)
- Single-file edits with clear, scoped changes
- Generating test files from explicit specifications
- Boilerplate, configuration files, and scaffolding
- Small refactors within a single file (renames, extracts, reorders)

**Use cloud model file tools for (complex work):**
- Multi-file coordinated refactors (e.g., renaming a function across 6 files)
- Architectural implementations requiring deep reasoning (async patterns, class hierarchies, state machines)
- Fixing or correcting output that `lm-local` generated incorrectly
- Security-sensitive code (auth flows, credential handling, encryption)
- Files exceeding ~200 lines where coherence matters

**Decision heuristic:** If you can describe the code change in one sentence, use `lm-local`. If the change requires multi-step reasoning or cross-file awareness, use cloud tools.

### Cloud Model — Permitted Uses Only
The cloud model may ONLY be used for:
1. **Planning**: Deciding what to build, reading issues, analyzing requirements.
2. **Architecture**: Designing module boundaries, data flow, API contracts.
3. **Complex Reasoning**: Debugging multi-file interactions, resolving ambiguous requirements.
4. **Shell Commands**: Running `gh`, `task`, `git`, `ruff` via `run_shell_command`.
5. **Code Review**: Analyzing diffs, posting PR review comments.
6. **Complex Code**: Multi-file refactors, security-critical implementations, or correcting `lm-local` errors.

### Fallback Behavior
If `/mcp list` shows `lm-local` as disconnected or unavailable, the cloud model may use its own file-writing tools as a fallback. Log the fallback in any progress comments posted to the issue.

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
