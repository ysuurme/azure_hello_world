---
name: ADR-011-diagram-studio-sketch
description: Diagram Studio module — first capability under ADR-010; refines a diagram via the grill pattern, generates D2 code, renders SVG with native --sketch enforced at the engine level
---

# ADR-011: Diagram Studio Module with Native D2 Sketch Rendering

## Status
Accepted

## applies_to
application, agent

## Context and Problem Statement

The user wants to generate D2 diagrams in a consistent hand-drawn sketch style from natural-language descriptions. This becomes the first concrete capability module under the workflow dispatcher (ADR-010). Three sub-decisions must be settled together because they are coupled:

1. **How is "sketch style" enforced?** The current `architecture_composer.py` mentions `theme: sketch` inside the LLM system prompt. That is unreliable — LLM output drifts, and the style becomes a gamble on prompt compliance rather than an engine invariant.
2. **Does the module run a single LLM call (description → D2), or a multi-turn grill?** A single-shot call produces inconsistent results because the LLM cannot ask follow-up questions; the user often does not know what they want until challenged.
3. **What artefacts persist?** The current `ArchitecturePersister` saves markdown + SVG. For a diagram, the structured intent (a `DiagramBrief`) is more valuable than the prose, because future revisions start from the brief, not from the raw description.

The decision must produce a module that is consistent (sketch every time), iteratively refinable (grill before generate), and reproducible (brief survives the session).

## Considered Options

* **Option A — Engine-level `--sketch`, grill-pattern refinement, persist trio.** `DiagramEngine.generate_svg()` always passes `--sketch` to the D2 binary. The `DiagramStudioModule` runs the refine pattern (codebase-first, always-recommend, no-branch-left-open) to produce a `DiagramBrief`. On user approval, it generates D2 from the brief, renders SVG, and persists `<name>.brief.md` + `<name>.d2` + `<name>.svg`.
* **Option B — Prompt-level sketch, single LLM call, persist SVG only.** Keep relying on `theme: sketch` in the LLM prompt. Generate D2 in one call. Save just the SVG.
* **Option C — Engine-level `--sketch`, single LLM call, persist SVG + D2.** Enforce sketch at engine level but skip the grill pattern.

## Decision Outcome

Chosen option: **Option A**, because (i) engine-level `--sketch` makes the style an invariant of the rendering layer rather than a gamble on LLM compliance; (ii) the grill pattern matches the Maker-Checker philosophy already in this codebase and prevents the diagram from being generated from underspecified intent; (iii) the trio persistence preserves the structured intent (`DiagramBrief`), the source (`D2`), and the deliverable (`SVG`), so a future revision can start from any of the three layers without re-running the LLM.

### Positive Consequences

* Sketch style is enforced regardless of LLM output — the engine flag is the source of truth.
* The grill loop catches under-specified diagrams before they waste an LLM call on the generation step.
* The `DiagramBrief` schema becomes reusable: future modules (ADR writer, design refinement) can subclass the same `RefinementMixin` with their own brief schemas.
* Persisting the trio means diagram revisions are cheap — open the `.brief.md`, edit, re-render.
* Removes the now-misleading `theme: sketch` references from `architecture_composer.py`'s system prompt; the composer no longer needs to know how diagrams are styled.

### Negative Consequences

* The `RefinementMixin` introduces a new abstraction that must be kept thin. Over-abstraction risk: solved by keeping it to one method (`grill_round`) and one schema slot (`brief_class`).
* `DiagramEngine.generate_svg()` gains a `sketch: bool = True` parameter — a small API change, but every existing caller (currently only `ui.app`) must accept the new default.
* The grill loop adds at least one extra round-trip before the diagram is generated. Mitigated by an "I want to draw this exactly as I described it" escape hatch (`/diagram --quick "..."`) deferred to Out of Scope for v1.
* `m_persist_design.py` grows a `persist_diagram(name, brief, d2_source, svg)` method alongside the existing `archive_solution`.

### Confirmation

* `src/utils/m_diagram_engine.py` `generate_svg(d2_syntax, sketch: bool = True)` always passes `--sketch` when `sketch=True`, verified by a unit test that asserts the subprocess args list contains `--sketch`.
* `src/agents/diagram_studio.py` exists; implements the `WorkflowModule` contract from ADR-010 and the grill pattern from `.agents/skills/refine/`.
* `src/agents/diagram_studio.py` produces a `DiagramBrief` dataclass with: `subject`, `components` (list of name/shape/group), `relationships` (list of from/to/label), `layout_direction`, `style` (defaulted to `sketch: true`).
* `DiagramStudioModule.handle()` returns `status="awaiting_approval"` after the grill loop reaches a complete brief; only on user approval does it return `status="completed"` with the generated artefacts.
* `src/utils/m_persist_design.py` exposes `persist_diagram(name, brief, d2_source, svg_bytes)` writing the trio under `DESIGNS_ARCHIVE_DIR/diagrams/<name>.{brief.md,d2,svg}`.
* `src/agents/architecture_composer.py` system prompt no longer references `theme: sketch` — sketch styling is no longer a composer concern.
* Tests in `tests/agents/test_diagram_studio.py` cover: grill round produces questions with recommendations, brief approval gate works, generated D2 is non-empty, rendered SVG bytes are produced, brief/D2/SVG trio is persisted.
* Revisit when (a) users repeatedly skip the grill and just want one-shot generation — signal that the `/diagram --quick` escape hatch should be promoted; or (b) the `DiagramBrief` schema has been forked for two other modules — signal that the mixin should be promoted to a full base class.

## Pros and Cons of the Options

### Option A — Engine-level sketch, grill refinement, persist trio

| | |
|---|---|
| **Good** | Sketch style is an engine invariant — cannot be broken by LLM drift. |
| **Good** | Grill pattern produces consistently-structured diagrams. |
| **Good** | Persisted brief enables cheap revisions. |
| **Good** | Refinement pattern is reusable across future capability modules. |
| **Bad** | Extra round-trip before the diagram appears (mitigation: quick mode deferred to OoS). |
| **Bad** | Introduces the `RefinementMixin` abstraction — must be kept thin. |

### Option B — Prompt-level sketch, single call, SVG only

| | |
|---|---|
| **Good** | Minimal code change. |
| **Bad** | Style consistency depends on LLM compliance — unreliable across model versions. |
| **Bad** | Under-specified diagrams produce poor first-shot output. |
| **Bad** | No persisted intent — every revision restarts from prose. |

### Option C — Engine sketch, single call, persist SVG + D2

| | |
|---|---|
| **Good** | Style enforced at engine level. |
| **Good** | Source D2 is editable for revisions. |
| **Bad** | Under-specified diagrams still produce poor output. |
| **Bad** | No structured `DiagramBrief` — future modules cannot reuse a refinement pattern. |
