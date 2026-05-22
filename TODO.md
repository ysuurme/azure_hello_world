# TODO

> Issues below are in the same format as `ISSUES.md` and can be moved there for `task sync` when ready to execute.

---

ISSUE: Graceful Copier Template Fallback in setup.py
LABELS: AFK
ESTIMATE: 3
PRIORITY: P3
**Goal**: Prevent `task setup` from crashing when `.copier-answers.yml` is missing by providing a graceful fallback mechanism.
**Description**: The current `src/tools/setup.py` script aggressively exits with an error if the copier answers file is missing. This breaks the `task setup` workflow for users bootstrapping manually outside of Copier or resolving conflicts. A graceful fallback or interactive prompt ensures the setup script remains robust.
**Requirements**:
1. Update `src/tools/setup.py` to check for `.copier-answers.yml`.
2. If missing, either prompt the user for `__PROJECT_NAME__`, `__PROJECT_DESCRIPTION__`, and `__PROJECT_TYPE__`, or use sensible placeholder defaults instead of calling `sys.exit(1)`.
3. Ensure `CONTEXT.md` replacement works cleanly with the defaults.
**Acceptance Criteria**:
- Running `task setup` without `.copier-answers.yml` completes successfully without crashing.
- `CONTEXT.md` is populated with either user-provided input or fallback defaults.
END_ISSUE

ISSUE: Automate GitHub Project Custom Fields Provisioning
LABELS: AFK
ESTIMATE: 5
PRIORITY: P4
**Goal**: Provide a true zero-touch quickstart by auto-creating missing Estimate and Priority fields on the GitHub Project.
**Description**: The agentic workflow relies heavily on the `Estimate` (Number) and `Priority` (Single Select) fields. Currently, `task setup` aborts if these are missing. Automatically provisioning them via `gh api graphql` or `gh project field-create` removes manual setup overhead for new repository initializations.
**Requirements**:
1. Update `.github/scripts/setup.ps1` to check for the presence of `Estimate` and `Priority`.
2. If missing, attempt to create them using `gh project field-create`.
3. For `Priority`, populate the single-select options with `P0,P1,P2,P3,P4`.
**Acceptance Criteria**:
- `task setup` successfully provisions the fields natively on a fresh GitHub Project.
- The user is not required to manually add these columns.
END_ISSUE

ISSUE: Ensure Base Labels are Created Before Issue Sync
LABELS: AFK
ESTIMATE: 2
PRIORITY: P3
**Goal**: Prevent `gh issue edit` and `sync-issues.ps1` from crashing due to missing repository labels.
**Description**: Fresh repositories lack the custom labels required by the agent workflow (e.g., `AFK`, `HITL`). When `sync-issues.ps1` attempts to push an issue with these labels, it fails unless the labels are created beforehand. Bootstrapping these during `task setup` ensures a smooth sync process.
**Requirements**:
1. Add a step in `.github/scripts/setup.ps1` that iterates through the required workflow labels (`AFK`, `HITL`, `agent:backlog`, etc.).
2. Use `gh label create <name> --force` or check existence before creating.
**Acceptance Criteria**:
- Running `task setup` provisions all essential labels on the GitHub repository.
- `task sync` does not throw "Label not found" exceptions on a clean repository.
END_ISSUE

ISSUE: Strip Metadata Headers from Synced Issue Bodies
LABELS: AFK
ESTIMATE: 3
PRIORITY: P3
**Goal**: Maintain clean, professional GitHub Issue descriptions by actively stripping metadata headers during sync.
**Description**: `sync-issues.ps1` correctly parses `LABELS:`, `ESTIMATE:`, and `PRIORITY:` to map them to native GitHub Project fields, but it leaves the raw text headers inside the issue body. Scrubbing these headers from the final body description improves readability and avoids redundant clutter.
**Requirements**:
1. Update `.github/scripts/sync-issues.ps1` to regex-replace or strip the metadata header lines from the `$IssueBody` string before calling `gh issue create` or `gh issue edit`.
2. Ensure only the true markdown content (Goal, Description, etc.) is pushed.
**Acceptance Criteria**:
- Newly synced issues display only the Goal, Description, Requirements, and Acceptance Criteria.
- Metadata headers are completely removed from the issue body in GitHub.
END_ISSUE

---
