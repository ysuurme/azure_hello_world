# Plan — Reference

Deep-dive reference for the `plan` skill. See [SKILL.md](SKILL.md) for the overview, scope,
and quick start. See [EXAMPLES.md](EXAMPLES.md) for a worked end-to-end session.

---

## Lean PRD — Full Schema

```markdown
## Problem Statement

One paragraph from the user's perspective. No implementation detail, no file paths, no
technology names unless they are constraints. Ends with a single sentence stating the
success criterion.

## User Stories

Minimum three; cover:
1. The happy path (primary flow)
2. The first likely failure mode
3. The second likely failure mode

Format: "As a [role], I want [action], so that [value]."

## Tracer Bullet

The single narrowest vertical slice that proves the full pipe works end-to-end:
<schema change> → <API endpoint> → <consumer observable response>

This becomes Issue #1 in the decomposed issue set. It must be independently mergeable.

## Implementation Decisions

Decisions agents need to make consistent choices across issues. Allowed content:
- Schema changes (field names, types, constraints)
- API contracts (endpoint paths, request/response shapes)
- Event type names and payload schemas
- Error codes and their semantics

Forbidden content:
- File paths or module names
- Library selection (belongs in ADRs)
- Class or function names

## Testing Decisions

For each module touched by this PRD, state:
- What constitutes a unit test (behaviour tested through which public interface)
- What constitutes an integration test (which boundary is crossed)
- What the acceptance criterion is (observable outcome, not internal state)

## Out of Scope

Concepts explicitly deferred. Each entry here becomes a `.out-of-scope.md` section post-merge.
Format: "X — deferred because Y."
```

---

## Issue Decomposition — Full Rules

### Ordering rules

1. **Tracer bullet first.** Always Issue #1, labelled `AFK` if fully automatable. Unblocks
   all subsequent issues that depend on the proven end-to-end path.
2. **Highest risk second.** The issue most likely to surface hidden constraints is Issue #2.
3. **Independent last.** Issues with no blockers and no blocked-by relationships can execute
   in any order.

### Sizing rules (Fibonacci)

| Size | Story Points | Expected Scope |
|------|-------------|----------------|
| XS | 1 | Single function or config change; no new tests needed |
| S | 2 | One module; one new test file |
| M | 3 | Two modules; two test files; no new dependencies |
| L | 5 | New bounded context or API endpoint; integration test required |
| XL | 8 | Spans multiple bounded contexts; architectural decision required |

Do not create issues larger than XL. An XL issue that cannot be split means the PRD tracer
bullet is too wide — return to `plan` and narrow it.

### HITL vs AFK — decision rubric

**HITL (Human-in-the-Loop):** Use when the issue requires any of:
- A human approval or review step that cannot be automated
- A decision with business or product implications (not purely technical)
- External service credentials or access the agent cannot provision
- A UI/UX decision requiring visual review

**AFK (Away-from-Keyboard):** Use when all of the following are true:
- The issue can be fully specified in the body with no ambiguity
- All acceptance criteria are mechanically verifiable by CI
- The implementation touches only bounded contexts the agent is authorised to modify
- No external credentials or approvals are required

### Issue body template

```markdown
**Goal**: <one-sentence goal>
**Description**: <what, why, and context — no implementation steps>

**Requirements**:
1. <requirement 1>
2. <requirement 2>

**Acceptance Criteria**:
- [ ] <criterion 1>
- [ ] <criterion 2>
```

---

## Deduplication — Full Procedure

```bash
# Step 1: Search open issues by key terms from the PRD
gh issue list --search "<term1> <term2>" --json number,title,state,labels

# Step 2: Search closed issues (in case an idea was rejected and closed)
gh issue list --search "<term1>" --state closed --json number,title,state

# Step 3: Check .out-of-scope.md knowledge base
grep "^## " .out-of-scope.md
grep -A5 "<relevant concept>" .out-of-scope.md

# Step 4: Cross-reference PRD user stories against found issues
# If overlap:   reference the existing issue; do not re-create it
# If rejected:  reference the .out-of-scope.md entry; do not re-propose
```

**Rule:** If a concept was rejected and added to `.out-of-scope.md`, it cannot be re-proposed
in this PRD. If new information makes reconsideration warranted, open a `refine` session
first — do not sneak it into a `plan` session.

---

## Testing Decisions — Reference by Module Type

| Module Type | Unit Test Target | Integration Test Target | Acceptance Criterion |
|-------------|-----------------|------------------------|---------------------|
| API endpoint | Request handler (schema validation, routing) | Full request → response cycle | HTTP status + response body matches contract |
| Domain service | Business logic through public method | Service → storage boundary | Observable state change or return value |
| Background task | Task function (mocked I/O) | Task → external service boundary | Side effect observable via storage or event |
| Data pipeline stage | Transform function (input → output) | Stage → next stage | Output schema valid + row count/quality check |
| CLI tool | Command handler (arg parsing, output) | Command → filesystem/process | stdout/stderr + exit code |

---

## .out-of-scope.md Record Format

Each deferred concept is appended as a `## ` section to `.out-of-scope.md` at the repo root.

```markdown
## <Concept Name>

**Date:** YYYY-MM-DD
**Reason:** <why deferred or rejected>
**Source ADR:** <ADR reference or N/A>

<Additional context if needed. One paragraph max.>

---
```

Append to `.out-of-scope.md`; do not create per-concept files. Headings are the searchable unit — `grep "^## " .out-of-scope.md` lists all rejected concepts.
