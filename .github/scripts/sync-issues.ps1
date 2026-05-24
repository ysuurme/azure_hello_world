param(
    [switch]$DryRun,
    [string]$ProjectName = "@hello_architect",
    [string]$ProjectOwner = "ysuurme"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Strip-MetadataHeaders([string]$Body) {
    $Body = $Body -replace '(?m)^LABELS:\s*.+(\r?\n|$)', ''
    $Body = $Body -replace '(?m)^ESTIMATE:\s*\d+(\r?\n|$)', ''
    $Body = $Body -replace '(?m)^PRIORITY:\s*P[0-4](\r?\n|$)', ''
    return $Body.TrimStart()
}

# Extract a single header value from the raw body text BEFORE stripping.
# Returns $null if the header is absent. Matches at line start only so values
# embedded in prose are not picked up.
function Get-HeaderValue([string]$Body, [string]$HeaderName) {
    $pattern = '(?m)^' + [regex]::Escape($HeaderName) + ':\s*(.+?)\s*$'
    $m = [regex]::Match($Body, $pattern)
    if ($m.Success) { return $m.Groups[1].Value.Trim() }
    return $null
}

# Resolve project metadata once at script start so we don't re-query per issue.
# Returns a hashtable with ProjectId, EstimateFieldId, PriorityFieldId,
# PriorityOptions (P0..P4 → optionId).
function Resolve-ProjectMetadata([string]$ProjectName, [string]$Owner) {
    Write-Host "🔎 Resolving project metadata for '$ProjectName' (owner: $Owner)..." -ForegroundColor Cyan

    $projectsJson = gh project list --owner $Owner --format json 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to list projects: $projectsJson"
        return $null
    }
    $projects = ($projectsJson | ConvertFrom-Json).projects
    $project = $projects | Where-Object { $_.title -eq $ProjectName } | Select-Object -First 1
    if (-not $project) {
        Write-Error "Project '$ProjectName' not found for owner '$Owner'."
        return $null
    }

    $fieldsJson = gh project field-list $project.number --owner $Owner --limit 50 --format json 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to list project fields: $fieldsJson"
        return $null
    }
    $fields = ($fieldsJson | ConvertFrom-Json).fields

    $estimateField = $fields | Where-Object { $_.name -eq 'Estimate' } | Select-Object -First 1
    $priorityField = $fields | Where-Object { $_.name -eq 'Priority' } | Select-Object -First 1

    if (-not $estimateField -or -not $priorityField) {
        Write-Warning "Estimate or Priority field missing on project '$ProjectName' — field syncing will be skipped."
    }

    $priorityOptions = @{}
    if ($priorityField -and $priorityField.options) {
        foreach ($opt in $priorityField.options) {
            $priorityOptions[$opt.name] = $opt.id
        }
    }

    return @{
        ProjectNumber    = $project.number
        ProjectId        = $project.id
        EstimateFieldId  = if ($estimateField) { $estimateField.id } else { $null }
        PriorityFieldId  = if ($priorityField) { $priorityField.id } else { $null }
        PriorityOptions  = $priorityOptions
    }
}

# After issue creation, the project item ID is needed to set custom fields.
# `gh issue create --project <name>` adds the issue to the project but does
# not return the item id, so we look it up by issue number.
#
# GitHub adds the newly-created issue to the project board asynchronously, so a
# lookup fired immediately after creation usually misses it. Poll with backoff
# until the item appears (or attempts run out) before giving up.
function Get-ProjectItemId([int]$IssueNumber, [int]$ProjectNumber, [string]$Owner, [int]$MaxAttempts = 6, [int]$DelaySeconds = 2) {
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $itemsJson = gh project item-list $ProjectNumber --owner $Owner --limit 200 --format json 2>&1
        if ($LASTEXITCODE -eq 0) {
            $items = ($itemsJson | ConvertFrom-Json).items
            $item = $items | Where-Object { $_.content -and $_.content.number -eq $IssueNumber } | Select-Object -First 1
            if ($item) { return $item.id }
        }
        if ($attempt -lt $MaxAttempts) { Start-Sleep -Seconds $DelaySeconds }
    }
    return $null
}

function Set-ProjectField {
    param(
        [string]$ItemId,
        [string]$ProjectId,
        [string]$FieldId,
        [Nullable[int]]$Number,
        [string]$SingleSelectOptionId
    )
    if (-not $ItemId -or -not $ProjectId -or -not $FieldId) { return $false }
    if ($PSBoundParameters.ContainsKey('Number')) {
        $out = gh project item-edit --id $ItemId --project-id $ProjectId --field-id $FieldId --number $Number 2>&1
    } else {
        $out = gh project item-edit --id $ItemId --project-id $ProjectId --field-id $FieldId --single-select-option-id $SingleSelectOptionId 2>&1
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    ⚠️  Failed to set project field: $out" -ForegroundColor Yellow
        return $false
    }
    return $true
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

$IssuesFile = "$PSScriptRoot\..\..\ISSUES.md"

Write-Host "🚀 Starting GitHub Issue Sync using PowerShell..." -ForegroundColor Cyan

if (-not (Test-Path $IssuesFile)) {
    Write-Error "ISSUES.md not found at path: $IssuesFile"
    exit 1
}

# Resolve project metadata once. If it fails we still proceed with title+body
# creation so partial functionality is preserved, but field syncing is off.
$projectMeta = $null
if (-not $DryRun) {
    $projectMeta = Resolve-ProjectMetadata -ProjectName $ProjectName -Owner $ProjectOwner
}

$Lines = Get-Content $IssuesFile -Raw

# Strip markdown code-fenced blocks before matching so documentation examples
# (e.g. the Block Format template at the top of ISSUES.md) cannot be parsed as
# real issues. Code fences are removed from the matching surface only — the
# original file is untouched.
$MatchingSurface = [regex]::Replace($Lines, '(?s)```.*?```', '')

# This regex accurately isolates our ISSUE block constraints
$Matches = [regex]::Matches($MatchingSurface, "(?s)ISSUE:\s*(.*?)\r?\n(.*?)END_ISSUE")

$IssuesCreated = 0

foreach ($Match in $Matches) {
    $Title    = $Match.Groups[1].Value.Trim()
    $RawBody  = $Match.Groups[2].Value.Trim()

    # Extract header values BEFORE stripping them from the body. Headers may
    # appear ANYWHERE in the block (the block format documents them as
    # "before the body" but we accept them inline too).
    $LabelsRaw = Get-HeaderValue $RawBody 'LABELS'
    $Estimate  = Get-HeaderValue $RawBody 'ESTIMATE'
    $Priority  = Get-HeaderValue $RawBody 'PRIORITY'

    # Also check the lines immediately preceding the ISSUE: marker — that is
    # the canonical placement in this repo's block format.
    $precedingHeaderBlock = ''
    $titleEscaped = [regex]::Escape($Title)
    $precMatch = [regex]::Match($MatchingSurface, "(?s)((?:^|\n)(?:LABELS|ESTIMATE|PRIORITY):[^\n]*\n)+(?=ISSUE:\s*$titleEscaped)")
    if ($precMatch.Success) { $precedingHeaderBlock = $precMatch.Value }
    if ($precedingHeaderBlock) {
        if (-not $LabelsRaw) { $LabelsRaw = Get-HeaderValue $precedingHeaderBlock 'LABELS' }
        if (-not $Estimate)  { $Estimate  = Get-HeaderValue $precedingHeaderBlock 'ESTIMATE' }
        if (-not $Priority)  { $Priority  = Get-HeaderValue $precedingHeaderBlock 'PRIORITY' }
    }

    $BodyText = Strip-MetadataHeaders $RawBody

    if ($DryRun) {
        Write-Host "DRY RUN: Would create issue '$Title'" -ForegroundColor Yellow
        Write-Host "         labels=$LabelsRaw  estimate=$Estimate  priority=$Priority" -ForegroundColor DarkGray
        continue
    }

    Write-Host "📦 Creating issue: $Title"
    Write-Host "    labels=$LabelsRaw  estimate=$Estimate  priority=$Priority" -ForegroundColor DarkGray

    # Safe multiline body parsing via temporary file injection protecting escaping logic.
    $TempFile = New-TemporaryFile
    $BodyText | Out-File -FilePath $TempFile.FullName -Encoding UTF8

    try {
        # Build gh issue create argv with optional --label flags.
        $createArgs = @('issue', 'create', '--title', $Title, '--body-file', $TempFile.FullName, '--project', $ProjectName)
        if ($LabelsRaw) {
            foreach ($lbl in ($LabelsRaw -split ',\s*')) {
                if ($lbl) { $createArgs += @('--label', $lbl.Trim()) }
            }
        }
        $Url = & gh @createArgs 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ Created at: $Url" -ForegroundColor Green
            $IssuesCreated++

            # Parse the issue number from the returned URL: ".../issues/<N>"
            $IssueNumber = $null
            if ("$Url" -match '/issues/(\d+)\s*$') { $IssueNumber = [int]$Matches[1] }

            # Set Estimate and Priority on the project item. Both require the
            # item id which we look up post-creation.
            if ($IssueNumber -and $projectMeta) {
                $ItemId = Get-ProjectItemId -IssueNumber $IssueNumber -ProjectNumber $projectMeta.ProjectNumber -Owner $ProjectOwner
                if ($ItemId) {
                    if ($Estimate -and $projectMeta.EstimateFieldId) {
                        if (Set-ProjectField -ItemId $ItemId -ProjectId $projectMeta.ProjectId -FieldId $projectMeta.EstimateFieldId -Number ([int]$Estimate)) {
                            Write-Host "    📐 Estimate=$Estimate" -ForegroundColor DarkGray
                        }
                    }
                    if ($Priority -and $projectMeta.PriorityFieldId) {
                        $optionId = $projectMeta.PriorityOptions[$Priority]
                        if ($optionId) {
                            if (Set-ProjectField -ItemId $ItemId -ProjectId $projectMeta.ProjectId -FieldId $projectMeta.PriorityFieldId -SingleSelectOptionId $optionId) {
                                Write-Host "    🎯 Priority=$Priority" -ForegroundColor DarkGray
                            }
                        } else {
                            Write-Host "    ⚠️  Unknown priority '$Priority' — must be one of: $($projectMeta.PriorityOptions.Keys -join ', ')" -ForegroundColor Yellow
                        }
                    }
                } else {
                    Write-Host "    ⚠️  Could not locate project item id for issue #$IssueNumber — Estimate/Priority not applied." -ForegroundColor Yellow
                }
            }

            # Re-read and dynamically delete the created issue to prevent duplication.
            # We also strip the contiguous LABELS:/ESTIMATE:/PRIORITY: header lines
            # immediately preceding the matched ISSUE: line, so no stub headers are
            # left behind after a successful sync.
            $CurrentLines = Get-Content $IssuesFile
            $UpdatedLines = [System.Collections.Generic.List[string]]::new()
            $InsideSpecificIssue = $false

            foreach ($Line in $CurrentLines) {
                if ($Line -match "^ISSUE:\s*$([regex]::Escape($Title))$") {
                    # Walk back through the already-kept lines and drop any
                    # trailing LABELS:/ESTIMATE:/PRIORITY: lines (allowing one
                    # optional blank line between header lines).
                    while ($UpdatedLines.Count -gt 0) {
                        $tail = $UpdatedLines[$UpdatedLines.Count - 1]
                        if ($tail -match '^(LABELS|ESTIMATE|PRIORITY):\s*' -or $tail -match '^\s*$') {
                            $UpdatedLines.RemoveAt($UpdatedLines.Count - 1)
                        } else {
                            break
                        }
                    }
                    $InsideSpecificIssue = $true
                } elseif ($Line -match "^END_ISSUE" -and $InsideSpecificIssue) {
                    $InsideSpecificIssue = $false
                } elseif (-not $InsideSpecificIssue) {
                    $UpdatedLines.Add($Line)
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
    Write-Host "🎉 Sync complete! $IssuesCreated issues created and removed from ISSUES.md." -ForegroundColor Green
}
