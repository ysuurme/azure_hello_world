# ADR-016: Externalize architecture & capability knowledge to cloud storage

## Status

Accepted (principle); storage placement and AI Search phasing deferred to the implementing issues.

## Context and Problem Statement

The app reads two kinds of content from the local filesystem at `PROJECT_ROOT`:

- the **capabilities corpus** — reusable WAF/technology knowledge scanned by `utils.m_search` and managed by `utils.m_capability_repo` (`PROJECT_ROOT/capabilities`);
- **project architecture artifacts** — the intake template (`config.TEMPLATE_PATH` → `architecture/000_architecture_template.md`) and the approved designs written by `utils.m_persist_design` (`PROJECT_ROOT/designs`).

The container image (`Dockerfile`) copies only `src/` and the built `.venv`. It does **not** copy `capabilities/` or `architecture/`, so in the cloud the `/design` flow degrades to default WAF guidance and a stub intake template (it does not crash — `m_search` and `intake_reviewer` have fallbacks). The `/diagram` flow is unaffected.

Baking this content into the image would fix the symptom but couples *content lifecycle* to *build lifecycle*: every capability or template update would require rebuild → repush → redeploy. The project's standing "knowledge store" vision is that architecture knowledge lives in Azure (Storage + AI Search) and is retrieved/updated by the app at runtime, with the global reusable knowledge base kept separate from project-local artifacts.

## Considered Options

- **Option A — Bake content into the image.** Add `COPY capabilities/ architecture/`.
- **Option B — Leave cloud `/diagram`-only.** Accept degraded `/design`, document it.
- **Option C — Externalize content to cloud storage**, retrieved at runtime via managed identity.

## Decision Outcome

Chosen: **Option C — externalize both the capabilities corpus and the project architecture artifacts to Azure Blob Storage**, retrieved at runtime via `DefaultAzureCredential` (the UAMI in the cloud). Option B is the **interim** until C lands; Option A is rejected as throwaway work that couples content to the build.

Design principles (details deferred to the implementing issues, where the open decisions are HITL):

- **Two stores, by reuse scope.** The **capabilities corpus** is cross-project reusable knowledge → a shared/global knowledge store. The **intake template and generated designs** are project-scoped → a project store (torn down with `rg-helloarch-dev`). This honours the "global knowledge base separate from project-local" constraint.
- **Git authors, blob serves.** Git remains the source of truth for authored knowledge (so changes are reviewed via PR); a publish/sync step writes to blob. Blob **versioning + soft-delete** is the runtime safety net (same hardening pattern as ADR-015 state).
- **Retrieval phased.** Phase 1: app reads blobs directly via the UAMI and caches in container ephemeral storage. Phase 2: reintroduce **Azure AI Search** for semantic retrieval — `m_search` currently *simulates* this and `m_ingest` already has idempotent SHA256-hashed ingestion. Note ADR-013 orphaned the legacy Basic-SKU Search; Phase 2 is a deliberate re-add with its own cost consideration.
- **Access isolation.** The app's UAMI gets data-plane read on the knowledge container only — never the `tfstate` container (different access population; see the storage-layering rationale in ADR-015).

### Positive Consequences

- Capability/template/design updates need no image rebuild or redeploy.
- All revisions and instances share one versioned content source.
- Content is reviewable (git) and recoverable (blob versioning).
- Removes the silent `/design` degradation once Phase 1 lands.

### Negative Consequences

- Runtime now depends on blob availability and a data-plane RBAC grant (mitigated by ephemeral caching).
- A publish/sync step is added between git and blob.
- Phase 2 reintroduces Azure AI Search — added cost and an ingestion pipeline to operate.

## Pros and Cons of the Options

### Option A — Bake into image
- Good, because it immediately restores full `/design` fidelity.
- Bad, because content updates require a rebuild+redeploy; contradicts the knowledge-store vision; throwaway once C lands.

### Option B — Cloud `/diagram`-only (interim)
- Good, because zero work; unblocks the current deployment.
- Bad, because `/design` runs degraded; only acceptable as a documented interim.

### Option C — Externalize to cloud storage
- Good, because content and build lifecycles decouple; matches the knowledge-store north star.
- Good, because git review + blob versioning give controlled, recoverable updates.
- Bad, because more moving parts (publish step, runtime dependency, eventual AI Search cost).
