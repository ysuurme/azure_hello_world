# 📝 Agile Issue Tracking

> Issues defined here are parsed by `.github/scripts/sync-issues.ps1` and synced to the **@hello_architect** GitHub Project via `task sync`.
> Successfully synced issues are automatically removed from this file to prevent duplication.

## Format

Wrap every issue within blocks so the parser can harvest them.

---

ISSUE: Provision Azure AI Search via Terraform
**Goal**: Establish the vector store infrastructure required for the Sentinel's RAG pipeline.
**Description**: The Architecture Sentinel requires Azure AI Search (Basic SKU with free Semantic Search) to serve as the vector store for capability document retrieval. This infrastructure must be provisioned via Terraform with Entra ID authentication — no API keys.
**Requirements**:
1. Add `azurerm_search_service` resource (Basic SKU) to `infra/main.tf`.
2. Add `azapi_resource` for `search_connection` linking Search to AI Hub via `authType = "ProjectManagedIdentity"`.
3. Introduce the `capability_host` resource for Agent Service tool execution.
4. Configure Terraform remote backend on Azure Blob Storage.
**Acceptance Criteria**:
- `terraform plan -detailed-exitcode` exits cleanly with no drift.
- Search Service is accessible via Managed Identity from the AI Foundry project.
- No hardcoded API keys in any `.tf` file.
END_ISSUE

ISSUE: Implement Trivy Container Security Scanning
**Goal**: Prevent vulnerable container images from reaching the registry.
**Description**: The Dockerfile follows a Multi-Stage Rootless pattern but currently lacks automated vulnerability scanning. Trivy must gate the image push to ensure no critical CVEs ship to production.
**Requirements**:
1. Add Trivy scan step to the CI pipeline (GitHub Action or Taskfile task).
2. Configure Trivy to fail on CRITICAL and HIGH severity vulnerabilities.
3. Output scan results as a GitHub Actions artifact for review.
**Acceptance Criteria**:
- `task docker:scan` runs Trivy against the built image locally.
- CI pipeline blocks PR merge if CRITICAL vulnerabilities are detected.
- Scan report is downloadable from the Actions tab.
END_ISSUE

ISSUE: Enforce DefaultAzureCredential Across All Clients
**Goal**: Guarantee seamless identity transition from local development to Azure Container Apps.
**Description**: While the agent factory uses `DefaultAzureCredential`, some utility modules may still contain direct credential instantiation. A full audit ensures every Azure SDK client inherits identity from the environment consistently.
**Requirements**:
1. Audit `src/utils/` for any direct credential construction outside `DefaultAzureCredential`.
2. Ensure `ClientManager` in `m_ai_client.py` is the single credential source.
3. Add integration test verifying credential passthrough from orchestrator to tools.
**Acceptance Criteria**:
- `grep -r "api_key\|AzureKeyCredential" src/` returns zero matches.
- All Azure SDK calls route through `ClientManager`.
- Test file added to `/tests`.
END_ISSUE

ISSUE: Add Application Insights Observability to Maker-Checker Loop
**Goal**: Enable production monitoring of the agent's reasoning traces and decision paths.
**Description**: The Maker-Checker loop currently logs locally via `m_log.py`. Application Insights integration will expose reasoning traces, tool invocations, and latency metrics to the Azure Portal for Day-2 operations.
**Requirements**:
1. Add `azure-monitor-opentelemetry` to project dependencies via `uv add`.
2. Create `src/utils/m_telemetry.py` wrapping OpenTelemetry instrumentation.
3. Instrument the `AgenticOrchestrator` state transitions (INTAKE → GENERATION → COMPLETE).
4. Expose trace IDs in Streamlit UI for debugging.
**Acceptance Criteria**:
- Traces appear in Application Insights within 60 seconds of agent invocation.
- Each orchestrator state transition is a distinct span.
- Test file verifying telemetry facade initialization added to `/tests`.
END_ISSUE
