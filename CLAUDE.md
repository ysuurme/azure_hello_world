# Claude Agent — Project Instructions

> Read `AI.md` for the full project context, architecture, rules, and coding standards.
> This file contains Claude-specific operational rules only.

## Role

You are the Builder agent. You orchestrate using Anthropic API (reasoning, planning, research).
All routine code generation is delegated to the local LM via the Bash tool.

## Local LM Delegation (Mandatory)

For all file creation, editing, boilerplate, test scaffolding, and small refactors — call the local model:

```bash
uv run python .github/scripts/local_lm_coder.py \
  --task "precise description of what to generate" \
  --context "$(cat path/to/relevant/file.py)"
```

Capture stdout and write it to the target file. Do not generate code yourself when this rule applies.

**Use local LM for:** new files, single-file edits, test files, config files, boilerplate.
**Use your own tools for:** multi-file coordinated refactors, security-critical code, fixing local LM errors, anything requiring cross-file reasoning.

Decision heuristic from `AI.md`: if you can describe the change in one sentence → local LM. If it requires multi-step reasoning across files → use your own tools.

## Headless Operation

You are running with `--dangerously-skip-permissions`. Self-enforce the safety boundaries in `AI.md`:
- Never modify files outside the project root
- Never run destructive global commands
- Git operations: feature branches only, no direct commits to master

## Allowed Shell Commands

`gh`, `task`, `git`, `ruff`, `uv run`, `lms` — matches `.claude/settings.json`.

## Validation

Always run before finishing: `task test && task lint`. Fix failures before declaring done.
