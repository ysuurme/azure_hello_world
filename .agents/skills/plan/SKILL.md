---
name: plan
description: Use when synthesising a Lean PRD from an Agent Brief, decomposing requirements into GitHub Issues, or checking scope against existing issues and out-of-scope decisions
---

# Plan

## Overview

Prevents unbounded scope and re-proposed rejected ideas by turning the Agent Brief into a structured Lean PRD, then breaking it into labelled GitHub Issues before any code is written.

**Primary artifact:** Lean PRD published as a GitHub Issue, decomposed into HITL/AFK-labelled grabbable issues.

## Scope

**Owns:** Lean PRD synthesis, tracer bullet framing, user story format, issue decomposition with HITL/AFK labelling, deduplication against open issues and `.out-of-scope.md`, testing decisions per PRD.

**Does not own:** Domain glossary or shared language (→ `refine`), static analysis or blast-radius data (→ `architecture`), code implementation (→ `tdd`), PR creation or branch naming (→ `version-control`).

**Interfaces with:** `refine` — Agent Brief is the primary input. `architecture` — blast-radius findings gate scope decisions. `tdd` — testing decisions in the PRD define acceptance criteria for the RED phase. `version-control` — issues created here are the targets for feature branches.

## When to Use

- Agent Brief has been signed off by `refine`
- Architecture map and blast-radius report are available from `architecture`
- Ready to break work into trackable, executable issues

**Do NOT use for:** Glossary or boundary decisions (→ `refine`), topology or dependency analysis (→ `architecture`), writing any code (→ `tdd`).

## Required Inputs

- Signed-off Agent Brief (from `refine`)
- Blast-radius report (from `architecture`)
- Access to `gh` CLI for deduplication and issue creation
- `.out-of-scope.md` knowledge base (flat file — one `## ` heading per rejected concept)

## Primary Outputs

- Lean PRD published as a GitHub Issue
- Decomposed child issues, each labelled `HITL` or `AFK`
- `.out-of-scope.md` entries for explicitly deferred concepts

## Core Pattern

### Step 1 — Deduplicate

Before writing a single word of PRD:
```bash
gh issue list --search "<key terms>" --json number,title,state
```
Also check `.out-of-scope.md` for rejected concepts. If the idea was rejected before, it does not get re-proposed — reference the original rejection instead.

### Step 2 — Lean PRD

Write the PRD as a GitHub Issue with this structure:

```markdown
## Problem Statement
One paragraph from the user's perspective. No implementation detail.

## User Stories
- As a [role], I want [action], so that [value].
(Minimum 3; cover the happy path and the two most likely failure modes)

## Tracer Bullet
The single narrowest vertical slice that proves the pipe works:
schema change → API endpoint → consumer response.
This is Issue #1 in decomposition.

## Implementation Decisions
Schema changes and API contracts only. No file paths.

## Testing Decisions
What makes a good test for this module. Drives the RED phase in `tdd`.

## Out of Scope
Anything explicitly deferred. Feeds `.out-of-scope.md` after merge.
```

### Step 3 — Issue Decomposition

Break the PRD into individual GitHub Issues. Rules:

- **Tracer bullet first** — always Issue #1, labelled `AFK` if fully automated
- Each issue is independently mergeable
- Every issue gets exactly one label: `HITL` or `AFK`

**HITL** — Human-in-the-Loop: issue requires a decision or approval at some point before it can close.
**AFK** — Away-from-Keyboard: agent can execute start-to-finish without interruption.

```bash
gh issue create \
  --title "feat: <title>" \
  --body "<body>" \
  --label "AFK"   # or HITL
```

## Quick Reference

| Step | Action | Tool |
|---|---|---|
| Deduplicate | Search open issues + `.out-of-scope.md` | `gh issue list` |
| PRD | Create as GitHub Issue | `gh issue create` |
| Decompose | One issue per vertical slice | `gh issue create` |
| Label | HITL or AFK on every issue | `--label` flag |

**Context sensitivity:** Medium. PRD synthesis requires coherent reasoning — run in Smart Zone when possible. Deduplication queries are stateless and safe at any fill level.

## Common Mistakes

**Skipping deduplication.**
A concept rejected in `.out-of-scope.md` will be re-proposed without this check. Always search before writing.

**Horizontal slices in decomposition.**
"Implement the data layer" is a horizontal slice — it delivers nothing observable end-to-end. Every issue must cut through all layers from schema to consumer.

**File paths in PRD.**
The PRD must reference interfaces and contracts only. File paths rot. An agent reading a stale path will implement in the wrong location.

**Missing testing decisions.**
If the PRD has no testing decisions, the `tdd` RED phase has no acceptance criteria. Every PRD must state what a good test looks like for this module.
