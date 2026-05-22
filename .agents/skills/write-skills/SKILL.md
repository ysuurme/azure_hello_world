---
name: write-skills
description: Use when creating new skills, editing existing skills, splitting an overgrown skill, or validating a skill before deployment
---

# Writing Skills for Agents

## Overview

A **skill** is a constraint document for AI agents — a reference that prevents hallucinated approaches by encoding proven patterns and hard rules. Skills are reusable across projects and sessions.

**Primary artifact:** Valid, MECE-compliant SKILL.md plus its companion REFERENCE.md, EXAMPLES.md, and optionally `scripts/`.

**Skills are:** Proven techniques, hard constraints, patterns, tool references.
**Skills are NOT:** Project-specific conventions, one-off solutions, or rules enforceable by a script or linter.

See [REFERENCE.md](REFERENCE.md) for the full SKILL.md template, routing-signal rules, ASO rules, and the baseline-first protocol in depth. See [EXAMPLES.md](EXAMPLES.md) for a worked end-to-end skill creation.

## Scope

**Owns:** Skill creation standards, SKILL.md / REFERENCE.md / EXAMPLES.md / `scripts/` directory shape, validation process (baseline → draft → verify), MECE enforcement and split/gap detection against the AGENTS.md Skills index and each existing skill's Scope block, routing signal format, update and split guidance, ASO rules.

**Does not own:** Project-specific agent instructions (→ `CONTEXT.md` / `AGENTS.md`), individual skill content.

**Interfaces with:** All other skills — this skill defines the contract every other skill must follow.

## When to Use

- Creating a new skill
- Editing or adding constraints to an existing skill
- Detecting whether a skill needs splitting (scope creep check)
- Validating a skill before deploying it

**Do NOT create a skill for:**
- Project-specific conventions (→ `CONTEXT.md` / `AGENTS.md`)
- One-off solutions that won't recur across projects
- Rules enforceable by a linter, hook, or script

## Core Pattern

### The Iron Law

**No skill without a failing baseline first.** Applies to new skills AND edits.

1. Run the pressure scenario — verify the agent gets it wrong
2. Document the exact rationalizations used — these become your constraints
3. Write the skill closing those specific loopholes
4. Verify compliance

Write skill before baseline? Delete it. Start over. No exceptions: don't keep it as "reference," don't adapt it while writing.

**Closing loopholes:** State the rule AND forbid the specific workaround. A rule without a closed escape route will be rationalized away.

### The MECE Law

**REQUIRED:** Before writing or updating any skill, read the Skills index in `AGENTS.md` and the `Scope` block (`Owns` / `Does not own` / `Interfaces with`) of every adjacent skill the new content might overlap with.

Every skill must be mutually exclusive and collectively exhaustive within the skill system the AGENTS.md index defines.

- **Mutually exclusive:** No `Owns` entry in one skill duplicates an `Owns` entry in another
- **Collectively exhaustive:** Every concern in the domain has exactly one skill that owns it

**MECE alarm — flag immediately when:**
- A new `Owns` entry already appears in another skill's Scope → resolve overlap before writing
- A constraint needs qualifying "except when X" more than twice → split signal
- Only half the skill is relevant for the task at hand → split signal
- A new independent trigger condition is being added to an existing skill → split signal

When a MECE alarm fires, stop and resolve it before continuing. Do not write around it.

## Quick Reference

### Directory Shape — Anthropic Open Skill Spec

Every skill directory MUST conform to:

```
.agents/skills/
  skill-name/
    SKILL.md              # Required — overview, scope, quick start. Hard cap: 500 lines.
    REFERENCE.md          # Required — deep-dive content overflowed from SKILL.md
    EXAMPLES.md           # Required — at least one runnable end-to-end example sequence
    scripts/              # Required when the skill implies deterministic operations (stubs allowed)
    supporting-file.*     # Only if needed
```

**Hard rules:**
- `SKILL.md` ≤ 500 physical lines. Overflow content moves to REFERENCE.md.
- `EXAMPLES.md` contains ≥ 1 runnable example sequence — copy-pasteable commands, prompts, or concrete artifacts. Prose-only descriptions do not count.
- `scripts/` is omitted only when the skill is pure documentation/process with no deterministic operation to script. When present, Phase-2 stubs that `throw` are acceptable while the logic is pending.

**What goes where:**
- `SKILL.md`: frontmatter, overview, scope, When-to-Use triggers, Core Pattern, quick-reference tables, common mistakes
- `REFERENCE.md`: full decision trees, complete schema templates, metric tables, step-by-step procedures
- `EXAMPLES.md`: end-to-end example sequences with real commands or concrete artifacts
- `scripts/`: deterministic operations the skill implies

### Frontmatter Rules

```yaml
---
name: skill-name-with-hyphens       # letters, numbers, hyphens only
description: Use when [triggering conditions only — never summarize the workflow]
---
```

Description = triggering conditions only. Summarizing the workflow lets the agent shortcut the skill body.

```yaml
# ❌ Summarizes workflow — agent skips the skill body
description: Use when executing plans — dispatches tool calls with code review between tasks

# ✅ Triggering conditions only — agent reads the skill
description: Use when executing implementation plans with independent tasks in the current session
```

### Checklists

**Create:**
1. Run baseline — verify agent fails, document exact failure modes
2. Write frontmatter (`name`, `description` — triggering conditions only)
3. Write Scope block (`Owns`, `Does not own`, `Interfaces with`)
4. Write constraints closing the specific loopholes from step 1 only
5. Author `REFERENCE.md` (deep content) and `EXAMPLES.md` (≥1 runnable sequence). Add `scripts/` if the skill implies deterministic operations.
6. Add the skill to the `## Skills` index in `AGENTS.md` with links to its REFERENCE.md and EXAMPLES.md
7. Validate — agent re-attempts scenario; if a new loophole is found, return to step 1 for it

**Update:**
1. Run baseline — verify agent fails with the current skill
2. Check MECE alarm conditions — does the fix expand scope or trigger a split?
3. Add constraints closing the specific gap; if content overflows, push to REFERENCE.md or add an example to EXAMPLES.md
4. Validate — passes new scenario AND all previous scenarios

**Split:**
1. Confirm two independent scopes — each must have its own standalone trigger
2. Create two new skill directories, each conforming to the four-file shape above
3. Distribute existing content — no duplication allowed
4. Delete the original skill directory
5. Update every skill (and `AGENTS.md`) that referenced the original

### AGENTS.md Index

Every skill must appear in the `## Skills` section of `AGENTS.md`. Where `REFERENCE.md` and `EXAMPLES.md` exist, they are linked in the References column. A skill that ships without an index entry is invisible to the agent.

## Common Mistakes

**Writing skill before baseline.** Delete it. Start over. The baseline defines what the skill must prevent — without it the constraints are guesses.

**Description summarizes workflow instead of trigger.** Ask: "does this tell the agent WHEN to use the skill, or WHAT it does?" Rewrite if the latter.

**`Does not own` entries without routing pointers.** Every exclusion must name where that concern lives — see Routing Signals in [REFERENCE.md](REFERENCE.md).

**Scope too broad** ("Owns: everything in this domain"). Scope must be specific enough that a second skill in the same domain has a non-overlapping `Owns` list.

**Scope creep on update.** Re-read the Scope block before every update. If new content doesn't fit in `Owns`, update Scope explicitly or route to the correct skill. If it triggers a MECE alarm, stop and split.

**Shipping without REFERENCE.md / EXAMPLES.md.** A SKILL.md without its companion files is incomplete per the open skill spec. EXAMPLES.md in particular is what an agent reads to learn the *shape* of compliant output — without it, the constraint hits but the worked pattern is missing.

**SKILL.md over 500 lines.** The cap is hard. Long-tail content (decision trees, full templates, deep procedures) belongs in REFERENCE.md.
