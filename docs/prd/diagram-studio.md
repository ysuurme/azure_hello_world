---
name: prd-diagram-studio
description: Lean PRD synthesised from the Agent Brief for the Workflow Dispatcher refactor and the Diagram Studio module
date: 2026-05-22
inputs:
  - docs/briefs/diagram-studio.md (Agent Brief)
  - docs/adr/ADR-010-workflow-dispatcher.md
  - docs/adr/ADR-011-diagram-studio-sketch.md
---

# Lean PRD: Workflow Dispatcher + Diagram Studio

## Problem Statement

Today the Streamlit chat in this project hard-binds to a single workflow: an intake reviewer that hands off to an architecture composer. The user — a solo technical-design practitioner — wants the same chat surface to support a growing set of distinct workflows (refine a single diagram, draft an ADR, compose an email, design a full architecture, …) without forking the orchestrator per capability or fragmenting the UI into separate tabs. The first concrete workflow to be added is **Diagram Studio**: the user describes a diagram in natural language; the agent grills them with structured questions until the intent is well-formed; on explicit approval, the agent emits D2 code and renders a hand-drawn sketch-style SVG; all three artefacts (intent, source, render) are persisted for future revision. Success is reached when the user can type `/diagram <description>` in the existing chat, complete a multi-turn refinement, approve the structured intent, and receive a consistently sketch-rendered diagram on disk and on screen — while every existing chat behaviour continues to work via `/design`.

## User Stories

Minimum five — happy path plus the four most likely failure modes.

1. **Happy path — diagram refinement.** *As a technical-design practitioner, I want to type `/diagram <description>`, answer one or two clarifying questions with recommendations, approve the structured intent, and receive a rendered sketch-style diagram, so that I can produce consistent, structured technical diagrams without writing D2 by hand.*
2. **Happy path — existing design flow preserved.** *As a technical-design practitioner, I want my existing chat behaviour (no slash command, or `/design <requirements>`) to continue producing the full Maker-Checker architecture document, so that the workflow refactor does not regress the capability I rely on today.*
3. **Failure — underspecified description.** *As a technical-design practitioner, I want the agent to surface ambiguities in my description (each with a recommended answer) before drawing anything, so that I never wait for a diagram that does not match my intent.*
4. **Failure — D2 compilation fails.** *As a technical-design practitioner, I want a D2 syntax error to surface the compiler stderr while preserving my refined brief, so that I can edit the brief and retry without re-running the entire grill loop.*
5. **Failure — unknown slash command.** *As a technical-design practitioner, I want a mistyped slash command to list the available commands rather than dispatching to the wrong module, so that command-typing mistakes are recoverable in one turn.*

## Tracer Bullet

The single narrowest vertical slice that proves the full pipe works end-to-end:

`user types /diagram <description>` → `WorkflowDispatcher` parses the slash command and routes to `DiagramStudioModule` → module makes a single LLM call producing D2 code (no grill yet) → `DiagramEngine.generate_svg(d2, sketch=True)` runs `d2 --sketch` → SVG bytes returned to the dispatcher → `ui.app` renders the SVG in the chat. The existing `/design` flow continues to work via a no-slash fallthrough to the unchanged `AgenticOrchestrator` so no regression is introduced.

This is Issue #1 in decomposition. Engine sketch flag, dispatcher skeleton, module v0, and UI integration all land together because each is meaningless without the others. The grill loop, approval gate, persistence, and meta-commands all build on top.

## Implementation Decisions

Schema, contracts, and event semantics only — no file paths, no class names beyond what is fixed by the brief's interface section.

### Slash-command grammar
- A user input is a "command" if its first whitespace-separated token starts with `/`.
- The command token is the entire first token (e.g. `/diagram`, `/design`, `/help`, `/exit`).
- The remainder of the input (everything after the command token) is the command's argument string and is dispatched to the module's `handle()` verbatim.
- Recognised meta-commands: `/help` (lists registered modules with descriptions), `/exit` (clears the active module and returns to dispatcher-idle).
- Unknown commands return the `/help` enumeration and do not change `active_module`.

### Session-state shape
```
session_state:
  active_module: str | None
  module_state:
    <module_name>: dict   # module-private state; opaque to the dispatcher
```

### Module contract
Every registered module exposes:
- `name: str` (e.g. `"Diagram Studio"`)
- `slash_command: str` (e.g. `"/diagram"`)
- `description: str` (one-line, surfaced by `/help`)
- `handle(user_input: str, module_state: dict) -> ModuleResponse`

`ModuleResponse` fields:
- `updated_state: dict`
- `response_text: str` (markdown for the chat)
- `artifacts: list` (zero or more rendered artefacts — bytes, file paths)
- `status: "in_refinement" | "awaiting_approval" | "completed" | "exited"`

### DiagramBrief schema (input to D2 generation)
```
DiagramBrief:
  subject: str                          # one-sentence description
  components: list[Component]
    Component:
      name: str
      shape: str                        # D2 primitive: cylinder, rectangle, hexagon, ...
      group: str | None                 # logical grouping
  relationships: list[Relationship]
    Relationship:
      source: str
      target: str
      label: str | None
  layout_direction: "right" | "down"
  style:
    sketch: bool = True
```

### Engine sketch contract
- `generate_svg(d2_syntax: str, sketch: bool = True) -> bytes | None`.
- When `sketch=True`, the subprocess invocation appends `--sketch` to the args list.
- All other behaviour unchanged from today.

### Persistence contract (diagram trio)
- `persist_diagram(name: str, brief: DiagramBrief, d2_source: str, svg_bytes: bytes) -> Path`.
- Writes three files under `<DESIGNS_ARCHIVE_DIR>/diagrams/<safe_name>_<timestamp>/`:
  - `brief.md` — DiagramBrief serialised as markdown tables (Glossary-style)
  - `source.d2` — the raw D2 code that was rendered
  - `render.svg` — the SVG bytes
- Returns the diagram directory path.
- Persistence errors are logged AND re-raised — diagrams treat the trio as the deliverable.

### Architecture composer prompt change
- The system prompt in the existing architecture composer no longer mentions `theme: sketch` or any D2 styling directive. Sketch styling becomes the engine's concern, not the composer's. Composer continues to emit a `d2` code block; the rendering layer is responsible for the visual style.

## Testing Decisions

By module:

### `WorkflowDispatcher`
- **Unit test:** command parsing (`/diagram args` splits into `("/diagram", "args")`), unknown-command fallback, module hand-off with state, module switch clearing prior state, exception isolation (raising module does not poison dispatcher state).
- **Integration test:** dispatcher with two stub modules registered; simulate a multi-turn conversation across modules.
- **Acceptance criterion:** given a scripted input sequence, the dispatcher's emitted `(updated_state, response_text, active_module)` tuple matches the expected fixture turn-by-turn.

### `DiagramStudioModule`
- **Unit test:** state-machine transitions (`in_refinement` → `awaiting_approval` → `completed`), grill round produces at least one question with a recommended answer, approval gate accepts `yes|approved|looks good` (case-insensitive) and rejects everything else, brief is preserved across an LLM failure during generation.
- **Integration test:** with a mocked LLM client returning scripted D2 code and a mocked DiagramEngine returning canned bytes, the module produces the full SVG output and persists the trio.
- **Acceptance criterion:** scripted three-turn happy-path conversation (describe → confirm grill → approve) produces non-empty SVG bytes + three files on disk.

### `DiagramEngine.generate_svg`
- **Unit test:** subprocess args list contains `--sketch` when `sketch=True`, does not when `sketch=False`. Subprocess failure returns `None`, missing binary returns `None`.
- **Integration test:** with a real D2 binary in CI (existing issue #28 covers binary install), render a known-good D2 string and assert SVG bytes are non-empty and contain `<svg`.
- **Acceptance criterion:** rendered SVG bytes start with `<?xml` or `<svg` and exceed 200 bytes.

### `m_persist_design.persist_diagram`
- **Unit test:** trio files are written with expected names; safe-name conversion strips non-alphanumeric; timestamped directory exists.
- **Integration test:** end-to-end with `tmp_path`; assert three files exist and their contents round-trip.
- **Acceptance criterion:** `(brief.md, source.d2, render.svg)` all present and non-empty under the timestamped directory.

### Existing `/design` flow preserved
- **Regression test:** running the current test suite (`tests/agents/test_app.py` and friends) passes unchanged after the tracer bullet lands. The no-slash fallthrough ensures this.

## Out of Scope

Each entry below was added to `.out-of-scope.md` during the `refine` session — listed here for PRD completeness.

- **LLM intent classifier for dispatch** — deferred because slash commands are deterministic and free; revisit at ~8 registered modules (ADR-010).
- **`/diagram --quick` one-shot mode** — deferred because the grill loop is the value proposition; revisit if usage shows it is over-eager (ADR-011).
- **Email drafter / ADR writer / design-refinement modules** — deferred because Diagram Studio is the proving ground for the dispatcher contract; add as separate briefs.
- **Module auto-discovery** — deferred; hardcoded registry suffices below ~8 modules (ADR-010 revisit criterion).
- **PNG rasterisation** — deferred; Streamlit renders SVG natively, and PNG would pull in `librsvg` or `cairosvg` (constraint violation).

## Decomposition

| # | Title | Label | Estimate | Priority |
|---|-------|-------|----------|----------|
| 1 | Tracer: `/diagram` end-to-end with engine sketch flag and no-slash fallthrough | AFK | 5 | P3 |
| 2 | Grill loop and DiagramBrief schema for Diagram Studio | AFK | 5 | P3 |
| 3 | Approval gate and diagram trio persistence | AFK | 3 | P3 |
| 4 | `/help` and `/exit` meta-commands | AFK | 2 | P4 |
| 5 | Extract DesignArchitectureModule and remove no-slash fallthrough | AFK | 5 | P3 |
| 6 | Pragmatic refactor of DesignArchitectureModule guided by tests | HITL | 8 | P4 |
