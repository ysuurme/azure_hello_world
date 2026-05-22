---
name: review
description: Use when validating a pull request, running the auto-fix loop on review findings, or enforcing architectural standards before a PR is approved for merge
---

# Review

## Overview

Prevents defects and architectural drift from reaching `main` by running a structured review cycle — Claude reviewer, auto-fix loop in an isolated worktree, and a hard HITL block when the loop cannot resolve a finding.

**Primary artifact:** Review report with all findings resolved or escalated, and a verified clean PR ready for `ship`.

## Scope

**Owns:** PR review execution (Claude), auto-fix and refine loop, finding verification and compaction, Senior Architect standard enforcement against `CONTEXT.md` principles, HITL escalation when the loop reaches its iteration limit.

**Does not own:** Code implementation (→ `tdd`), static topology analysis (→ `architecture`), merge and security governance (→ `ship`).

**Interfaces with:** `tdd` — review validates that GREEN and REFACTOR phases produced compliant code. `architecture` — blast-radius report from `architecture` is surfaced in the review. `ship` — a clean review (all findings resolved or explicitly escalated) is the gate for the `ship` phase.

## When to Use

- A PR is open and ready for review
- A `tdd` cycle has completed and findings need independent validation
- An `architecture` blast-radius report flagged at-risk modules that need code-level inspection

**Do NOT use for:** Writing implementation code (→ `tdd`), running topology analysis (→ `architecture`), merging or closing issues (→ `ship`).

## Required Inputs

- Open PR number
- `CONTEXT.md` (architectural constraints for Senior Architect enforcement)
- Blast-radius report from `architecture` (if available)

## Primary Outputs

- Review report with severity-tagged findings (BLOCK / WARN / INFO)
- Auto-fix commits in an isolated worktree (for each BLOCK/WARN resolved)
- HITL escalation comment + label (for findings not resolved after 3 iterations)
- Confirmed clean PR ready for `ship`

## Core Pattern

### Step 1 — Review

Run Claude as a Senior Architect reviewer against the PR diff:

```bash
gh pr diff <number> | claude --system "You are a Senior Architect. Review this diff for: (1) violations of boundaries in CONTEXT.md, (2) shallow modules, (3) internal mocking in tests, (4) missing acceptance criteria coverage. List findings with severity: BLOCK | WARN | INFO."
```

**BLOCK** — merge is prohibited until resolved.
**WARN** — must be addressed or explicitly waived before merge.
**INFO** — noted for future sessions, does not gate merge.

### Step 2 — Auto-Fix Loop

For each BLOCK or WARN finding, run the fix loop in an isolated worktree:

1. Generator agent applies the fix in the worktree
2. Run `pytest -x` — all tests must remain GREEN
3. Evaluator agent (Claude, separate system prompt) re-reviews the specific finding
4. If finding is resolved → mark resolved, move to next finding
5. If finding is not resolved → increment iteration counter

**Iteration limit: 3.** If a finding is not resolved after 3 iterations, stop the loop and escalate.

### Step 3 — Escalation (HITL Block)

When the loop hits the iteration limit:

```bash
gh pr comment <number> --body "## Review Escalation

**Finding:** <description>
**Iterations attempted:** 3
**Status:** UNRESOLVED — merge blocked

**Action required:** Human review needed before this PR can proceed.
Label: HITL"

gh pr edit <number> --add-label "HITL"
```

Do not attempt a 4th iteration. Do not merge. Surface to human and stop.

### Step 4 — Verify and Compact

Before marking the review complete:
- Re-read all findings against the current diff — not the diff at review start
- Consolidate related findings into a single summary comment
- Confirm all BLOCK findings are resolved or escalated

### Senior Architect Standard Enforcement

If a finding maps to a principle from `CONTEXT.md` or a constraint established in `refine` (encapsulation leak, tracer-bullet violation, mocking rule breach), it is automatically elevated to BLOCK regardless of initial severity. These are not negotiable.

## Quick Reference

| Severity | Gate | Resolution |
|---|---|---|
| BLOCK | Merge prohibited | Fix via loop or HITL escalation |
| WARN | Must address or waive | Fix, or explicit waiver comment in PR |
| INFO | No gate | Noted, tracked for future |
| Loop limit reached | Merge prohibited | HITL label + comment, human takes over |

**Context sensitivity:** Low for individual commit reviews. High for the fix loop — each fix iteration should start from a compact context to avoid compounding drift.

## Common Mistakes

**Reviewing stale diff.**
Always review the current diff, not an earlier snapshot. A fix may have already resolved the finding.

**Continuing past the iteration limit.**
Three iterations is the cap. A fourth attempt compounds drift and wastes context. Escalate and stop.

**WARN findings silently dropped.**
Every WARN must have either a fix commit or an explicit waiver comment in the PR. Silent drops become silent debt.

**Skipping blast-radius cross-reference.**
If `architecture` produced a blast-radius report for this PR, it must be referenced in the review. At-risk modules flagged there get BLOCK-severity treatment.
