# GEMINI.md — Project Context for AI Agents

> **Governance:** This file is a thin structural map and rule set. For deep architectural context, design philosophy, and learning goals, see [`agents.md`](agents.md). For coding enforcement protocols, see [`.agents/skills/`](.agents/skills/).

## Project Identity

**Azure Architecture Sentinel** — A Technical Design Authority (TDA) agent built on Azure AI Foundry. It ingests user requirements against the Microsoft Well-Architected Framework, queries a structured capability RAG repository, and generates architecture documents with D2 visual diagrams.

## Repository Layout

| Directory | Purpose |
|-----------|---------|
| `src/agents/` | Agent definitions (Intake Reviewer, Architecture Composer) |
| `src/utils/` | Business logic: orchestrator, tools, ingestion, logging, persistence |
| `src/ui/` | Streamlit frontend |
| `src/config.py` | Centralized configuration management |
| `tests/` | Unit and integration tests (pytest) |
| `capabilities/` | Git-backed Markdown RAG repository with YAML frontmatter |
| `architecture/` | Architecture decision records |
| `designs/` | Persisted AI-generated SVG and MD deliverables |
| `infra/` | Terraform IaC modules |
| `.agents/skills/` | Agent skill protocols: `design-architecture`, `design-infrastructure`, `review-code`, `write-skills` |
| `.github/scripts/` | Automation scripts (issue sync, agent listener) |
| `.github/workflows/` | GitHub Actions CI/CD |

## Rules

1. **Every PR must include a test file** in `/tests`.
2. **Always check `Taskfile.yml`** for existing automation before writing new scripts. Run `task --list` to discover available tasks.
3. **No hardcoded API keys.** All Azure connections use `DefaultAzureCredential` from `azure-identity`.
4. **UV is the package manager.** Use `uv add`, `uv sync`, `uv run` — never raw `pip install`.
5. **Code geometry constraints** are enforced via `.agents/skills/review-code`: <30-line functions, 2-level indent max, mandatory type hints, guard clauses.
6. **Standard Library First.** Prefer Python built-ins and stdlib over third-party packages unless there is clear justification.
