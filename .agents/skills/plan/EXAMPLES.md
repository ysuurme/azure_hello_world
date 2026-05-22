# Plan — Examples

Golden end-to-end session demonstrating the `plan` skill. See [SKILL.md](SKILL.md) for the
quick-start and [REFERENCE.md](REFERENCE.md) for the full PRD schema and decomposition rules.

The session below continues from the `refine` and `architecture` examples. See
[refine/EXAMPLES.md](../refine/EXAMPLES.md) and
[architecture/EXAMPLES.md](../architecture/EXAMPLES.md) for the preceding sessions.

---

## Example 1: Decomposing the SSE Streaming Endpoint PRD

**Inputs available:**
- Agent Brief: SSE Streaming Endpoint (from `refine`)
- Blast-radius report: `docs/arch/blast-radius.md` (from `architecture`)

### Step 1 — Deduplicate

```bash
# Search open issues
gh issue list --search "SSE streaming endpoint" --json number,title,state
# → []

gh issue list --search "stream Claude" --json number,title,state
# → []

# Check .out-of-scope.md
grep "^## " .out-of-scope.md
# → ## Embedded web framework (FastAPI/Flask) in the hello-world starter   (FastAPI rejected — not relevant to this SSE work)
# SSE itself is not rejected — proceed.
```

No duplicates found. No rejected concepts re-proposed.

### Step 2 — Write Lean PRD as GitHub Issue

```bash
gh issue create \
  --title "feat: SSE streaming endpoint (Lean PRD)" \
  --label "HITL" \
  --body "$(cat << 'EOF'
## Problem Statement
Browser clients need to receive Claude completion tokens in real time. Today the only
endpoint is GET /hello, which returns a complete response. Success: a client can open
GET /stream?q=<prompt> and receive tokens as they arrive without polling.

## User Stories
- As a browser developer, I want to stream Claude responses token-by-token, so that
  users see output immediately instead of waiting for the full completion.
- As a browser developer, when I submit an empty prompt, I want a 400 error, so that
  I know the request was malformed before the stream opens.
- As a browser developer, when Claude returns an error, I want a `data: error <message>`
  event followed by connection close, so that I can display the failure gracefully.

## Tracer Bullet
GET /stream?q=hello → three hardcoded tokens → data: [DONE] → connection closes.
No Claude integration yet — proves SSE framing only.

## Implementation Decisions
- Endpoint: GET /stream, query param q (string, max 1 000 chars, required)
- Response: Content-Type: text/event-stream; each event: `data: <token>\n\n`
- Terminal event: `data: [DONE]\n\n`
- Error response: HTTP 400 if q missing; `data: error <message>` on Claude failure

## Testing Decisions
- Unit: mock Claude SDK; assert emitted event sequence matches expected token list
- Integration: real HTTP request; assert SSE event sequence via client parser
- Acceptance: GET /stream?q=hello returns ≥ 1 data: events followed by data: [DONE]

## Out of Scope
- Multi-turn streaming — deferred: single call first
- Authentication on /stream — deferred: separate bounded context
- WebSocket alternative — rejected: SSE is sufficient (unidirectional)
EOF
)"
```

### Step 3 — Decompose into child issues

```bash
# Issue 1: Tracer bullet (AFK — fully automatable)
gh issue create \
  --title "feat(streaming): tracer bullet — GET /stream returns SSE token sequence" \
  --label "AFK" \
  --body "$(cat << 'EOF'
**Goal**: Prove the full SSE pipe works end-to-end with hardcoded tokens.
**Description**: Implement the minimal GET /stream endpoint that streams three hardcoded
tokens and emits data: [DONE]. No Claude integration yet — validates SSE framing only.

**Requirements**:
1. GET /stream returns Content-Type: text/event-stream
2. Response body: data: token1\n\ndata: token2\n\ndata: token3\n\ndata: [DONE]\n\n
3. Connection closes after [DONE]

**Acceptance Criteria**:
- [ ] pytest: assert response Content-Type is text/event-stream
- [ ] pytest: assert event sequence equals [token1, token2, token3, [DONE]]
- [ ] CI passes
EOF
)"

# Issue 2: Claude integration (AFK)
gh issue create \
  --title "feat(streaming): integrate Claude streaming SDK into GET /stream" \
  --label "AFK" \
  --body "$(cat << 'EOF'
**Goal**: Replace hardcoded tokens with a real Claude completion stream.
**Description**: Wire the Claude SDK streaming call into the tracer-bullet endpoint.
Claude API key is read from Settings. Error states: 400 on missing q, data: error event
on Claude failure.

**Requirements**:
1. Claude SDK streaming call per connection; q param forwarded as user message
2. Each token emitted as data: <token>\n\n
3. Stream ends with data: [DONE]\n\n
4. HTTP 400 returned if q is absent
5. data: error <message> emitted on Claude error then connection closes

**Acceptance Criteria**:
- [ ] pytest (mocked Claude): token sequence matches mock response
- [ ] pytest: missing q returns HTTP 400
- [ ] pytest: Claude error emits data: error <message> then closes
- [ ] CI passes
EOF
)"

# Issue 3: Integration test (HITL — needs human review of test scenario)
gh issue create \
  --title "test(streaming): end-to-end integration test for GET /stream" \
  --label "HITL" \
  --body "$(cat << 'EOF'
**Goal**: Verify the SSE endpoint against a real HTTP client.
**Description**: Write an integration test that makes a real HTTP request to a running
server and parses the SSE event stream. Requires human review to confirm the test
scenario covers the acceptance criterion before merge.

**Requirements**:
1. Integration test starts a real server instance (localhost, ephemeral port)
2. Client reads SSE events until [DONE]
3. Asserts ≥ 1 token received before [DONE]

**Acceptance Criteria**:
- [ ] Integration test passes with a real Claude API key in CI
- [ ] Human reviews and approves the test scenario before merge
EOF
)"
```

### Outcome

Plan session produces:

- 1 Lean PRD (HITL) — awaits human sign-off before implementation begins
- 3 decomposed issues: 2 AFK (fully automatable), 1 HITL (requires human review)
- No duplicates found; no `.out-of-scope.md` entries violated
- Multi-turn streaming and auth appended as `## ` sections to `.out-of-scope.md` post-merge

**Next:** `tdd` session opens Issue #1 (tracer bullet) and enters the RED phase.
