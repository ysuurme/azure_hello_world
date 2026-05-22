---
name: harness
description: Use when provisioning a development environment, configuring a managed agent session, managing context window health, or setting up the Planner/Generator/Evaluator split for a multi-step task
---

# Harness

## Overview

Prevents context degradation and unverified agent output by managing the execution environment and agent session lifecycle. The harness is the last line of defence before a Dumb Zone reset — it must always operate in the Smart Zone.

**Primary artifact:** Configured managed agent session with Planner/Generator/Evaluator split, durable event log, and a provisioned Dev Container environment.

## Scope

**Owns:** Dev Container and GitHub Codespaces provisioning, Planner/Generator/Evaluator agent split, event log (`emitEvent`), tool-call offloading, `compact()` and context reset protocol, `CONTEXT.md` and `AGENTS.md` loading at session start.

**Does not own:** `CONTEXT.md` content or the grill-me protocol (→ `refine`), TDD loop logic (→ `tdd`), PR review findings (→ `review`), merge and governance (→ `ship`).

**Interfaces with:** `refine` — `CONTEXT.md` and `AGENTS.md` are the harness initialisation inputs. `tdd` — the TDD loop runs inside harness sessions; log offloading keeps the loop fast. `review` — the Evaluator agent feeds findings to the review cycle.

## When to Use

- Starting any multi-step implementation task
- Provisioning a new isolated environment for a task
- Context fill is approaching the Transition Zone and action is needed
- Setting up the Evaluator agent to review Generator output

**Do NOT use for:** Writing `CONTEXT.md` content (→ `refine`), running the TDD loop (→ `tdd`), reviewing PR code quality (→ `review`).

## Required Inputs

- `CONTEXT.md` and `AGENTS.md` (loaded in this order at session start)
- Task description or GitHub Issue
- Toolchain requirements for the Dev Container

## Primary Outputs

- Provisioned Dev Container environment (disposable — one per task)
- Configured Planner/Generator/Evaluator agent split
- Event log entries for every significant state transition
- Tool-call outputs offloaded to filesystem (head + tail in context only)

## Core Pattern

### Environment Provisioning (Dev Container / GitHub Codespaces)

Environments are disposable — one per task, never shared between tasks.

**Dev Container standard:**
- Define in `.devcontainer/devcontainer.json`
- Include: language runtime, package manager, `gh` CLI, test runner (pytest), linter
- Docker available locally via Rancher Desktop for offline development
- GitHub Codespaces for cloud-hosted sessions

```json
{
  "name": "task-environment",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "features": {
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
  "postCreateCommand": "pip install -e '.[dev]'"
}
```

### Session Initialisation

Load in this order at the start of every session:
1. `CONTEXT.md` — domain glossary, boundaries, constraints
2. `AGENTS.md` — standing instructions and style preferences
3. Task-specific context (issue body, relevant test files)

If loading steps 1 + 2 + step 3 would push context fill into Transition Zone (> 100k tokens), offload step 3 to filesystem and load on demand.

### Planner / Generator / Evaluator Split

The agent must never grade its own work.

| Role | Responsibility | Provider |
|---|---|---|
| **Planner** | Breaks the issue into ordered steps; owns the task graph | Claude |
| **Generator** | Executes one step at a time; writes code and tests | Claude |
| **Evaluator** | Reviews Generator output against acceptance criteria; triggers re-generation on failure | Claude (separate instance, separate system prompt) |

**Evaluator system prompt must include:**
- The acceptance criteria from the PRD
- The architectural constraints from `CONTEXT.md`
- Explicit instruction to critique, not collaborate

### Tool-Call Offloading

Large outputs must never enter the context window:
- Test logs → write to `logs/test-output.txt`, read head + tail only
- Dependency graphs → write to `docs/architecture/graph.json`, read summary only
- Build artefacts → filesystem only

### Context Management

| Zone | Action |
|---|---|
| < 100k tokens | Proceed normally |
| 100k–250k tokens | Run `compact()` before starting any new complex task |
| > 250k tokens | Initiate context reset: write handoff artefact, reset session, re-initialise from `CONTEXT.md` |

**Exception:** Reference-only contexts (agent reads large codebases without synthesising novel solutions) may safely exceed 250k tokens — no reset required.

**`compact()` usage:** Organises the context for prompt cache hits. Run at the start of long sessions and before switching between major phases (e.g. end of RED phase, start of REFACTOR).

## Common Mistakes

**Starting a session without loading CONTEXT.md first.**
Every session begins with `CONTEXT.md` and `AGENTS.md`. An agent that skips this will hallucinate boundaries that were already agreed.

**Evaluator using the same system prompt as the Generator.**
The Evaluator must have an independent system prompt focused on critique. A shared prompt produces agreement bias, not evaluation.

**Loading raw tool output into context.**
Test logs and dependency graphs belong on the filesystem. Loading them in full pushes the session into Transition Zone before meaningful work begins.

**Reusing environments across tasks.**
Environments are cattle, not pets. A shared environment carries state from previous tasks. Provision fresh for each task.
