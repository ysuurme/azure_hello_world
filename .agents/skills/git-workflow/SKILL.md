---
name: git-workflow
description: Use when automating git operations including branch creation, commit, push, and pull request creation from agent-driven task completions linked to GitHub Issues
---

# Git Workflow for Agent-Driven Development

## Overview

Deterministic protocol for git operations when an agent completes work on a GitHub Issue. Ensures branches are linked, commits are traceable, PRs auto-close issues, and errors are caught before broken code is pushed.

## When to Use

- Agent is completing development work linked to a GitHub Issue
- Automating branch → commit → push → PR flow
- Working in the `agent-listener.ps1` two-phase loop (Phase B: Develop)

**Do NOT use for:**
- Manual developer workflows (use standard git flow)
- Exploratory branches not tied to an issue

## Baseline Failures (TDD Evidence)

Without this skill, agents consistently hallucinate these anti-patterns:

| Anti-Pattern | Impact |
|-------------|--------|
| `git checkout -b feature-name` instead of `gh issue develop` | Branch is NOT linked to the issue in GitHub |
| Descriptive commit messages | Not machine-parseable, inconsistent across agent runs |
| Hardcoded branch name in `git push` | Fragile — fails if branch name format changes |
| PR body omits `Closes #N` | Issue stays open after merge, requires manual cleanup |
| No `$LASTEXITCODE` checks | Broken code gets pushed after a failed test run |
| Checkout on dirty working tree | Silent data loss or checkout failure |

## Core Pattern

### Before (Hallucinated)

```powershell
git checkout -b add-error-logging
# ... make changes ...
git add .
git commit -m "Add error logging to orchestrator"
git push origin add-error-logging
gh pr create --title "Add error logging" --body "Added error logging"
```

### After (Correct)

```powershell
$IssueNumber = 42
$IssueTitle = "Add error logging"

# 1. Protect local work
$StashResult = git stash 2>&1
$DidStash = $StashResult -notmatch "No local changes"

try {
    # 2. Create linked branch (auto-links issue in GitHub)
    gh issue develop $IssueNumber --checkout 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Branch creation failed" }

    # 3. ... make changes ...

    # 4. Standardized commit
    git add . 2>&1 | Out-Null
    git commit -m "Agent completed task #$IssueNumber" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Commit failed" }

    # 5. Push current branch (name-agnostic)
    git push origin HEAD 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Push failed" }

    # 6. PR with auto-close reference
    gh pr create --title "Agent: $IssueTitle" --body "Closes #$IssueNumber" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "PR creation failed" }
}
finally {
    # 7. Always restore stashed work
    if ($DidStash) { git stash pop 2>&1 | Out-Null }
}
```

## Quick Reference

| Step | Command | Why |
|------|---------|-----|
| Protect local work | `git stash` | Prevents dirty-tree checkout failure |
| Create branch | `gh issue develop $N --checkout` | Auto-links branch to issue in GitHub UI |
| Commit | `git commit -m "Agent completed task #$N"` | Machine-parseable, traceable convention |
| Push | `git push origin HEAD` | Name-agnostic — works regardless of branch naming format |
| Create PR | `gh pr create --body "Closes #$N"` | Auto-closes issue on merge |
| Error guard | Check `$LASTEXITCODE -ne 0` after every command | Prevents pushing broken code |
| Restore work | `git stash pop` in `finally` block | Always restores developer's local changes |

## Common Mistakes

**Mistake:** Skipping error checks "because it usually works."
**Fix:** Every `git` and `gh` command MUST be followed by a `$LASTEXITCODE` check. No exceptions. If ANY step fails, abort the entire flow. Do not continue to the next step.

**Mistake:** Using `git push origin branch-name` with a hardcoded name.
**Fix:** Always use `git push origin HEAD`. The `gh issue develop` command may generate branch names in unexpected formats (`user/42-issue-title`). `HEAD` is always correct.

**Mistake:** Writing a descriptive PR body instead of the `Closes #N` reference.
**Fix:** The PR body MUST contain `Closes #N` on its own line. Additional description is allowed AFTER the closing reference, never instead of it.
