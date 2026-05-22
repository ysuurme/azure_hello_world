# Refine — Reference

Deep-dive reference for the `refine` skill. See [SKILL.md](SKILL.md) for the overview, scope,
and quick start. See [EXAMPLES.md](EXAMPLES.md) for a worked end-to-end session.

---

## Grill-Me Protocol — Full Decision Tree

### Phase 0 — Pre-flight: context fill check

Before opening any file:

1. Estimate current context fill.
2. If fill > 100k tokens (Transition Zone), invoke `compact()` before proceeding.
3. Never start a grill session above 100k tokens — alignment in the Transition Zone drifts.

### Phase 1 — Codebase orientation (before any questions)

1. Read `CONTEXT.md` fully — establish current glossary, boundaries, constraints, and
   out-of-scope declarations.
2. Read `AGENTS.md` — confirm standing instructions and skill invocation order.
3. Read `ADR_STRUCTURE.md` — identify ADRs matching the current `project_type`.
4. Identify which bounded context the new feature touches — write it down explicitly before
   asking any question.

**Gate:** Never ask the human what the codebase already says. If the answer is in a file, read
the file.

### Phase 2 — Domain language alignment

For every noun and verb in the raw user request:

1. **Existing term?** Check `CONTEXT.md` Glossary. If found, confirm the user means the same
   thing. If ambiguous, surface the two most likely meanings and recommend one.
2. **New term?** Draft a definition: `Term | Definition | Disambiguation`. Present it with a
   recommendation. Do not accept vague language — demand a precise, agreed token.
3. **Ambiguous term?** Surface the two most common meanings and ask which applies. Recommend
   one.

No interface design or code discussion until glossary terms are agreed.

### Phase 3 — Boundary interrogation

For every bounded context that the feature touches:

1. Read the `Owns` / `Does Not Own` columns in `CONTEXT.md`.
2. Ask: does the feature add logic to a context that does not own it? Flag as boundary
   violation risk.
3. Ask: does the feature require a new bounded context? If yes, draft its `Owns` / `Does Not
   Own` columns before proceeding.
4. Confirm that each constraint in `CONTEXT.md` Architectural Constraints is still satisfied.

**ADR trigger:** Any decision that relaxes or revises an existing architectural constraint must
be captured in a new ADR before the grill session ends.

### Phase 4 — Interface-first specification

Write the Agent Brief only after Phases 1–3 are complete. Rules:

- Describe system behaviour through contracts: request/response schemas, event types, state
  transitions.
- Never reference file paths, line numbers, or module names — those are volatile.
- Every interface entry must include: inputs, outputs, error states, and a testability note.
- Tracer bullet: identify the single narrowest vertical slice that proves all layers are
  connected end-to-end.

### Phase 5 — Decision capture

After every grilling round:

1. Any decision that was debated → write an ADR (`docs/adr/ADR-NNN.md`, MADR format).
2. Any constraint that changed → update `CONTEXT.md` Architectural Constraints.
3. Any new glossary term → update `CONTEXT.md` Glossary.
4. Any rejected concept → add to `CONTEXT.md` Out of Scope with date.

---

## CONTEXT.md — Full Schema Reference

```markdown
# CONTEXT.md — <project-name>

<project-description>

| Key   | Value                          |
|-------|--------------------------------|
| Project Type | application \| data \| agent |

---

## Glossary

| Term | Definition | Disambiguation |
|------|------------|----------------|

## Bounded Contexts

| Context | Owns | Does Not Own |
|---------|------|--------------|

## Module Map

Navigation index for agents. Read CONTEXT.md, identify the target bounded context,
then open only the files in that row.

| Module | Path | Bounded Context | Entry points |
|--------|------|-----------------|--------------|

## Issue-Type → Files Index

For each kind of work, read these files before opening anything else.

| Working on... | Read first |
|---------------|------------|

## Architectural Constraints

Invariants that must not be violated in any implementation.
(bullet list)

## Out of Scope

Concepts explicitly deferred or rejected. Prevents re-proposal in planning sessions.

| Concept | Reason deferred | Date |
|---------|-----------------|------|
```

---

## ADR — MADR Full Template

```markdown
# ADR-NNN: <Title>

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-NNN]

## applies_to
[application | data | agent | all]

## Context and Problem Statement

<Why this decision was needed. Background, constraints, the problem.>

## Considered Options

- Option A: <name>
- Option B: <name>

## Decision Outcome

**Chosen:** Option A — because <concise justification>.

### Positive Consequences

- <outcome>

### Negative Consequences

- <outcome>

## Pros and Cons of the Options

### Option A: <name>

- Good, because <reason>
- Bad, because <reason>

### Option B: <name>

- Good, because <reason>
- Bad, because <reason>
```

Store in `docs/adr/ADR-NNN-kebab-title.md`. Add an index entry to
`docs/adr/ADR_STRUCTURE.md`.

---

## Agent Brief — Full Template

```markdown
# Agent Brief: <feature name>

## Problem Statement
<One paragraph, user perspective, no implementation details.>

## Glossary Additions
| Term | Definition | Disambiguation |

## Bounded Context Changes
<List any new contexts or ownership changes agreed during grilling.>

## Interfaces

### <Interface Name>
**Input:** <schema / contract>
**Output:** <schema / contract>
**Error States:** <list>
**Testability:** <what makes this interface unit-testable>

## Constraints
<List architectural constraints that apply to this feature.>

## Out of Scope
<Concepts explicitly deferred during this grilling session.>

## Tracer Bullet
<The single narrowest vertical slice: schema → API → consumer.>
```

---

## Pragmatic Programmer Checks — Expanded

| Check | PP Reference | Trigger | Agent Action |
|-------|-------------|---------|--------------|
| Dig for requirements | PP-51 | User states a solution instead of a problem | Ask "what outcome does that enable?" until the root need surfaces |
| Think like a user | PP-52 | Feature described from builder's perspective | Reframe as "as a [role] trying to [job], what would I observe?" |
| Long-lived abstractions | PP-53 | Design references implementation details | Replace with interface / contract language |
| Broken windows | PP-4 | Existing code violates a stated constraint | Name the violation; do not work around it silently |
| Options not excuses | PP-3 | Constraint blocks a requirement | Propose at least two paths; recommend one |

---

## Context Sensitivity — Detailed

| Token Range | Zone | Agent Action |
|-------------|------|--------------|
| < 100k | Smart Zone | Proceed with grill session |
| 100k–150k | Approaching Transition Zone | Complete current phase; compact before next phase |
| 150k–250k | Transition Zone | Compact immediately; do not start a new phase |
| > 250k | Dumb Zone | Reset — write handoff artefact to disk, start fresh session |

Never start Phase 2 (Domain Language Alignment) above 100k tokens. A glossary agreed in the
Transition Zone is unreliable and will produce an Agent Brief that drifts during implementation.
