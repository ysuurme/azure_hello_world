---
name: ADR-010-workflow-dispatcher
description: Workflow dispatcher pattern — the main chat is functionality-agnostic and routes user input to capability modules via slash commands; replaces the monolithic AgenticOrchestrator entry point
---

# ADR-010: Workflow Dispatcher Architecture

## Status
Accepted

## applies_to
application, agent

## Context and Problem Statement

The Streamlit chat in `src/ui/app.py` currently hard-binds to a single workflow: `AgenticOrchestrator.orchestrate_cycle()` which drives `IntakeReviewer → ArchitectureComposer → DiagramEngine`. This shape is correct for "design an architecture" but cannot accommodate other workflows that the user wants to plug into the same chat surface — drafting an email, refining a single diagram, writing an ADR, etc.

Three constraints shape the decision:

1. **The chat is the workflow.** The user's mental model is "I open the chat and pick what I want to do today." A separate panel/tab per capability fragments that mental model and breaks muscle memory.
2. **Capabilities are heterogeneous.** Some are single-turn (cost lookup), some are multi-turn refinement loops (diagram studio, ADR writer, architecture design). The chat layer must not assume a turn count.
3. **The existing orchestrator is one capability among many.** It is not the architecture; it is a participant in the architecture.

The current shape forces every new capability to either fork `AgenticOrchestrator` (combinatorial explosion of phases) or live in a separate UI surface (mental-model fragmentation). Neither is sustainable.

## Considered Options

* **Option A — Slash-command dispatcher.** `WorkflowDispatcher` owns the chat entry point. User input starting with `/` is parsed as a command; the dispatcher routes to the matching `WorkflowModule`. Modules implement a common contract (`name`, `slash_command`, `description`, `handle(user_input, session_state) → ModuleResponse`). Hardcoded module registry; explicit human control over which capability is active.
* **Option B — LLM intent classifier dispatcher.** An LLM reads each user message and classifies which module should handle it. No slash commands; pure natural language routing.
* **Option C — Hybrid (slash command preferred, LLM fallback).** Slash command if present, LLM classification otherwise.
* **Option D — Status quo.** Keep `AgenticOrchestrator` as the chat entry point; add new capabilities as additional UI tabs/panels outside the chat.

## Decision Outcome

Chosen option: **Option A — Slash-command dispatcher**, because it matches the Maker-Checker philosophy already governing this codebase (the human stays in explicit control of state transitions), it costs zero LLM tokens for routing, it is deterministic and debuggable, and it mirrors the slash-command convention the user already operates in (Claude Code skills). An LLM intent classifier can be added later as Option C without breaking any module contract.

### Positive Consequences

* Single chat surface; one mental model regardless of which capability is in use.
* Modules are independently testable in isolation — the dispatcher mocks trivially in tests.
* Adding a new capability is a localised change: implement the module, register it in the dispatcher. No edits to existing modules.
* Routing is free (no LLM call). No misclassification failure mode.
* Slash commands are self-documenting: `/help` enumerates every registered module.

### Negative Consequences

* User must learn the slash-command vocabulary. Mitigated by `/help` and by suggesting commands in the welcome message.
* The existing `AgenticOrchestrator` is refactored into a `DesignArchitectureModule`. This is real work, not a wrapper — pragmatic refactor per Decision 10B, with tests as the safety net.
* Session state becomes module-scoped: the dispatcher must namespace state per active module to prevent cross-module state leakage.

### Confirmation

* `src/agents/workflow_dispatcher.py` exists; exposes a `WorkflowDispatcher` class with a hardcoded module registry.
* Every capability registered in the dispatcher exposes `name`, `slash_command`, `description`, and a `handle(user_input, session_state) → ModuleResponse` method.
* `src/ui/app.py` calls `WorkflowDispatcher.dispatch(user_input, session_state)` as its sole entry point — no direct calls to `AgenticOrchestrator` or any module class.
* `AgenticOrchestrator`'s intake → architecture flow is reachable only via the `/design` slash command, registered as `DesignArchitectureModule`.
* `/help` lists all registered modules with their descriptions.
* Session state is namespaced as `{active_module: str, module_state: {<module_name>: {...}}}`.
* Tests in `tests/agents/test_workflow_dispatcher.py` cover: command parsing, unknown-command fallback, module hand-off, multi-turn state preservation within a module, module switch clearing prior state.
* Revisit when (a) module count exceeds ~8 — signal that auto-discovery or config-driven registration is warranted; or (b) users consistently forget slash commands — signal that the LLM intent classifier (Option C) should be added.

## Pros and Cons of the Options

### Option A — Slash-command dispatcher

| | |
|---|---|
| **Good** | Deterministic — same input always routes to the same module. |
| **Good** | Zero LLM cost for routing. |
| **Good** | Self-documenting (`/help`). |
| **Good** | Matches existing Maker-Checker philosophy (human-driven state). |
| **Good** | Forward-compatible — Option C can be layered on top without API change. |
| **Bad** | User must learn the slash-command vocabulary. |
| **Bad** | No graceful handling of mistyped commands beyond a fallback message. |

### Option B — LLM intent classifier dispatcher

| | |
|---|---|
| **Good** | Pure natural language; no vocabulary to learn. |
| **Good** | Lower friction for first-time users. |
| **Bad** | Costs an LLM call per message even when the user knows exactly what they want. |
| **Bad** | Misclassification is silent and costly to debug. |
| **Bad** | Routing is non-deterministic across model versions. |
| **Bad** | Adds a new failure mode (classifier failure) on top of every module's own failure modes. |

### Option C — Hybrid

| | |
|---|---|
| **Good** | Best of both worlds in principle. |
| **Bad** | Adds Option B's complexity now when Option A is sufficient. |
| **Bad** | Premature: we cannot judge whether the LLM fallback is needed until we have usage data from Option A. |

### Option D — Status quo

| | |
|---|---|
| **Good** | Zero work. |
| **Bad** | Every new capability either forks the orchestrator or fragments the UI. |
| **Bad** | The user's stated goal ("main chat agnostic, modules bring functionality") is unreachable from this shape. |
