---
name: ADR-004-iam-provider-selection
description: Use when selecting a self-hosted IAM provider for identity management — internal employees with LDAP/AD, or external customers with multi-tenant SSO requirements
applies_to: "project_type: application, project_type: agent"
---

# ADR-004: IAM Provider Selection

> **Applies to:** `project_type: application` and `project_type: agent` — any project that exposes authenticated endpoints or manages user identity.

## Status
Proposed

## Context and Problem Statement

When a managed SaaS provider (Azure AD, Auth0) is ruled out by data residency, cost, or open-source requirements, a self-hosted IAM provider is needed. The two primary candidates are Keycloak and Zitadel.

## Considered Options

* Keycloak
* Zitadel

## Decision Outcome

Chosen: **Context-dependent** — see decision drivers below.

**Choose Keycloak when:** managing internal employees on a private network with LDAP/AD integration.
**Choose Zitadel when:** managing external customers or B2B tenants where each needs their own SSO and branding.

Both integrate identically with FastAPI via `OAuth2AuthorizationCodeBearer`. IAM server deployment follows `harness` environment standards.

### Confirmation

* Confirm chosen provider matches the identity population (internal employees vs external customers)
* Confirm LDAP/AD integration is only a requirement when Keycloak is chosen
* Confirm FastAPI dependency uses `OAuth2AuthorizationCodeBearer` — not provider-specific auth libraries
* Confirm IAM server provisioned via `harness` Dev Container / environment standards

## Pros and Cons of the Options

### Keycloak

| | |
|---|---|
| **Good** | Enterprise/on-premise/LDAP+AD integration — 10+ year ecosystem |
| **Good** | Gold standard for corporate identity: internal employee SSO, private network |
| **Good** | SAML + Kerberos + legacy AD support |
| **Bad** | Java runtime — higher memory footprint, slower startup |
| **Bad** | Multi-tenancy via Realms — management overhead at scale |

### Zitadel

| | |
|---|---|
| **Good** | Go runtime — low memory, instant startup, Kubernetes-friendly |
| **Good** | Native multi-tenancy for B2B SaaS (thousands of tenant organisations) |
| **Good** | Event-sourced audit log — immutable history of every identity change |
| **Bad** | Smaller ecosystem (but growing) |
| **Bad** | OAuth2 / OIDC / SAML only — no LDAP, Kerberos, or legacy AD |
