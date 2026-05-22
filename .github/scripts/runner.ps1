#Requires -Version 7.0
<#
.SYNOPSIS
    Start or gracefully stop the self-hosted GitHub Actions runner.

.DESCRIPTION
    Default: checks if the runner is already active, then starts run.cmd.
    -Offline: sends a graceful stop signal to Runner.Listener and waits for
    it to exit (finishes any in-progress job first).
#>
param([switch]$Offline)

$RunnerCmd = 'C:\Users\Yanni\Github\actions-runner\run.cmd'

if ($Offline) {
    $proc = Get-Process -Name 'Runner.Listener' -ErrorAction SilentlyContinue
    if (-not $proc) {
        Write-Host "Runner is not running." -ForegroundColor Yellow
        exit 0
    }
    Write-Host "Sending graceful stop to Runner.Listener (PID $($proc.Id))..." -ForegroundColor Cyan
    Stop-Process -Id $proc.Id   # no -Force: sends WM_CLOSE, runner drains current job
    $proc.WaitForExit(30000) | Out-Null
    if (-not $proc.HasExited) {
        Write-Host "Runner did not exit within 30 s — force-stopping." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force
    }
    Write-Host "Runner stopped." -ForegroundColor Green
    exit 0
}

if (-not (Test-Path $RunnerCmd)) {
    Write-Host "Runner not found at $RunnerCmd" -ForegroundColor Red
    Write-Host "Re-run the runner setup at: github.com/<repo>/settings/actions/runners/new" -ForegroundColor Yellow
    exit 1
}

$proc = Get-Process -Name 'Runner.Listener' -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "Runner already active (PID $($proc.Id)) — nothing to do." -ForegroundColor Yellow
    exit 0
}

Write-Host "GitHub Actions runner starting — Ctrl+C to stop." -ForegroundColor Cyan
& cmd /c $RunnerCmd
