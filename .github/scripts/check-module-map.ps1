#Requires -Version 7.0
<#
.SYNOPSIS
    Check that every new src/<domain>/ directory in the PR diff has a Module Map row in CONTEXT.md.

.DESCRIPTION
    Tracer for ADR-009. Detects new top-level src/<domain>/ directories added in this PR
    (present in HEAD, absent in BaseRef) and verifies CONTEXT.md contains a matching
    Module Map row. Exits 0 if all rows are present; exits 1 with a precise message
    naming the missing modules.

.PARAMETER BaseRef
    Git ref to diff against. Defaults to 'origin/master'.

.EXAMPLE
    pwsh .github/scripts/check-module-map.ps1
    pwsh .github/scripts/check-module-map.ps1 -BaseRef origin/main
#>

param(
    [string]$BaseRef = 'origin/master'
)

$ErrorActionPreference = 'Stop'

# ── Resolve repo root ──────────────────────────────────────────────────────────

$repoRoot = (git rev-parse --show-toplevel 2>&1)
if ($LASTEXITCODE -ne 0) {
    Write-Error "Not in a git repository."
    exit 1
}
$repoRoot = $repoRoot.Trim()

# ── Collect PR diff ────────────────────────────────────────────────────────────

$diffLines = @(git diff --name-only "${BaseRef}...HEAD" 2>&1)
if ($LASTEXITCODE -ne 0) {
    Write-Host "check-module-map: cannot diff against '$BaseRef' — skipping (exit 0)"
    exit 0
}

# ── Extract unique top-level src/<domain> names ───────────────────────────────

$domains = @(
    $diffLines |
        Where-Object { $_ -match '^src/([^/]+)/' } |
        ForEach-Object { $Matches[1] } |
        Sort-Object -Unique
)

if ($domains.Count -eq 0) {
    Write-Host "check-module-map: no src/<domain>/ paths in diff — pass"
    exit 0
}

# ── Filter to domains that are new (absent in BaseRef) ────────────────────────

$newDomains = @()
foreach ($domain in $domains) {
    $treeOut = @(git ls-tree $BaseRef "src/$domain" 2>&1)
    if ($LASTEXITCODE -ne 0 -or $treeOut.Count -eq 0) {
        $newDomains += $domain
    }
}

if ($newDomains.Count -eq 0) {
    Write-Host "check-module-map: no new top-level src/ domains — pass"
    exit 0
}

# ── Read CONTEXT.md ────────────────────────────────────────────────────────────

$contextPath = Join-Path $repoRoot 'CONTEXT.md'
if (-not (Test-Path $contextPath)) {
    Write-Error "CONTEXT.md not found at '$contextPath' — every new src/<domain>/ needs a Module Map row."
    exit 1
}

$contextContent = Get-Content $contextPath -Raw

# ── Check each new domain has a matching Module Map row ───────────────────────

$missing = @()
foreach ($domain in $newDomains) {
    if ($contextContent -notmatch [regex]::Escape("src/$domain/")) {
        $missing += "src/$domain/"
    }
}

if ($missing.Count -eq 0) {
    Write-Host "check-module-map: all new domains have Module Map rows — pass"
    exit 0
}

foreach ($m in $missing) {
    Write-Host "check-module-map: FAIL — missing Module Map row for: $m"
}
Write-Host "Add a row to the Module Map in CONTEXT.md for each path listed above."
exit 1
