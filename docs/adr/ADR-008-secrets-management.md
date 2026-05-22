---
name: ADR-008-secrets-management
description: Documents the secrets architecture per environment — which stores hold credentials for local dev, CI, and production, and how to verify no secrets leak into source control
applies_to: "all"
---

# ADR-008: Secrets Management

> **Applies to:** all project types — every generated project ships credentials it must keep out of source control.

## Status
Accepted

## Context and Problem Statement

Every project in this template requires at minimum two credentials: a GitHub token (`GH_TOKEN`)
for the Orchestrator Workflow and an Anthropic API key (`ANTHROPIC_API_KEY`) for AI-backed features.
Without a documented secrets architecture, developers must infer the correct store per environment
from README comments and workflow headers. This creates configuration drift, accidental commits
of `.env` files, and inconsistent rotation practices across environments.

The prerequisite `.gitignore` changes (issue #17) already exclude `.env` and
`.copier-answers.yml` from source control. This ADR records the per-environment secret store
decision so it cannot be re-debated in future refine sessions.

Related: ADR-004 (IAM Provider Selection) governs identity management for end-user
authentication. This ADR governs service-to-service and developer credentials — a
complementary concern. When a secret grants identity (e.g., a service-account key used as an
IAM principal), consult ADR-004 for the provider context.

## Considered Options

* **Option A — GitHub Secrets for dev/CI; cloud-native secret manager for production**
* **Option B — HashiCorp Vault for all environments**
* **Option C — Environment variables injected at deploy time (no dedicated store)**

## Decision Outcome

Chosen: **Option A** — GitHub Secrets for dev/CI; Azure Key Vault (corporate) or GCP Secret
Manager (personal) for production runtime.

**Rationale:** GitHub Secrets are zero-infrastructure for CI and fully integrated with GitHub
Actions. Cloud-native secret managers (Azure Key Vault / GCP Secret Manager) provide workload
identity federation at production runtime — no secret value is stored in the repository or
host environment. Option B (Vault) introduces a self-hosted dependency not justified at this
scale. Option C provides no audit trail or rotation support.

### Secrets store by environment

| Environment | Store |
|---|---|
| Local dev | `.env` file (git-ignored) |
| CI (GitHub Actions) | GitHub Actions Secrets |
| Production — corporate | Azure Key Vault |
| Production — personal | GCP Secret Manager |

### Confirmation

* Run `git grep -rP "ANTHROPIC_API_KEY\s*=" src/` — must return no matches; any API key
  assignment belongs in `.env`, not in source files.
* Run `git ls-files "*.env"` — must return empty; `.env` files must never be tracked by git.

## Pros and Cons of the Options

### Option A — GitHub Secrets + cloud-native secret manager

| | |
|---|---|
| **Good** | Zero infrastructure for CI — GitHub Secrets are built-in |
| **Good** | Cloud-native stores support workload identity federation (no static secrets at runtime) |
| **Good** | Per-environment isolation — dev, CI, and prod each use a different store |
| **Bad** | Two production stores to maintain (Azure KV for corporate, GCP SM for personal) |

### Option B — HashiCorp Vault for all environments

| | |
|---|---|
| **Good** | Single pane of glass across all environments |
| **Good** | Fine-grained policy, dynamic secrets, and audit log |
| **Bad** | Self-hosted operational burden not justified at project inception |
| **Bad** | Adds a hard infrastructure dependency before the project has users |

### Option C — Environment variables injected at deploy time

| | |
|---|---|
| **Good** | No external dependency |
| **Bad** | No audit trail, no rotation support, no access control |
| **Bad** | Secrets passed as plain text through CI logs if not carefully masked |
