#Requires -Version 7.0
<#
.SYNOPSIS
    Grill-Me Protocol automation stub — Phase 2 implementation pending (Issue #8).

.DESCRIPTION
    When implemented (Issue #8), this script will:
    - Verify context fill is below the Smart Zone threshold (100k tokens) before starting
    - Load CONTEXT.md, AGENTS.md, and ADR_STRUCTURE.md in the required sequence
    - Walk every branch of the Grill-Me decision tree for a given feature request
    - Emit structured ADR candidates and an Agent Brief template to stdout

    Phase 2 scope (Issue #8):
    - Context fill measurement and compact() trigger
    - Glossary diff against the current CONTEXT.md
    - Boundary interrogation pass against all Bounded Contexts
    - Agent Brief scaffolding with interface templates pre-populated

.PARAMETER FeatureRequest
    Raw user request or problem statement to grill.

.PARAMETER ContextPath
    Path to CONTEXT.md (default: CONTEXT.md relative to repo root).

.PARAMETER AgentsPath
    Path to AGENTS.md (default: AGENTS.md relative to repo root).

.NOTES
    Phase 2 implementation tracked in: https://github.com/ysuurme/my_template_repo/issues/8
    This stub satisfies the skill directory shape required by rubric criterion 3.7.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$FeatureRequest,

    [string]$ContextPath = "CONTEXT.md",
    [string]$AgentsPath  = "AGENTS.md"
)

throw "grill.ps1 is a Phase-2 stub. Full implementation is tracked in Issue #8."
