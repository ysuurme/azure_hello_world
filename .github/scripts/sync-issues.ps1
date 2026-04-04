param(
    [switch]$DryRun,
    [string]$ProjectName = "@hello_architect"
)

$IssuesFile = "$PSScriptRoot\..\..\ISSUES.md"

Write-Host "🚀 Starting GitHub Issue Sync using PowerShell..." -ForegroundColor Cyan

if (-not (Test-Path $IssuesFile)) {
    Write-Error "ISSUES.md not found at path: $IssuesFile"
    exit 1
}

$Lines = Get-Content $IssuesFile -Raw

# This regex accurately isolates our ISSUE block constraints
$Matches = [regex]::Matches($Lines, "(?s)ISSUE:\s*(.*?)\r?\n(.*?)\r?\nEND_ISSUE")

$IssuesCreated = 0

foreach ($Match in $Matches) {
    $Title = $Match.Groups[1].Value.Trim()
    $BodyText = $Match.Groups[2].Value.Trim()

    if ($DryRun) {
        Write-Host "DRY RUN: Would create issue '$Title'" -ForegroundColor Yellow
        continue
    }

    Write-Host "📦 Creating issue: $Title"
    
    # Safe multiline body parsing via temporary file injection protecting escaping logic.
    $TempFile = New-TemporaryFile
    $BodyText | Out-File -FilePath $TempFile.FullName -Encoding UTF8

    try {
        # Using `--body-file` completely bypasses inline shell string limits
        $Url = gh issue create --title $Title --body-file $TempFile.FullName --project $ProjectName 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ Created at: $Url" -ForegroundColor Green
            $IssuesCreated++
            
            # Re-read and dynamically delete the created issue to prevent duplication
            $CurrentLines = Get-Content $IssuesFile
            $UpdatedLines = @()
            $InsideSpecificIssue = $false
            
            foreach ($Line in $CurrentLines) {
                if ($Line -match "^ISSUE:\s*$([regex]::Escape($Title))$") {
                    $InsideSpecificIssue = $true
                } elseif ($Line -match "^END_ISSUE" -and $InsideSpecificIssue) {
                    $InsideSpecificIssue = $false
                } elseif (-not $InsideSpecificIssue) {
                    $UpdatedLines += $Line
                }
            }
            # Overwrite ISSUES.md
            $UpdatedLines | Set-Content $IssuesFile -Encoding UTF8
        } else {
            Write-Host "  🚫 Failed to create issue: $Title" -ForegroundColor Red
            Write-Host $Url -ForegroundColor Red
        }
    }
    finally {
        Remove-Item $TempFile.FullName -ErrorAction SilentlyContinue
    }
}

if ($DryRun) {
    Write-Host "🎉 Dry Run complete. Checked $($Matches.Count) pending issues safely." -ForegroundColor Magenta
} else {
    Write-Host "🎉 Integration sync complete! $IssuesCreated new issues tracked into ISSUES.md." -ForegroundColor Green
}
