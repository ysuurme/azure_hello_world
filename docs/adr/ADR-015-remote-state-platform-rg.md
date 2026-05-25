# ADR-015: Terraform remote state in a shared platform resource group

## Status

Accepted — OIDC fast-follow completed in issue #68. **Amended 2026-05-25** — a central platform Key Vault (`kv-platformy-dev`) is now provisioned in `rg-platformy-dev`, and local *container* dev authenticates as the scoped Service Principal using a client secret stored there. See the [Amendment](#amendment-2026-05-25-central-platform-key-vault--local-container-workload-identity) section. The no-secret-in-state invariant is preserved (the SP secret is created outside Terraform via `az` and never enters state).

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

**Secrets stance: keep secrets out of Terraform state.** The load-bearing insight is that *anything Terraform manages lands in state in plaintext* — so Key Vault as a write destination does not remove a *Terraform-generated* secret from state. ~~Key Vault is therefore not a solution to secret-in-state and is deferred until a genuine runtime secret (one that managed identity cannot cover) exists~~ — **superseded by the [2026-05-25 Amendment](#amendment-2026-05-25-central-platform-key-vault--local-container-workload-identity):** Key Vault is now introduced, but the invariant still holds because the SP secret is generated *outside* Terraform (via `az`) and stored in Key Vault, so it never enters state. Consistent with [ADR-008](ADR-008-secrets-management.md) designating Key Vault as the production-corporate store.

Instead, in priority order:
1. **Eliminate secrets** — the cloud path is already secretless via managed identity (UAMI → ACR + Foundry); local *native* dev uses `az login` + `DefaultAzureCredential`. The optional Service Principal password has been removed; CI authenticates via OIDC workload-identity federation (completed in issue #68, superseding the SP-password portion of ADR-013). `AZURE_AUTH_MODE=sp` is retained ~~solely as a **manual-only local path**~~ **(Amended 2026-05-25: now the standard path for local *container* dev — see Amendment)** — `AZURE_CLIENT_SECRET` is never stored in Terraform state or injected into CI or cloud environments; for local containers it lives in `kv-platformy-dev` and is injected at launch.
2. **Harden the state backend** (this ADR) — RBAC/Entra-only (`--allow-shared-key-access false`, `use_azuread_auth = true`), no public blob access, blob versioning + soft-delete for recovery. Encryption at rest is on by default. This protects the residual secrets that always leak into state.

### Positive Consequences

- Tearing down `rg-helloarch-dev` never destroys its own state.
- State is locked (blob lease) and recoverable (versioning), off the maintainer's laptop.
- RBAC-only access removes account-key sprawl; no public exposure of state blobs.
- One platform account scales to future projects via state-key prefixes — no per-project backend infrastructure.

### Negative Consequences

- A one-time manual bootstrap (`az` commands in README) is required before `terraform init -migrate-state`, since the backend cannot provision the account it depends on (chicken-and-egg).
- The platform RG/account is now a shared dependency whose deletion would affect every project's state — it must be treated as protected infrastructure.
- ~~Secrets still reside in state until the SP-password elimination fast-follow lands; backend hardening is the interim mitigation.~~ Resolved in issue #68: the SP password was removed and CI now uses OIDC federation; no extractable secret lands in state.

## Amendment (2026-05-25): central platform Key Vault + local-container workload identity

Two decisions that **extend** this ADR without breaching its core invariant.

### What changed

1. **A central platform Key Vault `kv-platformy-dev`** is provisioned in `rg-platformy-dev` (RBAC authorization mode), mirroring the `stplatformydev` tfstate pattern: one project-agnostic vault serving every project, long-lived, surviving any single project's teardown. This realizes [ADR-008](ADR-008-secrets-management.md)'s designation of Azure Key Vault as the corporate secrets store.
2. **Local *container* dev authenticates as the scoped Service Principal** (`sp-helloarch-dev`), not via the developer's `az login`. A client secret is provisioned on the SP and stored as `helloarch-sp-client-secret`. `task dev` (`.github/scripts/dev-up.ps1`) uses the developer's `az login` (granted **Key Vault Secrets Officer**) to fetch the secret and inject it into the container environment at launch; the running container uses `EnvironmentCredential` and never depends on `az login`.

### Why the deferral trigger is now met

The original stance deferred Key Vault until "a genuine runtime secret that managed identity cannot cover exists." That condition now holds: a laptop has no managed-identity metadata endpoint, so a local container cannot use a managed identity. To give the local container a **workload** identity — scoped RBAC, production parity with the cloud UAMI — rather than borrowing the developer's full-permission `az login`, a Service Principal client secret is unavoidable, and that is precisely a runtime secret MI cannot cover. Genuine app secrets (`anthropic-api-key`, `gh-token`) reinforce the need for the vault.

### Why the no-secret-in-state invariant still holds

The SP secret is generated **outside Terraform** via `az ad app credential reset` and written straight to Key Vault. Terraform manages the SP *application* but **not** its credentials (no `azuread_application_password` resource), so the secret never enters Terraform state. The hardened-backend rationale above is unaffected.

### Resulting identity model

| Context | Identity to Foundry | Secret |
|---|---|---|
| Native dev (no container) | `az login` → DefaultAzureCredential | none |
| Local container (`task dev`) | Service Principal via `EnvironmentCredential` | SP secret, from `kv-platformy-dev`, injected at launch |
| CI (GitHub Actions) | Service Principal via OIDC federation | none |
| Cloud Container App | UAMI (managed identity) | none |

One code path — `DefaultAzureCredential()` — resolves the environment-appropriate identity in every context; only the credential *source* differs.

### RBAC on the vault

- Developer (`az login`) → **Key Vault Secrets Officer** (create/manage secret values).
- SP and cloud UAMI → **Key Vault Secrets User** (read app secrets at runtime). The SP cannot read its *own* bootstrap secret (it needs the secret to authenticate), so that one value is launch-injected; all other app secrets are read at runtime. This read role is assigned when the first such app secret is stored.

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
