---
name: ship
description: Use when merging a reviewed PR, running pre-merge security checks, closing the linked GitHub Issue, or updating CONTEXT.md and out-of-scope records after merge
---

# Ship

## Overview

Prevents insecure or incomplete merges by running mandatory security gates, enforcing squash-merge discipline, and committing architectural lessons back to `CONTEXT.md` after every merge.

**Primary artifact:** Squash-merged PR with clean history, closed GitHub Issue, and updated knowledge base.

## Scope

**Owns:** Pre-merge security gates (sandboxing verification, supply chain review), `gh pr merge --squash` execution, auto-close enforcement (`Closes #N`), `.out-of-scope.md` updates, `CONTEXT.md` post-merge update.

**Does not own:** Code review findings (→ `review`), branch and commit operations (→ `version-control`), container and environment teardown (→ `harness`).

**Interfaces with:** `review` — a passing review is the prerequisite for ship. `version-control` — merge uses the branch and PR conventions established there. `refine` — `CONTEXT.md` updates feed back into the next session's initialisation.

## When to Use

- `review` has completed with all BLOCKs resolved or explicitly escalated and accepted
- PR has a linked issue with `Closes #N` in the body
- Ready to merge to `main`

**Do NOT use for:** Running code review (→ `review`), creating commits or branches (→ `version-control`).

## Required Inputs

- Open PR with all review BLOCKs resolved
- `Closes #N` present in the PR body
- Access to `gh` CLI and git

## Primary Outputs

- Squash-merged PR with deleted branch
- Closed GitHub Issue (via `Closes #N` auto-close)
- Updated `CONTEXT.md` with architectural lessons
- Updated `.out-of-scope.md` with deferred improvements

## Core Pattern

### Pre-Merge Checklist

Run in order. All BLOCK items must pass before merge is attempted.

**[BLOCK] Module Map check**
Verify every new `src/<domain>/` directory in this PR has a matching Module Map row in `CONTEXT.md` (ADR-009):
```powershell
pwsh .github/scripts/check-module-map.ps1
```
Non-zero exit → add the missing row(s) to the Module Map in `CONTEXT.md` before merge.

**[BLOCK] Sandboxing verification**
Confirm all agent-generated code was produced inside the Dev Container environment. No host credentials should have been accessible during generation. Check:
```bash
# Verify no .env or credential files were added
git diff main...HEAD --name-only | grep -E '\.env|credentials|secrets'
```
Any match → block merge, investigate before proceeding.

**[BLOCK] Supply chain review**
Check the dependency manifest for new or unpinned packages introduced in this PR:
```bash
git diff main...HEAD -- requirements*.txt pyproject.toml package*.json
```
For each new dependency: verify it is pinned to a specific version and is a known, maintained package. Unpinned or unvetted packages → block merge.

**[PASS] Auto-close validation**
Confirm the PR body contains `Closes #N` referencing the linked issue:
```bash
gh pr view <number> --json body | jq '.body | test("Closes #[0-9]+")'
```
If missing → add it before merge, do not skip.

### Merge

```bash
gh pr merge <number> --squash --delete-branch
```

Squash merge only. No merge commits, no rebase. `--delete-branch` keeps the remote clean.

### Post-Merge Cleanup

Run once after merge is confirmed.

**Update `.out-of-scope.md`**
Any improvement deferred during `review` or `plan` that was explicitly not included in this PR:
```bash
# Append new ## section to .out-of-scope.md
cat >> .out-of-scope.md << EOF

## <Concept>

**Date:** $(date +%Y-%m-%d)
**Reason:** <why deferred — deferred in PR #<number>>
**Source ADR:** <ADR reference or N/A>

---
EOF
```

**Update `CONTEXT.md`**
Commit new architectural lessons, revised glossary terms, or boundary clarifications discovered during this task back to `CONTEXT.md`. This is not optional — every merge that produced an architectural insight must update `CONTEXT.md`.

```bash
git add CONTEXT.md .out-of-scope.md
git commit -m "docs: update CONTEXT.md and out-of-scope after PR #<number>"
```

## Quick Reference

| Gate | Severity | Failure action |
|---|---|---|
| Module Map check | BLOCK | Add missing row(s) to `CONTEXT.md` Module Map |
| Sandboxing verification | BLOCK | Investigate, do not merge |
| Supply chain review | BLOCK | Pin or remove package, do not merge |
| Auto-close `Closes #N` | BLOCK | Add to PR body |
| `CONTEXT.md` update | Required | Commit before closing session |
| `.out-of-scope.md` update | Required | Commit before closing session |

**Context sensitivity:** Low. Merge and knowledge persistence operations are stateless and safe at any context fill level.

## Common Mistakes

**Merging without running the security checklist.**
The checklist is not optional for "small" PRs. Supply chain and sandboxing checks take minutes and prevent hard-to-reverse incidents.

**Skipping `CONTEXT.md` update after merge.**
Lessons not written to `CONTEXT.md` are lost. The next session starts without them. Every merge with an architectural insight must update `CONTEXT.md`.

**Using merge commit instead of squash.**
Merge commits pollute history. `--squash` is the only permitted merge strategy. If the repository has a branch protection rule requiring a different strategy, update the rule — do not bypass the skill.

**Closing the issue manually before confirming `Closes #N` in the PR body.**
The PR body must auto-close the issue on merge. Manual close breaks the traceability link between commit and issue.
