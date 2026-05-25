# ISSUES.md

Local improvement backlog. Add improvements as Agile User Story blocks below the ISSUES sentinel.

Run `task sync` to push pending blocks to GitHub Issues and the project board.
Run `task sync -- -DryRun` to preview without making changes.

---

## Block Format

Every block must follow this structure exactly so `sync-issues.ps1` can parse it:

```
```

Header fields — all optional, must appear before the body, in any order:

- `LABELS:` — comma-separated subset of the allowed label set. Agents must not create new labels. Allowed values:
  - `AFK` — issue can be processed autonomously by the orchestrator without human intervention
  - `HITL` — issue requires human decision or approval at some point; orchestrator will not pick it up automatically
  - `agent:backlog` `agent:implementing` `agent:review` `agent:merged` `agent:failed` — orchestrator state machine; set by the orchestrator, not by humans or agents writing issues
- `ESTIMATE:` — Fibonacci story point integer (see scale below). Synced to the **Estimate** field on the GitHub Project board. **Do not use the project board's Size field** (XS/S/M/L/XL) — it is not populated by any script and conflicts with Estimate as the single sizing signal.
- `PRIORITY:` — one of `P0 | P1 | P2 | P3 | P4` (see definitions below). Synced to the **Priority** field on the GitHub Project board.

After `task sync`, each processed block is removed from this file and lives as a GitHub Issue on the project board.

---

## Estimate

Estimates use the Fibonacci series: **1 · 2 · 3 · 5 · 8 · 13 · 21**. Points measure complexity, risk, and effort relative to the 1-point anchor — not calendar hours.

**Anchor — what is a 1?**

A 1-point issue is a single-file additive edit where correctness is verifiable by one command without running the test suite.

- *Update `Status: Proposed → Accepted` in one ADR file. Verified by `grep 'Status: Accepted' docs/adr/ADR-001.md`.*
- *Add a single `.gitignore` pattern as a standalone issue. Verified by `git check-ignore -v <pattern>`.*

A true 1 is rare as a standalone issue — in practice issues bundle and land at 2 minimum because AC always includes `uv run pytest`.

**Scale:**

| Points | Definition | Typical examples |
|--------|-----------|-----------------|
| 1 | Single-file additive edit; correctness verified by one command, no test run | Update one ADR status; add a single `.gitignore` pattern |
| 2 | Mechanical multi-file change; verifiable by CLI commands; no design decisions | Add a CI workflow file; add devcontainer config; update dependency pins |
| 3 | New document or single function with a clear spec; no architectural decision required | Add a `SECURITY.md`; write a multi-stage `Dockerfile`; add a coverage gate to CI |
| 5 | New cross-cutting behaviour touching multiple modules; tests required; path is clear | Add a new config field propagated through config, tests, and docs; port a script to a new runtime |
| 8 | Significant feature spanning multiple subsystems or requiring an explicit design decision | Multi-cloud deployment workflow with WIF; template restructure affecting generation output |
| 13 | Major system creation or replacement; end-to-end behaviour must be verified | Replace a polling-based pipeline with an event-driven one; introduce a new orchestration layer |
| 21 | Full architectural phase spanning every bounded context; compounding unknowns. **Decompose before implementation.** | A PRD tackled as a single issue rather than decomposed child issues |

**Rules of thumb:**
- If unsure between two values, pick the higher.
- Estimates include the full cost: implementation, tests, review, and any documentation AC requires.
- If a dependency is unresolved, do not estimate — flag for refinement first.
- `ESTIMATE: 13` or above requires `LABELS: HITL`. The agent does not proceed AFK.

---

## Priority

Priority expresses urgency and impact. Independent of size — a 1-point issue can be P2 if it blocks correct behaviour.

| Label | Name | Definition |
|-------|------|------------|
| P4 | Nice to have | Non-breaking improvement: clean-up, refactor, DX, or non-functional enhancement. No user-facing impact if deferred. |
| P3 | Normal — new work | New functionality. Application works without it, but planned and expected. |
| P2 | Priority — broken | Application not working correctly. Pick up in current or next sprint. Requires documented broken behaviour and reproduction path. |
| P1 | Application down | Completely unavailable or critically degraded. Immediate implementation. Extremely rare. |
| P0 | Multi-repo outage | Multiple repositories impacted. Incident-level response. |

Default new issues to **P3** (new work) or **P4** (improvement). Escalation to P2 or above requires the issue description to document the broken behaviour and a reproduction path or observable symptom.

---

<!-- ISSUES -->

ISSUE: Add OIDC federated credential for CI auth and retire SP-secret remnants
LABELS: HITL
ESTIMATE: 3
PRIORITY: P4

**Goal**
Give CI a keyless way to authenticate to Azure and finish retiring the static-secret auth path. The Terraform-generated SP password and `sp_client_secret` output were already removed pre-first-apply (so no secret ever entered remote state); the `azuread_application`/`azuread_service_principal` for `sp-helloarch-dev` and its Foundry role assignments remain, dormant, awaiting a credential.

**Description**
Local dev uses `az login` + `DefaultAzureCredential` (CONTEXT §4); cloud uses the UAMI. The remaining gap is CI: when a GitHub Actions workflow needs to run `terraform`/deploy, it should authenticate via OIDC workload-identity federation — a short-lived token exchange, no stored secret. Decision required (HITL): confirm whether CI deploy is in scope yet, and whether the app's optional `AZURE_AUTH_MODE=sp` path is kept or removed. Supersedes the SP-password portion of ADR-013.

**Requirements**
- Add `azuread_application_federated_identity_credential` on `azuread_application.helloarch` for the GitHub Actions subject (`repo:ysuurme/azure_hello_world:ref:refs/heads/master` or an environment subject), issuer `https://token.actions.githubusercontent.com`.
- Grant the CI principal the roles it needs for `terraform apply`, including `Storage Blob Data Contributor` on the `tfstate` container in `stplatformydev` (so CI can read/write remote state).
- Decide the fate of app-side `AZURE_AUTH_MODE=sp`; if removed, clean the optional `AZURE_CLIENT_SECRET` references from README.
- Record an ADR note superseding the SP-password portion of ADR-013, referencing ADR-015.

**Acceptance Criteria**
- A GitHub Actions workflow authenticates to Azure with no stored client secret (OIDC), and can run `terraform plan` against the remote backend.
- `git grep -n AZURE_CLIENT_SECRET` reflects the decided app-auth posture (removed, or clearly documented as a manual-only local path).
- `uv run pytest` passes.
END_ISSUE

