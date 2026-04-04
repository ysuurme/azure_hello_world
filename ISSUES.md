# 📝 Agile Issue Tracking

> Issues defined here are parsed by `.github/scripts/sync-issues.ps1` and synced to the **@hello_architect** GitHub Project via `task sync`.
> Successfully synced issues are automatically removed from this file to prevent duplication.

## Format

Wrap every issue within ISSUE / END_ISSUE blocks so the parser can harvest them.

---

ISSUE: Implement Semantic Chunking Tuning for RAG Pipeline
**Goal**: Optimize retrieval quality by tuning vector chunk sizes and BM25 coefficients based on observed agent behavior.
**Description**: Once Azure AI Search is provisioned (Terraform issue) and the ingestion pipeline is live (`m_ingest.py`), the default chunking strategy will likely produce suboptimal results. This issue creates evaluation scripts that measure retrieval accuracy and tune semantic configuration to minimize hallucination rates.
**Requirements**:
1. Implement `src/utils/m_ingest.py:ingest_local_markdown()` — walk `/capabilities/`, chunk via Document-Aware Recursive Chunking on natural headers, upload to AI Search with `mergeOrUpload`.
2. Add idempotency: `H(x) = SHA256(Content + Metadata)`, skip upload if hash unchanged.
3. Create an evaluation script comparing retrieval results against known-good capability matches.
4. Parameterize chunk size and BM25 coefficients for iterative tuning.
**Acceptance Criteria**:
- `task ingest` runs the full ingestion pipeline against `/capabilities/`.
- Idempotent: re-running on unchanged files produces zero uploads.
- Evaluation script outputs precision/recall metrics for the test query set.
- Test file added to `/tests`.
END_ISSUE

ISSUE: Add VNet and Private Link Network Isolation for PaaS Services
**Goal**: Enforce network-level blast radius isolation for AI Search and AI Foundry in production.
**Description**: The Terraform infrastructure issue provisions Azure AI Search and Foundry connections but exposes them on public endpoints. Production deployments require VNet integration with Private Endpoints (Private Link) so that AI Search, AI Foundry, and the Container App communicate exclusively over Microsoft's backbone — no public internet traversal.
**Requirements**:
1. Create a VNet with dedicated subnets for AI Search, AI Foundry, and Container Apps in `infra/main.tf`.
2. Add `azurerm_private_endpoint` resources for AI Search and AI Foundry linking to the VNet.
3. Configure Private DNS Zones (`privatelink.search.windows.net`, `privatelink.cognitiveservices.azure.com`) for name resolution.
4. Update the Container App environment to inject into the VNet subnet.
5. Disable public network access on AI Search and Foundry once Private Link is verified.
**Acceptance Criteria**:
- `terraform plan` succeeds with VNet, Private Endpoints, and DNS Zones in the graph.
- AI Search is unreachable from public internet; only accessible via Private Endpoint.
- Container App resolves AI Search and Foundry endpoints via Private DNS.
- Test connectivity from within the VNet validates end-to-end RAG pipeline.
END_ISSUE

ISSUE: Add Terraform Drift Detection Gate to CI Pipeline
**Goal**: Prevent infrastructure drift from going undetected between deployments.
**Description**: The current `pr-checks.yml` validates code quality (lint + test) but does not enforce infrastructure consistency. Adding `terraform plan -detailed-exitcode` as a CI gate ensures that any merged PR containing Terraform changes produces a clean plan — exit code 0 (no changes) or 2 (changes to apply) — and flags unexpected drift before it reaches production.
**Requirements**:
1. Add a `terraform-plan` job to `.github/workflows/pr-checks.yml` triggered on changes to `infra/**`.
2. Configure Azure credentials in GitHub Actions via OIDC federated identity (no stored secrets).
3. Run `terraform init` with the remote backend, then `terraform plan -detailed-exitcode`.
4. Fail the PR if exit code is non-zero and changes are unexpected.
5. Post plan output as a PR comment for review transparency.
**Acceptance Criteria**:
- PRs modifying `infra/` trigger the Terraform plan job.
- Plan output is visible as a PR comment.
- Unexpected drift (exit code 1) blocks merge.
- GitHub Actions uses OIDC — no `AZURE_CLIENT_SECRET` stored in repo secrets.
END_ISSUE

