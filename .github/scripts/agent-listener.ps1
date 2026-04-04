<# 
.SYNOPSIS
    Local agent listener that polls GitHub for issues labeled 'agent:dev'.
    Two-phase loop: Refine (formalize issue) → Develop (execute task).

.DESCRIPTION
    TEMPORARY ARCHITECTURE — This laptop-based listener is a Phase 1 scaffold.
    The production target is GitHub Codespaces with event-driven spin-up.

.NOTES
    Start via: task agent:listen
    Or directly: pwsh .github/scripts/agent-listener.ps1
#>

$LogFile = "$PSScriptRoot\..\..\logs\agent-listener.log"
$PollIntervalSeconds = 60

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
    param([int]$IssueNumber)
    
    Write-Log "🔨 Phase B: Developing issue #$IssueNumber..." -Color Yellow
    
    # Create linked branch and checkout
    gh issue develop $IssueNumber --checkout 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create development branch for issue #$IssueNumber"
    }

    # Execute the agent development task
    task agent:dev ISSUE=$IssueNumber 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "task agent:dev failed for issue #$IssueNumber (exit code: $LASTEXITCODE)"
    }
}

function Invoke-CommitAndPR {
    param([int]$IssueNumber, [string]$Title)
    
    git add . 2>&1 | Out-Null
    git commit -m "Agent completed task #$IssueNumber" 2>&1 | Out-Null
    git push origin HEAD 2>&1

    if ($LASTEXITCODE -ne 0) {
        throw "git push failed for issue #$IssueNumber"
    }

    gh pr create --title "Agent: $Title" --body "Closes #$IssueNumber" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "PR creation failed for issue #$IssueNumber"
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

            # Phase B: Develop
            Invoke-DevelopPhase -IssueNumber $IssueNumber

            # Success: commit, push, PR
            Invoke-CommitAndPR -IssueNumber $IssueNumber -Title $IssueTitle
            
            Update-IssueLabels -IssueNumber $IssueNumber -RemoveLabel "agent:in-progress" -AddLabel "agent:completed"
            Add-IssueComment -IssueNumber $IssueNumber -Body "✅ Development complete. PR created for review."
            Write-Log "🎉 Issue #${IssueNumber} completed. PR created." -Color Green
        }
        catch {
            Write-Log "❌ Error on issue #${IssueNumber}: $_" -Color Red
            Update-IssueLabels -IssueNumber $IssueNumber -RemoveLabel "agent:in-progress" -AddLabel "agent:failed"
            Add-IssueComment -IssueNumber $IssueNumber -Body "❌ Agent failed: ``$_``"
        }
        finally {
            # Always restore stashed work
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
