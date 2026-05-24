---
name: ADR-012-fastapi-backend
description: Adopt FastAPI as the HTTP API framework for the Azure Hello Architect application backend — supersedes the out-of-scope rejection of embedded web frameworks for the hello-world starter
---

# ADR-012: Adopt FastAPI for the Application Backend

## Status
Accepted

## applies_to
application

## Context and Problem Statement

The local MVP splits the in-process Streamlit monolith into a front-end + back-end pair. The back-end requires a real HTTP API surface for two reasons:

1. **Front/back split**: the Streamlit UI must call the backend over HTTP rather than importing Python modules directly, enforcing a clean separation of concerns and enabling independent deployment.
2. **Future web and mobile reuse**: the same HTTP surface should be consumable by web and mobile clients without rework. A raw socket handler cannot evolve into a multi-endpoint API without becoming a bespoke framework.

The existing stateless dispatch contract (slash-command routing via `WorkflowDispatcher`) maps naturally onto HTTP endpoints: each slash command becomes a POST route; session state lives in the caller.

The "Standard Library First" constraint recorded in `.out-of-scope.md` was scoped to the **hello-world starter template** — a template ethos discouraging unnecessary third-party dependencies in forks. It was never intended to govern a concrete application that ships a multi-endpoint HTTP API. This ADR consciously supersedes that rejection for the application backend.

## Considered Options

* **Option A — stdlib `http.server` reusing `src/main.py`**: extend the existing entry point with Python's built-in HTTP server to expose the dispatch contract over HTTP.
* **Option B — FastAPI**: introduce FastAPI (with Uvicorn as the ASGI server) as the HTTP API framework.

## Decision Outcome

Chosen option: **Option B — FastAPI**, because (i) request and response validation via Pydantic is non-negotiable on a multi-endpoint surface where malformed input can corrupt agent state; (ii) the OpenAPI schema is generated automatically, providing a machine-readable contract for front-end and future mobile clients; (iii) the ergonomics of route declaration, dependency injection, and async support are well-matched to the Maker-Checker loop's async agent calls; (iv) stdlib `http.server` would require hand-rolling all of the above and would converge on a bespoke, undertested framework with identical dependency overhead.

### Positive Consequences

* Request validation is enforced at the boundary — malformed payloads raise `422 Unprocessable Entity` before reaching agent logic.
* OpenAPI schema is auto-generated at `/docs` and `/openapi.json` — front-end and future mobile clients have a formal contract.
* Async route handlers compose naturally with async Azure SDK calls already used in `m_ai_client.py`.
* Pydantic models reuse the same validation library already present via `pydantic-settings` in `config.py`.
* The "Standard Library First" ethos is preserved for the template and `src/utils/` generic modules — this relaxation is scoped strictly to the application backend.

### Negative Consequences

* Adds `fastapi` and `uvicorn[standard]` to `pyproject.toml` dependencies.
* The "Standard Library First" rule in AGENTS.md Rule 6 requires an explicit annotation that the application backend is exempt — forks that do not need an HTTP API must justify keeping or removing these dependencies.

### Confirmation

* `fastapi` and `uvicorn` appear in `pyproject.toml` dependencies.
* The FastAPI/Flask entry is removed from `.out-of-scope.md`.
* `uv run pytest` passes green.
* Revisit if the project is ever downscoped back to a single-process Streamlit monolith — at that point this ADR can be superseded and the dependencies removed.

## Pros and Cons of the Options

### Option A — stdlib `http.server`

| | |
|---|---|
| **Good** | Zero new dependencies — consistent with hello-world starter ethos. |
| **Bad** | No request validation — malformed payloads reach agent logic unguarded. |
| **Bad** | No automatic OpenAPI schema — front-end contract is undocumented. |
| **Bad** | Async support requires manual threading or `asyncio` plumbing. |
| **Bad** | Routing, parsing, and error handling must be hand-rolled, producing a bespoke micro-framework. |

### Option B — FastAPI

| | |
|---|---|
| **Good** | Pydantic validation enforced at the boundary — bad input rejected before reaching agent logic. |
| **Good** | OpenAPI schema auto-generated — formal contract for all consumers. |
| **Good** | Async-native — composes cleanly with async Azure SDK calls. |
| **Good** | Minimal boilerplate for route declaration and dependency injection. |
| **Bad** | Adds `fastapi` and `uvicorn` to the dependency set. |
| **Bad** | Relaxes the "Standard Library First" constraint for the application backend — requires an explicit scoping note. |
