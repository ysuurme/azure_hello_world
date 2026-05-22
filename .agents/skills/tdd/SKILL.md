---
name: tdd
description: Use when implementing a feature, fixing a bug, or refactoring — any time code needs to be written or changed against a defined acceptance criterion
---

# TDD

## Overview

Prevents implementation drift and untested code by enforcing a strict Red-Green-Refactor loop. Every behaviour is proven by a failing test before implementation begins; every implementation stays minimal until the test passes.

**Primary artifact:** Passing pytest suite with minimal, refactored implementation code.

## Scope

**Owns:** Red-Green-Refactor loop enforcement, acceptance criteria traceability to the PRD, mocking rules, deep-module REFACTOR target, test suite ergonomics with pytest.

**Does not own:** Test infrastructure provisioning (→ `harness`), PR creation (→ `version-control`), code review (→ `review`), performance infrastructure (→ domain skills).

**Interfaces with:** `plan` — testing decisions in the PRD drive the RED phase. `harness` — the TDD loop runs inside managed sessions; large test logs are offloaded. Domain skills (`application-engineering`, `data-engineering`, `agentic-engineering`) — extend the REFACTOR phase with domain-specific patterns.

## When to Use

- Implementing any story or acceptance criterion from a GitHub Issue
- Fixing a bug (write a failing test reproducing the bug first)
- Refactoring a shallow module into a deep module

**Do NOT use for:** Setting up test infrastructure (→ `harness`), reviewing completed code (→ `review`).

## Required Inputs

- GitHub Issue with acceptance criteria or testing decisions from the Lean PRD
- Existing test suite (read before writing new tests)
- Domain skill loaded for the REFACTOR phase (`application-engineering`, `data-engineering`, or `agentic-engineering`)

## Primary Outputs

- Passing pytest suite (`uv run pytest` exits 0)
- Minimal implementation code that satisfies acceptance criteria
- Refactored modules with deeper interfaces and less duplication

## Core Pattern

### Red — Write One Failing Test

Write exactly one pytest test that verifies a specific behaviour through a public interface.

**Rules:**
- Test must fail before any implementation is written — verify this
- Test targets a public interface, never internal implementation details
- Mocks are allowed only at system boundaries: external APIs, databases, time (`datetime.now`), filesystem
- Internal collaborators are never mocked — test through them

```python
# ✅ Tests public interface
def test_order_total_includes_tax():
    order = Order(items=[Item("widget", 10.00)], tax_rate=0.1)
    assert order.total() == 11.00

# ❌ Mocks an internal collaborator
def test_order_total():
    with patch("orders.TaxCalculator") as mock:
        ...
```

### Green — Minimal Implementation

Write only enough code to make the current test pass. No more.

**Rules:**
- Do not anticipate future tests — implement only what the current test requires
- Do not write horizontal slices (e.g. the full data layer) while a single test is RED
- Hardcoding is acceptable in GREEN if it makes the test pass — REFACTOR will fix it

### Refactor — Deep Modules

Once GREEN, refactor to make the implementation deep: maximum behaviour behind the smallest possible interface.

**Deep module checklist:**
- [ ] Could the interface be smaller without losing expressiveness?
- [ ] Is there duplication that should move behind the interface?
- [ ] Does the module expose implementation details in its public surface?
- [ ] Are there two responsibilities that should be split?

**Refactor rules:**
- All tests must remain GREEN throughout
- Public interface must stay constant or shrink — never grow during REFACTOR
- Domain skills extend this phase with language-specific patterns

### Acceptance Criteria Traceability

Every test must map to a user story or testing decision in the Lean PRD. If a test cannot be traced to the PRD, it is either out of scope (delete it) or the PRD is incomplete (update it before continuing).

## Quick Reference

| Phase | Goal | Forbidden |
|---|---|---|
| RED | One failing test through public interface | Mocking internal collaborators |
| GREEN | Minimal code to pass current test | Anticipating future tests |
| REFACTOR | Deep module: shrink interface, hide complexity | Growing the public surface |

**Context sensitivity:** High during RED and GREEN (precise instruction following required). REFACTOR is lower sensitivity. If context fill reaches Transition Zone mid-loop, compact before starting the next RED phase.

## Common Mistakes

**Writing implementation before the test is confirmed failing.**
Run `pytest -x` first. If it passes without any implementation, the test is testing nothing.

**Mocking internal collaborators.**
Internal mocks make tests pass without proving behaviour. When the implementation changes, the mock masks the regression. Only mock at system boundaries.

**REFACTOR grows the interface.**
Adding a new public method during REFACTOR is scope creep. New behaviour belongs in a new RED phase.

**Test cannot be traced to the PRD.**
Tests that aren't in the PRD represent undiscussed scope. Trace it or delete it.
