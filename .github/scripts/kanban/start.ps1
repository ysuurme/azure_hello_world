#Requires -Version 7.0
<#
.SYNOPSIS
    HITL orchestration — pick a Backlog issue and run the full orchestration in this terminal.

.DESCRIPTION
    Presents an interactive picker of Backlog issues (or accepts -Issue N directly).
    Adds the HITL label so GHA cannot claim the issue while the terminal is working.
    Runs implement → review loop → merge directly in this session.
    Removes HITL on completion or error.

    agent:backlog is never set — no GHA trigger fires.

.PARAMETER Issue
    Issue number to start directly, skipping the interactive picker.

.PARAMETER MaxRetries
    Maximum implement→review cycles before marking agent:failed. Default: 3.

.EXAMPLE
    task start              # interactive picker
    task start ISSUE=13     # run orchestration for issue #13 directly
#>
param(
    [int]$Issue      = 0,
    [int]$MaxRetries = -1
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

if ($MaxRetries -lt 0) { $MaxRetries = $KanbanMaxRetries }

# ── Fetch Backlog items for this repo ─────────────────────────────────────────

$_owner = Get-ResolvedOwner
if (-not $_owner) {
    Write-Log "Cannot reach GitHub Project — check KANBAN_PROJECT_OWNER in .env. Run: task setup" -Color Red
    exit 1
}
$items = gh project item-list $KanbanProjectNumber `
    --owner $_owner --format json --limit 200 |
    ConvertFrom-Json |
    Select-Object -ExpandProperty items |
    Where-Object {
        $_.status -eq 'Backlog' -and
        $_.content.type -eq 'Issue' -and
        $_.content.repository -eq $KanbanRepo
    }

if (-not $items -or $items.Count -eq 0) {
    Write-Log "No Backlog issues found in project for $KanbanRepo." -Color Yellow
    exit 0
}

# ── Resolve target issue ──────────────────────────────────────────────────────

if ($Issue -gt 0) {
    $selected = $items | Where-Object { $_.content.number -eq $Issue } | Select-Object -First 1
    if (-not $selected) { throw "Issue #$Issue not found in Backlog for this repo." }
} else {
    Write-Host ""
    Write-Host "  Backlog — $KanbanRepo" -ForegroundColor Cyan
    Write-Host "  $('─' * 60)" -ForegroundColor DarkGray
    $i = 1
    foreach ($item in $items) {
        Write-Host ("  {0,2}. #{1,-4} {2}" -f $i, $item.content.number, $item.content.title) -ForegroundColor White
        $i++
    }
    Write-Host ""
    $raw = Read-Host "  Pick a number (1-$($items.Count))"
    $idx = [int]$raw - 1
    if ($idx -lt 0 -or $idx -ge $items.Count) { throw "Invalid selection." }
    $selected = $items[$idx]
}

$num = $selected.content.number
$url = $selected.content.url

Write-Host ""
Write-Host "  Issue   : $url" -ForegroundColor Cyan
Write-Host "  Mode    : HITL — running in terminal, GHA suppressed" -ForegroundColor Green
Write-Host ""

# ── Guard with HITL, then run the full orchestration ─────────────────────────

gh issue edit $num --repo $KanbanRepo --add-label 'HITL' 2>&1 | Out-Null
Write-Log "  HITL label added to #$num — GHA will not pick this up." -Color DarkGray

try {
    & "$PSScriptRoot\run.ps1" -Issue $num -MaxRetries $MaxRetries
} finally {
    gh issue edit $num --repo $KanbanRepo --remove-label 'HITL' 2>&1 | Out-Null
    Write-Log "  HITL label removed from #$num." -Color DarkGray
}
