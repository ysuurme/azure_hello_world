---
name: architecture
description: Use when mapping dependencies, identifying structural anti-patterns, computing blast radius of a proposed change, or validating topology against boundaries declared in CONTEXT.md
---

# Architecture

## Overview

Prevents structural drift and unplanned side-effects by making the dependency topology visible before changes are committed. Every proposed change gets a blast-radius computation; findings that violate `CONTEXT.md` boundaries block progress.

**Primary artifact:** Architecture map with dependency metrics and blast-radius report posted as a PR comment.

## Scope

**Owns:** Dependency graph generation and visualisation, circular dependency and layer-violation detection, deep/shallow module identification, fragility and coupling metric interpretation, blast-radius computation, GitHub Issue cross-reference loop, refactoring demand enforcement.

**Does not own:** Domain model design decisions (→ `refine`), infrastructure and deployment topology (→ `harness`), CI/CD pipeline configuration (→ `harness`).

**Interfaces with:** `refine` — topology validates the boundaries declared in `CONTEXT.md`. `plan` — blast-radius findings gate scope decisions in the Lean PRD. `review` — blast-radius report is posted as a PR comment for reviewer visibility.

## When to Use

- Before committing any change that touches more than one module
- When a `refine` session declares a new boundary that needs structural validation
- When fragility or coupling signals suggest a refactoring is overdue
- When `review` surfaces a pattern-grade failure

**Do NOT use for:** Domain modelling or glossary decisions (→ `refine`), writing implementation code (→ `tdd`).

## Required Inputs

- Current codebase
- `CONTEXT.md` bounded contexts (defines the layer boundaries to validate against)
- PR diff or list of proposed changed modules

## Primary Outputs

- Dependency graph (written to filesystem — never loaded into context in full)
- Blast-radius report (posted as a PR comment via `gh pr comment`)
- List of blocked / at-risk / safe modules
- Refactoring recommendation (proceed | refactor first | block)

## Core Pattern

### Dependency Analysis

Use whatever static analysis tool is available for the language (e.g. `pyreverse`, `pydeps`, `dependency-cruiser`, `madge`). Output to filesystem — never load raw graph data into the context window.

**What to look for:**
- Circular dependencies — flag immediately, block merge
- Layer boundary violations — flag per boundaries in `CONTEXT.md`
- God Objects — single module with high fan-in from multiple layers
- Anemic domain models — logic scattered across thin wrappers

**Module depth classification:**
- **Deep module:** Large implementation, small interface. Target state.
- **Shallow module:** Interface complexity ≈ implementation complexity. Refactoring trigger.

### Blast-Radius Computation

Run before any code is committed to a PR. Steps:

1. Identify all modules directly changed
2. Trace all callers and dependents (one level up)
3. Check each against layer boundaries in `CONTEXT.md`
4. Classify each affected module: **safe** (within boundary) or **at-risk** (crosses boundary)
5. Post the report as a PR comment using `gh pr comment`

**Blast-radius report format:**
```
## Blast-Radius Report

**Changed:** module-a, module-b
**At-risk:** module-c (crosses domain boundary defined in CONTEXT.md §Bounded Contexts)
**Safe:** module-d, module-e

**Recommendation:** [proceed | refactor first | block]
```

### GitHub Issue Research Loop

After generating the topology report, cross-reference findings with open GitHub Issues:
```bash
gh issue list --label architecture --json number,title,body | jq '.[] | ...'
```
Flag any open issue that overlaps with the current blast-radius. Prevents duplicate work.

## Quick Reference

| Signal | Action |
|---|---|
| Circular dependency | Block — do not proceed |
| Layer boundary violation | Block — flag in blast-radius report |
| Shallow module detected | Trigger REFACTOR phase in `tdd` |
| Pattern grade F | Block — raise with `refine` before `plan` |
| Blast-radius crosses boundary | Post report, await explicit approval |

**Context sensitivity:** Medium. Graph outputs go to filesystem; only summary metrics enter context. Safe to run in Transition Zone if raw outputs are offloaded.

## Common Mistakes

**Loading raw graph output into context.**
Dependency graphs can be thousands of lines. Write to disk, read only the summary. Loading the full graph pushes the session into Transition Zone.

**Skipping blast-radius for "small" changes.**
Blast radius is non-negotiable regardless of change size. A one-line change in a high-fan-in module can have a wide blast radius.

**Blocking without a recommendation.**
Every block must include a concrete recommendation: refactor X before proceeding, or raise with `refine` to revise the boundary.
