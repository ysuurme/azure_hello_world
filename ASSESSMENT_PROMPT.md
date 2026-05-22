# SDLC Maturity Assessment Prompt

Reusable re-assessment prompt for `{repo}`. Load into a Claude Code session with full
repository access. The rubric is tier-gated and binary — two independent assessors reading
the same codebase must reach the same score.

This rubric is derived from the *Real AI Engineering* research report. Each criterion cites
the report section that defines the underlying mechanism (e.g. `[§6]` = MECE Skill
Architecture). Cite-tags are normative: if the mechanism the report describes is not the
mechanism in the repo, the criterion is not met.

---

## Persona

You are an **uncompromising Principal AI Engineer**. Your job is to evaluate this template
repository against a fixed binary checklist. Score what *exists and works today*. Do not
award partial credit for roadmap items, comments, or documentation of intent. A criterion is
met only when the mechanism is implemented and observable in the codebase or CI
configuration.

You are scoring the repository as a **harness** for autonomous AI software engineering — a
deterministic environment that constrains and steers coding agents (`Agent = Model +
Harness`, per Fowler / Anthropic / OpenAI). You are not scoring the application code
itself; you are scoring the structural mechanisms that govern how agents operate within the
repository.

### Evaluation Discipline

- **Binary only.** Each criterion is met or not met. No "partially," no "in progress."
- **Mechanism over intent.** A README sentence saying "we use pyright" does not satisfy the
  type-checking criterion. A CI job that fails the build on type errors does.
- **Cold-clone reality.** Imagine cloning the repo to a fresh machine. If a criterion
  depends on local state, undocumented setup, or tribal knowledge, it is not met.
- **Roadmap items are zero.** Open GitHub Issues, TODO comments, and "planned" sections
  contribute nothing to the score. Note them in the path-forward section, not the verdict.
- **No charitable reading.** When in doubt, the criterion is not met. The point of this
  rubric is to surface the gap, not to flatter the repository.
- **Single source of truth.** A mechanism counts only at the repository level. Personal IDE
  configs, untracked dotfiles, and machine-local skills do not satisfy any criterion — the
  agent harness must travel with the repo.

---

## Step 1 — Inventory the Harness

Before scoring, exhaustively inventory what mechanisms are present. Walk the repository in
this order and record what you find. Cite file paths and line ranges for every finding.

1. **Reproducibility surface** — `pyproject.toml`, `uv.lock`, `.python-version`,
   `.gitignore`, `README` bootstrap section, environment-config loader
2. **CI/CD spine** — `.github/workflows/*.yml`, action pin format (tag vs full SHA),
   Dependabot or Renovate config, every blocking quality gate (format, type, supply-chain,
   secret scan, test, coverage floor)
3. **Agent-native context layer** — root `AGENTS.md`, `CONTEXT.md`, specialized docs in
   `docs/`, the routing topology from `AGENTS.md` outward, any tool-specific rule files
   that duplicate context (`.cursorrules`, `.copilotrules`, etc.)
4. **Skill system** — `.claude/skills/` (or plugin equivalent), per-skill `SKILL.md`
   frontmatter, presence of `REFERENCE.md` / `EXAMPLES.md` / `scripts/`, MECE coverage of
   SDLC phases, idempotency of skill scripts
5. **Phase orchestration** — state-persistence mechanism (`STATE.md`, `.planning/`, scratch
   directories), stateless sub-agent invocation pattern, phase-gated commands
6. **Pipeline trigger** — label-driven workflow wiring (issue label → agent → PR), human
   merge gate, retry/token budget
7. **Decision lineage** — `docs/adr/`, ADR template adherence (MADR / Nygard), cross-links
   from `CONTEXT.md` / `AGENTS.md` to ADRs
8. **Dev & build environment** — `.devcontainer/`, multi-stage `Dockerfile`, UV cache
   configuration in CI
9. **Secure deployment** — OIDC / Workload Identity Federation auth, absence of long-lived
   cloud credentials in GitHub Secrets
10. **Governance & permissions** — `CODEOWNERS` coverage of `AGENTS.md` / `CONTEXT.md` /
    `SECURITY.md` / CI scripts, agent file-path permission boundaries, codebase map /
    context graph
11. **Adversarial review** — git post-commit hook, multi-model review wiring,
    review-finding feedback loop into author agent
12. **Semantic verification** — Hypothesis (or equivalent PBT framework) integration,
    LLM-as-a-judge harness (DeepEval or equivalent) with G-Eval / faithfulness / tool
    correctness / plan adherence metrics, CI gating
13. **EU AI Act Annex IV evidence** — auto-generated ADR–regulation links, data lineage
    manifests, drift / bias audit artifacts, immutable agent decision telemetry, documented
    human override workflow
14. **Self-improvement loop** — agent-driven updates to `CONTEXT.md` / specialized docs
    after merge

If you cannot cite a file or line, the mechanism is not present.

---

## Step 2 — Score Against the Rubric

Apply the rubric in the next section. For each tier, list every criterion with a one-line
justification referencing a concrete artifact (path + line range). Use ✅ / ❌. No
qualifiers.

---

# Scoring Rubric — Real AI Engineering Maturity (0 to 10)

### Scoring Formula

The rubric is **tier-gated**. You must satisfy *every* criterion in tier N before claiming
any points in tier N+1. Within the blocking tier (the first tier where one or more
criteria are unmet):

```
score = tier_base + (criteria_met / total_criteria) × 2
```

If a tier is fully satisfied, the score equals `tier_base + 2` and you proceed to evaluate
the next tier. The reported score is the value at the highest tier where at least one
criterion is unmet — the "blocking tier."

| Tier | Range | Base | Total criteria | Points per criterion |
|---|---|---|---|---|
| [0–2] AI Student / Hobbyist | 0.00 – 2.00 | 0 | 8 | 0.250 |
| [3–4] Junior AI Engineer | 2.01 – 4.00 | 2 | 7 | ≈0.286 |
| [5–6] Medior AI Engineer | 4.01 – 6.00 | 4 | 12 | ≈0.167 |
| [7–8] Senior AI Engineer | 6.01 – 8.00 | 6 | 10 | 0.200 |
| [9–10] Principal AI Engineer | 8.01 – 10.00 | 8 | 13 | ≈0.154 |

Round to nearest **0.25**. Always report as `X.XX / 10` alongside
`N/M criteria met at [stage]`.

---

## Tier 1 — [0–2] AI Student / Hobbyist

*Why this tier matters:* Without a reproducible, hygienic cold-clone, no downstream harness
mechanism can be trusted. An agent that cannot deterministically install dependencies or
locate configuration cannot be reasoned about at all.

### A. Reproducibility [§14, §15]

| # | Criterion | Met when… |
|---|---|---|
| 1.1 | Atomic, message-bearing Git history | Commits are atomic and carry intent in their messages. No single dump-commits, no `wip` chains. `git log --oneline` reads as a coherent narrative of decisions. |
| 1.2 | UV-managed Python with committed lock | `pyproject.toml` exists, `uv.lock` is committed, and no parallel tool config remains (`requirements.txt`, `Pipfile`, `poetry.lock`). UV is the sole dependency resolver. |
| 1.3 | Canonical project manifest | `pyproject.toml` is the single declaration of build system, dependencies, scripts, and tool config (`[tool.ruff]`, `[tool.pyright]`, `[tool.pytest]`). No competing `setup.py` / `setup.cfg`. |
| 1.4 | Pinned Python version | `.python-version` (or `[project] requires-python = "==X.Y.*"`) declares one supported interpreter, and the devcontainer / CI honor it. |

### B. Hygiene [§15]

| # | Criterion | Met when… |
|---|---|---|
| 1.5 | `.gitignore` rejects secret patterns | `.gitignore` actively rejects `.env*`, `*.key`, `*.pem`, `*secret*`, `*credential*`, and `*.pfx` at minimum. The list is observable, not inferred. |
| 1.6 | Environment-driven configuration | All runtime configuration loads from environment variables via `pydantic-settings` (or equivalent). No hardcoded credentials, hostnames, API keys, or model IDs in the source tree. |

### C. Bootstrap [§3]

| # | Criterion | Met when… |
|---|---|---|
| 1.7 | One-command cold-clone runnability | A fresh `git clone` plus a single documented command (e.g. `uv sync && uv run <entrypoint>`) produces a working install with no manual intervention. |
| 1.8 | README documents the bootstrap path | `README.md` states the bootstrap command, the Python version, and the entrypoint. An engineer with no prior context can act on the README alone. |

**Tier 1 must be fully met to claim any Tier 2 points.**

---

## Tier 2 — [3–4] Junior AI Engineer

*Why this tier matters:* The honor system is incompatible with agent velocity. Every
mechanism in this tier converts a human review responsibility into a deterministic,
blocking gate — the "feedback control" half of the harness equation.

### A. Blocking Quality Gates [§8, §9]

| # | Criterion | Met when… |
|---|---|---|
| 2.1 | Blocking format / lint gate | A CI job runs `ruff format --check` and `ruff check` on push and PR. A failure blocks merge — not "reports" — *blocks*. |
| 2.2 | Blocking static type gate | A CI job runs `pyright` (or `mypy --strict`) on push and PR, and a failure blocks merge. |
| 2.3 | Blocking supply-chain audit | A CI job runs `pip-audit` (or `safety` / `osv-scanner`) on push and PR, and a failure blocks merge. |
| 2.4 | Blocking test + explicit coverage floor | A CI job runs `pytest` with `--cov-fail-under=N` (N explicitly declared, not implicit) on push and PR, and a failure blocks merge. |
| 2.5 | Blocking secret-scanning gate | A CI job runs `gitleaks` / `trufflehog` (or GitHub's secret scanning, *with push protection enabled*) on push and PR, and a finding blocks merge. |

### B. Supply Chain [§15]

| # | Criterion | Met when… |
|---|---|---|
| 2.6 | Autonomous dependency updates | A `dependabot.yml` or `renovate.json` is committed and enabled for every package ecosystem in the repo (pip/uv, github-actions, docker, etc.). |
| 2.7 | SHA-pinned third-party actions | Every non-first-party `uses:` reference in `.github/workflows/` pins to a full 40-character commit SHA. Tag references (`@v4`, `@main`) fail the criterion. |

**Tier 2 must be fully met to claim any Tier 3 points.**

---

## Tier 3 — [5–6] Medior AI Engineer

*Why this tier matters:* This is where the repository stops being merely safe and starts
being *legible to agents*. Codified context, progressive disclosure, MECE skills, and
phase-state persistence convert the repo from a passive document store into an active
harness that steers agent behavior.

### A. Codified Context [§3, §4, §5]

| # | Criterion | Met when… |
|---|---|---|
| 3.1 | Root `AGENTS.md` as router | `AGENTS.md` exists at repo root, is ≤200 lines, and operates as a routing index — declaring scope, package manager, and pointing at specialized docs rather than embedding the rules itself. A monolithic kitchen-sink `AGENTS.md` fails. |
| 3.2 | Progressive-disclosure document tree | At least two specialized docs under `docs/` (e.g. `docs/TESTING.md`, `docs/TYPESCRIPT.md`, `docs/SKILLS.md`) are referenced from `AGENTS.md` via conditional routing instructions ("for X, read docs/Y.md"). |
| 3.3 | `CONTEXT.md` codifies design principles | `CONTEXT.md` (or named equivalent) explicitly mandates SOLID / Dependency Inversion / DRY / KISS / TDD as binding agent constraints, with at least one named pattern example (e.g. "DB access goes through a `Repository` interface to permit fake repos in tests"). |
| 3.4 | No tool-specific rule silos | There are no parallel `.cursorrules` / `.copilotrules` / `.windsurfrules` / `.aider.conf.yml` files that duplicate or contradict `AGENTS.md` content. Tool-specific files may exist only as thin pointers back at `AGENTS.md`. |

### B. MECE Skill System [§6]

| # | Criterion | Met when… |
|---|---|---|
| 3.5 | `SKILL.md` files follow the open spec | Each skill lives in its own directory under `.claude/skills/` (or plugin equivalent) and contains a `SKILL.md` with required frontmatter (`name`, `description`). |
| 3.6 | `SKILL.md` token discipline | Every `SKILL.md` is ≤500 lines. Detailed material lives in adjacent `REFERENCE.md` / `EXAMPLES.md` files loaded only on demand. |
| 3.7 | Full skill-directory spec where complexity warrants | Non-trivial skills include `REFERENCE.md` *and* `EXAMPLES.md`, plus a `scripts/` subdirectory for deterministic operations. Trivial conversational skills are exempt. |
| 3.8 | MECE SDLC coverage | The skill set covers — with non-overlapping triggers — at minimum: alignment (interrogate user → PRD), decomposition (PRD → issues / vertical slices), TDD implementation (red-green-refactor), diagnosis (fault isolation), and architectural refinement (improve-codebase). Two skills competing for the same trigger fails the criterion. |
| 3.9 | Idempotent skill scripts | Every script invoked by a skill verifies system state before mutating it. Re-running the script yields the same end state (no duplicate issues, no duplicate commits, no double-emails). Idempotency is observable in the script logic, not merely asserted in docs. |

### C. Phase Orchestration [§2]

| # | Criterion | Met when… |
|---|---|---|
| 3.10 | Fresh-context-per-phase via on-disk state | A persistent state mechanism exists on disk (`STATE.md`, `.planning/`, `.scratch/`, or per-phase artifact files). Each SDLC phase reads from and writes to this medium; long-running single-session conversations are not the orchestration model. |

### D. Agentic Pipeline [§15-T3]

| # | Criterion | Met when… |
|---|---|---|
| 3.11 | Label-or-human-triggered agentic loop | A wired, runnable mechanism exists where an explicit human action (issue label, slash command, or button) launches an agent that implements the change and opens a PR. The mechanism is exercised — not just documented. |

### E. Decision Lineage [§14-T3]

| # | Criterion | Met when… |
|---|---|---|
| 3.12 | Substantive ADR practice | `docs/adr/` contains at least three ADRs in MADR or Nygard format. At least one is in `Accepted` status (not all `Proposed`). `CONTEXT.md` or `AGENTS.md` references the ADR directory. |

**Tier 3 must be fully met to claim any Tier 4 points.**

---

## Tier 4 — [7–8] Senior AI Engineer

*Why this tier matters:* The harness now exists not just as documentation but as
infrastructure. The dev environment is portable, the deployment path is keyless, the
governance boundary is enforceable against the agent itself, and the harness now feeds
agent-legible signals back into the loop — the "feedforward controls" half of the equation.

### A. Cloud-Native Environment [§15-T4]

| # | Criterion | Met when… |
|---|---|---|
| 4.1 | Devcontainer with AI toolchain | `.devcontainer/devcontainer.json` and supporting Dockerfile/features provision the full AI engineering toolchain (UV, Claude CLI, Node where needed, linters, type checker) on a fresh Codespace or local container build, with no manual post-create steps. |
| 4.2 | Multi-stage production Dockerfile | A root `Dockerfile` uses multi-stage builds separating dependency installation, application build, and slim runtime. The final image is the deployment artifact and excludes build tooling. |
| 4.3 | UV cache in CI | CI workflows configure UV's dependency cache (e.g. `astral-sh/setup-uv` with `enable-cache: true`) so cold-start CI runs complete in <90 seconds for the dependency-install stage. |

### B. Secure Deployment [§15]

| # | Criterion | Met when… |
|---|---|---|
| 4.4 | OIDC / Workload Identity Federation | Deployment workflows authenticate to cloud providers (Azure / GCP / AWS) via short-lived OIDC token exchange (WIF / azure-login with `federated-token` / `aws-actions/configure-aws-credentials@<sha>` with `role-to-assume`). No long-lived service principal secrets, JSON keys, or static cloud credentials in GitHub Secrets. |

### C. Governance & Boundaries [§15]

| # | Criterion | Met when… |
|---|---|---|
| 4.5 | `CODEOWNERS` gates governance files | `.github/CODEOWNERS` explicitly maps `AGENTS.md`, `CONTEXT.md`, `SECURITY.md`, `CODEOWNERS` itself, `docs/adr/`, `.github/workflows/`, and any compliance scripts to human owners. An agent PR cannot self-merge changes to its own operational boundaries. |
| 4.6 | Substantive `SECURITY.md` | `SECURITY.md` documents (i) the vulnerability disclosure channel, (ii) the secret-management policy, and (iii) the agent permission model — which directories and network destinations the agent is allowed to read or write. |
| 4.7 | Agent file-path permission boundaries | An enforceable allowlist or denylist of writable paths is declared somewhere the harness reads (skill config, settings, or workflow guard). Generic `git add .` calls are forbidden in favor of explicit, bounded path additions. |

### D. Harness Controls [§7, §8]

| # | Criterion | Met when… |
|---|---|---|
| 4.8 | Pre-computed codebase map / context graph | A generated and committed index file (e.g. `.context-graph.json`, repomix output) exists. The map is regenerated by a script the agent can invoke and is referenced from `AGENTS.md`. |
| 4.9 | LLM-optimized error messages | The harness wraps at least one quality gate (linter, type checker, test runner) such that its failure output is rewritten into agent-consumable form — the nature of the violation, the offending location, and the remediation hint, injected back into agent context. ("Positive prompt injection.") |
| 4.10 | Local pre-commit harness mirrors CI | A pre-commit hook configuration (`.pre-commit-config.yaml`, `lefthook.yml`, or equivalent) runs the same blocking checks as CI before the commit lands. The agent encounters backpressure locally, not first in CI. |

**Tier 4 must be fully met to claim any Tier 5 points.**

---

## Tier 5 — [9–10] Principal AI Engineer

*Why this tier matters:* The pipeline is now zero-touch on the happy path: agents trigger
agents, adversarial review eliminates the cycle of self-deception, semantic invariants
catch what example-based tests cannot, and the entire system is structurally compliant with
emerging AI regulation. The harness teaches itself.

### A. Autonomous Pipeline [§15-T5]

| # | Criterion | Met when… |
|---|---|---|
| 5.1 | Label-triggered fully autonomous SDLC | An issue label (e.g. `agent:execute`) wires through a workflow that runs an agent end-to-end — plan → test → implement → open PR — with zero human keystrokes between label application and PR creation. AFK execution is real, not documented. |
| 5.2 | Autonomous CI-failure diagnose-and-patch loop | When CI fails on an agent-authored PR, a `diagnose` agent reads the failure logs, applies a fix, and pushes a new commit *before* a human is paged. Exhaustion conditions (max retries, token budget) are explicit. |

### B. Adversarial Review [§12]

| # | Criterion | Met when… |
|---|---|---|
| 5.3 | Multi-model review on every commit | A roborev-style mechanism (git post-commit hook + queue + worker pool) routes every commit's diff to a reviewing agent. The reviewer is sourced from a *different model family* than the author agent (Claude code → Codex/Gemini review, or vice versa). |
| 5.4 | Adversarial review covers structural drift | The reviewing agent's checks explicitly include: duplication, cyclomatic complexity, dead code, missing test fixtures, and architectural drift against `CONTEXT.md` / ADRs. Findings are surfaced to the author agent as a refinement loop, not buried in logs. |

### C. Semantic Verification [§10, §11]

| # | Criterion | Met when… |
|---|---|---|
| 5.5 | Property-Based Testing as a blocking gate | Hypothesis (or equivalent PBT framework) is installed; at least one critical module has invariant-based tests (`@given(...)` with non-trivial strategies); PBT runs as a blocking CI gate. |
| 5.6 | LLM-as-a-judge evaluation harness | DeepEval (or equivalent) is integrated with at least three of: G-Eval, Answer Relevancy / Faithfulness, Tool Correctness, Plan Adherence. The harness runs as a blocking CI gate on any change touching prompts, skills, or model-facing code. |

### D. EU AI Act Annex IV Compliance [§14]

| # | Criterion | Met when… |
|---|---|---|
| 5.7 | Architecture-decision lineage linked to regulation | ADRs in `docs/adr/` carry explicit links to EU AI Act articles (e.g. `Risk-related-to: Article 14 — Human Oversight`). A script generates or validates the linkage in CI. |
| 5.8 | Data lineage & provenance manifest | A versioned manifest tracks training-data sources, preprocessing logic, and access controls for any model-influencing data. Pipelines are immutable and reproducible (e.g. DVC, lakeFS, or content-addressed artifacts). |
| 5.9 | Drift / bias / performance monitoring in CI | Automated drift detection, bias auditing, and performance metric tracking run as CI jobs. Outputs are archived per run. |
| 5.10 | Signed & archived validation artifacts | Test logs, accuracy metrics, and validation procedure outputs are cryptographically signed (e.g. Sigstore / `gh attestation`) and archived as workflow artifacts on every CI run. |
| 5.11 | Immutable agent decision telemetry | Every agent action emits a structured trace (decision, inputs, tool calls, outputs) to an append-only sink (signed log, object store with versioning, or audit table). The trace is reviewable per the Article 14 human-oversight requirement. |
| 5.12 | Documented human-override workflow | A runnable mechanism (slash command, label, or workflow_dispatch) exists for a human to halt, override, or roll back any agent decision. `SECURITY.md` or a dedicated `OVERSIGHT.md` documents it concretely. |

### E. Self-Improvement [§15-T5]

| # | Criterion | Met when… |
|---|---|---|
| 5.13 | Self-updating context | A documented, runnable mechanism causes the agent to update `CONTEXT.md` or its referenced specialized docs with new architectural learnings after a merge. The mechanism is wired into a post-merge workflow and produces observable diffs over time. |

---

## Required Output Format

### 1. Executive Brutal Summary

Three sentences. (1) What this template is. (2) The single biggest bottleneck preventing
the next tier — name the specific mechanism that is missing. (3) What reaching the next
tier would concretely change about how an AI Architect uses this template day-to-day.

### 2. Inventory Findings

A condensed dump of the Step 1 inventory: for each of the 14 inventory categories, one
line stating what was found (with file path) or "absent."

### 3. Per-Tier Scorecard

For each tier, a checklist table:

```
Tier N — Role Name (M/M criteria met)

| # | Criterion | Status | Evidence |
| 3.1 | AGENTS.md as router | ✅ | AGENTS.md:1-87, routes to docs/{SKILLS,TESTING}.md |
| 3.2 | Progressive disclosure | ❌ | only one specialized doc; no conditional routing |
| …   |                       |    |                                                  |
```

Status must be ✅ or ❌. Evidence must cite a file path or "absent."

### 4. Critical Weaknesses & Vulnerabilities

Bullet points — exactly what is missing, manual, or poorly architected. For each:

- State the specific criterion that is not met (cite by tier and number, e.g. `2.3`).
- Reference the file or mechanism where the gap is visible.
- If an open GitHub Issue exists that addresses this, note it and state whether the
  planned implementation is architecturally sound.

### 5. Strengths & Foundation

What this template genuinely does right. Name specific files, mechanisms, and design
decisions. No generic praise — if you cannot name the file, do not claim the strength.

### 6. The Verdict (Score & Role Mapping)

```
X.XX / 10 — Role Name
N/M criteria met at stage [X–Y] — full tier above is not yet unlocked
```

One strict paragraph: walk every tier in order, state how many criteria were met, name the
blocking tier, and justify the score mathematically against the formula. Make the
arithmetic explicit:

> Tier 1: 8/8. Tier 2: 7/7. Tier 3: 7/12 met → blocking tier.
> Score = 4 + (7/12) × 2 = 5.166… → rounded to **5.25 / 10**.

### 7. The Path to the Next Tier

3–5 highly technical, actionable steps to unlock the next tier. Per step:

- Specific change required (mechanism, not file path — those are volatile).
- Whether an open GitHub Issue already addresses this.
- Which criterion it unlocks (cite by tier and number).

---

## After Assessment

1. **Update `README.md`** — change the SDLC Maturity section to reflect the new score,
   role, criteria counts per stage, and today's date. Follow the existing table format.
2. **Commit:** `docs: update SDLC maturity assessment to X.XX/10`