---
name: application-engineering
description: Use when designing or building AI-backed APIs and services — REST endpoints, request/response contracts, Claude API integration (single-call patterns), streaming AI responses to clients, OTel instrumentation, authentication, or service-to-service communication
---

# Application Engineering

## Overview

Covers the design and implementation of production AI application services. The primary use case is a FastAPI service that calls the Claude API as a dependency — one Claude call per API request, returning structured or streamed results. **FastAPI** is the standard framework; **Anthropic Python SDK** is the primary AI provider; **Pydantic** validates every boundary. OTel instrumentation is mandatory from day one (ADR-003).

**Primary artifact:** Production AI-backed API or service — Claude as a replaceable port, OTel-instrumented, Pydantic-contracted.

**Boundary with `agentic-engineering`:** This skill owns **single-call** Claude patterns — one `messages.create` per API request. If the service drives a Plan-Act-Observe loop with multiple tool calls across iterations, that loop belongs in `agentic-engineering`. A FastAPI endpoint that *invokes* an agent lives here; the agent itself lives there.

## Scope

**Owns:** REST API design and implementation, input validation and serialisation at request boundaries (Pydantic), Claude API integration as a service dependency (single-turn completions, structured outputs via tool_use, SSE streaming to client), AI port/adapter pattern (provider-agnostic abstraction), OTel instrumentation at the request boundary, AI error handling (rate limits, timeouts, exponential backoff), authentication and authorisation patterns, background task design, service-to-service communication, contract testing for API consumers.

**Does not own:** Plan-Act-Observe loops and multi-turn autonomous agents (→ `agentic-engineering`), agent state persistence and multi-step orchestration (→ `agentic-engineering`), infrastructure and environment provisioning (→ `harness`), data pipeline design (→ `data-engineering`), domain model design (→ `refine`).

**Interfaces with:** `refine` — application layer implements ports defined during alignment; no business logic in routers. `tdd` — contract tests drive the RED phase for API behaviour. `agentic-engineering` — an API endpoint may *invoke* an agent; agent internals live there. `harness` — deployment, environment, and managed identity for secrets.

## When to Use

- **Trigger:** Designing or implementing a REST API endpoint that calls Claude
- **Trigger:** Defining request/response models and validation
- **Trigger:** Instrumenting a service with OTel traces and structured logs
- **Trigger:** Setting up authentication or authorisation
- **Trigger:** Implementing streaming AI responses to a client via SSE
- **Trigger:** Adding exponential backoff for Claude API rate limits

**Do NOT use for:**
- Plan-Act-Observe agent loops (→ `agentic-engineering`)
- Multi-step orchestration with tool calls across iterations (→ `agentic-engineering`)
- Infrastructure or deployment configuration (→ `harness`)

## Required Inputs

- Domain model and port interfaces (from `refine`)
- Acceptance criteria from Lean PRD testing decisions (from `plan`)
- ADR-003 (OTel instrumentation standard) and ADR-004 (IAM provider) from `docs/adr/`

## Primary Outputs

- FastAPI router with Pydantic-validated request/response models
- `AICompletionPort` abstraction with `ClaudeAdapter` implementation
- OTel-instrumented service layer (one span per Claude call)
- Contract tests using `FakeAIPort` (Claude never called in tests)

## tdd REFACTOR Phase Patterns

When the GREEN phase is complete, extend the REFACTOR phase with these application-engineering patterns:

- **Router → Service → Port:** Business logic must not live in the router. Move any logic from routers into the service layer. Claude must be accessed only through an abstract `AICompletionPort`.
- **Deep service modules:** The service's public interface should be minimal — one method per use case. Move validation, retry, and OTel span creation behind this interface.
- **Port/adapter split:** If the `ClaudeAdapter` is too thick (contains business logic), extract it. Adapters translate; services orchestrate.
- **Contract test completeness:** Every public endpoint must have a contract test using `FakeAIPort`. If a test calls the real Claude, extract it into an integration test suite gated by an env var.
- **OTel span per Claude call:** Each `AICompletionPort.complete` or `complete_structured` call must be wrapped in a tracer span. If it isn't after GREEN, add it in REFACTOR.

---

## Core Patterns

### FastAPI — Pydantic-Native, OpenAPI by Default

```python
from fastapi import FastAPI, Depends
from pydantic import BaseModel

app = FastAPI(title="AI Application API", version="1.0.0")

class AnalyseRequest(BaseModel):
    text: str
    language: str = "en"

class AnalyseResponse(BaseModel):
    summary: str
    sentiment: str
    key_points: list[str]

@app.post("/v1/analyse", response_model=AnalyseResponse)
async def analyse(
    request: AnalyseRequest,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalyseResponse:
    return await service.analyse(request)
```

OpenAPI docs auto-generated at `/docs` (Swagger UI) and `/redoc`. Always set `response_model=` — without it FastAPI cannot generate correct OpenAPI docs and may leak internal fields.

### Router → Service → Port (Hexagonal)

Business logic never lives in the router. Claude is accessed only through an abstract port.

```
routers/        # FastAPI routes — input validation + response shaping only
services/       # Business logic — calls ports, orchestrates domain logic
ports/          # Abstract interfaces (AICompletionPort, etc.)
adapters/       # Concrete implementations injected via Depends()
```

```python
# ✅ Thin router, Claude behind a port
@router.post("/analyse", response_model=AnalyseResponse)
async def analyse(request: AnalyseRequest, service: AnalysisService = Depends(get_service)):
    return await service.analyse(request)

# ❌ Claude call directly in router — no abstraction, untestable
@router.post("/analyse")
async def analyse(request: AnalyseRequest):
    client = AsyncAnthropic()
    response = await client.messages.create(...)
    return parse(response)
```

### Claude API Integration — Single-Call Pattern

```python
# ports/ai_port.py
from abc import ABC, abstractmethod
from pydantic import BaseModel

class AICompletionPort(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system: str = "") -> str: ...

    @abstractmethod
    async def complete_structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel: ...

# adapters/claude_adapter.py
from anthropic import AsyncAnthropic
from ports.ai_port import AICompletionPort

class ClaudeAdapter(AICompletionPort):
    def __init__(self, model: str = "claude-opus-4-5"):
        self._client = AsyncAnthropic()
        self._model = model

    async def complete(self, prompt: str, system: str = "") -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def complete_structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            tools=[{
                "name": "return_result",
                "description": f"Return the structured result as {schema.__name__}",
                "input_schema": schema.model_json_schema(),
            }],
            tool_choice={"type": "tool", "name": "return_result"},
            messages=[{"role": "user", "content": prompt}],
        )
        tool_block = next(b for b in response.content if b.type == "tool_use")
        return schema(**tool_block.input)
```

**Register via dependency injection:**

```python
from functools import lru_cache
from fastapi import Depends
from ports.ai_port import AICompletionPort
from adapters.claude_adapter import ClaudeAdapter

@lru_cache
def get_ai_port() -> AICompletionPort:
    return ClaudeAdapter()

def get_analysis_service(ai: AICompletionPort = Depends(get_ai_port)) -> AnalysisService:
    return AnalysisService(ai_port=ai)
```

This makes Claude swappable without touching business logic. Tests inject a `FakeAIPort`.

### OTel Instrumentation at the Request Boundary

Instrument at the service layer, not the router. Emit one span per Claude call. Follow ADR-003 — no proprietary cloud SDK in instrumentation paths.

```python
from opentelemetry import trace
from opentelemetry.semconv.ai import SpanAttributes   # opentelemetry-semantic-conventions-ai

tracer = trace.get_tracer(__name__)

class AnalysisService:
    def __init__(self, ai_port: AICompletionPort) -> None:
        self._ai = ai_port

    async def analyse(self, request: AnalyseRequest) -> AnalyseResponse:
        with tracer.start_as_current_span("ai.analyse") as span:
            span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, "claude-opus-4-5")
            span.set_attribute(SpanAttributes.LLM_REQUEST_TYPE, "completion")
            result = await self._ai.complete_structured(
                prompt=f"Analyse the following text:\n\n{request.text}",
                schema=AnalyseResponse,
            )
            span.set_attribute(SpanAttributes.LLM_RESPONSE_FINISH_REASON, "tool_use")
            return result
```

### Streaming AI Responses via SSE

Stream Claude output directly to the client. Do not buffer the full response.

```python
import json
from fastapi.responses import StreamingResponse
from anthropic import AsyncAnthropic

client = AsyncAnthropic()

@router.post("/v1/generate")
async def generate(request: GenerateRequest) -> StreamingResponse:
    async def token_stream():
        async with client.messages.stream(
            model="claude-opus-4-5",
            max_tokens=2048,
            messages=[{"role": "user", "content": request.prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield f"data: {json.dumps({'token': text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(token_stream(), media_type="text/event-stream")
```

### AI Error Handling — Rate Limits and Timeouts

```python
import asyncio
from anthropic import RateLimitError, APITimeoutError, APIStatusError

MAX_RETRIES = 3

async def complete_with_retry(ai_port: AICompletionPort, prompt: str) -> str:
    for attempt in range(MAX_RETRIES):
        try:
            return await ai_port.complete(prompt)
        except RateLimitError:
            if attempt == MAX_RETRIES - 1:
                raise
            await asyncio.sleep(2 ** attempt)          # exponential backoff: 1s, 2s, 4s
        except APITimeoutError:
            if attempt == MAX_RETRIES - 1:
                raise
        except APIStatusError as e:
            if e.status_code >= 500 and attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)
            else:
                raise
    raise RuntimeError("Unreachable")
```

Never catch `anthropic.AuthenticationError` in retry logic — it is not transient.

---

## Quick Reference

### API Style Selection

| Style | When | Framework |
|---|---|---|
| **REST** | Transactional operations (CRUD, AI completion endpoints, webhooks) | FastAPI |
| **SSE** | Streaming AI responses to browser or CLI clients | FastAPI `StreamingResponse` |
| **GraphQL** | Query-heavy clients needing flexible access to nested data | Strawberry + FastAPI |

### Auth Patterns

| Use case | Pattern |
|---|---|
| User-facing API | OAuth2 with JWT (`fastapi.security.OAuth2PasswordBearer`) |
| Service-to-service | API key header (`X-API-Key`) validated via dependency |
| Managed identity | Azure Managed Identity / GCP Service Account — no key in code |

For self-hosted IAM selection → `docs/adr/ADR-004-iam-provider-selection.md`.
Never put secrets in environment variables — fetch from secrets manager at runtime via managed identity (→ `harness`).

### API Versioning

Always version from day one:
```python
router = APIRouter(prefix="/v1", tags=["analysis"])
```

---

## Implementation

### Project Structure

```
src/
  api/
    routers/          # FastAPI route handlers — thin, no business logic
    services/         # Business logic layer — orchestrates ports
    ports/            # Abstract interfaces: AICompletionPort, etc.
    adapters/         # Concrete implementations: ClaudeAdapter, etc.
    models/           # Pydantic request/response models
  main.py             # FastAPI app initialisation and lifespan
```

### Contract Testing

```python
# tests/api/test_analyse_contract.py
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from ports.ai_port import AICompletionPort

class FakeAIPort(AICompletionPort):
    async def complete(self, prompt: str, system: str = "") -> str:
        return "Mocked response"

    async def complete_structured(self, prompt: str, schema):
        return schema(summary="stub", sentiment="neutral", key_points=[])

def test_analyse_response_contract(client: TestClient) -> None:
    response = client.post("/v1/analyse", json={"text": "Hello world"})
    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
    assert "sentiment" in body
    assert "key_points" in body
```

Test the contract, not the AI output. The `FakeAIPort` is the controlled collaborator — Claude itself is never called in unit tests.

### Running with UV

```bash
uv run uvicorn src.main:app --reload   # Dev server
uv run pytest tests/                   # Run contract and integration tests
```

---

## Common Mistakes

**Claude call directly in the router.**
Untestable, unswappable, no OTel span. Every Claude call goes through an `AICompletionPort` adapter.

**Using a Plan-Act-Observe loop inside an API service.**
If the service needs to call Claude multiple times with tools in a loop, that is an agent — load `agentic-engineering` and expose the agent via a thin endpoint here.

**No `response_model=` on endpoints.**
FastAPI cannot generate correct OpenAPI docs and may serialise internal fields. Every endpoint must declare `response_model=`.

**Secrets in environment variables.**
Environment variables are visible in process lists and container inspection. Fetch secrets from a secrets manager at runtime via managed identity (→ `harness`).

**Catching `RateLimitError` without backoff.**
Immediate retry on rate limit triggers another rate limit. Always use exponential backoff.

**No OTel span on AI calls.**
AI calls are the most expensive and latency-sensitive operation in the service. If they are not instrumented, debugging production latency is guesswork.

**Missing `Closes #N` in commits.**
Version control convention from `version-control` — the PR auto-close link is required. `ship` validates this before merge.

**No versioning from day one.**
Always prefix routes with `/v1/`. Retrofitting versioning onto an unversioned API breaks existing clients.
