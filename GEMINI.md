# GEMINI.md — Project Context for AI Agents

> **Governance:** Thin structural map and rule set. Deep architecture in [`agents.md`](agents.md). Coding enforcement in [`.agents/skills/`](.agents/skills/).

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

Branches: `feature/issue-N` from `main`. Commits: `feat(#N): Title`. PRs target `main` with `Closes #N`. Agent self-reviews every PR. Human approval required. Branch auto-deleted on merge. Full protocol in `.agents/skills/git-workflow/SKILL.md`.

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
