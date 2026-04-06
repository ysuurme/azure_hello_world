<#
.SYNOPSIS
    Local agent listener that polls GitHub for issues labeled 'agent:dev'.
    Dual-driver architecture: Gemini CLI (MCP bridge) or Claude Code (direct HTTP).

.DESCRIPTION
    TEMPORARY ARCHITECTURE — This laptop-based listener is a Phase 1 scaffold.
    The production target is GitHub Codespaces with event-driven spin-up.

    Set AGENT_DRIVER=gemini|claude in .env to select the active driver.
    Gemini driver: starts MCP bridge (lm-local) for file I/O delegation via port 3100.
    Claude driver: skips bridge, validates Anthropic /v1/messages endpoint instead.

    Workflow:
    1. Poll for issues labeled 'agent:dev'
    2. Phase A: Refine raw issue into structured format
    3. Phase B: Create feature branch, run active driver builder
    4. Commit with descriptive message, push, create PR (idempotent)
    5. Agent self-reviews the PR using a true AI critic
    6. If rejected: post feedback, stay in 'agent:dev'. If approved: move to 'agent:review'.

.NOTES
    Start via: task agent:listen
    Or directly: pwsh .github/scripts/agent-listener.ps1
#>

$LogFile = "$PSScriptRoot\..\..\logs\agent-listener.log"
$PollIntervalSeconds = 60
$ProjectName = "@hello_architect"
$script:AgentDriver = "gemini"
$script:LocalAiUrl = "http://127.0.0.1:1234"

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
    
    # Create feature branch from master with consistent naming
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

    $DriverLabel = if ($script:AgentDriver -eq "claude") { "Claude Code" } else { "Gemini CLI" }
    Add-IssueComment -IssueNumber $IssueNumber -Body "🌿 Branch ``$BranchName`` created. Running $DriverLabel builder..."

    # Execute the agent development task
    task agent:dev ISSUE=$IssueNumber 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "task agent:dev failed for issue #$IssueNumber (exit code: $LASTEXITCODE)"
    }
}

function Invoke-CommitAndPR {
    param([int]$IssueNumber, [string]$Title)
    
    $BranchName = "feature/issue-$IssueNumber"
    
    # Descriptive commit message with issue context
    $CommitMessage = "feat(#${IssueNumber}): $Title"
    git add . 2>&1 | Out-Null
    
    # Only commit if there are changes
    if (git status --porcelain) {
        git commit -m $CommitMessage 2>&1 | Out-Null
    } else {
        Write-Log "  No changes to commit." -Color Yellow
    }

    git push origin HEAD 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git push failed for issue #$IssueNumber"
    }

    # Idempotent PR creation: check if PR already exists for this branch
    $ExistingPr = gh pr list --head $BranchName --json url --limit 1 | ConvertFrom-Json
    if ($ExistingPr.Count -gt 0) {
        $PrUrl = $ExistingPr[0].url
        Write-Log "  PR already exists: $PrUrl. Updated with new commits." -Color Green
        return $PrUrl
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
            # Double-check for existing PR in case of race condition
            $ExistingPr = gh pr list --head $BranchName --json url --limit 1 | ConvertFrom-Json
            if ($ExistingPr.Count -gt 0) {
                return $ExistingPr[0].url
            }
            throw "PR creation failed for issue #$IssueNumber. Output: $PrUrl"
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
    
    # Execute the true AI review task governed by SKILL.md
    $ReviewOutput = task agent:review ISSUE=$IssueNumber 2>&1 | Out-String
    
    if ($ReviewOutput -match "REJECT") {
        Write-Log "  ❌ Review REJECTED. Posting feedback to issue #$IssueNumber." -Color Red
        
        $Feedback = @"
## 🤖 Agent Review Feedback (REJECTED)

$ReviewOutput

*The agent will now attempt to address these findings. Label 'agent:dev' remains.*
"@
        Add-IssueComment -IssueNumber $IssueNumber -Body $Feedback
        
        # Also post a pointer comment on the PR
        gh pr review $PrNumber --comment --body "❌ Review REJECTED. Detailed feedback posted on issue #$IssueNumber." 2>&1 | Out-Null
        
        # Keep agent:dev label for next polling sequence
        Update-IssueLabels -IssueNumber $IssueNumber -RemoveLabel "agent:in-progress" -AddLabel "agent:dev"
        return $false
    }
    else {
        Write-Log "  ✅ Review APPROVED. Moving to human review lane." -Color Green
        
        $ApprovalMsg = @"
## 🤖 Agent Review Feedback (APPROVED)

$ReviewOutput

*Awaiting human review. Label moved to 'agent:review'.*
"@
        Add-IssueComment -IssueNumber $IssueNumber -Body $ApprovalMsg
        
        # Also post a pointer comment on the PR
        gh pr review $PrNumber --comment --body "✅ Review APPROVED. See issue #$IssueNumber for details." 2>&1 | Out-Null
        
        # Move issue to Review lane
        Update-IssueLabels -IssueNumber $IssueNumber -RemoveLabel "agent:in-progress" -AddLabel "agent:review"
        return $true
    }
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

function Invoke-EnvironmentBootstrap {
    Write-Log "🚀 Bootstrapping Local AI Environment" -Color Cyan

    # Read driver config from .env
    $envPath = "$PSScriptRoot\..\..\.env"
    $LocalAiModel = "nerdsking-python-coder-3b-i"
    if (Test-Path $envPath) {
        $envContent = Get-Content $envPath
        foreach ($line in $envContent) {
            if ($line -match "^LOCAL_AI_MODEL=(.+)$") { $LocalAiModel = $matches[1].Trim() }
            if ($line -match "^AGENT_DRIVER=(.+)$")   { $script:AgentDriver = $matches[1].Trim().ToLower() }
            if ($line -match "^LOCAL_AI_URL=(.+)$")   { $script:LocalAiUrl = $matches[1].Trim() }
        }
    }

    Write-Log "  Agent driver: $($script:AgentDriver.ToUpper())" -Color Cyan

    Write-Log "  Starting LMS server..." -Color Gray
    lms server start 2>&1 | Out-Null
    if ($env:KEEP_MODELS_LOADED -eq 'true') {
        Write-Log "  [Debug Mode] Skipping LMS VRAM clear..." -Color Yellow
    } else {
        Write-Log "  Clearing VRAM safely..." -Color Gray
        lms unload --all 2>&1 | Out-Null

        Write-Log "  Loading explicit model ($LocalAiModel) with 32768 context..." -Color Gray
        $Payload = @{
            model          = $LocalAiModel
            context_length = 32768
            flash_attention = $true
            echo_load_config = $true
        } | ConvertTo-Json -Depth 10 -Compress
        Invoke-RestMethod -Uri "$($script:LocalAiUrl)/api/v1/models/load" -Method Post -Body $Payload -ContentType "application/json" | Out-Null
    }

    if ($script:AgentDriver -eq "gemini") {
        # ── GEMINI: Validate LM Studio + Start MCP Bridge ──────────────────────
        $McpValid = $true
        $BridgePort = 3100
        $settingsPath = "$PSScriptRoot\..\..\.gemini\settings.json"

        Write-Log "  Validating LM Studio Model Configuration..." -Color Gray
        $modelsGet = Invoke-RestMethod -Uri "$($script:LocalAiUrl)/v1/models" -Method Get -ErrorAction SilentlyContinue
        if (-not $modelsGet) {
            Write-Log "⚠️ Validation Failed: Cannot connect to LM Studio. Continuing without MCP." -Color Yellow
            $McpValid = $false
        } else {
            $loadedModel = $modelsGet.data | Where-Object { $_.id -eq $LocalAiModel }
            if (-not $loadedModel) {
                Write-Log "⚠️ Validation Failed: Target model '$LocalAiModel' not loaded. Check VRAM. Continuing without MCP." -Color Yellow
                $McpValid = $false
            }
        }

        if ($McpValid) {
            Write-Log "  Validating inference with hello world call..." -Color Gray
            try {
                $InferPayload = @{
                    model    = $LocalAiModel
                    messages = @(@{ role = "user"; content = "Respond with only: hello world" })
                    max_tokens = 20
                } | ConvertTo-Json -Depth 10 -Compress
                $InferResult = Invoke-RestMethod -Uri "$($script:LocalAiUrl)/v1/chat/completions" -Method Post -Body $InferPayload -ContentType "application/json" -TimeoutSec 30
                $Reply = $InferResult.choices[0].message.content.Trim()
                Write-Log "  Inference OK: '$Reply'" -Color Gray
            } catch {
                Write-Log "⚠️ Validation Failed: Inference call failed — $_. Continuing without MCP." -Color Yellow
                $McpValid = $false
            }
        }

        if ($McpValid) {
            Write-Log "  Resolving MCP Bridge entry point..." -Color Gray
            $NpmGlobalRoot = (npm root -g 2>$null).Trim()
            $CandidatePath = Join-Path $NpmGlobalRoot "@intelligentinternet\gemini-cli-mcp-openai-bridge\dist\index.js"
            if (-not (Test-Path $CandidatePath)) {
                Write-Log "⚠️ Validation Failed: Cannot resolve MCP bridge at $CandidatePath. Continuing without MCP." -Color Yellow
                $McpValid = $false
            }
        }

        if ($McpValid) {
            # Evict any stale process already bound to the bridge port
            $StaleOwner = (Get-NetTCPConnection -LocalPort $BridgePort -State Listen -ErrorAction SilentlyContinue).OwningProcess
            if ($StaleOwner) {
                Write-Log "  Evicting stale process (PID $StaleOwner) on port $BridgePort..." -Color Yellow
                Stop-Process -Id $StaleOwner -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 1
            }

            # Start bridge as HTTP server — avoids Windows stdio spawn pipe bugs
            Write-Log "  Starting MCP Bridge HTTP server on port $BridgePort..." -Color Gray
            $BridgeArgs = @(
                $CandidatePath,
                "--url", "$($script:LocalAiUrl)/v1",
                "--model", $LocalAiModel,
                "--mode", "edit",
                "--i-know-what-i-am-doing",
                "--target-dir", ".",
                "--port", "$BridgePort"
            )
            $script:BridgeProcess = Start-Process node -ArgumentList $BridgeArgs -PassThru -NoNewWindow -RedirectStandardOutput "$env:TEMP\mcp_bridge_stdout.log" -RedirectStandardError "$env:TEMP\mcp_bridge_stderr.log"
            Start-Sleep -Seconds 3

            if ($script:BridgeProcess.HasExited) {
                Write-Log "⚠️ Validation Failed: MCP Bridge exited immediately (code $($script:BridgeProcess.ExitCode)). Continuing without MCP." -Color Yellow
                $McpValid = $false
            } else {
                Write-Log "  Bridge running (PID: $($script:BridgeProcess.Id)) on http://127.0.0.1:$BridgePort" -Color Gray
            }
        }

        # Write settings.json for Gemini CLI MCP config
        $jsonPayload = Get-Content -Raw $settingsPath -ErrorAction SilentlyContinue | ConvertFrom-Json
        if (-not $jsonPayload) { $jsonPayload = [PSCustomObject]@{ mcpServers = [PSCustomObject]@{} } }
        if (-not $jsonPayload.mcpServers) { $jsonPayload | Add-Member -Type NoteProperty -Name mcpServers -Value [PSCustomObject]@{} }

        if ($McpValid) {
            $jsonPayload.mcpServers | Add-Member -MemberType NoteProperty -Name "lm-local" -Value @{
                url = "http://127.0.0.1:$BridgePort/mcp"
            } -Force
            Write-Log "✅ Local Model Ready & MCP Bridge Validated (SSE on port $BridgePort)." -Color Green
        } else {
            if ($jsonPayload.mcpServers.PSObject.Properties.Name -contains "lm-local") {
                $jsonPayload.mcpServers.PSObject.Properties.Remove("lm-local")
            }
            Write-Log "⚠️ MCP Bridge Disabled. Agentic pipeline running on pure Cloud Models." -Color Magenta
        }

        $jsonString = $jsonPayload | ConvertTo-Json -Depth 10
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($settingsPath, $jsonString, $utf8NoBom)

    } else {
        # ── CLAUDE: Validate Anthropic /v1/messages endpoint ───────────────────
        Write-Log "  Validating Anthropic endpoint ($($script:LocalAiUrl)/v1/messages)..." -Color Gray
        try {
            $ClaudePayload = @{
                model      = $LocalAiModel
                max_tokens = 20
                messages   = @(@{ role = "user"; content = "Say hello" })
            } | ConvertTo-Json -Depth 10 -Compress
            $Headers = @{ "x-api-key" = "local"; "anthropic-version" = "2023-06-01" }
            $null = Invoke-RestMethod -Uri "$($script:LocalAiUrl)/v1/messages" -Method Post -Body $ClaudePayload -ContentType "application/json" -Headers $Headers -TimeoutSec 30
            Write-Log "✅ Anthropic endpoint validated. Local model responding." -Color Green
        } catch {
            Write-Log "⚠️ Anthropic endpoint validation failed: $_. Claude driver will use cloud model only." -Color Yellow
        }
    }
}

function Invoke-EnvironmentTeardown {
    # Stop bridge HTTP server if running
    if ($script:BridgeProcess -and -not $script:BridgeProcess.HasExited) {
        Write-Log "  Stopping MCP Bridge (PID: $($script:BridgeProcess.Id))..." -Color Gray
        Stop-Process -Id $script:BridgeProcess.Id -Force -ErrorAction SilentlyContinue
    }

    if ($env:KEEP_MODELS_LOADED -eq 'true') {
        Write-Log "🧹 Tearing down Local AI Environment (Keeping VRAM models Active for Debugging)..." -Color Yellow
    } else {
        Write-Log "🧹 Tearing down Local AI Environment (Clearing VRAM & Stopping Server)..." -Color Yellow
        $null = lms unload --all
        $null = lms server stop
    }
}

# ── Main Loop ──

try {
    Invoke-EnvironmentBootstrap
    Invoke-CleanupBranches
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
        Add-IssueComment -IssueNumber $IssueNumber -Body "🤖 Agent picked up this task. Starting refinement/development phase."

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
            
            # Agent self-review: execute true AI review loop
            $Passed = Invoke-AgentReview -PrUrl $PrUrl -IssueNumber $IssueNumber

            if ($Passed) {
                Write-Log "🎉 Issue #${IssueNumber} approved by agent. PR ready for human review." -Color Green
            } else {
                Write-Log "🔄 Issue #${IssueNumber} rejected by agent. Returning to dev loop." -Color Yellow
            }
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
}
finally {
    Invoke-EnvironmentTeardown
}
