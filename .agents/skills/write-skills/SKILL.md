---
name: write-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

# Writing Skills for Antigravity/Gemini Agents

## Overview

**Development Skills vs. Documentation Skills:**
- **Development Skills** (e.g., Code Review, Design Infrastructure, Design Architecture): A **strong emphasis on Test-Driven Development (TDD)** must be enforced. You write test cases (pressure scenarios), watch them fail, write the skill, watch agents comply, and refactor loopholes. If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.
- **Documentation Skills** (e.g., this `write-skills` SKILL.md): The focus is strictly on **structure, clarity, and best practices** tailored specifically for the Antigravity/Gemini execution environment, ensuring readability and strict adherence to architectural standards.

**Personal skills live in agent-specific directories (e.g., `<project-root>/.agents/skills/`)** 

**REQUIRED BACKGROUND:** You MUST understand Test-Driven Development principles before using this skill. This skill adapts TDD strictly to Development skills, and structural rigor to Documentation skills.

## What is a Skill?

A **skill** is a reference guide for proven techniques, patterns, or tools that an AI Agent can natively read via `view_file`. Skills help future Agent instances find and apply effective approaches without hallucinating paths.

**Skills are:** Reusable techniques, patterns, tools, reference guides.
**Skills are NOT:** Narratives about how you solved a problem once or project-specific constraints.

## TDD Mapping for Skills

| TDD Concept | Skill Creation |
|-------------|----------------|
| **Test case** | Pressure scenario / Problem statement |
| **Production code** | Skill document (`SKILL.md`) |
| **Test fails (RED)** | Agent violates rule or hallucinate approaches without skill (baseline) |
| **Test passes (GREEN)** | Agent complies strictly with skill present |
| **Refactor** | Close logic loopholes while maintaining compliance |
| **Write test first** | Run baseline scenario BEFORE writing skill |
| **Watch it fail** | Document exact rationalizations the agent uses |
| **Minimal code** | Write skill addressing those specific violations |
| **Watch it pass** | Verify the agent now complies |
| **Refactor cycle** | Plug loopholes → re-verify |

## When to Create a Skill
**Create when:**
- A process or technique wasn't intuitively obvious to the Agent.
- You'd reference this approach again across multiple projects.
- The pattern applies broadly.
- Other AI agents would benefit from this deterministic behavior.

**Don't create for:**
- One-off solutions.
- Standard practices well-documented on the public web (use `search_web` instead).
- Project-specific conventions (put in `USER_RULES` or `AGENT.md`/Workspace rules).
- Mechanical constraints if it can be codified via a bash script or validation hook instead.

## Skill Types

### Technique
Concrete method with steps to follow (e.g., `condition-based-waiting`, `root-cause-tracing`).

### Pattern
A way of framing architectural architectures (e.g., `flatten-with-flags`, `test-invariants`).

### Reference
Syntax guides, CLI tooling definitions, API documentation.

## Directory Structure

```
.agents/
  skills/
    skill-name/
      SKILL.md              # Main reference (required)
      supporting-file.*     # Only if needed
```

**Keep inline within `SKILL.md`:**
- Principles and concepts
- Code patterns (< 50 lines)
- Bulleted implementation plans

## `SKILL.md` Structure

**Frontmatter (YAML):**
- Two required fields: `name` and `description`
- Max 1024 characters total
- `name`: Use letters, numbers, and hyphens only
- `description`: Third-person, describes ONLY when to use (NOT what it does)
  - Start with "Use when..." to focus on triggering conditions
  - Include specific symptoms, situations, and contexts
  - **NEVER summarize the skill's workflow in the description**

```markdown
---
name: Skill-Name-With-Hyphens
description: Use when [specific triggering conditions and symptoms]
---

# Skill Name

## Overview
What is this? Core principle in 1-2 sentences.

## When to Use
Bullet list with SYMPTOMS and use cases. Include when NOT to use.

## Core Pattern
Before/after code comparison.

## Quick Reference
Table or bullets for scanning common operations.

## Implementation
Inline code for simple patterns, or link to supporting file.

## Common Mistakes
What goes wrong + fixes.
```

## Agent Search Optimization (ASO)

**Critical for discovery:** The Agent needs to FIND your skill during its tasks.

### 1. Rich Description Field

**Purpose:** Agents read the description from standard metadata parsing to decide which skills to `<view_file>` for a given task. 
Make it answer: "Should I read this skill right now?"

**Format:** Start with "Use when..." to focus on triggering conditions.

**CRITICAL: Description = When to Use, NOT What the Skill Does**
The description should ONLY describe triggering conditions. Do NOT summarize the skill's process or workflow in the description.
If you summarize the workflow, the agent will take the shortcut and try to hallucinate the rest without reading the `SKILL.md` document natively.

```yaml
# ❌ BAD: Summarizes workflow - Agent may follow this instead of reading skill
description: Use when executing plans - dispatches tool calls with code review between tasks

# ✅ GOOD: Just triggering conditions, no workflow summary
description: Use when executing implementation plans with independent tasks in the current session
```

### 2. Keyword Coverage
Use words the Agent would actively search for:
- Tools: Actual command line names (e.g., `git`, `uv`, `pytest`).
- Error messages: "Hook timed out", "race condition".
- Synonyms: "timeout/hang/freeze".

### 3. Token Efficiency (Critical)
Always optimize your word count.
- Move details to CLI tool help logs instead of pasting 2,000 lines of `man` pages into a markdown file.
- Use explicit cross-references when necessary (`**REQUIRED:** See other-skill`).
- Compress examples to single, meaningful Python/Bash implementations.

### 4. Naming Convention
Write skill names by what you DO or the core insight:
- ✅ `condition-based-waiting` over `async-test-helpers`
- ✅ `root-cause-tracing` over `debugging-techniques`

## Creating the Iron Law (Test First)

`NO SKILL WITHOUT A FAILING TEST FIRST`
- This applies to NEW skills AND EDITS to existing skills.
- Write a skill before testing? Delete it. Start over.
- Provide a failing scenario, check if the Agent executes it wrong, and THEN supply the `.agents/skills/` documentation.

### Bulletproofing Skills Against Rationalization
Skills that enforce discipline need to resist rationalization. AI Agents are highly logic-driven and try to find loopholes when minimizing operations.

**Close Every Loophole Explicitly:**
Don't just state the rule - forbid specific workarounds.

<Bad>
Write code before test? Delete it.
</Bad>

<Good>
Write code before test? Delete it. Start over.
**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Delete means delete
</Good>

## Skill Creation Checklist

**Phase 1 - Baseline:**
- Create a pressure scenario prompt and ask the Agent to execute it.
- Verify the Agent fails or hallucinates behavior without the explicit skill.

**Phase 2 - Draft Constraint:**
- Name the skill using hyphens.
- Add YAML frontmatter with `name` and `description` ("Use when...").
- Keep the overview clear and problem-focused.
- Write explicit constraints closing the specific loopholes the Agent used.

**Phase 3 - Validation:**
- Let the Agent read `SKILL.md` and attempt the same previous prompt.
- Verify the Agent strictly adheres to the skill guidelines.
- Commit to the `.agents/skills/` project directory.

## The Bottom Line
Creating skills under `.agents/skills/` creates reusable, deterministic behavior across projects. Use the same discipline applied to coding: identify the failure, code the solution, test the boundary. Apply this rigor to your organizational documentation.