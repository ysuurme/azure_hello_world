---
name: design-infrastructure
description: Use when tasked with creating Dockerfiles, building Terraform modules, configuring CI/CD pipelines, mapping cloud storage dynamics, or defining multi-cloud infrastructure architecture
---

# Infrastructure Orchestration Protocol (Senior Educational Architect)

## Overview
This skill governs the execution environment of our systems. While the Python Domain (`design-architecture.md`) captures business value, this skill protects the delivery mechanism and cloud orchestration. It ensures all pipelines, containers, and resources prioritize **Least Privilege**, **Blast Radius Minimization**, and **Cloud Fluidity**.

**Scope Exclusivity:** This skill exclusively governs the **delivery mechanism, container lifecycle, and cloud orchestration state**. It is strictly mutually exclusive from any Python business logic or system domain mapping.

## When to Use
- **Trigger:** Asked to construct a `Dockerfile` for Python workloads.
- **Trigger:** Asked to set up Infrastructure as Code (e.g., Terraform main.tf / modules).
- **Trigger:** Asked to construct CI/CD workflows for deployments.

## Core Process: The Infrastructure Maker/Checker Loop

1. **The Maker**: Draft the proposed Terraform configuration, Dockerfile layers, or Azure ARM templates.
2. **The Checker**: Immediately critique your own Maker proposal specifically against **Least-Privilege Networking**, **Container Blast Radius**, and **Cost Anomalies**.
3. **The TDD Edge Requirement**: You must define how the infrastructure state will be validated before deployment. (e.g., How is Terraform drift detected in CI? Is the image scanned by Trivy, or is the pilot exempted?)

## Multi-Cloud Placement Strategy

Infrastructure must remain "Cloud Fluid" by prioritizing open-source Python abstractions (`azure-storage-blob`, `google-cloud-storage`). However, when placing workloads, the architect MUST justify the chosen provider based on strategic advantages rather than habit:

* **Azure (Default State Backend):** Due to strict technology footprint synergy (e.g., VSCode integrations, GitHub native paths), **Azure Blob Storage is the preferred default** for locking Terraform state (using Conditional Leases and Service Principals). Preferred for Hybrid Benefit, Enterprise Compliance (Entra ID), and generic web workloads. 
* **GCP:** Reserve explicitly for ML-first, BigQuery, and extreme data-gravity environments via Vertex AI.
* **Storage Latency Mapping:** Cross-cloud infrastructure MUST note that archiving behaviors are different. GCP provides instantaneous millisecond retrieval from Archive, whereas Azure Blob requires a multi-hour asynchronous "Request/Wait" rehydration process that the Python host must natively handle.

## Core Hard Constraints (Red Flags)

Reject any infrastructure proposal that violates these non-negotiable paradigms:

### 1. Azure Identity & Networking Standards
- **Compute Identity**: Default to **System-Assigned Managed Identities** for all app compute nodes to eliminate credential rotation entirely. Use **Service Principals** (App Registrations) strictly for external, headless automation scripts (like CI/CD Terraform pipelines).
- **Secrets Management**: Never inject raw secrets as `ENV` variables in a Dockerfile or standard app configuration. Secrets MUST be fetched dynamically from **Azure Key Vault** using the host's Managed Identity. 
- **Network Isolation**: Compute instances MUST be deployed inside a Virtual Network (VNet). Absolute ban on assigning Public IPs directly to VMs/App Services unless brokered via Front Door/App Gateway. Use **Azure Private Link (Private Endpoints)** when integrating PaaS services like Key Vault or CosmosDB to prevent internal traffic from traversing the public internet.

### 2. Terraform Integrity
- **Modular State**: Extract logic into single-purpose DRY modules.
- **Remote Lock Ban**: Local state execution is banned. State MUST be encrypted, remote, and locked via Azure Storage.
- **Drift Management**: Mandate the `terraform plan -detailed-exitcode` flag in pipelines (exit code 2 dictates a drift diff needing immediate attention).

### 3. Docker "Blast Radius" Minimization
- **Multi-Stage Optimization**: Use a "Builder" image to install compilers/C-extensions. The final runtime layer must NEVER inherit compilers like `gcc`, `git`, or shells to prevent lateral movement.
- **Rootless Policy**: Images must create a dedicated user and swap context via the `USER` directive. Executing as `root` is an immediate failure.
- **Base Image Defaults**: Default to `python:3.12-slim` for standard production workloads. Default to Distroless Python (`gcr.io/distroless/python3`) for maximum security environments lacking shells entirely.
- **Health & Scanners**: Images MUST define `HEALTHCHECK` pinging a `/health` endpoint using pure standard library (`urllib`). **Trivy** vulnerability scans prior to deployment are *highly recommended*, though they are not a hard requirement to allow flexibility for short-lived, non-sensitive pilot initiatives.

## Technical Appendix: Infrastructure Implementation Map
Use these strict multi-cloud deployment mappings when generating codified infrastructure or delivery templates:

| Requirement | Implementation Pattern | Multi-Cloud Adaptation |
|-------------|------------------------|------------------------|
| **Auth & Identity** | OpenID Connect (OIDC) | Workload Identity (GCP) vs Managed Identity (Azure) |
| **Orchestration** | K8s Deployment | GKE (GCP) vs AKS (Azure) |
| **IaC State** | Remote Locked Backend | GCS Bucket (GCP) vs Blob Container (Azure) |
| **CI/CD Drift** | Scheduled Plan Runs | Exit Code 2 triggers Alerting/Issue creation |

## The Output Format: Infrastructure Map First

When acting as the Senior Educational Architect for infrastructure, your output must flow as:

1. `[Strategic Cloud Mapping]` (Justifying the Azure/GCP resource positioning and Auth bounds).
2. `[Maker Proposal]` (The Terraform blocks, Dockerfile payload, or YAML pipeline).
3. `[Checker Critique: Least Privilege & Blast Radius]` (Your aggressive security self-audit).
4. `[TDD Invariants]` (Defining the Terraform drift exit-code bounds and stating whether a Trivy scan gate applies).
