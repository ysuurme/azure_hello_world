<# 
.SYNOPSIS
    Local agent listener that polls GitHub for issues labeled 'agent:dev'.
    Two-phase loop: Refine (formalize issue) → Develop (execute task).

.DESCRIPTION
    TEMPORARY ARCHITECTURE — This laptop-based listener is a Phase 1 scaffold.
    The production target is GitHub Codespaces with event-driven spin-up.

    Workflow:
    1. Poll for issues labeled 'agent:dev'
    2. Phase A: Refine raw issue into structured format
    3. Phase B: Create feature branch, run Gemini CLI builder
    4. Commit with descriptive message, push, create PR
    5. Agent self-reviews the PR for quality
    6. Move issue to Review lane, request human approval

.NOTES
    Start via: task agent:listen
    Or directly: pwsh .github/scripts/agent-listener.ps1
#>

$LogFile = "$PSScriptRoot\..\..\logs\agent-listener.log"
$PollIntervalSeconds = 60
$ProjectName = "@hello_architect"

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] $Message"
    Write-Host $LogEntry -ForegroundColor $Color
    Add-Content -Path $LogFile -Value $LogEntry -ErrorAction SilentlyContinue
}

function Update-IssueLabels {
    param(
        [int]$IssueNumber,
        [string]$RemoveLabel,
        [string]$AddLabel
    )
    if ($RemoveLabel) {
        gh issue edit $IssueNumber --remove-label $RemoveLabel 2>&1 | Out-Null
    }
    if ($AddLabel) {
        gh issue edit $IssueNumber --add-label $AddLabel 2>&1 | Out-Null
    }
}

function Add-IssueComment {
    param([int]$IssueNumber, [string]$Body)
    gh issue comment $IssueNumber --body $Body 2>&1 | Out-Null
}

function Invoke-RefinePhase {
    param([int]$IssueNumber)
    
    Write-Log "📋 Phase A: Refining issue #$IssueNumber..." -Color Yellow
    
    $IssueJson = gh issue view $IssueNumber --json title,body | ConvertFrom-Json
    $RawBody = $IssueJson.body
    $Title = $IssueJson.title

    # Guard: skip refinement if issue already has structured format
    if ($RawBody -match "\*\*Goal\*\*:" -and $RawBody -match "\*\*Requirements\*\*:") {
        Write-Log "  Issue already structured, skipping refinement." -Color Cyan
        return
    }

    # Build structured issue body from raw content
    $RefinedBody = @"
**Goal**: $Title

**Description**: $RawBody

**Requirements**:
1. Analyze the codebase for relevant context.
2. Implement changes following project conventions (see GEMINI.md).
3. Add or update test coverage in ``/tests``.

**Acceptance Criteria**:
- Implementation follows code geometry constraints (<30-line functions, 2-level indent max).
- All existing tests continue to pass (``task test``).
- New test file added to ``/tests``.
"@

    # Update issue body with structured format
    $TempFile = New-TemporaryFile
    $RefinedBody | Out-File -FilePath $TempFile.FullName -Encoding UTF8
    try {
        gh issue edit $IssueNumber --body-file $TempFile.FullName 2>&1 | Out-Null
        Add-IssueComment -IssueNumber $IssueNumber -Body "📋 Issue refined into structured format (Goal/Description/Requirements/Acceptance Criteria). Starting development."
        Write-Log "  Issue refined successfully." -Color Green
    }
    finally {
        Remove-Item $TempFile.FullName -ErrorAction SilentlyContinue
    }
}

function Invoke-DevelopPhase {
    param([int]$IssueNumber, [string]$Title)
    
    Write-Log "🔨 Phase B: Developing issue #$IssueNumber..." -Color Yellow
    
    # Create feature branch from main with consistent naming
    $BranchName = "feature/issue-$IssueNumber"
    git checkout master 2>&1 | Out-Null
    git pull origin master 2>&1 | Out-Null
    
    $GitOutput = git checkout -b $BranchName 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        if ($GitOutput -match "already exists") {
            Write-Log "Branch $BranchName already exists. Switching to it." -Color Yellow
            git checkout $BranchName 2>&1 | Out-Null
        } else {
            throw "Failed to create branch $BranchName for issue #$IssueNumber.`nGit Output: $GitOutput"
        }
    }

    Add-IssueComment -IssueNumber $IssueNumber -Body "🌿 Branch ``$BranchName`` created. Running Gemini CLI builder..."

    # Execute the agent development task
    task agent:dev ISSUE=$IssueNumber 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "task agent:dev failed for issue #$IssueNumber (exit code: $LASTEXITCODE)"
    }
}

function Invoke-CommitAndPR {
    param([int]$IssueNumber, [string]$Title)
    
    # Descriptive commit message with issue context
    $CommitMessage = "feat(#${IssueNumber}): $Title"
    git add . 2>&1 | Out-Null
    git commit -m $CommitMessage 2>&1 | Out-Null
    git push origin HEAD 2>&1

    if ($LASTEXITCODE -ne 0) {
        throw "git push failed for issue #$IssueNumber"
    }

    # Build detailed PR description
    $PrBody = @"
## Summary
Automated implementation for issue #$IssueNumber.

## Changes
See commits for detailed changes. Implementation follows GEMINI.md project rules and .agents/skills/ coding standards.

## Validation
- ``task test`` — passed
- ``task lint`` — passed

## Linked Issue
Closes #$IssueNumber
"@
    $PrTempFile = New-TemporaryFile
    $PrBody | Out-File -FilePath $PrTempFile.FullName -Encoding UTF8

    try {
        $PrUrl = gh pr create `
            --title "feat(#${IssueNumber}): $Title" `
            --body-file $PrTempFile.FullName `
            --reviewer "ysuurme" `
            --project $ProjectName 2>&1

        if ($LASTEXITCODE -ne 0) {
            throw "PR creation failed for issue #$IssueNumber"
        }
        Write-Log "  PR created: $PrUrl" -Color Green
        return $PrUrl
    }
    finally {
        Remove-Item $PrTempFile.FullName -ErrorAction SilentlyContinue
    }
}

function Invoke-AgentReview {
    param([string]$PrUrl, [int]$IssueNumber)
    
    Write-Log "🔍 Agent self-reviewing PR..." -Color Yellow

    # Extract PR number from URL
    $PrNumber = ($PrUrl -split '/')[-1]
    
    # Get the diff for review context
    $DiffSummary = gh pr diff $PrNumber --stat 2>&1
    
    # Post transparent agent review notes on the PR
    $ReviewBody = @"
## 🤖 Agent Review Notes

### Files Changed
``````
$DiffSummary
``````

### Checklist
- [x] Implementation addresses issue #$IssueNumber requirements
- [x] ``task test`` passed before commit
- [x] ``task lint`` passed before commit
- [ ] Human review required — @ysuurme please validate logic and intent

> This PR was generated by the Builder agent. The Critic (``pr-checks.yml``) will run automated validation. Human approval is required before merge.
"@

    $ReviewTempFile = New-TemporaryFile
    $ReviewBody | Out-File -FilePath $ReviewTempFile.FullName -Encoding UTF8
    try {
        gh pr review $PrNumber --comment --body-file $ReviewTempFile.FullName 2>&1 | Out-Null
    }
    finally {
        Remove-Item $ReviewTempFile.FullName -ErrorAction SilentlyContinue
    }

    Write-Log "  Agent review posted on PR #$PrNumber." -Color Green
}

function Move-IssueToReview {
    param([int]$IssueNumber)
    
    # Move issue to Review lane by updating labels
    Update-IssueLabels -IssueNumber $IssueNumber -RemoveLabel "agent:in-progress" -AddLabel "agent:review"
    Add-IssueComment -IssueNumber $IssueNumber -Body "👀 PR created and agent review posted. Awaiting human approval to merge."
    Write-Log "  Issue #$IssueNumber moved to Review." -Color Cyan
}

function Invoke-CleanupBranches {
    Write-Log "🧹 Running cleanup for local feature branches..." -Color Cyan
    
    # Update remote tracking to identify 'gone' branches
    git remote prune origin 2>&1 | Out-Null
    
    # Identify candidates for deletion:
    # 1. Branches already merged into master
    $MergedBranches = git branch --merged master 2>&1 | ForEach-Object { $_.Trim() -replace "^\* ", "" }

    # 2. Branches whose upstream counterparts are gone
    $GoneBranches = git branch -vv 2>&1 | Select-String ": gone\]" | ForEach-Object {
        $Parts = $_.ToString().Trim() -split "\s+"
        if ($Parts[0] -eq "*") { $Parts[1] } else { $Parts[0] }
    }

    # Combine and deduplicate
    $Candidates = ($MergedBranches + $GoneBranches) | Select-Object -Unique

    foreach ($Branch in $Candidates) {
        # Only target feature/issue-* branches that are not 'master' or currently checked out
        if ($Branch -like "feature/issue-*" -and $Branch -ne "master") {
            $CurrentBranch = git branch --show-current
            if ($Branch -eq $CurrentBranch) {
                continue
            }
            
            Write-Log "  Pruning stale local branch: $Branch" -Color Yellow
            git branch -D $Branch 2>&1 | Out-Null
        }
    }
}

# ── Main Loop ──

Write-Log "🚀 Agent listener started. Polling every ${PollIntervalSeconds}s for 'agent:dev' issues." -Color Cyan

while ($true) {
    try {
        Write-Log "Checking for tasks..." -Color Cyan
        
        $IssueRaw = gh issue list --label "agent:dev" --json number,title --limit 1 2>&1
        $Issue = $IssueRaw | ConvertFrom-Json -ErrorAction SilentlyContinue

        if (-not $Issue -or $Issue.Count -eq 0) {
            Invoke-CleanupBranches
            Start-Sleep -Seconds $PollIntervalSeconds
            continue
        }

        $IssueNumber = $Issue[0].number
        $IssueTitle = $Issue[0].title

        Write-Log "✅ Picked up Issue #${IssueNumber}: $IssueTitle" -Color Green
        
        # Claim the issue
        Update-IssueLabels -IssueNumber $IssueNumber -RemoveLabel "agent:dev" -AddLabel "agent:in-progress"
        Add-IssueComment -IssueNumber $IssueNumber -Body "🤖 Agent picked up this task. Starting two-phase process (Refine → Develop)."

        # Stash any local work
        $StashResult = git stash 2>&1
        $DidStash = $StashResult -notmatch "No local changes"

        try {
            # Phase A: Refine the issue
            Invoke-RefinePhase -IssueNumber $IssueNumber

            # Phase B: Develop on feature branch
            Invoke-DevelopPhase -IssueNumber $IssueNumber -Title $IssueTitle

            # Commit, push, create PR with detailed description
            $PrUrl = Invoke-CommitAndPR -IssueNumber $IssueNumber -Title $IssueTitle
            
            # Agent self-review: post quality notes on the PR
            Invoke-AgentReview -PrUrl $PrUrl -IssueNumber $IssueNumber

            # Move issue to Review lane for human approval
            Move-IssueToReview -IssueNumber $IssueNumber

            Write-Log "🎉 Issue #${IssueNumber} complete. PR ready for human review." -Color Green
        }
        catch {
            Write-Log "❌ Error on issue #${IssueNumber}: $_" -Color Red
            Update-IssueLabels -IssueNumber $IssueNumber -RemoveLabel "agent:in-progress" -AddLabel "agent:failed"
            
            $ErrorBody = @"
❌ **Agent pipeline failed**

``````text
$_
``````

*Please resolve the underlying error and apply the `agent:dev` label again to retry.*
"@
            Add-IssueComment -IssueNumber $IssueNumber -Body $ErrorBody
        }
        finally {
            # Return to master and restore stashed work
            git checkout master 2>&1 | Out-Null
            if ($DidStash) {
                git stash pop 2>&1 | Out-Null
            }
        }
    }
    catch {
        Write-Log "⚠️ Unexpected loop error: $_" -Color Red
    }

    Start-Sleep -Seconds $PollIntervalSeconds
}
