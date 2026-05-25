# ADR-015: Terraform remote state in a shared platform resource group

## Status

Accepted

## Context and Problem Statement

The `infra/` stack initially used local Terraform state (a file on the maintainer's laptop, gitignored). Local state has no locking (concurrent `apply` corrupts it), no off-machine backup (losing the file orphans every managed resource), and stores secret-bearing values in plaintext on disk.

Two coupled decisions are needed: *where* remote state lives, and *how* the secrets that inevitably land in state are managed.

A naive fix puts the state storage account inside the project resource group `rg-helloarch-dev`. But that conflicts directly with [ADR-013](ADR-013-dedicated-foundry.md)'s core invariant: the dedicated-Foundry design exists so `az group delete rg-helloarch-dev` cleanly tears down the whole project. State stored in that same RG would be destroyed by its own teardown — orphaning anything the delete missed and removing the ability to `terraform destroy`. The backend must outlive the thing it tracks.

Terraform state is also secret-bearing: anything Terraform manages (e.g. the generated `azuread_service_principal_password`) persists in state in plaintext. This raises the question of whether Azure Key Vault belongs on the critical path.

## Considered Options

- **Option A — State storage in the project RG (`rg-helloarch-dev`).**
- **Option B — State storage in a shared, project-agnostic platform RG (`rg-platformy-dev`).**
- **Secrets sub-decision — (1) eliminate secrets from state, (2) harden the backend, (3) route secrets through Key Vault.**

## Decision Outcome

Chosen: **Option B — a shared platform resource group `rg-platformy-dev` holding a single hardened storage account `stplatformydev`**, with per-project state keys in one `tfstate` container (`helloarch/terraform.tfstate`).

The platform RG is long-lived and project-agnostic: one state account backs every project, surviving any single project's teardown. This preserves ADR-013's clean-teardown invariant and matches the production pattern (consolidated state estate), advancing the project's learning objective rather than working against it.

**Secrets stance: harden the backend; do not introduce Key Vault for this concern.** The load-bearing insight is that *anything Terraform manages lands in state in plaintext* — so Key Vault as a write destination does not remove a Terraform-generated secret from state. Key Vault is therefore not a solution to secret-in-state and is deferred until a genuine runtime secret (one that managed identity cannot cover) exists, consistent with [ADR-008](ADR-008-secrets-management.md) designating Key Vault as the production-corporate store.

Instead, in priority order:
1. **Eliminate secrets** — the cloud path is already secretless via managed identity (UAMI → ACR + Foundry); local dev uses `az login` + `DefaultAzureCredential`. Removing the optional Service Principal password (and using OIDC workload-identity federation for CI) is tracked as a fast-follow.
2. **Harden the state backend** (this ADR) — RBAC/Entra-only (`--allow-shared-key-access false`, `use_azuread_auth = true`), no public blob access, blob versioning + soft-delete for recovery. Encryption at rest is on by default. This protects the residual secrets that always leak into state.

### Positive Consequences

- Tearing down `rg-helloarch-dev` never destroys its own state.
- State is locked (blob lease) and recoverable (versioning), off the maintainer's laptop.
- RBAC-only access removes account-key sprawl; no public exposure of state blobs.
- One platform account scales to future projects via state-key prefixes — no per-project backend infrastructure.

### Negative Consequences

- A one-time manual bootstrap (`az` commands in README) is required before `terraform init -migrate-state`, since the backend cannot provision the account it depends on (chicken-and-egg).
- The platform RG/account is now a shared dependency whose deletion would affect every project's state — it must be treated as protected infrastructure.
- Secrets still reside in state until the SP-password elimination fast-follow lands; backend hardening is the interim mitigation.

## Pros and Cons of the Options

### Option A — State in the project RG

- Good, because simplest — one RG, no extra platform resource.
- Bad, because `az group delete rg-helloarch-dev` destroys its own state, breaking ADR-013's teardown invariant.
- Bad, because state cannot be shared across projects.

### Option B — Shared platform RG

- Good, because state outlives any single project teardown.
- Good, because it matches the production consolidated-state pattern and serves all future projects.
- Bad, because it introduces a shared dependency and a one-time bootstrap step.

### Secrets — why not Key Vault now

- Good (harden-only), because it addresses the actual threat surface (state at rest) without adding infrastructure for a non-solution.
- Bad (Key Vault now), because a KV write does not remove the secret from state — it would be churn for a single secret slated for removal.
- Deferred: Key Vault returns when a runtime secret that managed identity cannot cover actually exists (ADR-008 production-corporate store).
