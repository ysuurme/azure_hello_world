# Security

This document describes the secrets required by this project, the rationale behind each,
and how to configure them per environment.

---

## GH_TOKEN

**Purpose:** Authenticates GitHub CLI (`gh`) calls within the Orchestrator Workflow — creating
issues, moving kanban cards, and mutating GitHub Projects v2 boards.

**Why classic PAT, not fine-grained PAT:** GitHub Projects v2 mutations (add/move/archive
project items) require the `project` OAuth scope. Fine-grained PATs do not expose this scope;
they are scoped to repository permissions only. Until GitHub extends fine-grained PATs to
cover Projects v2, a classic PAT with `project`, `read:org`, `repo`, `user`, `workflow` scopes is the only supported option. Each scope earns its place: `project` for kanban board mutations, `repo` for issue/PR/commit operations, `workflow` for any PR that touches `.github/workflows/*.yml` (the orchestrator self-edits CI on occasion), `read:org` for org-owned projects, `user` for identity calls (`gh api user`).

**Accepted risk:** Classic PATs carry broader permissions than fine-grained PATs. Mitigations:
- Scope the token to `project`, `read:org`, `repo`, `user`, `workflow` only — no `admin:*`, `delete_repo`, or `write:packages`.
- Never share the token across projects; generate one per repository.
- Rotate on the schedule below.

**Rotation guidance:**
1. Open GitHub → Settings → Developer Settings → Personal access tokens → Tokens (classic).
2. Generate a new token scoped to `project`, `read:org`, `repo`, `user`, `workflow`.
3. Copy the new token value.
4. Update the secret in every environment (see table below).
5. Verify the Orchestrator Workflow completes a successful kanban-lane move.
6. Revoke the old token.

---

## ANTHROPIC_API_KEY

**Purpose:** Authenticates calls to the Anthropic Claude API made by agent skills and any
AI-backed endpoints in this project.

**Scope:** One key per project is sufficient. Do not share a key across multiple production
services — per-service keys make compromise blast-radius containment and rotation easier.

**Rotation guidance:**
1. Open console.anthropic.com → API Keys.
2. Create a new key and label it with the project name and date (e.g., `my-project-2026-05`).
3. Copy the new key value.
4. Update the secret in every environment (see table below).
5. Run `uv run pytest` against the staging environment to confirm the new key is active.
6. Delete the old key from the Anthropic console.

---

## Secrets Architecture by Environment

| Secret | Local dev (`.env`) | CI (GitHub Actions) | Production — corporate | Production — personal |
|---|---|---|---|---|
| `GH_TOKEN` | `.env` (git-ignored) | GitHub Actions Secret | Azure Key Vault | GCP Secret Manager |
| `ANTHROPIC_API_KEY` | `.env` (git-ignored) | GitHub Actions Secret | Azure Key Vault | GCP Secret Manager |
| `CLAUDE_CODE_OAUTH_TOKEN` | Not applicable — developer credential | GitHub Actions Secret | N/A — developer credential | N/A — developer credential |

**Local dev:** Copy `.env.example` to `.env` and populate values. The `.env` file is
git-ignored and must never be committed.

**CI:** Store secrets under the repository's Settings → Secrets and variables → Actions.
Reference them in workflows as `${{ secrets.SECRET_NAME }}`.

**Production — corporate:** Retrieve secrets from Azure Key Vault at runtime via the
workload-identity federation configured in the deployment pipeline. No secret value is
ever stored in the repository or environment variables of the host.

**Production — personal:** Retrieve secrets from GCP Secret Manager at runtime via the
service account attached to the Cloud Run or GCE instance. No secret value is stored
in the repository.

---

## Orchestrator Credentials

The orchestrator is a label-driven pipeline running on a self-hosted GitHub Actions runner on
the developer's machine. When an issue receives the `agent:backlog` label, the runner executes
a full PowerShell pipeline: **Refine → Develop → PR → Review loop → Squash-merge →
CONTEXT.md update**. Two secrets drive the pipeline at runtime.

### Pipeline secrets

| Secret | Role in pipeline |
|---|---|
| `GH_TOKEN` | Authenticates all `gh` CLI calls — creating/updating issues, moving kanban cards, opening PRs, and squash-merging |
| `CLAUDE_CODE_OAUTH_TOKEN` | Authenticates all `claude` CLI calls — Refine, Develop, Review, commit-message generation, and post-merge CONTEXT.md update |

### CLAUDE_CODE_OAUTH_TOKEN

**Purpose:** Authenticates every `claude -p` / `claude --print` invocation in the pipeline.
Used in all five phases:

- **Refine** — structures the issue body and assigns estimate/priority
- **Develop** — runs Claude Code non-interactively to implement requirements and verify with `uv run pytest`
- **Review** — agent self-review of the PR diff against acceptance criteria
- **Commit-message** — generates a conventional commit message from the staged diff
- **Context update** — patches `CONTEXT.md` after the PR is squash-merged

**How to obtain:**
1. Open claude.ai → click your profile → **Settings**.
2. Navigate to the **Claude Code** tab.
3. Under **OAuth Token**, click **Generate** (or **Regenerate** to rotate).
4. Copy the displayed token immediately — it is not shown again.

**Accepted risk:** The token grants full Claude Code CLI access under your Anthropic account.
Mitigations:
- Store the token exclusively as a GitHub Actions Secret — never in `.env` or committed files.
- Rotate on the schedule below.

**Rotation guidance:**
1. Open claude.ai → Settings → Claude Code → OAuth Token → **Regenerate**.
2. Copy the new token value.
3. Update the `CLAUDE_CODE_OAUTH_TOKEN` secret in GitHub: Settings → Secrets and variables → Actions.
4. Verify the next orchestrator run completes without a `claude` authentication error.
5. The old token is invalidated automatically on regeneration.

### Self-hosted runner

The `implement` job requires a self-hosted runner registered with the `gha-project` label
(see `runs-on: [self-hosted, gha-project]` in `.github/workflows/orchestrator.yml`). The
runner must have `uv`, `claude` (Claude Code CLI), `git`, and `gh` pre-installed.

- **Start:** `task runner` — starts the runner in the foreground; press Ctrl+C to interrupt.
- **Graceful stop:** `task runner OFFLINE=1` — sends a drain signal; the runner finishes any
  in-progress job before exiting.

### AFK operation checklist

One-time setup steps for a freshly generated project:

1. **Create the repository** — push the generated project to GitHub.
2. **Create a GitHub Project (v2)** — add a Status field (single-select) with at least four
   options: Backlog, Implementing, Review, Merged. Optionally add Estimate (number) and
   Priority (single-select) fields.
3. **Populate `.env`** — copy `.env.example` to `.env` and set:
   - `GH_TOKEN` — your classic PAT with `project`, `read:org`, `repo`, `user`, `workflow` scopes
   - `KANBAN_PROJECT_NUMBER` — the project number from the GitHub Project URL
   - `KANBAN_PROJECT_OWNER` — your GitHub username or organisation
4. **Add GitHub Actions Secrets** — in repository Settings → Secrets and variables → Actions,
   create:
   - `GH_TOKEN` — the same classic PAT as above
   - `CLAUDE_CODE_OAUTH_TOKEN` — obtained from claude.ai → Settings → Claude Code
5. **Run project setup** — `task setup` — queries the GitHub Project for field/option IDs
   and writes them to `.env` and as GitHub Actions repository variables.
6. **Register the self-hosted runner** — follow the setup wizard at
   `github.com/<org>/<repo>/settings/actions/runners/new`. During registration, add the
   custom label `gha-project` so the `implement` job can target this runner.
7. **Verify runner connectivity** — in GitHub → Settings → Actions → Runners, confirm the
   runner status shows **Idle**.
8. **Start the runner** — `task runner` — keep the terminal open while AFK operation is active.
9. **Sync issues** — `task sync` — pushes the local `ISSUES.md` backlog to GitHub Issues and
   applies the `agent:backlog` label to ready items.
10. **Trigger the first run** — apply the `agent:backlog` label to any open issue; the
    orchestrator picks it up and runs the full implement → review → merge pipeline.

---

## Deployment Credentials

The `deploy.yml` workflow deploys the container image built by `build.yml` to either
Azure Container Apps or GCP Cloud Run. The target cloud is selected by the repository
variable `DEPLOY_TARGET` (`azure` or `gcp`), set once at project setup. Both jobs
authenticate via **Workload Identity Federation (WIF)** — no service principal secret
or service account JSON key is ever stored in the repository.

### Required secrets and variables

| Cloud | Repository variables | Repository secrets |
|---|---|---|
| Azure | `DEPLOY_TARGET=azure`, `AZURE_CONTAINER_APP_NAME`, `AZURE_RESOURCE_GROUP` | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` |
| GCP   | `DEPLOY_TARGET=gcp`, `GCP_CLOUD_RUN_SERVICE`, `GCP_REGION` | `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT` |

Variables live under **Settings → Secrets and variables → Actions → Variables**.
Secrets live under **Settings → Secrets and variables → Actions → Secrets**.

### Provisioning WIF for Azure

> **HITL — human action required.** This procedure cannot run from inside CI; it
> requires Owner or User Access Administrator on the target subscription. Perform
> it once, manually, after `deploy.yml` lands on `main`. The repository secrets
> and variables produced in steps 4–5 are what `deploy.yml` consumes at runtime.

1. **Create an Entra ID app registration**
   ```bash
   az ad app create --display-name "github-actions-<repo>"
   APP_ID=$(az ad app list --display-name "github-actions-<repo>" --query "[0].appId" -o tsv)
   az ad sp create --id "$APP_ID"
   ```
2. **Grant the service principal contributor on the resource group**
   ```bash
   SUB_ID=$(az account show --query id -o tsv)
   az role assignment create \
     --assignee "$APP_ID" \
     --role contributor \
     --scope "/subscriptions/$SUB_ID/resourceGroups/<AZURE_RESOURCE_GROUP>"
   ```
3. **Add a federated credential trusting this GitHub repository** (one per environment
   you intend to deploy to — repeat for `staging` and `production`):
   ```bash
   az ad app federated-credential create --id "$APP_ID" --parameters '{
     "name": "github-<repo>-staging",
     "issuer": "https://token.actions.githubusercontent.com",
     "subject": "repo:<owner>/<repo>:environment:staging",
     "audiences": ["api://AzureADTokenExchange"]
   }'
   ```
4. **Record the three identifiers as GitHub Actions secrets**:
   - `AZURE_CLIENT_ID` — `$APP_ID`
   - `AZURE_TENANT_ID` — `az account show --query tenantId -o tsv`
   - `AZURE_SUBSCRIPTION_ID` — `$SUB_ID`
5. **Record the deployment targets as repository variables**:
   - `DEPLOY_TARGET=azure`
   - `AZURE_CONTAINER_APP_NAME` — the Container App name
   - `AZURE_RESOURCE_GROUP` — the resource group containing the Container App
6. **Allow the Container App to pull the GHCR image** — either make the GHCR package
   public, or configure registry credentials on the Container App (`az containerapp
   registry set --server ghcr.io --username <user> --password <PAT>`). A PAT with
   `read:packages` scope is sufficient.

### Provisioning WIF for GCP

> **HITL — human action required.** This procedure cannot run from inside CI; it
> requires `roles/iam.workloadIdentityPoolAdmin` and `roles/iam.serviceAccountAdmin`
> on the target project. Perform it once, manually, after `deploy.yml` lands on
> `main`. The repository secrets and variables produced in steps 4–5 are what
> `deploy.yml` consumes at runtime.

1. **Create a workload identity pool and OIDC provider for GitHub**
   ```bash
   PROJECT_ID=<gcp-project-id>
   gcloud iam workload-identity-pools create "github-pool" \
     --project="$PROJECT_ID" --location="global" \
     --display-name="GitHub Actions Pool"
   gcloud iam workload-identity-pools providers create-oidc "github-provider" \
     --project="$PROJECT_ID" --location="global" \
     --workload-identity-pool="github-pool" \
     --display-name="GitHub OIDC" \
     --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
     --issuer-uri="https://token.actions.githubusercontent.com" \
     --attribute-condition="assertion.repository=='<owner>/<repo>'"
   ```
2. **Create a service account for the deploy workflow and grant Cloud Run deploy roles**
   ```bash
   gcloud iam service-accounts create github-deploy \
     --project="$PROJECT_ID" --display-name="GitHub Actions Deploy"
   SA_EMAIL="github-deploy@$PROJECT_ID.iam.gserviceaccount.com"
   gcloud projects add-iam-policy-binding "$PROJECT_ID" \
     --member="serviceAccount:$SA_EMAIL" --role="roles/run.admin"
   gcloud projects add-iam-policy-binding "$PROJECT_ID" \
     --member="serviceAccount:$SA_EMAIL" --role="roles/iam.serviceAccountUser"
   ```
3. **Bind the GitHub repository to the service account**
   ```bash
   PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
   gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
     --project="$PROJECT_ID" \
     --role="roles/iam.workloadIdentityUser" \
     --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/<owner>/<repo>"
   ```
4. **Record the WIF provider resource name and service account email as secrets**:
   - `GCP_WORKLOAD_IDENTITY_PROVIDER` — `projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
   - `GCP_SERVICE_ACCOUNT` — `$SA_EMAIL`
5. **Record the deployment targets as repository variables**:
   - `DEPLOY_TARGET=gcp`
   - `GCP_CLOUD_RUN_SERVICE` — the Cloud Run service name
   - `GCP_REGION` — the region the service runs in (e.g., `europe-west1`)
6. **Allow Cloud Run to pull the GHCR image** — either make the GHCR package public,
   or mirror the image to Artifact Registry. Cloud Run does not support pulling from a
   private GHCR registry with credentials at runtime; mirroring is the supported path.

### Running the GHCR image locally for manual testing

Pull and run the same image the pipeline will deploy. Useful for reproducing a
production issue or smoke-testing before triggering `deploy.yml`.

1. **Authenticate Docker to GHCR** (only required while the package is private):
   ```bash
   echo "$GH_TOKEN" | docker login ghcr.io -u <github-username> --password-stdin
   ```
   The `GH_TOKEN` PAT needs `read:packages` scope.
2. **Pull the image** — use a pinned SHA tag for reproducibility, or `latest` for the
   most recent build on `main`:
   ```bash
   docker pull ghcr.io/<owner>/<repo>:<image_tag>
   ```
3. **Run the container**:
   ```bash
   docker run --rm -it \
     --env-file .env \
     -p 8000:8000 \
     ghcr.io/<owner>/<repo>:<image_tag>
   ```
   Adjust the published port to match whatever the application binds to. `--env-file`
   wires the same secrets used in local dev — never bake secret values into a `docker
   run` command line, as they leak into shell history and process listings.
