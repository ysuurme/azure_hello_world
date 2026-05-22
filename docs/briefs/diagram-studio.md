---
name: agent-brief-diagram-studio
description: Interface-first Agent Brief for the Workflow Dispatcher refactor plus the Diagram Studio module as its first capability — input to the `plan` skill
date: 2026-05-22
session: refine
---

# Agent Brief: Workflow Dispatcher + Diagram Studio Module

## Problem Statement

Today the Streamlit chat is a single-purpose workflow that drives `IntakeReviewer → ArchitectureComposer → DiagramEngine`. The user wants the chat to be a workflow-agnostic surface that dispatches to capability modules (diagram refinement, full architecture design, ADR drafting, email composition, …) based on slash commands. The first concrete capability is **Diagram Studio**: a module that grills the user via the refine pattern to produce a structured diagram intent, then emits D2 code and a rendered SVG in a consistent hand-drawn sketch style. This brief covers both the dispatcher scaffold and the Diagram Studio module — they are designed and shipped together so the scaffold has a real first user.

## Glossary Additions

| Term | Definition | Disambiguation |
|------|------------|----------------|
| Workflow Dispatcher | The component sitting between the chat UI and capability modules; parses slash commands and routes user input to the matching module. | Not the orchestrator — it does not drive a workflow itself, it only routes. |
| Workflow Module (Capability Module) | A self-contained capability registered with the dispatcher; implements `name`, `slash_command`, `description`, `handle(user_input, session_state) → ModuleResponse`. | Distinct from `agents/*` agent classes — a module *may use* one or more agents internally. |
| Slash Command | A user input starting with `/` that selects the active module (e.g. `/diagram`, `/design`, `/help`). | Not a shell command; parsed entirely client-side by the dispatcher. |
| Sketch Style | The native D2 `--sketch` rendering mode — hand-drawn aesthetic enforced at the binary-execution layer, independent of the D2 source. | Not a D2 theme number; not a CSS class; not a prompt directive. |
| DiagramBrief | The structured intent artefact produced by the Diagram Studio grill loop; the input to D2 code generation. | Distinct from the Agent Brief (which is this document); distinct from the architecture markdown. |
| Refinement Pattern | The grill-me protocol (codebase-first, always-recommend, no-branch-left-open, interface-first) applied to capability modules to produce a Brief artefact before generating the deliverable. | A reusable pattern extracted from the `refine` skill; not the skill itself. |
| ModuleResponse | The return contract of `WorkflowModule.handle()`: `updated_state`, `response_text`, `artifacts`, `status`. | A typed record, not a free-form dict. |

## Bounded Context Changes

Two new bounded contexts are added; two existing ones change ownership at the edges.

**New: `workflow_dispatcher`**
- **Owns:** Slash-command parsing, module registry, session-state hand-off between turns, module switch / exit handling, `/help` enumeration.
- **Does Not Own:** Module internals (delegated to each module), LLM calls (delegated to the module that needs them), rendering (delegated to `utils.m_diagram_engine` or equivalent).

**New: `diagram_studio`**
- **Owns:** `DiagramBrief` schema, the grill loop for diagram refinement, D2 code generation from an approved brief, the approval gate, diagram-artefact persistence trio.
- **Does Not Own:** D2 binary execution (→ `utils.m_diagram_engine`), LLM client management (→ `utils.m_ai_client`), sketch flag enforcement (delegated downward to the engine), workflow routing (→ `workflow_dispatcher`).

**Changed: `utils.m_diagram_engine`**
- **Gains:** `sketch: bool = True` parameter on `generate_svg`; always appends `--sketch` to the subprocess args when true.
- **Loses:** Nothing.

**Changed: `agents.architecture_composer`**
- **Loses:** The `theme: sketch` directive and the entire D2 styling section in its system prompt. Sketch styling moves out of the composer's concern and into the engine.
- **Loses:** Direct invocation from `ui.app` — now invoked only via the `DesignArchitectureModule` registered with the dispatcher.

**Changed: `utils.m_orchestrator`**
- **Becomes:** The internal state machine of the new `DesignArchitectureModule`. The class either moves into `src/agents/design_architecture.py` as a private collaborator, or the module wraps it without modification. Choice deferred to `plan`.

## Interfaces

### `WorkflowDispatcher.dispatch`

**Input:** `user_input: str`, `session_state: dict` (shape: `{active_module: str | None, module_state: dict[str, dict]}`)

**Output:** `DispatchResult` with:
- `updated_session_state: dict`
- `response_text: str` (markdown for the chat)
- `artifacts: list[Artifact]` (zero or more rendered artefacts — SVG, file links)
- `active_module: str | None`

**Behaviour:**
- If `user_input` starts with `/`, parse the first whitespace-separated token as the slash command. Look up the matching module in the registry; set `active_module` to that module's name; clear any prior `module_state` for the new module's slot; dispatch the remainder of `user_input` (post-command) to `module.handle()`.
- If `user_input` does not start with `/` and `active_module` is set, route to the active module's `handle()`.
- If `user_input` does not start with `/` and `active_module` is unset, return the welcome / help message.
- Recognised meta-commands: `/help` (lists registered modules), `/exit` (clears `active_module`).

**Error States:**
- Unknown slash command → `response_text` lists available commands; `active_module` unchanged.
- Module raises → caught at dispatch boundary; `response_text` carries a sanitised error; `active_module` unchanged.

**Testability:** Mock the module registry with two stub modules; assert command parsing, fallback, state namespacing, and exception isolation.

### `WorkflowModule` (Protocol / ABC)

**Required attributes:** `name: str`, `slash_command: str`, `description: str`.

**Required method:** `handle(user_input: str, module_state: dict) → ModuleResponse`

**ModuleResponse:**
- `updated_state: dict` — module-private state for the next turn
- `response_text: str` — markdown to display
- `artifacts: list[Artifact]` — zero or more (e.g. SVG bytes, file paths)
- `status: Literal["in_refinement", "awaiting_approval", "completed", "exited"]`

**Behaviour:** A module is responsible for its own multi-turn state. The dispatcher does not interpret `status` beyond logging — modules signal completion themselves and the user can `/exit` at any time.

**Testability:** Each module is testable in isolation with a mock LLM client; the dispatcher is mocked away.

### `DiagramStudioModule.handle`

**Input:** `user_input: str`, `module_state: dict` (initially `{}`; accumulates a `DiagramBrief` draft across turns)

**Output:** `ModuleResponse` per the contract above.

**Behaviour (state machine):**
1. **First turn (empty state):** Apply the refine pattern. Read the user's initial description. Identify what is under-specified (components without shapes, missing groupings, ambiguous relationships, no layout direction). Emit a grill round: one or more questions, **each with a recommended answer**. `status = "in_refinement"`.
2. **Subsequent grilling turns:** Update the brief draft with the user's answers. If gaps remain, emit the next grill round. If the brief is complete, emit it back to the user as a structured proposal and ask for explicit approval (`yes`, `approved`, `looks good`, etc.) or revision. `status = "awaiting_approval"`.
3. **Approval turn:** Generate D2 code from the approved brief. Render SVG via `DiagramEngine.generate_svg(d2, sketch=True)`. Persist the trio. Return SVG bytes + file paths as artefacts. `status = "completed"`.
4. **Any turn:** `/exit` or `/diagram --reset` clears module state and returns the user to the dispatcher's idle state.

**Error States:**
- LLM fails during grill round → `response_text` reports the failure; `status` stays `in_refinement`; module state is preserved.
- D2 compilation fails → `response_text` carries the D2 stderr; the brief is preserved so the user can adjust and retry; `status` stays `awaiting_approval`.
- Persistence fails → SVG is still returned to the user; failure is logged; `status` is `completed` regardless (the deliverable is what matters).

**Testability:** Mock the LLM client to return scripted grill questions and D2 code; mock `DiagramEngine` to return canned SVG bytes; assert the state machine transitions and the trio is written.

### `DiagramBrief` schema

```
DiagramBrief:
  subject: str                          # one-sentence description of what the diagram depicts
  components: list[Component]
    Component:
      name: str
      shape: str                        # D2 shape primitive (cylinder, rectangle, hexagon, ...)
      group: str | None                 # logical grouping (Bronze, Silver, Gold, ...)
  relationships: list[Relationship]
    Relationship:
      source: str                       # component name
      target: str                       # component name
      label: str | None
  layout_direction: Literal["right", "down"]
  style:
    sketch: bool = True                 # always true in v1; reserved for future themes
```

**Testability:** Pure dataclass; round-trip serialisation to/from markdown is asserted by `tests/agents/test_diagram_studio.py`.

### `DiagramEngine.generate_svg` (modified)

**Input:** `d2_syntax: str`, `sketch: bool = True`

**Output:** `bytes | None` (unchanged)

**Behaviour:** When `sketch=True`, append `--sketch` to the D2 subprocess invocation. All other behaviour unchanged.

**Error States:** Unchanged.

**Testability:** Existing test stub of `subprocess.run` asserts `--sketch` is in the args list when `sketch=True`, absent when `sketch=False`.

### `m_persist_design.persist_diagram`

**Input:** `name: str`, `brief: DiagramBrief`, `d2_source: str`, `svg_bytes: bytes`

**Output:** `Path` to the diagram directory (or to the parent if flat-naming is chosen).

**Behaviour:** Writes three files under `DESIGNS_ARCHIVE_DIR/diagrams/<safe_name>_<timestamp>/`:
- `brief.md` — serialised DiagramBrief (human-readable markdown table form)
- `source.d2` — the raw D2 code that was rendered
- `render.svg` — the SVG bytes

**Error States:** Filesystem errors are logged and re-raised — persistence failure is not silently swallowed for diagrams (unlike the SVG-as-deliverable path).

**Testability:** Mock filesystem; assert all three files written with expected names.

## Constraints

- **ADR-010** (this brief): workflow modules must not call each other directly; composition flows through the dispatcher. Slash commands are the only routing primitive in v1.
- **ADR-011** (this brief): sketch enforcement is engine-level only; module code does not pass D2 styling directives. The refine pattern is reused as a *mixin or shared protocol*, not a re-run of the full refine skill.
- **ADR-009** (existing): Module Map and Issue-Type Index in `CONTEXT.md` are updated in the same PR that introduces the new modules. Skip-update is a blocking ship gate.
- **ADR-008** (existing): No hardcoded secrets; LLM client comes from `m_ai_client.ClientManager`.
- **ADR-007** (existing): Project type is `application`; relevant ADRs are 003, 004, 007, 008, 009 + the new 010, 011.
- **CONTEXT.md "Standard library first"**: D2 binary remains the only non-stdlib dependency on the rendering path. Slash-command parsing uses stdlib `str.split`/`shlex`.
- **AGENTS.md rule 7**: Changes to `CONTEXT.md` go through this refine session — done in the same PR that ships the brief.

## Out of Scope

- **LLM intent classifier** — deferred to a future ADR-010 addendum if slash commands prove insufficient. Recorded in `.out-of-scope.md`.
- **`/diagram --quick` one-shot mode** — deferred until usage shows the grill loop is over-eager. Recorded in `.out-of-scope.md`.
- **Email drafter module, ADR writer module, refinement of existing designs module** — deferred; the dispatcher must accommodate them but they are not built in this brief.
- **Module auto-discovery / config-driven registration** — hardcoded registry suffices below ~8 modules (ADR-010 revisit criterion).
- **PNG rasterisation of the rendered SVG** — Streamlit renders SVG directly; PNG export is a follow-up if a downstream consumer needs it.
- **Multi-diagram session state** — one active diagram per `/diagram` session; switching diagrams requires `/exit` then `/diagram` again.

## Tracer Bullet

The narrowest end-to-end slice that proves all layers connect:

1. User types `/diagram a medallion architecture: source api, raw landing zone with csv and json, then bronze, silver, gold sqlite databases, ending at a machine learning model` in the Streamlit chat.
2. `WorkflowDispatcher` parses `/diagram`, sets `active_module = "diagram_studio"`, dispatches the remainder to `DiagramStudioModule.handle()`.
3. The module runs **one** grill round: asks (with recommendation) "I see seven components — shall I group them as Source / Landing / Bronze / Silver / Gold / Model with flow direction `right`? **Recommended: yes**", `status = "in_refinement"`.
4. User replies `yes`. Module produces the full `DiagramBrief` and asks for approval, `status = "awaiting_approval"`.
5. User replies `approved`. Module generates D2 code from the brief, calls `DiagramEngine.generate_svg(d2, sketch=True)`, which invokes `d2 --sketch input.d2 output.svg`.
6. Module calls `m_persist_design.persist_diagram(name="medallion-sketch", brief, d2_source, svg_bytes)`. Three files land under `designs/diagrams/medallion_sketch_<timestamp>/`.
7. Streamlit displays the SVG in the chat, with a link to the persisted trio.

This slice exercises: slash-command parsing, module hand-off, multi-turn module state, grill-pattern question-with-recommendation, approval gate, brief → D2 generation, engine `--sketch` flag, trio persistence, UI render. Every architectural layer is touched. If any one is broken, the slice fails visibly.

## Out-of-Brief Notes (for `plan`)

- The existing `AgenticOrchestrator` refactor into `DesignArchitectureModule` is in-scope architecturally but should ship as a **second PR** after the dispatcher + Diagram Studio land. Order: (1) dispatcher scaffold with Diagram Studio and a thin temporary `DesignArchitectureModule` that wraps the existing orchestrator unchanged; (2) refactor the wrapped orchestrator into the module's natural shape, guided by the existing test suite. This honours Decision 10B (pragmatic refactor with tests as safety net).
- The `RefinementMixin` abstraction is deliberately kept thin — one method, one schema slot. Promote to a full base class only when a second module needs it.
