#Requires -Version 7.0
<#
.SYNOPSIS
    Stage 3 — Agent self-review of open PR against acceptance criteria.

.DESCRIPTION
    Internal function library — dot-sourced by run.ps1. Not a direct Taskfile target.

    Retrieves the PR diff and the linked issue's acceptance criteria, asks
    Claude Code to review the implementation, and posts the verdict as a
    comment on both the PR and the issue.

    APPROVED → label agent:review; item stays in Review lane.
    REJECTED → post feedback; label agent:implementing; move item back to Implementing for re-pickup.
#>

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

function Resolve-PR {
    param([int]$IssueNumber, [int]$PRNumber)
    if ($PRNumber -gt 0) { return $PRNumber }

    $branch = git rev-parse --abbrev-ref HEAD
    $found  = gh pr list --head $branch --json number --limit 1 | ConvertFrom-Json
    if ($found.Count -gt 0) { return $found[0].number }

    if ($IssueNumber -gt 0) {
        $title       = gh issue view $IssueNumber --repo $KanbanRepo --json title --jq '.title' 2>&1
        $issueBranch = Get-BranchName -Number $IssueNumber -Title $title
        $found       = gh pr list --head $issueBranch --json number --limit 1 | ConvertFrom-Json
        if ($found.Count -gt 0) { return $found[0].number }
    }

    throw "Could not resolve PR. Pass PR=N or run from the feature branch."
}

function Invoke-Review {
    param([int]$IssueNumber = 0, [int]$PRNumber = 0)

    if ($IssueNumber -eq 0) { $IssueNumber = Get-CurrentIssueNumber }
    $PRNumber = Resolve-PR -IssueNumber $IssueNumber -PRNumber $PRNumber
    if ($IssueNumber -eq 0) {
        $prBody = gh pr view $PRNumber --json body --jq '.body' 2>&1
        if ($prBody -match '#(\d+)') { $IssueNumber = [int]$Matches[1] }
    }

    $sp          = Get-IssueEstimate -IssueNumber $IssueNumber
    $reviewModel = Get-PhaseModel -Estimate $sp -Phase 'review'
    Write-Log "▶ Review — issue #$IssueNumber / PR #$PRNumber  model=$reviewModel  SP=$sp" -Color Cyan
    Set-AgentState -IssueNumber $IssueNumber -Label 'agent:review'
    Add-Comment -Number $IssueNumber -Body "· reviewing PR #$PRNumber"

    $issue = gh issue view $IssueNumber --repo $KanbanRepo --json title,body | ConvertFrom-Json
    $diff  = gh pr diff $PRNumber 2>&1 | Out-String

    # Retrieve signal history — includes 🤖✅ Tests Passing output and any prior rejections.
    $signal = gh issue view $IssueNumber --repo $KanbanRepo --json comments `
        --jq '[.comments[] | select(.body | startswith("🤖"))] | map(.body) | join("\n---\n")' 2>&1 | Out-String
    $signalSection = if ($LASTEXITCODE -eq 0 -and $signal.Trim() -and $signal.Trim() -ne 'null') {
        "`nSIGNAL HISTORY (test results, prior implementation notes, previous rejections — use this to verify correctness):`n$($signal.Trim())"
    } else { '' }

    $prompt = @"
You are performing a strict code review for a pull request in this repository.

ISSUE TITLE: $($issue.title)

ISSUE BODY (contains Acceptance Criteria):
$($issue.body)

PR DIFF:
$diff
$signalSection

REVIEW INSTRUCTIONS:
- Verify every requirement and acceptance criterion is fully met.
- Check for bugs, regressions, missing test coverage, or style violations.
- Check that the conventions in AGENTS.md and .agents/skills/ are followed.
- The signal history includes the test run output (🤖✅ Tests Passing) — verify it confirms the requirements are tested.
- Be strict: reject if anything is incomplete, incorrect, or missing.

First line of your response MUST be exactly APPROVED or REJECTED (all caps).
Follow with your detailed reasoning.
"@

    $review   = Invoke-ClaudeStreaming -Prompt $prompt -AllowedTools 'Read,Glob,Grep' -Label 'Review' -Model $reviewModel -MaxTurns $KanbanMaxTurns_Review
    $approved = $review -match '(?im)^APPROVED'
    $verdict  = if ($approved) { 'APPROVED' } else { 'REJECTED' }

    $issueComment = if ($approved) {
        "🤖✅ Review Approved`n`n$review`n`n*Awaiting human review.*"
    } else {
        "🤖❌ Review Rejected`n`n$review`n`n*Returning to Implementing for fixes.*"
    }

    Add-Comment -Number $IssueNumber -Body $issueComment
    $prComment = if ($approved) { "🤖✅ Review Approved — see issue #${IssueNumber}." }
                 else           { "🤖❌ Review Rejected — see issue #${IssueNumber} for details." }
    gh pr review $PRNumber --comment --body $prComment 2>&1 | Out-Null

    if ($approved) {
        Write-Log "✅ Review APPROVED — PR #$PRNumber ready for human merge." -Color Green
    } else {
        Set-AgentState -IssueNumber $IssueNumber -Label 'agent:implementing'
        Write-Log "❌ Review REJECTED — issue #$IssueNumber returned to Implementing." -Color Red
    }

    return $approved
}

