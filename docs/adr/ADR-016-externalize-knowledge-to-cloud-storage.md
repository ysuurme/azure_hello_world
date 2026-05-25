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

- **Two containers in the platform storage account, by reuse scope.** Both stores live in the platform account (`stplatformydev` for dev, `stplatformyprod` for prod — environment is the account boundary, per ADR-015 layering), as distinct, clearly-named containers: a `capabilities` container (cross-project reusable knowledge, kept separate from project-local artifacts) and a `designs` container (project-scoped intake template + generated designs, keyed by a project prefix, e.g. `helloarch/`). Trade-off accepted deliberately: project designs now persist beyond `az group delete rg-helloarch-dev` — generated outputs survive teardown of the ephemeral compute, rather than dying with it.
- **Blob is the version control.** Content is managed directly in blob, with **versioning + soft-delete** providing history and rollback. DEV and PRD are separated by environment (separate platform accounts), not by git branches. Accepted trade-off: knowledge edits are not PR-reviewed; in exchange, content is environment-scoped, directly editable, and independently versioned. Operators inspect and validate content with a blob viewer (Azure Storage Explorer, the VS Code Azure Storage extension, or the portal Storage browser).
- **Retrieval phased.** Phase 1: app reads blobs directly via the UAMI and caches in container ephemeral storage. Phase 2: reintroduce **Azure AI Search** for semantic retrieval — `m_search` currently *simulates* this and `m_ingest` already has idempotent SHA256-hashed ingestion. Note ADR-013 orphaned the legacy Basic-SKU Search; Phase 2 is a deliberate re-add with its own cost consideration.
- **Access isolation.** The app's UAMI gets data-plane read on the knowledge container only — never the `tfstate` container (different access population; see the storage-layering rationale in ADR-015).

### Positive Consequences

- Capability/template/design updates need no image rebuild or redeploy.
- All revisions and instances share one versioned content source.
- Content is environment-scoped (dev/prd by account) and recoverable via blob versioning; inspectable with a blob viewer.
- Removes the silent `/design` degradation once Phase 1 lands.

### Negative Consequences

- Runtime now depends on blob availability and a data-plane RBAC grant (mitigated by ephemeral caching).
- Knowledge edits bypass PR review (blob is the VC); versioning + soft-delete and disciplined editing compensate.
- Phase 2 reintroduces Azure AI Search — added cost and an ingestion pipeline to operate.

## Amendment (2026-05-25): diagrams are project-scoped, not platform

A storage-scope boundary was drawn (companion to ADR-015's central Key Vault amendment):

- **Platform storage** (`stplatformydev`, `rg-platformy-dev`) holds **cross-board knowledge** reusable across projects: the capabilities corpus (as decided above) and centrally-maintained ADRs / validated implementation patterns.
- **Project storage** — a dedicated account **`sthelloarchdev` in `rg-helloarch-dev`** (container `diagrams`) — holds **project-scoped working artifacts**: the Diagram Studio trio (`brief.json` + `source.d2` + `render.svg`), keyed by a stable slug.

This **diverges from this ADR's original "designs in the platform account" placement for the diagram artifact specifically.** Diagrams are working artifacts ("render many, keep a few"), not cross-project knowledge, so they live with the project. **Accepted trade-off:** the project storage account is destroyed by `az group delete rg-helloarch-dev` (ADR-013) — the inverse of the survive-teardown property this ADR sought for designs. High-quality *designs* may later be elevated into platform persistent storage; that elevation is out of scope for now.

Access stays secretless and hardened (consistent with ADR-015): account keys disabled, the backend identity (SP locally, UAMI in cloud) holds **Storage Blob Data Contributor** on the project account, and **blob versioning + soft-delete** provide history — realizing "blob is the version control" for the build-forward (multi-session) flow. The capabilities corpus and the `/design` template/designs externalization (issue #70) are unaffected and remain platform-scoped.

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
