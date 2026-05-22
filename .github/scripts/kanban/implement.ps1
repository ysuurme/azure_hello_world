#Requires -Version 7.0
<#
.SYNOPSIS
    Stage 2 — Implementing: Refine → Architecture → Develop → PR.

.DESCRIPTION
    Internal function library — dot-sourced by run.ps1. Not a direct Taskfile target.

    Phase A  Refine       — structures the issue body using the ISSUES.md template if
                            not already structured. Assigns estimate and priority if absent.
    Phase A.5 Architecture — blast-radius computation; emits .planning/<issue>/BLAST_RADIUS.md;
                            records state transitions.
    Phase B  Develop      — invokes Claude Code non-interactively to implement all
                            requirements and verify with uv run pytest.
    Phase C  PR           — commits (Claude-generated message), pushes, opens PR.
#>

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"
. "$PSScriptRoot\architecture.ps1"

# ── Phase A: Refine ───────────────────────────────────────────────────────────

function Invoke-Refine {
    param([int]$Number)
    Write-Log "  Phase A — Refine issue #$Number" -Color Yellow
    Set-PipelineState -IssueNumber $Number -Phase 'refining'

    $issue    = gh issue view $Number --repo $KanbanRepo --json title,body,comments | ConvertFrom-Json
    $template = Get-IssueTemplate

    # Determine what needs work
    $needsBodyRefine = $false
    if ($template) {
        $headings        = $template -split '\r?\n' |
            Where-Object { $_ -match '^\*\*\w' } |
            ForEach-Object { ($_ -split ':')[0] }
        $missing         = @($headings | Where-Object { $issue.body -notmatch [regex]::Escape($_) })
        $needsBodyRefine = $missing.Count -gt 0
    } else {
        $needsBodyRefine = $true
    }

    # Short-circuit: a prior pass that completed refinement posts a "· refined —" comment
    # at the bottom of Invoke-Refine. Body is locally verifiable, the marker proves
    # estimate/priority were addressed — so we can skip Get-ProjectFieldValues entirely.
    $hasRefinedMarker = @($issue.comments | Where-Object { $_.body -like '* refined*' }).Count -gt 0
    if (-not $needsBodyRefine -and $hasRefinedMarker) {
        Write-Log "  Issue already fully refined — skipping." -Color DarkGray
        return
    }

    # Estimate and Priority are GitHub Project fields — not labels.
    # Get-ProjectFieldValues returns $null for two distinct cases:
    #   1. gh call failed (rate limit, network, missing scope) — we DON'T know the current values
    #   2. Issue is not on the project board — we can't write back anyway
    # In either case, refining estimate/priority via LLM would either overwrite
    # known-good manual values (case 1) or write to a board the issue isn't on
    # (case 2). Treat null as "skip field refine" — body refine still runs.
    $projectFields = Get-ProjectFieldValues -IssueNumber $Number
    if ($null -eq $projectFields) {
        Write-Log "  ⚠️ Could not read project fields — skipping estimate/priority refine (any manual values preserved)." -Color Yellow
        $needsEstimate = $false
        $needsPriority = $false
    } else {
        $needsEstimate = -not ($null -ne $projectFields.estimate -and "$($projectFields.estimate)" -ne '')
        $needsPriority = -not $projectFields.priority
    }

    if (-not $needsBodyRefine -and -not $needsEstimate -and -not $needsPriority) {
        Write-Log "  Issue already fully refined — skipping." -Color DarkGray
        return
    }

    $bodyInstruction = if ($needsBodyRefine -and $template) {
        "REWRITE the body to match this field structure exactly (fill all fields from the raw issue — do not invent requirements):`n`n$template"
    } elseif ($needsBodyRefine) {
        "REWRITE the body with: **Goal**, **Description**, **Requirements** (numbered), **Acceptance Criteria** (bulleted)."
    } else {
        "Body is already structured — copy it unchanged into the 'body' field."
    }

    $estimateInstruction = if ($needsEstimate) {
        'ASSIGN estimate: Fibonacci SP — 1=trivial single-file, 2=small bounded, 3=moderate multi-file, 5=clear multi-component, 8=complex architectural, 13=large multi-area, 21=epic requiring human collaboration.'
    } else {
        'Estimate already set — output null.'
    }

    # Discover the actual priority option names configured in this project.
    $priorityOpts = @([System.Environment]::GetEnvironmentVariables('Process').Keys) |
        Where-Object { $_ -match '^KANBAN_PRIORITY_OPT_' } |
        ForEach-Object { $_ -replace '^KANBAN_PRIORITY_OPT_', '' } |
        Sort-Object
    $priorityOptsStr = if ($priorityOpts) { $priorityOpts -join ', ' } else { 'P0, P1, P2, P3, P4' }

    $priorityInstruction = if ($needsPriority) {
        "ASSIGN priority using exactly one of the project's configured values: $priorityOptsStr"
    } else {
        'Priority already set — output null.'
    }

    $prompt = @"
You are refining a GitHub issue so it is fully specified before implementation begins.

ISSUE TITLE: $($issue.title)
CURRENT BODY:
$($issue.body)

TASKS:
1. Body: $bodyInstruction
2. Estimate: $estimateInstruction
3. Priority: $priorityInstruction

Return ONLY valid JSON — no markdown fences, no explanation:
{"body":"<full issue body>","estimate":<number or null>,"priority":"<one of the allowed values or null>"}
"@

    $raw = $prompt | claude --model $KanbanModel_Sonnet 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw "Claude refinement failed: $raw" }

    $json = $raw.Trim()
    if ($json -match '(?s)```(?:json)?\s*(\{.+\})\s*```') { $json = $Matches[1] }
    $parsed = $json | ConvertFrom-Json -ErrorAction SilentlyContinue
    if (-not $parsed) {
        Write-Log "  ⚠️ Refine: could not parse response — skipping." -Color Yellow
        return
    }

    if ($needsBodyRefine -and $parsed.body) {
        $tmp = New-TemporaryFile
        try {
            $parsed.body.Trim() | Out-File $tmp.FullName -Encoding utf8
            gh issue edit $Number --repo $KanbanRepo --body-file $tmp.FullName 2>&1 | Out-Null
        } finally {
            Remove-Item $tmp.FullName -ErrorAction SilentlyContinue
        }
    }

    if ($needsEstimate -and $null -ne $parsed.estimate -and $parsed.estimate -ne 'null') {
        Set-ProjectEstimate -IssueNumber $Number -Estimate ([int]$parsed.estimate)
    }

    if ($needsPriority -and $parsed.priority -and $parsed.priority -ne 'null') {
        Set-ProjectPriority -IssueNumber $Number -Priority $parsed.priority
    }

    $changes = @()
    if ($needsBodyRefine)                                                                   { $changes += 'body structured' }
    if ($needsEstimate -and $null -ne $parsed.estimate -and $parsed.estimate -ne 'null')   { $changes += "estimate=$($parsed.estimate)" }
    if ($needsPriority -and $parsed.priority -and $parsed.priority -ne 'null')             { $changes += "priority=$($parsed.priority)" }

    Add-Comment -Number $Number -Body "· refined — $($changes -join ', ')"
    Write-Log "  Issue #$Number refined: $($changes -join ', ')" -Color Green
}

# ── Phase B: Develop ──────────────────────────────────────────────────────────

function Invoke-Develop {
    param([int]$Number, [string]$Branch)
    Write-Log "  Phase B — Develop issue #$Number on $Branch" -Color Yellow
    Set-PipelineState -IssueNumber $Number -Phase 'implementing'
    Move-ToLane -IssueNumber $Number -OptionId $KanbanOpt_Implementing -LaneName 'Implementing'
    Add-Comment -Number $Number -Body "· branch checked out — starting"

    if ((Get-ChildItem .agents/skills -Recurse -Filter *.md -ErrorAction SilentlyContinue).Count -eq 0) {
        Write-Log "⚠️ Skills directory is empty — agent constraints will not be applied." -Color Yellow
    }

    $issue = gh issue view $Number --repo $KanbanRepo --json title,body | ConvertFrom-Json

    # Retrieve all agent signal comments (🤖-prefixed) — full decision history for this issue.
    # Includes review rejections, CI failures, prior implementation summaries, and errors.
    $signal = gh issue view $Number --repo $KanbanRepo --json comments `
        --jq '[.comments[] | select(.body | startswith("🤖"))] | map(.body) | join("\n---\n")' 2>&1 | Out-String
    $signalSection = if ($LASTEXITCODE -eq 0 -and $signal.Trim() -and $signal.Trim() -ne 'null') {
        "`nISSUE SIGNAL HISTORY (agent decisions and outcomes — address all rejections and failures before finishing):`n$($signal.Trim())"
    } else { '' }

    $prompt = @"
You are implementing GitHub issue #$Number on branch $Branch in this repository.

ISSUE TITLE: $($issue.title)

ISSUE BODY:
$($issue.body)
$signalSection
INSTRUCTIONS:
1. Read AGENTS.md and CONTEXT.md first to understand the project boundaries and constraints.
2. Read the relevant parts of the codebase before writing any code.
3. Implement every requirement listed in the issue body completely.
4. Follow all conventions in AGENTS.md. The skill files in ``.agents/skills/`` are your constraint documents — locate the relevant skill via the Skills index in AGENTS.md, then read its SKILL.md (and REFERENCE.md / EXAMPLES.md if linked) before implementing.
5. After implementation run ``uv run pytest`` to verify the test suite passes.
6. If tests fail, diagnose and fix the root cause before stopping.
7. Do NOT commit any changes — only implement.
8. End your response with a concise bullet-point summary of every file you changed.
"@

    $sp       = Get-IssueEstimate -IssueNumber $Number
    $devModel = Get-PhaseModel -Estimate $sp -Phase 'implement'
    $devTurns = Get-ImplementMaxTurns -Estimate $sp
    Write-Log "  Model: $devModel  SP=$sp  max-turns=$devTurns" -Color DarkGray

    $allText           = [System.Text.StringBuilder]::new()
    $modifiedFiles     = [System.Collections.Generic.List[string]]::new()
    $explorationPosted = $false
    $writingPosted     = $false
    $testedOnce        = $false

    $prompt | claude --model $devModel --allowedTools "Read,Write,Edit,Bash,Glob,Grep" --max-turns $devTurns --output-format stream-json --verbose 2>&1 |
    ForEach-Object {
        $raw = [string]$_
        try {
            $ev = $raw | ConvertFrom-Json -ErrorAction Stop

            $blocks = if ($ev.message.content) { $ev.message.content }
                      elseif ($ev.content)      { $ev.content }
                      else                      { @() }

            foreach ($block in $blocks) {
                switch ($block.type) {
                    'text' {
                        Write-Host $block.text -NoNewline
                        $null = $allText.Append($block.text)
                    }
                    'tool_use' {
                        $inputReady = ($block.input.PSObject.Properties | Measure-Object).Count -gt 0
                        if ($inputReady) {
                            Write-Host "`n  $(Format-ToolLine -Name $block.name -ToolInput $block.input)" -ForegroundColor DarkCyan
                        }

                        if ($block.name -in @('Read','Glob','Grep') -and -not $explorationPosted) {
                            $explorationPosted = $true
                            Add-Comment -Number $Number -Body "· exploring codebase"
                        }
                        if ($block.name -in @('Write','Edit') -and $block.input.file_path) {
                            if (-not $writingPosted) {
                                $writingPosted = $true
                                Add-Comment -Number $Number -Body "· writing implementation"
                            }
                            $fp = $block.input.file_path
                            if (-not $modifiedFiles.Contains($fp)) { $modifiedFiles.Add($fp) }
                        }
                        if ($block.name -eq 'Bash' -and $block.input.command -match 'pytest' -and -not $testedOnce) {
                            $testedOnce = $true
                            Add-Comment -Number $Number -Body "· running tests"
                        }
                    }
                }
            }

            if ($ev.type -eq 'result') { Write-Host '' }
        } catch {
            if ($raw.Trim()) { Write-Host $raw -ForegroundColor DarkGray }
        }
    }

    if ($LASTEXITCODE -ne 0) { throw "Claude Code exited with code $LASTEXITCODE." }

    $bullets     = ($allText.ToString() -split '\r?\n') |
                   Where-Object { $_ -match '^\s*[-*•]' } |
                   Select-Object -Last 20
    $summaryText = if ($bullets) { $bullets -join "`n" } else { '(see PR diff for details)' }
    $fileSection = if ($modifiedFiles.Count -gt 0) {
        $fileLines = ($modifiedFiles | Select-Object -Unique |
                      ForEach-Object { "- ``$(Split-Path $_ -Leaf)``" }) -join "`n"
        "`n`n**Files changed ($($modifiedFiles.Count)):**`n$fileLines"
    } else { '' }
    Add-Comment -Number $Number -Body "🤖 Implementation$fileSection`n`n$summaryText"
    Write-Log "  Implementation finished for issue #$Number." -Color Green

    # Independent verification — output posted as signal so the reviewer can read exact results
    Write-Log "  Running test suite independently..." -Color DarkGray
    $testOutput = uv run pytest --tb=short -q 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Add-Comment -Number $Number -Body "🤖⚠️ Tests Failing`n``````text`n$($testOutput.Trim())`n``````"
        throw "Test suite failed after implementation for issue #$Number"
    }
    $testSummary = (($testOutput -split '\r?\n') | Where-Object { $_.Trim() } | Select-Object -Last 4) -join "`n"
    Add-Comment -Number $Number -Body "🤖✅ Tests Passing`n``````text`n$($testSummary.Trim())`n``````"
    Write-Log "  Tests passing ✅" -Color Green
}

# ── Phase C: Commit + PR ──────────────────────────────────────────────────────

function Invoke-CommitAndPR {
    param([int]$Number, [string]$Title, [string]$Branch)
    Write-Log "  Phase C — Commit + PR for issue #$Number" -Color Yellow

    # Auto-format before staging so ruff format --check in CI always passes.
    $fmtOut = uv run ruff format . 2>&1 | Out-String
    Write-Log "  ruff format: $($fmtOut.Trim())" -Color DarkGray

    # Stage only known-safe paths rather than git add . — an agent implementation
    # can create .env files, credentials, or other sensitive artefacts; the allowlist
    # ensures nothing outside these directories ever reaches the index.
    # Stage every tracked + untracked change that .gitignore allows. The denylist
    # below is the final safety net for sensitive leaf names. Previously a static
    # allowlist silently dropped legitimate edits to files like SECURITY.md and
    # .devcontainer/devcontainer.json, leading to "Already implemented — no new
    # changes" false positives and PR-creation failures despite real work on disk.
    git add -A 2>&1 | Out-Null

    # Guard: inspect every staged path against a denylist and silently unstage any match.
    # docs/adr/ is exempt — ADR filenames legitimately contain words like "secret" or
    # "credential" (e.g. ADR-008-secrets-management.md) and must never be dropped.
    $denyPatterns = @('.env', '*.key', '*.pem', '*.pfx', '*secret*', '*credential*')
    foreach ($file in @(git diff --staged --name-only 2>&1)) {
        if ($file -like 'docs/adr/*') { continue }
        $leaf = Split-Path $file -Leaf
        if ($denyPatterns | Where-Object { $leaf -like $_ }) {
            git reset HEAD -- $file 2>&1 | Out-Null
            Write-Log "  WARNING: sensitive file unstaged from index: $file" -Color Red
        }
    }

    if (git diff --cached --name-only 2>&1) {
        $diff    = git diff --staged 2>&1 | Out-String
        $message = Get-CommitMessage -Diff $diff -FallbackMessage "feat(#${Number}): $Title"
        $msgFile = New-TemporaryFile
        try {
            $message | Out-File $msgFile.FullName -Encoding utf8
            $commitOut = git commit -F $msgFile.FullName 2>&1 | Out-String
            if ($LASTEXITCODE -ne 0) { throw "git commit failed for issue #${Number}:`n$commitOut" }
        } finally {
            Remove-Item $msgFile.FullName -ErrorAction SilentlyContinue
        }
    } else {
        # No new changes this run. Determine whether the branch as a whole has any
        # commits vs the default branch — if not, there is nothing to PR. This is
        # the typical state for tracker/coordinator issues whose acceptance criteria
        # are satisfied by previously-merged child PRs: the implement phase correctly
        # produces no diff, and forcing a PR here would fail with "no commits between
        # branches". Return $null so the caller (run.ps1) closes the issue as merged
        # without invoking the review/merge stages.
        $defaultBranch = gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>$null
        git fetch --quiet origin $defaultBranch 2>$null
        $aheadCount = [int]((git rev-list --count "origin/${defaultBranch}..HEAD" 2>$null) | Out-String).Trim()

        if ($aheadCount -eq 0) {
            Write-Log "  ✅ Already implemented — branch has no commits ahead of $defaultBranch. Skipping PR." -Color Green
            Add-Comment -Number $Number -Body "🤖✅ Already Implemented`n`nAll acceptance criteria are satisfied without code changes — branch ``$Branch`` has no commits ahead of ``$defaultBranch``. Tests pass. Closing as merged without raising a PR."
            return $null
        }

        Write-Log "  ✅ No new changes this run — prior commits on branch. Proceeding to PR." -Color Green
        Add-Comment -Number $Number -Body "🤖 Implementation`n`nNo new changes this run — branch already carries prior commits implementing this issue. Proceeding to PR and review."
    }

    # Capture stderr so any push rejection (workflow scope, branch protection,
    # secret scanning) surfaces in the thrown message. Previously `2>$null`
    # turned every push failure into a useless generic "git push failed" —
    # observed when issue #42 modified .github/workflows/ci.yml and the PAT
    # lacked the `workflow` scope; the real GitHub error never made it to logs.
    $pushOut = git push --quiet origin HEAD 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        throw "git push failed for branch ${Branch}:`n$($pushOut.Trim())"
    }

    $existing = gh pr list --head $Branch --json url --limit 1 | ConvertFrom-Json
    if ($existing.Count -gt 0) {
        $prUrl = $existing[0].url
        Write-Log "  PR already exists: $prUrl" -Color DarkGray
    } else {
        $body = @"
## Summary
Automated implementation for issue #$Number by Claude Code agent.

## Validation
- ``uv run pytest`` — ✅ passed (verified by orchestrator)

## Linked Issue
Closes #$Number
"@
        $tmp = New-TemporaryFile
        try {
            $body | Out-File $tmp.FullName -Encoding utf8
            $prUrl = gh pr create `
                --title "feat(#${Number}): $Title" `
                --body-file $tmp.FullName `
                --head $Branch 2>$null
            if ($LASTEXITCODE -ne 0) { throw "PR creation failed for issue #$Number" }
            $prUrl = $prUrl.Trim()
        } finally {
            Remove-Item $tmp.FullName -ErrorAction SilentlyContinue
        }
        Write-Log "  PR created: $prUrl" -Color Green
    }

    Add-Comment -Number $Number -Body "· PR opened — $prUrl"
    return $prUrl
}

# ── Orchestrator entry point ──────────────────────────────────────────────────

function Invoke-Implement {
    param([int]$IssueNumber = 0, [switch]$Force)

    if ($IssueNumber -eq 0) { $IssueNumber = Get-CurrentIssueNumber }
    if ($IssueNumber -eq 0) {
        throw "No issue found — Invoke-Implement must be called with an explicit IssueNumber."
    }

    $meta           = gh issue view $IssueNumber --repo $KanbanRepo --json title | ConvertFrom-Json
    $expectedBranch = Get-BranchName -Number $IssueNumber -Title $meta.title
    $branch         = git rev-parse --abbrev-ref HEAD

    if ($branch -ne $expectedBranch) {
        Write-Log "  Creating feature branch for issue #$IssueNumber..." -Color DarkGray
        Add-Comment -Number $IssueNumber -Body "· picked up — branch ``$expectedBranch``"
        $branch = New-FeatureBranch -Number $IssueNumber -Title $meta.title
    }

    if (-not $Force) {
        $existingPR = gh pr list --head $branch --json number,url --limit 1 | ConvertFrom-Json
        if ($existingPR.Count -gt 0) {
            Write-Log "  PR #$($existingPR[0].number) already exists — skipping implement." -Color DarkGray
            return $existingPR[0].url
        }
    }

    Write-Log "▶ Implement — issue #$IssueNumber on $branch" -Color Cyan

    try {
        Invoke-Refine        -Number $IssueNumber
        Invoke-Architecture  -IssueNumber $IssueNumber
        Invoke-Develop       -Number $IssueNumber -Branch $branch
        $prUrl = Invoke-CommitAndPR -Number $IssueNumber -Title $meta.title -Branch $branch

        if ($null -eq $prUrl) {
            # Invoke-CommitAndPR returned the no-diff sentinel — branch has no commits
            # ahead of the default branch. Skip the PR/review/merge stages; the caller
            # (Invoke-Orchestration) will mark this as merged and close the issue.
            Write-Log "✅ Implement complete — issue already satisfied; no PR needed." -Color Green
            return $null
        }

        Write-Log "✅ Implement complete — PR at $prUrl" -Color Green
        return $prUrl
    } catch {
        Add-Comment -Number $IssueNumber -Body "🤖❌ Implement Failed`n``````text`n$_`n``````"
        throw
    }
}
