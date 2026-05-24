# ADR-013: Dedicated Azure AI Foundry in the project resource group

## Status

Accepted

## Context and Problem Statement

Azure Hello Architect is a hello-world project with two goals: learn cloud deployment end-to-end, and leave behind a clean, self-contained tool. The app authenticates to an Azure AI Foundry project via `AIProjectClient`. Initially (ADR-scaffold in issue #57) the plan reused a central, shared Foundry (`aaif-payg`/`firstProject` in `rg-payg-openai`) and the project resource group held only the Service Principal.

Two competing forces:
- A **central, shared** Foundry minimises duplication and is how a production estate consolidates AI infra across many apps.
- A **dedicated** Foundry in the project's own resource group gives full isolation, clean teardown (`az group delete`), and — crucially for a learning project — forces us to provision the Foundry itself as IaC.

The legacy `infra/` "sentinel" stack also provisioned an unused AI Hub + Project + Search (Basic SKU) in `rg-hobby-ai-dev`, which was dead weight and confusing alongside the project stack.

## Considered Options

- **Option A — Central shared Foundry.** Point the app at `aaif-payg`; project RG holds only app/compute.
- **Option B — Dedicated Foundry in `rg-helloarch-dev`.** Provision a new AIServices account + project + model deployments + SP + RBAC, all in one resource group, as a single Terraform stack.

## Decision Outcome

Chosen: **Option B — dedicated Foundry in `rg-helloarch-dev`** (swedencentral).

The learning objective and "self-contained, portable, cleanly deletable" goal outweigh the minor duplication cost (MaaS model deployments are billed per-token, so there is no idle cost). The two Terraform stacks (`infra/` sentinel + `infra/project/` SP) were consolidated into a single top-level `infra/` stack that provisions everything for the project. The legacy sentinel stack was retired from configuration.

### Positive Consequences

- One `az group delete rg-helloarch-dev` tears down the entire project.
- The Foundry account, project, and model deployments are now codified as IaC (the learning artifact).
- No coupling to shared infrastructure; region-consistent (swedencentral).
- Single source of truth — `infra/` — instead of two overlapping stacks.

### Negative Consequences

- Model deployments and quota are duplicated rather than shared.
- The deployed legacy sentinel resources (notably an Azure AI Search **Basic** SKU, ~fixed monthly cost) are now orphaned and must be destroyed separately.
- The dedicated Foundry was bootstrapped via `az`/REST first; the Terraform stack codifies the verified shape but must be reconciled with the live resources (import or destroy/recreate) before `terraform apply` is the source of truth.

## Pros and Cons of the Options

### Option A — Central shared Foundry
- Good, because no duplication; one place to manage models and quota.
- Good, because fastest path to a working MVP.
- Bad, because it couples a throwaway learning project to shared infra.
- Bad, because it defeats clean teardown and the "package everything for this project" goal.

### Option B — Dedicated Foundry
- Good, because full isolation and clean teardown.
- Good, because we learn to provision Foundry as IaC.
- Bad, because more to provision and minor duplication.
