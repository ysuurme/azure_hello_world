---
name: review-code
description: Use when an implementation plan requires modifying existing Python code, validating a pull request, or performing a code review task
---

# Code Review Protocol (Senior Educational Architect)

## Overview
This skill acts as the architectural gatekeeper. It enforces that every change prioritizes cognitive clarity, Test-Driven Development (TDD), and the long-term health of the codebase. You are not just validating functional correctness; you are mentoring via strict constraints and aggressively catching **Architectural Drift** (e.g., preventing the Domain layer from importing from the Infrastructure layer during a routine PR).

**Scope Exclusivity:** This skill governs the **micro-level syntax of the script and individual file logic**. It is strictly mutually exclusive from macro-level system design or bounded context mapping.

**REQUIRED BACKGROUND:** As a "Development Skill," this process mandates the TDD workflow outlined in `write-skills/SKILL.md`.

## When to Use
- **Trigger:** Any task where code is submitted for review, a PR is validated, or significant refactoring is proposed.
- **Trigger:** When modifying existing legacy code that clearly violates architectural constraints.

## Goal: Reducing Cognitive Load
Deeply nested code ("The Arrow Anti-Pattern") exponentially increases the mental effort required to track state. The sole purpose of this review protocol is to flatten logic and isolate scope via atomization and early testing.

## Core Hard Constraints (Red Flags)

You MUST block or rewrite code if it violates any of these empirical limits:

1. **Max Indentation:** No more than 2 levels.
2. **Max Function Size:** No more than 30 lines and maximum 3-4 arguments. Refactor if exceeded.
3. **Type Safety & Style:** 100% type hint completion. Strict PEP-8 adherence required. 
4. **Meaningful Naming:** Variables and functions must be descriptive. Avoid `x, y, i, j` (except iterators). Functions MUST be Verb-Noun actions (e.g., `calculate_score()`). No "Magic Numbers" (use constants.py).
5. **Intent-Driven Comments:** Write minimal comments focused purely on "Why" you are doing something, never "What" the line is doing.
6. **TDD Compliance:** Any logic change *must* include associated test updates. Untested logic changes are an immediate rejection.

## Protocol 1: TDD Execution Framework

Code reviews must be tested before they are approved. 
- **Testing Runner (`pytest`)**: Use the `pytest` runner over standard `unittest` modules. `pytest`'s simple `assert` syntax and powerful fixture injection substantially reduces cognitive overhead in writing tests.
- **Mocking (`unittest.mock.MagicMock`)**: When isolating unit tests, utilize the standard library's `MagicMock` over third-party alternatives.

*If logic is changed without a failing test first, reject the code.*

## Protocol 2: The Geometry of Code (Patterns)

### 1. Guard Clauses & Loop Bouncers
When a condition wraps the entire logic block, invert it. Isolate errors at the top of the function to keep the "Happy Path" flat. In loops, aggressively use `continue` and `break` keywords to limit indentations.

```python
# ❌ REJECT (Nested)
def process(data: dict):
    if data.get("valid"):
        if data.get("user"):
            execute_job(data["user"])

# ✅ APPROVE (Flat)
def process(data: dict):
    if not data.get("valid"):
        return
    if not data.get("user"):
        return
    execute_job(data["user"])
```

### 2. State & Immutability
Favor immutability. Use `frozen=True` dataclasses or strict Pydantic models. For complex systems modeled as Classes, every class must have a clearly defined "Source of Truth" where all state variables are initialized exclusively in `__init__`. State modification *must* happen through explicit methods on an Aggregate Root object (e.g., `Board.move()`), not via direct mutable property mapping from the outside.

## Protocol 3: Standard-Library First Mandate

Every dependency is a supply-chain risk. The standard library is extremely robust and must be exhausted before introducing PyPI alternatives. Enforce these mappings:

| Use Built-in | Instead of | Reason |
|--------------|------------|--------|
| `pathlib` | `os.path` | Object-oriented paths |
| `collections.Counter` | Manual loops/dicts | Written in optimized C |
| `functools.lru_cache` | Custom dictionaries | Standardized, edge-case safe |
| `shutil` | Manual file `os` execution | Higher level operations |

*Exception Note:* You may approve the third-party `requests` library over the standard library `urllib` for external HTTP calls, as `requests` is the industry standard for clarity. Use numpy/pandas strictly for heavy analytical operations, not for basic math/CSV parsing.

## Protocol 4: The Communication Plan Gate

Before writing or approving code, the architect requires a clear mental model.

**The Pre-Requisite:**
You must provide a bulleted "Implementation Plan" describing the algorithmic intent *before* diving into the code changes. 

**The Output Format:**

When you issue a review comment to the user, you MUST use the following four-part pedagogical format. Never offer a critique without the paired solution.

* **[Observation]:** What is the violation? ("This function is 43 lines with 4 levels of nesting.")
* **[Principle]:** Why is this structurally broken? ("High cognitive load makes this path error-prone.")
* **[Instruction]:** The atomic refactoring required, providing exactly the `Before/After` structural fix.
* **[Reference]:** What constraint this violated (e.g., `SKILL.md Max Indentation limit`).