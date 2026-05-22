#Requires -Version 7.0
<#
.SYNOPSIS
    Bootstrap — discover GitHub Project field/option IDs and write to .env + GitHub Actions variables.

.DESCRIPTION
    Reads KANBAN_PROJECT_NUMBER and KANBAN_PROJECT_OWNER from .env, queries the
    GitHub Project for the Status field and all its option IDs, then:
      1. Writes the discovered IDs back to .env for local use.
      2. Sets matching GitHub Actions repository variables for kanban-lanes.yml and orchestrator.yml.

    Run once after creating the GitHub Project and setting KANBAN_PROJECT_NUMBER
    and KANBAN_PROJECT_OWNER in .env.

.EXAMPLE
    task setup
#>

$ErrorActionPreference = 'Stop'

$_Root    = "$PSScriptRoot\..\.."
$_EnvPath = "$_Root\.env"

# ── Load .env ─────────────────────────────────────────────────────────────────

if (-not (Test-Path $_EnvPath)) {
    Write-Error ".env not found at $_EnvPath"
    exit 1
}

foreach ($line in (Get-Content $_EnvPath)) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$' -and $line -notmatch '^\s*#') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim('"').Trim("'"), 'Process')
    }
}

$ProjectNumber = if ($env:KANBAN_PROJECT_NUMBER) { [int]$env:KANBAN_PROJECT_NUMBER } else { 0 }
$ProjectOwner  = if ($env:KANBAN_PROJECT_OWNER)  { $env:KANBAN_PROJECT_OWNER }       else { '' }

if ($ProjectNumber -eq 0) {
    Write-Error "KANBAN_PROJECT_NUMBER is not set in .env. Add it and re-run task setup."
    exit 1
}
if (-not $ProjectOwner) {
    Write-Error "KANBAN_PROJECT_OWNER is not set in .env. Add it and re-run task setup."
    exit 1
}

# ── Scope check ───────────────────────────────────────────────────────────────
# Warn when the active gh auth context is missing any of the required PAT scopes.
# Required scopes match README.md and SECURITY.md: project, read:org, repo, user, workflow.
# NOTE: local gh auth scopes do NOT verify the GH_TOKEN repo secret — they are
# independent tokens. The warning below is a reminder to verify the secret, not
# a guarantee.
Write-Host ""
Write-Host "🔐 Checking gh auth token scopes..." -ForegroundColor Cyan
$_authStatusOut = gh auth status --show-token 2>&1 | Out-String

$_requiredScopes = @('project', 'read:org', 'repo', 'user', 'workflow')
$_presentScopes  = @()
if ($_authStatusOut -match 'Token scopes:\s*(.+)') {
    $_presentScopes = [regex]::Matches($Matches[1], "'([^']+)'") | ForEach-Object { $_.Groups[1].Value }
}
$_missingScopes = @($_requiredScopes | Where-Object { $_ -notin $_presentScopes })

if ($_missingScopes.Count -eq 0) {
    Write-Host "  ✅ All required PAT scopes detected: $($_requiredScopes -join ', ')" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  WARNING: missing PAT scopes in active gh auth context: $($_missingScopes -join ', ')" -ForegroundColor Yellow
    Write-Host "  ⚠️  Required (classic PAT): $($_requiredScopes -join ', ')" -ForegroundColor Yellow
    Write-Host "  ⚠️  The GH_TOKEN repo secret must be a classic PAT with ALL the above scopes." -ForegroundColor Yellow
    Write-Host "  ⚠️  Local gh auth scopes do NOT verify the GH_TOKEN secret — check the PAT settings page directly." -ForegroundColor Yellow
    Write-Host "  ⚠️  Fine-grained PATs do not support Projects v2 — use a classic PAT." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🔍 Querying project #$ProjectNumber (owner: $ProjectOwner)..." -ForegroundColor Cyan

# ── Fetch field list ──────────────────────────────────────────────────────────

$fieldsJson = gh project field-list $ProjectNumber --owner $ProjectOwner --format json 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to list project fields: $fieldsJson"
    exit 1
}

$fields      = ($fieldsJson | ConvertFrom-Json).fields
$statusField = $fields | Where-Object { $_.type -eq 'ProjectV2SingleSelectField' -and $_.name -match 'status|state' } | Select-Object -First 1

if (-not $statusField) {
    $statusField = $fields | Where-Object { $_.type -eq 'ProjectV2SingleSelectField' } | Select-Object -First 1
}
if (-not $statusField) {
    Write-Error "No SINGLE_SELECT field found in project #$ProjectNumber. Add a Status field to the project first."
    exit 1
}

Write-Host "  Found field: '$($statusField.name)' (ID: $($statusField.id))" -ForegroundColor Green
$options = $statusField.options

Write-Host ""
Write-Host "  Options:" -ForegroundColor Cyan
$options | ForEach-Object { Write-Host ("    [{0}] {1}" -f $_.id, $_.name) -ForegroundColor White }

# ── Resolve project node ID ───────────────────────────────────────────────────
Write-Host ""
Write-Host "  Resolving project node ID (KANBAN_PROJECT_ID)..." -ForegroundColor Cyan
$_projectListJson = gh project list --owner $ProjectOwner --format json 2>&1 | Out-String
$ProjectNodeId = $null
if ($LASTEXITCODE -eq 0) {
    try {
        $ProjectNodeId = ($_projectListJson | ConvertFrom-Json).projects |
            Where-Object { $_.number -eq $ProjectNumber } |
            Select-Object -ExpandProperty id -First 1
    } catch {}
}
if ($ProjectNodeId) {
    Write-Host "  KANBAN_PROJECT_ID: $ProjectNodeId" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Could not resolve project node ID for #$ProjectNumber — KANBAN_PROJECT_ID will not be set." -ForegroundColor Yellow
}

$estimateField = $fields | Where-Object { $_.name -match '^estimate$' } | Select-Object -First 1
$priorityField = $fields | Where-Object { $_.type -eq 'ProjectV2SingleSelectField' -and $_.name -match '^priority$' } | Select-Object -First 1

# ── Auto-provision missing custom fields ──────────────────────────────────────

$_needsRefetch = $false

if (-not $estimateField) {
    Write-Host "  'Estimate' field not found — creating Number field..." -ForegroundColor Yellow
    $createOut = gh project field-create $ProjectNumber --owner $ProjectOwner --name "Estimate" --data-type NUMBER 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️  Could not create 'Estimate' field: $($createOut.Trim())" -ForegroundColor Yellow
    } else {
        Write-Host "  ✅ Created 'Estimate' Number field." -ForegroundColor Green
        $_needsRefetch = $true
    }
}

if (-not $priorityField) {
    Write-Host "  'Priority' field not found — creating Single Select field with P0,P1,P2,P3,P4..." -ForegroundColor Yellow
    $createOut = gh project field-create $ProjectNumber --owner $ProjectOwner --name "Priority" --data-type SINGLE_SELECT --single-select-options "P0,P1,P2,P3,P4" 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️  Could not create 'Priority' field: $($createOut.Trim())" -ForegroundColor Yellow
    } else {
        Write-Host "  ✅ Created 'Priority' Single Select field with options P0,P1,P2,P3,P4." -ForegroundColor Green
        $_needsRefetch = $true
    }
}

if ($_needsRefetch) {
    Write-Host "  Re-fetching field list after provisioning..." -ForegroundColor Cyan
    $fieldsJson = gh project field-list $ProjectNumber --owner $ProjectOwner --format json 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) {
        $fields        = ($fieldsJson | ConvertFrom-Json).fields
        $estimateField = $fields | Where-Object { $_.name -match '^estimate$' } | Select-Object -First 1
        $priorityField = $fields | Where-Object { $_.type -eq 'ProjectV2SingleSelectField' -and $_.name -match '^priority$' } | Select-Object -First 1
    }
}

if ($estimateField) {
    Write-Host "  Found field: '$($estimateField.name)' (ID: $($estimateField.id))" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  No 'Estimate' field found — Estimate sync will be skipped." -ForegroundColor Yellow
}
if ($priorityField) {
    Write-Host "  Found field: '$($priorityField.name)' (ID: $($priorityField.id))" -ForegroundColor Green
    Write-Host "  Priority options:" -ForegroundColor Cyan
    $priorityField.options | ForEach-Object { Write-Host ("    [{0}] {1}" -f $_.id, $_.name) -ForegroundColor White }
} else {
    Write-Host "  ⚠️  No 'Priority' field found — Priority sync will be skipped." -ForegroundColor Yellow
}

# ── Auto-detect lane options ──────────────────────────────────────────────────

function Find-Option([string[]]$Patterns) {
    foreach ($p in $Patterns) {
        $match = $options | Where-Object { $_.name -match $p } | Select-Object -First 1
        if ($match) { return $match }
    }
    return $null
}

$laneBacklog      = Find-Option @('backlog', 'todo', 'to.do', 'new')
$laneImplementing = Find-Option @('implement', 'progress', 'doing', 'in.progress')
$laneReview       = Find-Option @('review', 'testing', 'qa')
$laneMerged       = Find-Option @('merged?', 'done', 'complete', 'closed')

# ── Interactive fallback for unmatched lanes ──────────────────────────────────

function Select-Option([string]$LaneName, $Current) {
    if ($Current) {
        Write-Host "  Auto-detected '$LaneName' → '$($Current.name)'" -ForegroundColor DarkGray
        return $Current
    }
    Write-Host ""
    Write-Host "  Could not auto-detect '$LaneName'. Select the matching option:" -ForegroundColor Yellow
    for ($i = 0; $i -lt $options.Count; $i++) {
        Write-Host ("    {0}. {1}" -f ($i + 1), $options[$i].name) -ForegroundColor White
    }
    $raw = Read-Host "  Pick a number (1-$($options.Count))"
    $idx = [int]$raw - 1
    if ($idx -lt 0 -or $idx -ge $options.Count) { throw "Invalid selection for '$LaneName'." }
    return $options[$idx]
}

Write-Host ""
Write-Host "  Mapping lanes..." -ForegroundColor Cyan
$laneBacklog      = Select-Option 'Backlog'      $laneBacklog
$laneImplementing = Select-Option 'Implementing' $laneImplementing
$laneReview       = Select-Option 'Review'       $laneReview
$laneMerged       = Select-Option 'Merged'       $laneMerged

# ── Write .env ────────────────────────────────────────────────────────────────

function Set-EnvVar([string]$Path, [string]$Key, [string]$Value) {
    $lines  = if (Test-Path $Path) { Get-Content $Path } else { @() }
    $found  = $false
    $result = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=") {
            "$Key=$Value"
            $found = $true
        } else {
            $line
        }
    }
    if (-not $found) { $result += "$Key=$Value" }
    $result | Out-File $Path -Encoding utf8
}

Write-Host ""
Write-Host "  Writing IDs to .env..." -ForegroundColor Cyan

Set-EnvVar $_EnvPath 'KANBAN_STATUS_FIELD_ID'  $statusField.id
Set-EnvVar $_EnvPath 'KANBAN_OPT_BACKLOG'      $laneBacklog.id
Set-EnvVar $_EnvPath 'KANBAN_OPT_IMPLEMENTING' $laneImplementing.id
Set-EnvVar $_EnvPath 'KANBAN_OPT_REVIEW'       $laneReview.id
Set-EnvVar $_EnvPath 'KANBAN_OPT_MERGED'       $laneMerged.id
if ($ProjectNodeId) { Set-EnvVar $_EnvPath 'KANBAN_PROJECT_ID' $ProjectNodeId }

if ($estimateField) { Set-EnvVar $_EnvPath 'KANBAN_ESTIMATE_FIELD_ID' $estimateField.id }
if ($priorityField) {
    Set-EnvVar $_EnvPath 'KANBAN_PRIORITY_FIELD_ID' $priorityField.id
    foreach ($opt in $priorityField.options) {
        Set-EnvVar $_EnvPath "KANBAN_PRIORITY_OPT_$($opt.name)" $opt.id
    }
}

# ── Set GitHub Actions repository variables ───────────────────────────────────

Write-Host "  Setting GitHub Actions repository variables..." -ForegroundColor Cyan

$ghVars = @{
    KANBAN_PROJECT_NUMBER   = "$ProjectNumber"
    KANBAN_PROJECT_OWNER    = $ProjectOwner
    KANBAN_STATUS_FIELD_ID  = $statusField.id
    KANBAN_OPT_BACKLOG      = $laneBacklog.id
    KANBAN_OPT_IMPLEMENTING = $laneImplementing.id
    KANBAN_OPT_REVIEW       = $laneReview.id
    KANBAN_OPT_MERGED       = $laneMerged.id
}
if ($ProjectNodeId)  { $ghVars['KANBAN_PROJECT_ID']      = $ProjectNodeId }
if ($estimateField) { $ghVars['KANBAN_ESTIMATE_FIELD_ID'] = $estimateField.id }
if ($priorityField) {
    $ghVars['KANBAN_PRIORITY_FIELD_ID'] = $priorityField.id
    foreach ($opt in $priorityField.options) { $ghVars["KANBAN_PRIORITY_OPT_$($opt.name)"] = $opt.id }
}

foreach ($kv in $ghVars.GetEnumerator()) {
    $out = gh variable set $kv.Key --body $kv.Value 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️ Could not set GH variable '$($kv.Key)': $($out.Trim())" -ForegroundColor Yellow
    } else {
        Write-Host "  ✅ $($kv.Key) = $($kv.Value)" -ForegroundColor DarkGray
    }
}

# ── Provision base labels ─────────────────────────────────────────────────────

Write-Host ""
Write-Host "🏷️  Provisioning base labels..." -ForegroundColor Cyan

$_LabelRepo = gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>&1 | Out-String
$_LabelRepo = $_LabelRepo.Trim()

if ($LASTEXITCODE -ne 0 -or -not $_LabelRepo) {
    Write-Host "  ⚠️  Could not resolve repo — skipping label provisioning." -ForegroundColor Yellow
} else {
    $BaseLabels = @(
        @{ Name = 'AFK';                Color = '0075ca'; Description = 'Agent executes start-to-finish without interruption' }
        @{ Name = 'HITL';               Color = 'e4e669'; Description = 'Requires human decision or approval before closing' }
        @{ Name = 'planning';           Color = 'c5def5'; Description = 'Planning artifact — PRD or Agent Brief' }
        @{ Name = 'enhancement';        Color = 'a2eeef'; Description = 'New feature or request' }
        @{ Name = 'bug';                Color = 'd73a4a'; Description = 'Something is not working' }
        @{ Name = 'agent:backlog';      Color = '0075ca'; Description = 'Queued in Backlog for orchestrator pickup' }
        @{ Name = 'agent:implementing'; Color = 'e4e669'; Description = 'Agent is actively implementing (refine + develop)' }
        @{ Name = 'agent:review';       Color = '969696'; Description = 'Agent self-review passed — awaiting human approval' }
        @{ Name = 'agent:merged';       Color = '0e8a16'; Description = 'Merged and closed by orchestrator' }
        @{ Name = 'agent:failed';       Color = 'd73a4a'; Description = 'Agent error — see issue comments' }
    )
    foreach ($lbl in $BaseLabels) {
        $out = gh label create $lbl.Name `
            --color $lbl.Color `
            --description $lbl.Description `
            --repo $_LabelRepo `
            --force 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ⚠️  Failed to create label '$($lbl.Name)': $($out.Trim())" -ForegroundColor Yellow
        } else {
            Write-Host "  ✅ Label '$($lbl.Name)'" -ForegroundColor DarkGray
        }
    }
}

Write-Host ""
Write-Host "✅ Setup complete. Run 'task start' to pick up backlog issues." -ForegroundColor Green
