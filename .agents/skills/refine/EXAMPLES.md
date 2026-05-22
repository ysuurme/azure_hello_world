# Refine — Examples

Golden end-to-end session demonstrating the `refine` skill. See [SKILL.md](SKILL.md) for
the quick-start and [REFERENCE.md](REFERENCE.md) for the full decision-tree and schema
reference.

---

## Example 1: Adding an SSE Streaming Endpoint

**Context:** An engineer wants to add a Server-Sent Events (SSE) endpoint that streams Claude
completions to a browser client. No SSE infrastructure exists yet.

### Step 0 — Context fill check

```
Agent estimates context fill: ~18k tokens. Smart Zone — proceed.
```

### Step 1 — Codebase orientation

Agent reads (in order):
1. `CONTEXT.md` — identifies `project_type: application`, no SSE in bounded contexts.
2. `AGENTS.md` — confirms skill sequence: refine → architecture → plan → tdd.
3. `docs/adr/ADR_STRUCTURE.md` — loads ADR-003 (API patterns), ADR-007 (project type).
4. `src/main.py` — finds `HTTPHandler` serving `GET /hello` only.
5. `src/config.py` — finds `Settings`; no streaming config yet.

Agent's first message to the human:

> I've read the codebase. The entry point is `HTTPHandler` in `src/main.py`, which handles
> `GET /hello` only today. No SSE infrastructure exists.
>
> Before we design the endpoint I need to align on three things:
>
> 1. **Term "stream"** — do you mean SSE (`text/event-stream`, long-lived HTTP) or chunked
>    transfer encoding? My recommendation: **SSE** — it is browser-native and restartable.
> 2. **Bounded context** — the new endpoint belongs in `src/`. I'd add a `streaming` bounded
>    context to `CONTEXT.md`. Agree?
> 3. **Claude call model** — single streaming call per SSE connection or multi-turn?
>    My recommendation: **single call** first (tracer bullet).

### Step 2 — Glossary agreement

Human responds: "SSE, yes. Single call for now."

Agent adds to `CONTEXT.md`:

```markdown
# Glossary addition
SSE Endpoint | A GET endpoint returning Content-Type: text/event-stream that emits Claude
               completion tokens as `data:` events. | Not WebSocket — no bidirectional
               channel needed.

# Bounded Contexts addition
src/streaming/ | Owns: SSE response lifecycle, Claude streaming adapter |
                 Does Not Own: authentication (→ src/auth/), prompt construction (→ refine)
```

### Step 3 — ADR trigger

The `http.server` stdlib does not support SSE natively. "Standard Library First" (ADR-003)
is under pressure. Agent writes `docs/adr/ADR-010-sse-stdlib-workaround.md`:

```markdown
# ADR-010: SSE via http.server manual write

## Status
Accepted

## applies_to
application

## Context and Problem Statement
`http.server` does not expose a streaming write API. SSE requires holding the connection
open and flushing individual `data:` events. A third-party server (FastAPI, aiohttp) would
resolve this cleanly but violates ADR-003 (Standard Library First).

## Considered Options
- Option A: http.server with manual `wfile.write` + `flush()` loop
- Option B: Add FastAPI / uvicorn

## Decision Outcome
**Chosen:** Option A — stdlib-only approach is sufficient for the tracer bullet. Option B
deferred to Out of Scope.

### Negative Consequences
- Manual Content-Type and event framing required in `src/streaming/`.
```

### Step 4 — Agent Brief output

```markdown
# Agent Brief: SSE Streaming Endpoint

## Problem Statement
Browser clients need to receive Claude completion tokens in real time without polling.
Success: a single `GET /stream?q=<prompt>` request returns a `text/event-stream` response
where each `data:` event contains one token, ending with `data: [DONE]`.

## Glossary Additions
| SSE Endpoint | GET endpoint returning text/event-stream; emits Claude tokens as data: events | Not WebSocket |

## Bounded Context Changes
New context: src/streaming/ — owns SSE lifecycle and Claude streaming adapter.

## Interfaces

### GET /stream
**Input:** query param `q` (string, max 1 000 chars, required)
**Output:** `Content-Type: text/event-stream`; each event: `data: <token>\n\n`; terminal: `data: [DONE]\n\n`
**Error States:** HTTP 400 if `q` absent; `data: error <message>\n\n` then close on Claude failure
**Testability:** mock Claude SDK; assert emitted event sequence matches expected token list

## Constraints
- ADR-003 (Standard Library First): use http.server + manual write; no FastAPI
- ADR-010 (SSE workaround): manual Content-Type and event framing in src/streaming/
- No hardcoded secrets: Claude API key via Settings.claude_api_key

## Out of Scope
- Multi-turn streaming — deferred: single call first
- FastAPI migration — rejected per ADR-003

## Tracer Bullet
`GET /stream?q=hello` → three hardcoded tokens → `data: [DONE]` → connection closes.
```

**Outcome:** Agent Brief signed off. `architecture` session can begin.

---

## Example 2: Revising a Glossary Term Mid-Session

**Context:** During grilling, the engineer uses "pipeline" to mean two different things in
two consecutive sentences.

**Agent action:**

> You used "pipeline" twice with different meanings:
> - "the data pipeline" → appears to mean the ETL process (Raw → Bronze → Silver → Gold)
> - "the request pipeline" → appears to mean the HTTP middleware chain
>
> These are distinct concepts. I recommend:
> - **ETL Pipeline** — the Medallion data flow owned by `data-engineering`
> - **Request Pipeline** — the HTTP handler chain owned by `application-engineering`
>
> Which term applies to what you are designing right now?

This surfaces a broken window (ambiguous shared language) before it propagates into the
Agent Brief and creates divergent implementations.
