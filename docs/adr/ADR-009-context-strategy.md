---
name: ADR-009-context-strategy
description: Context strategy for template and generated projects — Module Map plus Issue-Type Index inside CONTEXT.md, Context Protocol inside AGENTS.md, enforced by a blocking ship gate
---

# ADR-009: Context Strategy for Template and Generated Projects

## Status
Accepted

## Context and Problem Statement

Coding agents read broadly because the standard repository files do not give them enough precision to be confident in a narrow read. They hedge by reading more, which degrades context fill and slows down every session. Three additional constraints make this acute for this repository:

1. **Template fan-out.** The repository generates three project shapes (`application`, `agent`, `ml`) via Copier. A context strategy written for one shape mis-fires on the other two.
2. **Propagation requirement.** Any mechanism the strategy introduces must survive `copier copy` — local-only files and machine-local skill paths do not satisfy the constraint.
3. **Skill propagation gap.** Skill files referenced by `AGENTS.md` currently live at `~/.claude/skills/` (machine-local) and do not travel via Copier. The maturity assessment in `README.md` already flags this as the blocking gap at the Mid-Level tier.

The strategy must answer two questions for every agent session: *which 3–5 files are relevant to this issue?* and *how do I keep the map accurate as the project grows?*

## Considered Options

* **Option A — Homework draft verbatim.** Introduce a separate `CLAUDE.md` for behavioural rules, treat `AGENTS.md` as pipeline config, fix a Module Map keyed on generic data-pipeline categories (ingest / transform / model / viz), enforce via a "Context Protocol" instruction block.
* **Option B — Extend `AGENTS.md` and `CONTEXT.md`.** Keep `AGENTS.md` as the single standing-instructions file (vendor-neutral cross-tool standard). Add a Module Map and Issue-Type → Files Index to `CONTEXT.md`, anchored on the bounded contexts already declared there. Add a Context Protocol block to `AGENTS.md` §Session Initialisation. Make Module Map updates a blocking ship gate. Require skill files to physically travel via Copier.
* **Option C — Status quo.** Leave `CONTEXT.md` with bounded contexts only. Rely on agents to navigate via `Grep` and `Glob` from the bounded-context names.

## Decision Outcome

Chosen option: **Option B**, because it preserves the cross-tool `AGENTS.md` convention (no `CLAUDE.md` duplication), anchors the new navigation tables on abstractions that already exist in `CONTEXT.md` (bounded contexts), survives Copier propagation through files that are already templated, and converts the self-improvement loop from aspiration to enforcement via the ship gate.

### Positive Consequences

* Single source of truth for agent behaviour (`AGENTS.md`).
* Module Map and Issue-Type Index are project_type-agnostic at template time because they are keyed on bounded contexts and on invariants (`src/utils/`, `src/tools/`, `.github/scripts/kanban/`) shared across all three shapes.
* The blocking ship gate makes the "every task improves the map" claim mechanical, not voluntary.
* No new top-level files in the generated project — `AGENTS.md`, `CONTEXT.md`, and `docs/adr/` already propagate.

### Negative Consequences

* The Module Map at template-time is shallow (lists only what is invariant across project_types). The first feature in a generated project must extend it. This is by design but represents real work on day one.
* The ship-gate enforcement requires a new check in the `ship` skill — adds CI complexity.
* The skill-propagation gap is now in-scope; closing it touches `copier.yml` and possibly introduces a build step that copies user-level skills into the template tree.

### Confirmation

* `CONTEXT.md` contains a Module Map section with at minimum the invariant rows (`src/`, `src/utils/`, `src/tools/`, `tests/`, `.github/scripts/kanban/`, `docs/adr/`, `.agents/skills/`, `AGENTS.md`, `CONTEXT.md`).
* `CONTEXT.md` contains an Issue-Type → Files Index keyed on bounded contexts (orchestrator change, `src/utils/` change, ADR addition, CI workflow change, developer-tool change, new `src/<domain>/`).
* `AGENTS.md` §Session Initialisation contains the Context Protocol block.
* `AGENTS.md` Rules contains "name your target files before reading any code" and "Module Map updates are required when adding `src/<domain>/`".
* `CONTEXT.md` Architectural Constraints contains the skill-propagation invariant and the Map-update invariant.
* `ship` skill rejects PRs that add a new top-level `src/<domain>/` without a matching Module Map row.
* `.agents/skills/` (at repo root) contains the skill files referenced by `AGENTS.md`. Source of truth lives in this template repo; the junction at `~/.claude/skills/` → `.agents/skills/` makes them available to Claude on the developer's machine. Copier copies the directory verbatim into every generated project.
* Revisit when a fourth `project_type` is added or when the Issue-Type Index outgrows ten rows (signal that the bounded-context anchoring is too coarse).

## Addendum — Generated codebase-map artefact removed (supersedes the #79 addition)

**Context:** Issue #79 added a committed dependency-graph artefact written by the architecture
phase on every pipeline run, intended to satisfy SDLC maturity criterion 4.8 ("Pre-computed
codebase map / context graph"). It has since been **removed**: the architecture phase no longer
writes a committed map, and the file was deleted from the tree.

**Decision:** The Module Map in `CONTEXT.md` is the **single, leading source of truth** for repo
structure and agent navigation. The architecture phase still performs static analysis
(fan-in / fan-out, module depth) but emits the result only as transient blast-radius evidence —
`.planning/<issue>/BLAST_RADIUS.md` (gitignored, never merged) plus the blast-radius issue/PR
comment. No generated map is committed to the repository.

**Consequence:** Agents initialise a session from `CONTEXT.md` (Context Protocol). There is no
generated artefact to substitute for it. SDLC criterion 4.8 is no longer satisfied by a
committed map; revisit if a persisted context graph is wanted again.

## Addendum — Out-of-Scope Ledger Split (issue #80)

**Context:** The original ADR-009 decision designated `CONTEXT.md` as the canonical source of
truth. The "Out of Scope" section in `CONTEXT.md` was a table of rejected concepts. The `plan`
skill spec referenced `.out-of-scope/` (a directory) as the deduplication target, but no such
path existed, making the deduplication step non-operational.

Issue #80 migrates the ledger to a single flat file (`.out-of-scope.md`) so that rejected
concepts are searchable via `grep` and `gh repo view` without any directory traversal. This
addendum explicitly authorises the resulting split in source-of-truth responsibility.

**Decision:**

| Dimension | CONTEXT.md | .out-of-scope.md |
|-----------|------------|------------------|
| Authorship | Manually maintained — agents update per ADR-009 confirmation criterion | Manually maintained — agents append entries after plan-phase decisions |
| Purpose | Human entry point — domain glossary, bounded contexts, Module Map, architectural constraints | Machine source of truth — plan-phase deduplication; one `## ` heading per rejected concept |
| Audience | Humans and agents at session start (mandatory read) | Plan skill only, via `grep` or `gh repo view` |
| Update trigger | Refine session or new `src/<domain>/` discovery | Every plan session that defers a concept |
| Canonical? | Yes — remains the single canonical human entry point | Authoritative for deduplication only |

**Authorisation statement:** CONTEXT.md remains the canonical human entry point and the single
source of truth for domain glossary, bounded contexts, the Module Map, the Issue-Type Index,
and architectural constraints. `.out-of-scope.md` is hereby authorised as the machine source
of truth for plan-phase deduplication of rejected concepts. The two files are complementary,
not competing: CONTEXT.md §Out of Scope holds a top-5 summary view with an explicit cross-link;
`.out-of-scope.md` holds the full ledger with date and source ADR cross-links.

**Confirmation:**

* `.out-of-scope.md` exists at repo root; contains one `## ` heading per rejected concept.
* `CONTEXT.md` §Out of Scope is a top-5 summary table with an explicit cross-link to `.out-of-scope.md`.
* `plan/SKILL.md` Required Inputs references `.out-of-scope.md` (flat file), not `.out-of-scope/` (directory).
* Plan-phase deduplication instructions in `plan/SKILL.md` reference `.out-of-scope.md`.
* Revisit if the ledger grows past 50 entries (signal that a directory structure is warranted).

## Pros and Cons of the Options

### Option A — Homework draft verbatim

| | |
|---|---|
| **Good** | Strong "name your files before opening any" discipline. |
| **Good** | The compounding-benefit claim (every task makes the map sharper) is the right intuition. |
| **Bad** | Introduces `CLAUDE.md` alongside `AGENTS.md`, splitting source of truth and privileging one vendor over Gemini and the cross-tool `AGENTS.md` standard. |
| **Bad** | Re-roles `AGENTS.md` as pipeline config — collides with the existing `config.ps1` which is already the pipeline config. |
| **Bad** | Issue-Type Index keyed on generic data-pipeline categories misfires for `application` and `agent` project_types. |
| **Bad** | Self-improvement loop is documented as a norm, not enforced as a gate. |

### Option B — Extend `AGENTS.md` and `CONTEXT.md`

| | |
|---|---|
| **Good** | Reuses existing files that already propagate via Copier. |
| **Good** | Anchors on bounded contexts already declared in `CONTEXT.md` — no new vocabulary to learn. |
| **Good** | Blocking ship gate converts aspiration into mechanism. |
| **Good** | Forces resolution of the skill-propagation gap rather than working around it. |
| **Bad** | Module Map is shallow at template-time; first feature in a generated project does real work to extend it. |
| **Bad** | New ship-gate check is non-trivial to implement reliably (must detect new top-level `src/<domain>/` directories in PR diff). |

### Option C — Status quo

| | |
|---|---|
| **Good** | Zero additional work. |
| **Good** | No new failure modes in CI. |
| **Bad** | Agents continue reading broadly because the navigation surface is incomplete. |
| **Bad** | The "every task makes context sharper" benefit is left on the table. |
| **Bad** | Bounded-context declarations stay declarative without becoming navigational. |
