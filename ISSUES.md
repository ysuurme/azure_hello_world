# 📝 Agile Issue Tracking

> Issues defined here are parsed by `.github/scripts/sync-issues.ps1` and synced to the **@hello_architect** GitHub Project via `task sync`.
> Successfully synced issues are automatically removed from this file to prevent duplication.

## Format

Wrap every issue within ISSUE / END_ISSUE blocks so the parser can harvest them.

---

ISSUE: Restore AGENT_DRIVER dispatch in agent-listener.ps1

**Goal**: Re-apply the Claude driver bootstrap logic to agent-listener.ps1 that was lost in commit 370f194 ("removed CLaude").

**Description**:
The listener currently always starts the MCP bridge and has no concept of AGENT_DRIVER. The Phase 2 implementation added:
- Reading `AGENT_DRIVER` from `.env` (defaulting to `gemini`)
- Skipping the MCP bridge startup when `AGENT_DRIVER=claude`
- Validating the Anthropic endpoint (`/v1/messages`) instead when `AGENT_DRIVER=claude`
- Driver-aware branch comment in `Invoke-DevelopPhase`
These changes were reverted and need to be re-applied cleanly.

**Requirements**:
1. Read `AGENT_DRIVER` and `LOCAL_AI_URL` from `.env` in `Invoke-EnvironmentBootstrap` alongside existing `LOCAL_AI_MODEL` parsing.
2. Log the active driver at bootstrap: `Agent driver: GEMINI` or `Agent driver: CLAUDE`.
3. Gate the entire MCP bridge block (bridge process, npm resolution, settings.json write) behind `if ($script:AgentDriver -eq "gemini")`.
4. When `AGENT_DRIVER=claude`, validate the Anthropic endpoint: POST to `$LOCAL_AI_URL/v1/messages` with a hello-world payload and log success or warning.
5. In `Invoke-DevelopPhase`, set `$DriverLabel` dynamically: `"Claude Code"` or `"Gemini CLI"`.
6. Update the `.SYNOPSIS` / `.DESCRIPTION` comment block to reflect the dual-driver architecture.

**Acceptance Criteria**:
- `task agent:listen:debug` with `AGENT_DRIVER=gemini` starts the MCP bridge as before — no regression.
- `task agent:listen:debug` with `AGENT_DRIVER=claude` skips the bridge, validates `/v1/messages`, logs `Agent driver: CLAUDE`.
- All existing tests pass (`task test`).
- Lint passes (`task lint`).

END_ISSUE

ISSUE: Validate AGENT_DRIVER value on bootstrap

**Goal**: Fail loudly and early when `AGENT_DRIVER` is set to an unrecognised value, rather than producing a cryptic "task not found" error mid-run.

**Description**:
`task agent:dev` dispatches to `agent:dev:gemini` or `agent:dev:claude` based on `AGENT_DRIVER`. A typo (e.g. `AGENT_DRIVER=Gemini` or `AGENT_DRIVER=gemnii`) silently resolves to a non-existent task name and the listener logs a confusing exit-code failure after the issue is already claimed.

**Requirements**:
1. In `Invoke-EnvironmentBootstrap`, after reading `AGENT_DRIVER`, assert the value is `gemini` or `claude` (case-insensitive, normalise to lowercase).
2. If invalid, log a clear error and exit the script with a non-zero code before any git or GitHub operations are performed.
3. Add the same guard to the `status` task in `Taskfile.yml` as a pre-flight check when `AGENT_DRIVER` is set.

**Acceptance Criteria**:
- Starting the listener with `AGENT_DRIVER=typo` exits immediately with a clear error message naming the invalid value and the accepted values.
- Valid values `gemini` and `claude` (any casing) proceed normally.

END_ISSUE

ISSUE: Extend status task to validate the active driver CLI

**Goal**: The `status` task (run before every listener start) should verify the active driver's CLI is installed and authenticated, not just `gh` and `ssh`.

**Description**:
Currently `status` checks GitHub CLI auth and SSH. When `AGENT_DRIVER=claude`, it does not check whether `claude` is installed or logged in. When `AGENT_DRIVER=gemini`, it does not check `gemini --version`. A missing CLI surfaces as a silent failure inside a running agent session rather than a clean pre-flight error.

**Requirements**:
1. Read `AGENT_DRIVER` in the `status` task (or pass it as a variable).
2. If `gemini`: run `gemini --version` and fail with a clear message if not found.
3. If `claude`: run `claude --version` and fail with a clear message if not found.
4. Keep existing `gh auth status` and `ssh -T git@github.com` checks.

**Acceptance Criteria**:
- `task status` (or `task agent:listen`) fails with a driver-specific error message when the active driver CLI is absent.
- No regression when both CLIs are installed.

END_ISSUE

ISSUE: LLM-powered Phase A issue refinement

**Goal**: Replace the static template in `Invoke-RefinePhase` with an actual LLM call that analyses and formalises the raw issue.

**Description**:
Phase A currently wraps the raw issue body in a hardcoded markdown template (Goal / Description / Requirements / Acceptance Criteria). There is no intelligence applied — requirements are always the same three generic lines. With both Gemini and Claude available as drivers, Phase A should use the active cloud model to read the raw issue, extract implicit requirements, flag ambiguity, and produce a properly structured issue body. This is where reasoning adds the most value before any code is written.

**Requirements**:
1. When the issue body is unstructured (current guard condition already detects this), invoke the active driver CLI with a focused refinement prompt.
2. The prompt should instruct the model to: extract a clear Goal, write a precise Description, enumerate concrete Requirements derived from the issue text, and define measurable Acceptance Criteria.
3. The model output replaces the static template as the new issue body (written back via `gh issue edit --body-file`).
4. Respect `AGENT_DRIVER`: use `gemini -p` for the Gemini driver, `claude -p` for the Claude driver.
5. Keep the existing guard: if the issue is already structured, skip refinement.

**Acceptance Criteria**:
- A raw one-liner issue body is transformed into a structured four-section format by the LLM.
- The refinement comment posted to the issue reflects LLM-generated content, not the static template.
- Lint and tests pass.

END_ISSUE

ISSUE: Dispatch agent:review to active driver

**Goal**: `agent:review` should use the active `AGENT_DRIVER` rather than always running Gemini CLI.

**Description**:
`agent:review` is hardcoded to `gemini -p`. When `AGENT_DRIVER=claude`, the review step still invokes Gemini — this is inconsistent and requires Gemini credentials even in a Claude-only setup. The review task should dispatch to `agent:review:gemini` or `agent:review:claude` using the same pattern as `agent:dev`.

**Requirements**:
1. Rename current `agent:review` body to `agent:review:gemini`.
2. Add `agent:review:claude` that uses `claude --dangerously-skip-permissions -p` with an equivalent critic prompt referencing `AI.md` and `.agents/skills/review-code/SKILL.md`. Output must still start with `APPROVED` or `REJECTED` so the listener parse logic works unchanged.
3. Add `agent:review` dispatcher: `task agent:review:{{.AGENT_DRIVER | default "gemini"}} ISSUE={{.ISSUE}} PR={{.PR}}`.

**Acceptance Criteria**:
- `task agent:review ISSUE=N PR=M` with `AGENT_DRIVER=claude` invokes Claude, not Gemini.
- The `APPROVED`/`REJECTED` parse in `agent-listener.ps1` works for both driver outputs.
- Lint and tests pass.

END_ISSUE

ISSUE: Install d2 binary in pr-checks.yml CI workflow

**Goal**: Fix the CI test suite so `task test` passes on `ubuntu-latest` runners.

**Description**:
`task test` calls the `d2` binary to compile a test diagram. `d2` is not installed on GitHub-hosted `ubuntu-latest` runners, so the test step silently fails or errors on every PR. The CI is currently a broken critic.

**Requirements**:
1. Add a step to `.github/workflows/pr-checks.yml` to install the `d2` binary before `task test` runs. Use the official install script: `curl -fsSL https://d2lang.com/install.sh | sh -s --`.
2. Verify the install step runs before the Test step.
3. Confirm the workflow passes end-to-end on a test PR.

**Acceptance Criteria**:
- `pr-checks.yml` lint and test steps both pass on `ubuntu-latest` without manual intervention.
- The d2 install adds no more than 30 seconds to CI runtime.

END_ISSUE

ISSUE: Clean up stale .pyc file and add logs/ to .gitignore

**Goal**: Remove build artefacts from version control and prevent log files from being committed.

**Description**:
Two housekeeping issues:
1. `.github/scripts/__pycache__/local_coder.cpython-310.pyc` is a compiled artefact from a deleted source file. It has no corresponding `.py` source and should be removed.
2. The `logs/` directory (written by `agent-listener.ps1`) is not in `.gitignore`. Log files are runtime output and should never be committed.

**Requirements**:
1. Delete `.github/scripts/__pycache__/local_coder.cpython-310.pyc` and the `__pycache__` directory if empty.
2. Add `logs/` and `**/__pycache__/` to `.gitignore` if not already present.
3. Verify `.gitignore` also covers `.env` (secrets must not be committed).

**Acceptance Criteria**:
- `git status` shows no `__pycache__` or `logs/` entries after the change.
- `.gitignore` explicitly covers `logs/`, `**/__pycache__/`, and `.env`.
- Lint and tests pass.

END_ISSUE
