---
name: agentic-engineering
description: Use when building autonomous AI agents with the Claude API — Plan-Act-Observe loops, tool use, multi-agent coordination, context window management, agent state persistence, or testing agent behaviour
---

# Agentic Engineering

## Overview

Covers the design and implementation of autonomous AI agents. An agent is distinguished from an AI-backed API by its loop structure: it calls Claude multiple times across iterations, selects tools, observes results, and continues until a goal is achieved or the iteration cap is reached. All patterns are **provider-agnostic** — tool definitions, loop logic, and output validation are decoupled from the LLM provider. Core loop: **Plan → Act → Observe**.

**Primary artifact:** Functioning autonomous agent — tool use, structured outputs, multi-agent coordination — built provider-agnostically on the Anthropic SDK (primary) with the Google AI SDK as the secondary slot.

**Boundary with `application-engineering`:** If Claude makes **one call per API request**, that is an AI-backed API — load `application-engineering`. If Claude makes **multiple tool calls in a loop** before returning a final result, that is an agent — load this skill. A FastAPI endpoint that invokes an agent lives in `application-engineering`; the agent loop itself lives here.

## Scope

**Owns:** Plan-Act-Observe loop design and state management, tool definition standard (Pydantic → JSON Schema), structured output enforcement with correction on parse failure, provider-agnostic action executor, multi-agent coordination (Orchestrator + Handoff patterns), context window management within agent loops (sliding window, prompt caching), agent state persistence (Checkpointer pattern), agent testing patterns, OTel span emission per loop iteration.

**Does not own:** Single-turn Claude API calls and AI-backed REST endpoints (→ `application-engineering`), agent deployment infrastructure and environment provisioning (→ `harness`), data pipeline patterns used by agents (→ `data-engineering`), domain model design (→ `refine`).

**Interfaces with:** `application-engineering` — agents are exposed to clients via thin API endpoints; single-call AI patterns and streaming SSE to client live there. `harness` — agent runtime deployment, Planner/Generator/Evaluator split, environment provisioning. `tdd` — agent behaviour verified via RED-GREEN-REFACTOR; domain-specific testing patterns extend REFACTOR here.

## When to Use

- **Trigger:** Building an agent that calls Claude with tools across multiple iterations
- **Trigger:** Implementing structured output enforcement with correction on parse failure
- **Trigger:** Designing a Plan-Act-Observe loop or multi-turn autonomous flow
- **Trigger:** Coordinating multiple agents (Orchestrator + Handoff)
- **Trigger:** Managing context window limits within an agent loop
- **Trigger:** Writing tests for agent behaviour (not API contracts)
- **Trigger:** Persisting agent state for HITL approvals or crash recovery

**Do NOT use for:**
- Single-turn Claude calls within an API request (→ `application-engineering`)
- Agent deployment and infrastructure (→ `harness`)
- Data pipelines that agents consume (→ `data-engineering`)

## Required Inputs

- Goal specification and tool definitions (from `refine` or Lean PRD)
- Pydantic models for structured final response
- Acceptance criteria for agent behaviour (from `plan` testing decisions)

## Primary Outputs

- Plan-Act-Observe loop implementation with `MAX_ITERATIONS` cap
- Tool registry with `execute_tool` that never raises
- Structured output enforcement with correction-on-failure
- `AgentCheckpoint` persistence after every iteration
- Agent behaviour tests (mock at the LLM boundary, not at tool execution)

## tdd REFACTOR Phase Patterns

When the GREEN phase is complete, extend the REFACTOR phase with these agentic-engineering patterns:

- **`execute_tool` never raises:** If any tool implementation can raise an exception, wrap it. The agent loop must always receive a string result — errors are observations, not crashes.
- **Provider-agnostic executor isolation:** The `execute_tool` function must not import from `anthropic` or any other provider SDK. If it does, extract the provider coupling to the loop level.
- **Checkpointer completeness:** State is persisted after every iteration. If the Checkpointer only saves on success, add saves for `"running"` and `"awaiting_approval"` states.
- **Sliding window correctness:** The message history trim must preserve the system message and at least one user/assistant pair. If the trim removes the system prompt, fix the filter logic.
- **Termination coverage:** The test suite must cover all three termination paths — (1) successful parse, (2) `max_iterations` exceeded, (3) non-recoverable tool error. Missing coverage = missing termination guarantee.
- **OTel span per iteration:** Each loop iteration must emit a span. If spans are missing after GREEN, add them in REFACTOR — agent latency is invisible without per-iteration traces.

---

## Core Patterns

### The Plan-Act-Observe Loop

A recursive state machine. The agent receives a goal, generates a thought, selects a tool, executes it, and observes the result — repeating until the `final_response` schema is satisfied or `max_iterations` is reached.

```
[Goal]
  └─→ [Plan: Generate Thought]
        └─→ [Act: Select + Execute Tool]
              └─→ [Observe: Parse Result]
                    ├─→ loop (tool_use) ──────────────────────────────┐
                    │                                                  │
                    └─→ end_turn → [Structured Output: Pydantic]      │
                                         ├─→ parse ok  → DONE         │
                                         └─→ parse fail → Correction ─┘
```

**Termination conditions (in priority order):**
1. `final_response` parses into the target Pydantic model → success
2. `max_iterations` reached → raise typed `AgentMaxIterationsError` → hard stop
3. Tool returns non-recoverable terminal error → hard stop

**Always cap iterations — never remove this guard:**

```python
MAX_ITERATIONS = 10

for iteration in range(MAX_ITERATIONS):
    response = llm.generate(messages, tools=tools)
    # ... process response
else:
    raise AgentMaxIterationsError(f"Agent did not complete within {MAX_ITERATIONS} iterations")
```

### Structured Output Enforcement

Every final agent response must parse into a Pydantic model. On failure, inject the validation error back into the loop as a Correction Observation — not a crash.

```python
from pydantic import BaseModel, ValidationError

def parse_or_correct(raw: str, model: type[BaseModel], messages: list[dict]) -> BaseModel | None:
    try:
        return model.model_validate_json(raw)
    except ValidationError as e:
        messages.append({
            "role": "user",
            "content": f"Your response failed validation:\n{e}\n\nCorrect your output and retry.",
        })
        return None  # loop continues
```

### Provider-Agnostic Action Executor

The `execute_tool` function is the critical isolation layer. Tool execution must be completely decoupled from the LLM provider.

```python
from collections.abc import Callable

TOOL_REGISTRY: dict[str, Callable] = {
    "search_documents": search_documents,
    "transfer_to_agent": transfer_to_agent,
}

def execute_tool(tool_name: str, tool_input: dict) -> str:
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        return f"Error: Tool '{tool_name}' does not exist. Available tools: {list(TOOL_REGISTRY.keys())}"
    try:
        return str(fn(**tool_input))
    except Exception as e:
        return f"Error: {e}"
```

**Rule:** `execute_tool` never raises. It always returns a string. This prevents the agent from halting on recoverable errors.

---

## Quick Reference

### Tool Definition Template (Pydantic → JSON Schema)

```python
from pydantic import BaseModel, Field

class SearchDocuments(BaseModel):
    """
    Searches the document store for relevant content.
    Use when the user asks for information that requires document retrieval.
    Returns: list of matching document excerpts as a JSON string.
    """
    query: str = Field(..., description="The search query")
    max_results: int = Field(5, ge=1, le=20, description="Maximum number of results to return")
```

**Convert to provider format:**

```python
# Claude format
claude_tool = {
    "name": "search_documents",
    "description": SearchDocuments.__doc__,
    "input_schema": SearchDocuments.model_json_schema(),
}
```

**Tool description rules:** Write as technical documentation — what it does, when to use it, what each parameter means, what it returns. Vague descriptions → wrong tool selection.

### Context and State Management

| Scope | Mechanism |
|---|---|
| Short-term | Thread-local message histories trimmed via sliding window |
| Long-term | Vector search (RAG-based retrieval for cross-session knowledge) |
| Prompt cache | Cache system prompt + tool defs for iterative loops (Claude: `cache_control`) |

**Sliding window:**

```python
def trim_messages(messages: list[dict], max_tokens: int = 8_000) -> list[dict]:
    system = [m for m in messages if m["role"] == "system"]
    history = [m for m in messages if m["role"] != "system"]
    while estimate_tokens(history) > max_tokens and len(history) > 2:
        history = history[2:]
    return system + history
```

**Prompt caching (Claude) — cache long-lived static content only:**

```python
system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]
```

Do NOT cache per-turn messages or tool results.

### Multi-Agent Coordination

**Orchestrator Pattern:** A Lead Agent dispatches tasks to specialised sub-agents.

```python
class TransferToAgent(BaseModel):
    """
    Transfer control to a specialised sub-agent.
    Use when the current task requires expertise outside your own scope.
    Returns: the sub-agent's final response as a string.
    """
    agent_name: str = Field(..., description="Target agent identifier")
    task: str = Field(..., description="Clear, self-contained task description")
    context: dict = Field(default_factory=dict, description="Relevant state to pass forward")
```

**Rule:** The `context` dict must be self-contained. The sub-agent has no access to the orchestrator's message history.

### State Persistence (Checkpointer)

Save state after every loop iteration. Enables HITL approvals and crash recovery.

```python
@dataclass
class AgentCheckpoint:
    run_id: str
    iteration: int
    messages: list[dict]
    tool_calls: list[dict]
    status: str  # "running" | "awaiting_approval" | "complete" | "failed"
```

| Backend | When |
|---|---|
| **Firestore (GCP)** | Production; HITL approval workflows |
| **SQLite** | Local development and testing |

---

## Implementation

### Full Agent Loop (Claude API)

```python
import anthropic
from pydantic import BaseModel

client = anthropic.Anthropic()
MAX_ITERATIONS = 10

def run_agent(goal: str, tools: list[dict], response_model: type[BaseModel], system: str = "") -> BaseModel:
    messages = [{"role": "user", "content": goal}]

    for iteration in range(MAX_ITERATIONS):
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4_096,
            system=system,
            tools=tools,
            tool_choice={"type": "auto"},
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text = next((b.text for b in response.content if hasattr(b, "text")), "")
            result = parse_or_correct(text, response_model, messages)
            if result:
                return result

        elif response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            messages.append({"role": "user", "content": tool_results})

    raise AgentMaxIterationsError(f"Agent did not complete within {MAX_ITERATIONS} iterations")
```

### Streaming with SSE (Internal — Accumulate Before Executing)

```python
# Accumulate partial tool call JSON before executing — never execute on a fragment
with client.messages.stream(model="claude-opus-4-5", tools=tools, messages=messages) as stream:
    accumulated: dict[str, str] = {}

    for event in stream:
        if event.type == "content_block_start" and event.content_block.type == "tool_use":
            accumulated[event.content_block.id] = ""
        elif event.type == "content_block_delta" and hasattr(event.delta, "partial_json"):
            accumulated[str(event.index)] = accumulated.get(str(event.index), "") + event.delta.partial_json

    final = stream.get_final_message()
```

For streaming agent text output **to a client** (SSE to browser/CLI) → `application-engineering`.

### Agent Observability

Emit OpenTelemetry spans — one span per loop iteration. General OTel setup → `harness`. For agent-specific visualisation tooling → `docs/adr/ADR-006-agent-observability.md`.

```python
from opentelemetry import trace

tracer = trace.get_tracer("agent.loop")

for iteration in range(MAX_ITERATIONS):
    with tracer.start_as_current_span("agent.iteration") as span:
        span.set_attribute("agent.iteration", iteration)
        span.set_attribute("agent.stop_reason", response.stop_reason)
        span.set_attribute("agent.tool_calls", len([b for b in response.content if b.type == "tool_use"]))
```

---

## Common Mistakes

| Mistake | Consequence | Correction |
|---|---|---|
| Vague tool descriptions | Wrong tool selection or missing required params | Write as technical docs: what, when, params, returns |
| No `max_iterations` cap | Infinite loop → runaway cost | Always set `MAX_ITERATIONS = 10`; raise `AgentMaxIterationsError` |
| Executing partial streaming JSON | JSON parse error mid-loop | Accumulate all `partial_json` deltas before executing |
| Raising on tool execution error | Agent halts; no recovery | `execute_tool` never raises — return `"Error: <message>"` |
| Crashing on hallucinated tool name | Agent halts | Check `TOOL_REGISTRY`; return available tool names as feedback |
| Provider-coupled tool logic | Vendor lock-in | Keep `execute_tool` provider-agnostic; registry is the only coupling point |
| No state persistence | Crash = lost work; HITL impossible | Checkpoint after every iteration |
| Passing full history to sub-agent | Irrelevant context; performance degrades | Pass only a `context: dict` with the specific state the sub-agent needs |
| Building agent loop inside a router | Untestable, blocks the request thread | Agent loop runs in a service or background task; thin endpoint triggers it |
