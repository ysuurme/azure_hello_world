#Requires -Version 7.0
<#
.SYNOPSIS
    Issue decomposition stub — Phase 2 implementation pending (Issue #9).

.DESCRIPTION
    When implemented (Issue #9), this script will:
    - Read a Lean PRD from a GitHub Issue or local Markdown file
    - Run a deduplication pass against open GitHub Issues and .out-of-scope.md entries
    - Parse PRD sections (Tracer Bullet, User Stories, Implementation Decisions, Out of Scope)
    - Classify each decomposed issue as HITL or AFK using the decision rubric
    - Apply Fibonacci sizing estimates based on scope heuristics
    - Emit a decomposition manifest (JSON) for review before creating any GitHub Issues
    - Optionally execute `gh issue create` for each decomposed issue (--Execute flag)

    Phase 2 scope (Issue #9):
    - `gh issue list` deduplication pass (open + closed issues)
    - PRD Markdown section parser
    - HITL/AFK classification rules from REFERENCE.md
    - Dry-run mode (default) + --Execute flag for live issue creation
    - .out-of-scope.md section generation for concepts deferred in the PRD

.PARAMETER PRDIssueNumber
    GitHub Issue number containing the Lean PRD to decompose.

.PARAMETER OutOfScopePath
    Path to the .out-of-scope.md flat-file ledger (default: .out-of-scope.md).

.PARAMETER DryRun
    If set (default), emits the decomposition manifest without creating any GitHub Issues.

.PARAMETER Execute
    If set, creates GitHub Issues for each decomposed item after manifest review.

.NOTES
    Phase 2 implementation tracked in: https://github.com/ysuurme/my_template_repo/issues/9
    This stub satisfies the skill directory shape required by rubric criterion 3.7.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$PRDIssueNumber,

    [string]$OutOfScopePath = ".out-of-scope.md",
    [switch]$DryRun,
    [switch]$Execute
)

throw "decompose.ps1 is a Phase-2 stub. Full implementation is tracked in Issue #9."
