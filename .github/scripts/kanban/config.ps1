#Requires -Version 7.0
# config.ps1 — Central configuration for the kanban orchestrator.
#
# OVERRIDING: All values can be overridden per-machine via .env (KANBAN_* env vars
# take precedence). Edit this file to change repo-wide defaults.
#
# MODEL SELECTION LOGIC
#   Estimate (Fibonacci SP) drives model and turn-budget selection:
#   - Implement : SP > OpusImplementThreshold → Opus; else Sonnet
#   - Review    : SP > OpusReviewThreshold    → Opus; else Sonnet
#   - Aux tasks : always Haiku (commit messages, context updates)
#
# TURN BUDGETS
#   --max-turns prevents infinite agentic loops. Values are generous — cost is
#   not a constraint. The 5-hour Anthropic token-window reset is the hard limit.
#   Review gets a flat budget (read-only phase, no writes).
#   Implement scales with SP — larger tasks genuinely need more exploration.

$OrchestratorConfig = @{

    # ── Models ────────────────────────────────────────────────────────────────
    ModelSonnet = 'claude-sonnet-4-6'          # implement (low-SP), review (low-SP), refine, context-update
    ModelOpus   = 'claude-opus-4-7'            # implement (high-SP), review (high-SP)
    ModelHaiku  = 'claude-haiku-4-5-20251001'  # commit messages, auxiliary one-shot calls

    # ── Model tier thresholds (story points) ─────────────────────────────────
    # SP > threshold → Opus for that phase; SP <= threshold → Sonnet
    OpusImplementThreshold = 5   # 1–5 → Sonnet implement  |  8–21 → Opus implement
    OpusReviewThreshold    = 3   # 1–3 → Sonnet review     |  5–21 → Opus review

    # ── Turn budgets — implement (scales with SP) ─────────────────────────────
    # Each entry is the max-turns for that Fibonacci SP value.
    # Key 0 = unknown estimate fallback.
    MaxTurns_Implement = @{
        0  = 60    # unknown estimate — safe floor
        1  = 60    # trivial: floor is the ceiling; >30 turns signals a loop
        2  = 70    # small: marginal bump, bounded scope
        3  = 80    # moderate: multi-file, some exploration needed
        5  = 100   # medium: multi-component, deeper codebase reading
        8  = 130   # complex: architectural changes, many files
        13 = 160   # large: multi-area, extensive exploration + implementation
        21 = 200   # epic: maximum budget — HITL path, Opus on full codebase
    }

    # ── Turn budgets — other phases (flat) ───────────────────────────────────
    MaxTurns_Refine        = 15   # structured output + label assignment — lightweight
    MaxTurns_Review        = 30   # read-only: inspect code + signal history, no writes
    MaxTurns_ContextUpdate = 15   # diff analysis + generate a unified patch

    # ── Orchestrator behaviour ────────────────────────────────────────────────
    MaxRetries = 2    # implement→review cycles before agent:failed
}
