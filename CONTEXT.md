# System Context & Domain Glossary

This file serves as the system prompt and architectural glossary for AI agents. Use this document to understand the fundamental architecture, data flow, and codebase topography so you can navigate the repository effectively without exhausting context limits.

## Project Identity

**Azure Architecture Sentinel** — A Technical Design Authority (TDA) agent running on Azure AI Foundry. The Streamlit chat surface is a **workflow dispatcher** (ADR-010): user input prefixed with a slash command routes to one of several capability modules — the original "Design Architecture" flow, the new "Diagram Studio" refinement loop, and future modules (ADR drafting, email composition, etc.). Each capability is self-contained; the chat is functionality-agnostic.

| Key | Value |
|-----|-------|
| Project Type | application |

## Architectural Context

### 1. The Sentinel Concept (Technical Design Authority)
The agent acts as a TDA. It operates using a **"Maker-Checker"** loop:
- **Maker**: Formulate proposals retrieving from internal GitHub markdown notes and WAF guidance.
- **Checker**: Critique proposals specifically on "Security" and "Cost."
- **Refinement**: Fallback to "Value" alternatives based on estimated budgets evaluated via live API Tooling.

### 2. Ingestion Pipeline & Identity
The Sentinel uses advanced methods for data processing (`src/utils/m_ingest.py`):
- **Idempotency**: Avoids duplicative compute by calculating `H(x) = SHA256(Content_{raw} + Metadata_{source})`. Compares against the AI Search Index metadata; only upload/embed if the hash drifts (using `mergeOrUpload`).
- **Document Intelligence**: Uses the Azure Document Intelligence (Layout Model) to strictly preserve complex tables via structured Markdown, enabling "Document-Aware Recursive Chunking" on natural headers instead of arbitrary 1000-token breaks.

### 3. The Tool Layer ("Cost vs Resiliency")
The Agent is equipped with explicitly defined tools such as `calculate_cost()` located in `src/utils/m_tools.py`.
- **Function**: Queries the Azure Retail Prices API.
- **Goal**: Elevates the agent from "Searchbot" to "Financial Architect," directly exposing the real-world financial cost (e.g., $35/mo Front Door) incurred by its WAF resiliency recommendations across a presented "Trade-off Matrix."

### 4. Code & Directory Architecture Standards
- Python logic utilizes **UV** package management inside `.venv`.
- Follows strict **Single Responsibility**, **Object-Oriented Clarity**, and **PEP-8 Meaningful Naming**.
- The `src/` directory rigidly abstracts Trigger boundaries from the business logic encapsulated cleanly within the `utils/` directory. Connections utilize `DefaultAzureCredential` to ensure seamless transition from local `az login` to production environments on Azure Container Apps.
- **Native Secret Management**: Uses a local vault named 'LocalStore' for secret management.

### 5. Workflow Dispatcher and Capability Modules (ADR-010, ADR-011)
The Streamlit chat is a thin surface that calls `WorkflowDispatcher.dispatch(user_input, session_state)`. The dispatcher parses slash commands (`/diagram`, `/design`, `/help`, `/exit`) and routes to a registered `WorkflowModule`. Each module implements `name`, `slash_command`, `description`, and `handle(user_input, module_state) → ModuleResponse(updated_state, response_text, artifacts, status)`. Modules that need multi-turn refinement (e.g. `DiagramStudioModule`) reuse the **refine pattern** as a thin mixin / shared protocol — produce a structured **Brief** artefact, gate on user approval, then emit the deliverable. The first module is **Diagram Studio**, producing a `DiagramBrief` → D2 → sketch-rendered SVG trio. The existing intake → architecture flow becomes the `DesignArchitectureModule` registered under `/design`.

---

## Glossary

| Term | Definition | Disambiguation |
|------|------------|----------------|
| Workflow Dispatcher | Component sitting between the chat UI and capability modules; parses slash commands and routes user input to the matching module (ADR-010). | Not the orchestrator — it does not drive a workflow itself, it only routes. |
| Workflow Module / Capability Module | Self-contained capability registered with the dispatcher; implements `name`, `slash_command`, `description`, `handle()`. | Distinct from `agents/*` agent classes — a module *may use* one or more agents internally. |
| Slash Command | User input starting with `/` that selects the active module (`/diagram`, `/design`, `/help`, `/exit`). | Not a shell command; parsed client-side by the dispatcher. |
| Sketch Style | Native D2 `--sketch` rendering mode — hand-drawn aesthetic enforced at the binary-execution layer, independent of D2 source (ADR-011). | Not a D2 theme number; not a CSS class; not a prompt directive. |
| DiagramBrief | Structured intent artefact produced by the Diagram Studio grill loop; the input to D2 code generation. | Distinct from Agent Briefs produced by the `refine` skill; distinct from the architecture markdown produced by the composer. |
| Refinement Pattern | Grill-me protocol (codebase-first, always-recommend, no-branch-left-open, interface-first) applied to capability modules to produce a Brief artefact before generating the deliverable. | A reusable pattern extracted from the `refine` skill; not the skill itself. |
| ModuleResponse | Return contract of `WorkflowModule.handle()`: `updated_state`, `response_text`, `artifacts`, `status`. | A typed record, not a free-form dict. |

## Bounded Contexts

| Context | Owns | Does Not Own |
|---------|------|--------------|
| `workflow_dispatcher` | Slash-command parsing, module registry, session-state hand-off, `/help` and `/exit` meta-commands. | Module internals, LLM calls, rendering. |
| `diagram_studio` | `DiagramBrief` schema, diagram refine-pattern grill loop, D2 code generation from approved brief, approval gate, diagram trio persistence. | D2 binary execution (→ `utils.m_diagram_engine`), LLM client management (→ `utils.m_ai_client`), workflow routing (→ `workflow_dispatcher`). |
| `design_architecture` | Multi-turn architecture design (intake review → composer); cost-aware Maker-Checker loop. | Workflow routing (→ `workflow_dispatcher`), diagram styling (→ `diagram_studio` / `m_diagram_engine`). |
| `utils.m_diagram_engine` | Safe execution of the D2 binary; sketch flag enforcement (`--sketch`). | D2 code generation, diagram intent. |
| `utils.m_persist_design` | Filesystem persistence of approved artefacts — architecture markdown + SVG, and diagram trio (brief + d2 + svg). | The structure of the artefacts themselves. |

---

## Codebase Map & Topography

Use this module map to pinpoint the relevant files for your task and avoid loading unnecessary files into context.

> **Infrastructure lives in `infra/` (Terraform), intentionally outside this Python module map.** It provisions the Azure cloud backend — ACR + user-assigned identity + Container Apps + Foundry — secretless via managed identity. azurerm `~> 4.0`, remote state in a shared platform RG (ADR-015). See README → *Cloud Deployment (Azure)*. Do not add `infra/` resources to the fan-in/out table below; it tracks `src/` modules only.

### Module Fan-in/Fan-out Summary

| Module | Fan-in | Fan-out | Classification | Purpose / Responsibility |
|--------|--------|---------|----------------|--------------------------|
| `agents.architecture_composer` | 0 | 6 | deep module | Orchestrates capability retrieval, decision-making, and architecture generation. |
| `agents.intake_reviewer` | 0 | 5 | deep module | Refines user intake, extracts requirements, and evaluates feasibility against constraints. |
| `config` | 0 | 1 | deep module | Centralized configuration via pydantic-settings; loads from `.env`. |
| `ui.app` | 0 | 9 | deep module | Streamlit frontend for the Maker-Checker conversation loop. |
| `utils.m_ai_client` | 0 | 4 | deep module | Manages `DefaultAzureCredential` and instantiates connections to Azure AI Foundry models. |
| `utils.m_capability_repo` | 0 | 4 | deep module | Parses markdown/YAML capability records from local storage. |
| `utils.m_diagram_engine` | 0 | 5 | deep module | Bridges Composer markdown to D2 diagram syntax and SVGs. |
| `utils.m_health_check` | 0 | 4 | deep module | Validates environment, credentials, and API readiness. |
| `utils.m_ingest` | 0 | 2 | deep module | Idempotent RAG ingestion pipeline via Azure AI Search. |
| `utils.m_log` | 0 | 4 | deep module | Centralized logging and telemetry wrapping. |
| `utils.m_persist_design` | 0 | 4 | deep module | Persists approved markdown and SVG deliverables to the `designs/` directory. |
| `utils.m_search` | 0 | 1 | deep module | Abstraction for executing semantic queries against AI Search. |
| `utils.m_tools` | 0 | 2 | deep module | Function calling capabilities for agents (e.g., `calculate_cost`). |
| `agents.workflow_dispatcher` | 1 (`ui.app`) | 2+ | deep module | Slash-command parser and capability-module router; sole entry point from `ui.app`. (ADR-010) |
| `agents.diagram_studio` | 1 (`workflow_dispatcher`) | 4 | deep module | Diagram capability module: grill loop → DiagramBrief → D2 → sketch-rendered SVG. (ADR-011) |
| `agents._refinement` | 1 (`diagram_studio`) | 0 | deep module | RefinementMixin encoding the grill pattern: read known → identify gaps → emit questions with recommendations. |
| `agents.design_architecture` | 1 (`workflow_dispatcher`) | 5 (`intake_reviewer`, `architecture_composer`, `utils.m_diagram_engine`, `utils.m_persist_design`, `utils.m_ai_client`) | deep module | Owns the `/design` lifecycle: intake review → composer → SVG render → archive. (ADR-010) |

### Issue-Type → Files Index

| Working on... | Read first |
|---------------|------------|
| Adding a new capability module | `docs/adr/ADR-010-workflow-dispatcher.md`, `docs/adr/ADR-011-diagram-studio-sketch.md` (reference implementation), `src/agents/workflow_dispatcher.py`, `src/agents/diagram_studio.py` |
| Changing dispatch / slash-command behaviour | `docs/adr/ADR-010-workflow-dispatcher.md`, `src/agents/workflow_dispatcher.py`, `tests/agents/test_workflow_dispatcher.py` |
| Changing diagram rendering / sketch behaviour | `docs/adr/ADR-011-diagram-studio-sketch.md`, `src/utils/m_diagram_engine.py`, `src/agents/diagram_studio.py` |
| Changing architecture-design flow (intake → composer) | `src/agents/design_architecture.py`, `src/agents/intake_reviewer.py`, `src/agents/architecture_composer.py` |
| Persistence of designs / diagrams | `src/utils/m_persist_design.py`, `src/config.py` (`DESIGNS_ARCHIVE_DIR`) |

## Architectural Constraints

Invariants that must not be violated in any implementation.

- **Workflow modules must not call each other directly** — composition flows through the dispatcher (ADR-010).
- **Slash commands are the only routing primitive in v1** — no LLM intent classifier (ADR-010).
- **Sketch enforcement is engine-level** — module code does not pass D2 styling directives; the engine appends `--sketch` (ADR-011).
- **The refine pattern is reused as a thin mixin / shared protocol, not a re-run of the full refine skill** — diagrams produce a `DiagramBrief`, not a full Agent Brief + CONTEXT.md updates (ADR-011).
- **Module Map and Issue-Type Index updates ship in the same PR as the new module** — blocking ship gate (ADR-009).

## Out of Scope

Top-5 summary view; full ledger in `.out-of-scope.md`.

| Concept | Reason deferred | Date |
|---------|-----------------|------|
| LLM intent classifier for dispatch | Slash commands are sufficient and free; revisit when ~8+ modules registered (ADR-010) | 2026-05-22 |
| `/diagram --quick` one-shot mode | Defer until usage shows the grill loop is over-eager (ADR-011) | 2026-05-22 |
| Email drafter / ADR writer / design-refinement modules | Dispatcher must accommodate them but they are not built in this brief | 2026-05-22 |
| Module auto-discovery / config-driven registration | Hardcoded registry suffices below ~8 modules (ADR-010 revisit criterion) | 2026-05-22 |
| PNG rasterisation of rendered SVG | Streamlit renders SVG directly; revisit if a downstream consumer needs PNG | 2026-05-22 |

### Legend

| Term | Meaning |
|------|---------|
| Fan-in  | Number of modules that import this module — high fan-in = wide blast radius |
| Fan-out | Number of modules this module imports |
| Deep module    | Large implementation, small interface — target state |
| Shallow module | Interface ≈ implementation complexity — refactoring trigger |
| High fan-in    | Risk: a change here propagates to many callers |

> **Navigation Tip:** When tasked with modifying business logic, always scope your file reads (`view_file`) exclusively to the target module and its direct dependencies in `src/utils/`. Do not greedily read files outside the blast radius.
