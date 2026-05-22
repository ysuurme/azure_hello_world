---
name: version-control
description: Use when creating a branch, making commits, pushing to remote, opening a pull request, or automating the full branch-to-PR flow linked to a GitHub Issue
---

# Version Control

## Overview

Enforces consistent branch, commit, and PR conventions so that every piece of work is traceable from GitHub Issue to squash-merged commit. Used by every workflow phase that touches git or the GitHub API.

**Primary artifact:** Linked branch → commit(s) → PR tied to a GitHub Issue.

## Scope

**Owns:** Branch naming convention, commit message format, PR creation with issue auto-close (`Closes #N`), GitHub CLI (`gh`) command patterns, agent-driven automation of the branch → commit → PR flow, worktree creation for isolated fix branches.

**Does not own:** CI/CD pipeline configuration (→ `harness`), code review standards (→ `review`), PR merge and security governance (→ `ship`).

**Interfaces with:** All workflow skills — every phase that touches git or the GitHub API uses the conventions defined here.

## When to Use

- Starting work on a GitHub Issue — create the branch
- Committing implementation or test changes
- Opening a PR for review
- Automating the full flow from an agent-driven task completion

**Do NOT use for:** Configuring CI/CD (→ `harness`), reviewing PR content (→ `review`), merging (→ `ship`).

## Required Inputs

- GitHub Issue number (required — the traceability anchor for all branch and PR operations)
- Issue title (for branch slug and PR title)
- Local git repository with `gh` CLI authenticated

## Primary Outputs

- Feature branch named `feature/{issue-number}-{dense-slug}`
- Commit with message following `<type>(<scope>): <description>` format and `Closes #N`
- PR with title, summary, and `Closes #N` in body

## Core Pattern

### Branch Naming

```
feature/{issue-number}-{dense-slug}     # New feature linked to a GitHub Issue
fix/{issue-number}-{dense-slug}         # Bug fix linked to a GitHub Issue
docs/{issue-number}-{dense-slug}        # Documentation only
refactor/{issue-number}-{dense-slug}    # Refactoring with no behaviour change
```

Use kebab-case. Slug: 2–4 words maximum, describing the change densely. Issue number is required — it is the traceability anchor that links the branch to the kanban pipeline and enables auto-branch detection in `implement.ps1`.

```bash
git checkout -b feature/42-user-auth-endpoint
git checkout -b fix/17-gitignore-secret-patterns
git checkout -b docs/16-sdlc-prd
```

The Director Workflow (`implement.ps1`) auto-generates branch names as `feature/{number}-{word1}-{word2}-{word3}` from the issue title. Manual branches must follow the same pattern so `Get-CurrentIssueNumber` can parse the issue number from the branch name.

### Commit Message Format

```
<type>(<scope>): <short description>

[optional body — explain WHY, not WHAT]

Closes #<issue-number>
```

**Types:** `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
**Scope:** module or domain area affected (e.g. `orders`, `auth`, `pipeline`)
**Closes #N:** required on the final commit before PR creation

```bash
git commit -m "feat(orders): add tax calculation to order total

Resolves rounding error in multi-item orders with fractional tax rates.

Closes #42"
```

### PR Creation

```bash
gh pr create \
  --title "feat(orders): add tax calculation to order total" \
  --body "## Summary
- Added tax calculation logic to Order.total()
- Covered by 4 new pytest cases

## Closes
Closes #42" \
  --base main
```

**PR body must contain `Closes #N`.** Validated by `ship` before merge.

### Worktree for Isolated Fix Branches

When the review auto-fix loop needs an isolated environment:

```bash
git worktree add ../fix-branch-<description> -b fix/<description>
# Work in ../fix-branch-<description>
# On completion:
git worktree remove ../fix-branch-<description>
```

## Quick Reference

| Convention | Pattern | Example |
|---|---|---|
| Feature branch | `feature/<desc>` | `feature/user-auth` |
| Fix branch | `fix/<desc>` | `fix/order-rounding` |
| Commit type | `feat\|fix\|refactor\|test\|docs\|chore` | `feat(orders): ...` |
| Auto-close | `Closes #N` in commit or PR body | `Closes #42` |
| Merge strategy | Squash only (owned by `ship`) | `gh pr merge --squash` |

**Context sensitivity:** Low. Version-control operations are stateless and safe at any context fill level.

## Common Mistakes

**Missing `Closes #N` in PR body.**
`ship` validates this before merge. If it's missing, the issue stays open after merge and the traceability link is broken.

**Committing directly to `main`.**
All changes go through a branch and PR. No exceptions. Direct commits to `main` bypass `review` and `ship`.

**Long, descriptive branch names.**
Branch names are navigational, not descriptive. Keep under 5 words. The PR title and commit message carry the description.

**Forgetting to remove worktrees.**
Abandoned worktrees accumulate as stale directories. Always `git worktree remove` after the fix branch is merged or abandoned.
