---
name: design-architecture
description: Use when tasked with designing a new feature, establishing domain models, structuring a data pipeline, or defining architectural boundary interactions
---

# Architecture Design Protocol (Senior Educational Architect)

## Overview
This skill acts as the bedrock for modern Python applications. By prioritizing the Domain over the delivery mechanism, it ensures business logic is completely isolated from vendor lock-in, cloud idioms, and external frameworks. 

**Scope Exclusivity:** This skill governs the **macro-level structure of the system and architectural boundaries**. It is strictly mutually exclusive from micro-level script syntax or individual code reviews.

**REQUIRED BACKGROUND:** As a "Development Skill," this process mandates the TDD workflow outlined in `write-skills/SKILL.md`.

## When to Use
- **Trigger:** Asked to plan a new sub-system, API endpoint, or feature set.
- **Trigger:** Asked to refactor a "Big Ball of Mud" codebase into modular components. 
- **Trigger:** Asked to map out data flows between microservices or external cloud resources.

## Core Process: The Sentinel Maker/Checker Loop

Architecture cannot be drafted linearly. You must execute a cyclic "Maker-Checker" dialogue before finalizing structural plans:
1. **The Maker**: Draft the proposed object layout and boundary map.
2. **The Checker**: Immediately critique your own Maker proposal specifically on **Security Vulnerabilities** and **Operational Cost Thresholds**.
3. **The TDD Edge Requirement**: You must define the *testable boundaries* of the Domain before writing any logic. (What happens when the external payload is malformed? What is the fail-state?)

## Core Hard Constraints (Red Flags)

You MUST reject any architecture that violates the following non-negotiable paradigms:

### 1. Hexagonal & Clean Architecture (Dependency Injection)
- **Dependency Flow**: The dependency direction must point strictly inward toward the Domain Core. 
- The Domain cannot import from databases, FastAPIs, or specific cloud SDKs.
- **Ports & Adapters**: Expose external requirements via Abstract Base Classes (`abc.ABC`) or `typing.Protocol` (Ports). Concrete implementations (Adapters) inject outward.

### 2. Domain-Driven Design (DDD) Types
- **Entities**: Business logic with identity. Map using `pydantic` models or `dataclasses` with explicit ID fields.
- **Value Objects**: Immutable attributes. Enforce `frozen=True` dataclasses.
- **The Thin Mediator**: The Application/Use Case layer must contain ZERO business logic. It strictly orchestrates data retrieval and execution commands.

### 3. Data Flow & The Zero-Artifact Policy
- **Zero Intermediate Artifacts**: Runtimes are strictly prohibited from writing temporary CSVs, JSONs, or intermediate text files to disk. Volatile state belongs in memory; persistent state belongs in a centralized SQL Database or secure blob storage.
- **Data Trust Tiering (Medallion)**: Isolate raw IO (Raw) from structurally validated domains (Bronze/Silver/Gold). System invariants (e.g., Target verification) act as hard gates that trigger errors before advancing.
- **Bounded Contexts**: Use directory structure and Anti-Corruption Layers (ACLs) to logically separate domains (e.g., Billing User vs. Support User). Do not leak models across boundaries.

### 4. Vendor Neutrality & Telemetry
Avoid supply-chain risk and vendor lock-in.
- Use `SQLAlchemy` (ORM/Core) over raw vendor database drivers.
- Use `OpenTelemetry` standards over proprietary cloud logging configurations.
- Use a single, unified Telemetry Facade across the whole application, disabling fragmented `print` and `logging.basicConfig()` usages.

### 5. Architectural Drift Prevention
Software architecture can drift from its intended Clean/Hexagonal structure. You must actively prevent "Architectural Drift"—instances where business logic begins to leak into API controllers or the Domain layer starts importing from external Infrastructure. The resulting "Antigravity" software must remain lightweight, agile, and cloud-fluid.

## Technical Appendix: Structural Implementation Map
Use structured patterns when defining the translation between theoretical DDD concepts and their physical cloud equivalents:

| Requirement | Implementation Pattern | Multi-Cloud Adaptation |
|-------------|------------------------|------------------------|
| **Persistence** | Repository Pattern (DDD) | SQL (GCP Cloud SQL) vs NoSQL (Azure Cosmos) |
| **Async Tasks** | Domain Events | Pub/Sub (GCP) vs Service Bus (Azure) |
| **Observability**| OpenTelemetry SDK | Cloud Monitoring (GCP) vs Azure Monitor |

## The Output Format: Diagram-First Communication

When you act as the Senior Educational Architect to propose a new design, you MUST provide a visual context map. 

Do not just output raw text. **You are required to output a declarative Diagram**.

**Primary format:** D2 Graph (`d2` code block) with the `theme: sketch` property enabled to represent whiteboarding.
**Fallback format:** If D2 is unsupported by the host, use standard `mermaid` graphs.

### Output Structure:
1. `[The Sentinel Design Diagram]` (D2/Mermaid visual context mapping the Ports, Adapters, and Domains).
2. `[Maker Proposal]` (Explanation of the Entities and Bounded Contexts).
3. `[Checker Critique: Security & Cost]` (An aggressive assessment of your own proposal).
4. `[Testable Invariants (TDD)]` (How will the Domain fail gracefully?).
