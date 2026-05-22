# Write Skills — Reference

Deep-dive reference for the `write-skills` skill. See [SKILL.md](SKILL.md) for the overview, scope, and quick start. See [EXAMPLES.md](EXAMPLES.md) for a worked end-to-end skill creation.

---

## SKILL.md Template

Use this as the canonical starting point. Every section is required unless the skill is genuinely empty for it — and a genuinely empty section is itself a signal the skill is too small to deserve its own directory.

```markdown
---
name: skill-name-with-hyphens
description: Use when [triggering conditions only]
---

# Skill Name

## Overview
Core principle in 1-2 sentences. What problem does this skill prevent?

Link out: "See [REFERENCE.md](REFERENCE.md) for X. See [EXAMPLES.md](EXAMPLES.md) for Y."

## Scope
**Owns:** What this skill is solely responsible for.
**Does not own:** What explicitly falls outside (→ `other-skill`).
**Interfaces with:** `other-skill` — what the handoff is and why.

## When to Use
- **Trigger:** Specific symptom or situation.
- **Do NOT use for:** Explicit exclusions (→ `other-skill`).

## Core Pattern
The key constraint or technique with a before/after example.

## Quick Reference
Tables or bullets for scanning during active work.

## Common Mistakes
What the agent gets wrong without this skill + the fix.
```

The cap of 500 physical lines on `SKILL.md` is non-negotiable. When content grows past that, the agent stops reading the tail end during active work. Push the overflow into `REFERENCE.md` (which the agent reads on demand) and keep `SKILL.md` scannable.

---

## REFERENCE.md / EXAMPLES.md / scripts/ Contract

| File | Required | Purpose | Loaded |
|------|----------|---------|--------|
| `SKILL.md` | Always | Quick start: scope, triggers, core pattern, quick-ref tables | Every invocation |
| `REFERENCE.md` | Always | Deep content: full templates, decision trees, schemas, deep procedures | On demand from SKILL.md links |
| `EXAMPLES.md` | Always | ≥1 runnable end-to-end example sequence | On demand from SKILL.md links |
| `scripts/` | When skill implies deterministic ops | Executable helpers (stubs allowed while logic is pending) | Invoked by the agent or human |

**"Runnable example sequence"** means: an agent could follow the example top-to-bottom and produce the same artefact. Acceptable forms:

- A sequence of shell commands with expected output
- A sequence of agent prompts and the file diffs/content they produce
- A worked walkthrough of a decision with concrete inputs, the rules applied, and the output artefact

**Not acceptable:** A prose paragraph describing what the skill "would" produce, without showing the actual inputs and outputs.

---

## Routing Signals

Routing signals are pointers inside skill content that direct an agent to the correct skill for a given concern. They are not documentation — agents follow them actively.

**Format:** `` → `skill-name` ``

**Usage rules:**
- Every `Does not own` entry MUST have a `→ skill-name` pointer
- Every `Do NOT use for` exclusion MUST have a `→ skill-name` pointer
- Mandatory pre-reads use: `` **REQUIRED:** See → `skill-name` ``
- Never leave a gap without a pointer — "not here" without "go there" is an agent dead end

**In practice:**

```markdown
**Does not own:** Model serving (→ `mlops`), feature pipeline implementation (→ `data-engineering`).
**Do NOT use for:** Production deployment (→ `mlops`).
**REQUIRED:** See → `design-system` before defining bounded contexts.
```

---

## Agent Search Optimization

Agents select which skill to read from the `description` field alone — they do not read the body to decide whether the skill is relevant.

1. **Description = when to use, not what the skill does.** See frontmatter rules in `SKILL.md`.
2. **Keyword coverage.** Use words the agent would search for: error messages, synonyms, exact command names as they appear in the agent's context. If the trigger keyword is `RetryError` but the description says "retry mechanism", the match misses.
3. **Token efficiency.** Dense and direct. No motivational text, no repeated explanations. Move large reference material to `REFERENCE.md` and `EXAMPLES.md` so the descriptor list scans cleanly.
4. **Naming.** Action- or insight-oriented: `condition-based-waiting` not `async-helpers`; `write-skills` not `skill-utils`.

---

## The Baseline-First Protocol

The Iron Law in `SKILL.md` states: no skill without a failing baseline first. The deep version:

### Step 1 — Construct the Pressure Scenario

A pressure scenario is a realistic prompt where the agent must apply the skill's principle without being told to. The scenario must be specific enough that an undirected agent will rationalize the wrong answer.

Bad scenario: "Tell me how to wait for a condition." — too direct, agent will guess correctly.
Good scenario: "I have a test that fails intermittently because the upstream service is slow. Fix it." — undirected; agent will reach for `sleep()`.

### Step 2 — Run the Baseline

Run the scenario against a fresh agent that has no access to the skill draft. Capture:

- The agent's chosen approach
- Every reason the agent gave for that approach ("this is simpler", "this is more idiomatic", "users expect this")

Those reasons are the loopholes the skill must close.

### Step 3 — Draft the Constraints

For each rationalization, write a constraint that names the rationalization and forbids it. Stating only the rule, not the workaround, fails — the agent will rationalize a fresh variation.

Bad: "Use condition-based waiting."
Good: "Use condition-based waiting. Do not use `sleep()` even when the wait is 'short' or 'simple' — those are the exact rationalizations that put it back in. If you cannot construct a condition, the operation is asynchronous in a way you have not yet understood; stop and ask."

### Step 4 — Verify

Run the same pressure scenario against an agent that has access to the new skill. Verify:

- The agent applies the constraint
- The agent does not produce a new rationalization that bypasses the constraint

If a new rationalization appears, return to Step 3 for that rationalization. The skill is not done until every rationalization is closed.

---

## MECE Invariants

The MECE Law in `SKILL.md` states the rule. The deep version names the invariants you check before committing any skill change:

1. **Owns-set partition.** Pick any concern in the project's skill domain. There must be exactly one skill whose `Owns` block contains it. Zero = collectively-exhaustive failure (gap). Two or more = mutually-exclusive failure (overlap).
2. **Routing closure.** Every `Does not own` and `Do NOT use for` entry resolves to an existing skill via a `→ skill-name` pointer. A pointer to a non-existent skill is a routing dead end.
3. **Independent triggers.** Two skills' `description` fields must trigger on disjoint conditions. If both trigger on the same condition, they overlap regardless of what `Owns` says.
4. **Stand-alone usability.** Each skill must be readable without loading its neighbors. Cross-references via `→ skill-name` are pointers, not dependencies.

A change that breaks any of these invariants must be resolved before the skill is merged.

---

## Common Rationalizations the Agent Will Use to Skip Baseline

Knowing the pattern in advance helps you catch it during skill review:

- *"This is obviously correct, no baseline needed."* — If it were obvious, the agent wouldn't be failing scenarios in the first place. The baseline is what proves it isn't obvious.
- *"I already have the constraints in my head."* — They will drift while you write. The baseline freezes the failure mode.
- *"This is a small edit, baseline overkill."* — Small edits introduce most of the regressions, because they bypass the protocol.
- *"I'll baseline after, then adjust."* — After is too late. The constraints written without a baseline shape the baseline you eventually run.

If you find yourself making any of these arguments, you are the failing baseline.
