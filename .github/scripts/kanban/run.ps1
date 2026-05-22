#Requires -Version 7.0
<#
.SYNOPSIS
    Orchestrate the full pipeline (implement → review loop → merge) for a single issue.

.DESCRIPTION
    Called by start.ps1 (HITL) and orchestrator.yml (GHA). Not a direct Taskfile target.

    Acquires a per-issue process lock, runs the implement stage (refine + develop + PR),
    then drives the review → implement loop up to MaxRetries times. Merges on first
    approval. Marks agent:failed and posts a comment if retries are exhausted.

    Always returns to a clean, origin-synced default branch on exit.

.PARAMETER Issue
    Issue number to orchestrate. Required.

.PARAMETER MaxRetries
    Maximum implement→review cycles before marking agent:failed. Default: from config.ps1.
#>
param(
    [int]$Issue      = 0,
    [int]$MaxRetries = -1
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

if ($Issue -le 0) { throw "Issue number is required. This script is invoked with -Issue N by start.ps1 or orchestrator.yml." }
if ($MaxRetries -lt 0) { $MaxRetries = $KanbanMaxRetries }
. "$PSScriptRoot\implement.ps1"
. "$PSScriptRoot\review.ps1"
. "$PSScriptRoot\merge.ps1"

# ── Full orchestration for one issue ─────────────────────────────────────────

function Invoke-Orchestration {
    param([int]$IssueNumber, [switch]$Force)

    # Prevent two concurrent terminal instances from processing the same issue.
    if (-not (Acquire-OrchestratorLock -IssueNumber $IssueNumber)) {
        Write-Log "  ⏳ Issue #$IssueNumber is locked by another process — skipping." -Color Yellow
        return
    }

    $stashed = $false

    try {
        $meta = gh issue view $IssueNumber --repo $KanbanRepo --json title | ConvertFrom-Json
        Write-Log "━━━ Orchestrator: issue #$IssueNumber — $($meta.title)" -Color Cyan

        Set-AgentState -IssueNumber $IssueNumber -Label 'agent:implementing'

        $stashOut = git stash 2>&1
        $stashed  = $stashOut -notmatch 'No local changes'

        $implementResult = Invoke-Implement -IssueNumber $IssueNumber -Force:$Force

        if ($null -eq $implementResult) {
            # Implement signalled "already satisfied" — branch has no commits ahead of
            # the default branch (typical for tracker/coordinator issues whose work
            # was delivered by previously-merged child PRs). Mark merged, close,
            # skip the review/merge stages.
            Clear-IssueReviewCount -IssueNumber $IssueNumber
            Set-AgentState -IssueNumber $IssueNumber -Label 'agent:merged'
            gh issue close $IssueNumber --repo $KanbanRepo --reason completed 2>&1 | Out-Null
            Write-Log "🎉 Issue #$IssueNumber complete — already implemented; closed without PR." -Color Green
            return
        }

        $branch = Get-BranchName -Number $IssueNumber -Title $meta.title
        $prList = gh pr list --head $branch --json number --limit 1 | ConvertFrom-Json
        if ($prList.Count -eq 0) { throw "No PR found for branch $branch after implement stage." }
        $prNum = $prList[0].number

        # Read the CUMULATIVE review count — persists across stall recovery and GHA reruns.
        $cyclesDone = Get-IssueReviewCount -IssueNumber $IssueNumber
        $approved   = $false

        while ($cyclesDone -lt $MaxRetries) {
            Write-Log "  Review cycle $($cyclesDone + 1) / $MaxRetries" -Color DarkGray
            $approved = Invoke-Review -IssueNumber $IssueNumber -PRNumber $prNum
            $cyclesDone++
            Set-IssueReviewCount -IssueNumber $IssueNumber -Count $cyclesDone

            if ($approved) { break }

            if ($cyclesDone -lt $MaxRetries) {
                Write-Log "  Review rejected — re-running implement (cycle $($cyclesDone + 1)/$MaxRetries)..." -Color Yellow
                Invoke-Implement -IssueNumber $IssueNumber -Force | Out-Null
            }
        }

        if (-not $approved) {
            Clear-IssueReviewCount -IssueNumber $IssueNumber
            Set-AgentState -IssueNumber $IssueNumber -Label 'agent:failed'
            Add-Comment -Number $IssueNumber -Body "🤖❌ Orchestrator Error`n`nMax retries reached ($cyclesDone/$MaxRetries review cycles). Manual intervention required."
            Write-Log "⛔ Gave up after $cyclesDone cycles for issue #$IssueNumber." -Color Red
            return
        }

        Clear-IssueReviewCount -IssueNumber $IssueNumber
        Invoke-Merge -IssueNumber $IssueNumber -PRNumber $prNum
        Write-Log "🎉 Issue #$IssueNumber complete." -Color Green

    } catch {
        Clear-IssueReviewCount -IssueNumber $IssueNumber
        Set-AgentState -IssueNumber $IssueNumber -Label 'agent:failed'
        Add-Comment -Number $IssueNumber -Body "🤖❌ Orchestrator Error`n``````text`n$_`n``````"
        Write-Log "❌ Orchestrator error for issue #$IssueNumber : $_" -Color Red
    } finally {
        Release-OrchestratorLock
        if ($stashed) { git stash pop 2>&1 | Out-Null }

        # Always return to a clean, origin-synced master so the next issue starts fresh.
        $default = gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>$null
        $curr    = git rev-parse --abbrev-ref HEAD 2>$null

        if ($curr -and $curr -ne $default) {
            if (git status --porcelain 2>$null) {
                git stash push --include-untracked --quiet `
                    -m "auto: pre-master-switch from issue #$IssueNumber orchestrator" 2>$null
            }
            Write-Log "  ↩ Returning to $default (feature branch '$curr' preserved for human review)." -Color DarkGray
            git checkout --quiet $default 2>$null
        }
        git fetch --quiet origin $default 2>$null
        git reset --hard --quiet "origin/$default" 2>$null
    }
}

# ── Entry point ───────────────────────────────────────────────────────────────

Invoke-Orchestration -IssueNumber $Issue
