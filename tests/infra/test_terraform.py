"""Content tests for the consolidated Terraform stack in infra/.

The stack provisions the dedicated Hello Architect Foundry (AIServices account +
project + Mistral model deployments) plus the Service Principal and RBAC, all in
rg-helloarch-dev. The legacy sentinel stack and the infra/project/ subfolder were
retired when this stack was consolidated to the top level.
"""

import re
from pathlib import Path

INFRA_DIR = Path(__file__).parent.parent.parent / "infra"
MAIN_TF = INFRA_DIR / "main.tf"
PROVIDERS_TF = INFRA_DIR / "providers.tf"
VARIABLES_TF = INFRA_DIR / "variables.tf"
OUTPUTS_TF = INFRA_DIR / "outputs.tf"


# --- File layout ---------------------------------------------------------


def test_main_tf_exists() -> None:
    assert MAIN_TF.exists(), "infra/main.tf must exist"


def test_providers_tf_exists() -> None:
    assert PROVIDERS_TF.exists(), "infra/providers.tf must exist (industry-standard layout)"


def test_variables_tf_exists() -> None:
    assert VARIABLES_TF.exists(), "infra/variables.tf must exist"


def test_outputs_tf_exists() -> None:
    assert OUTPUTS_TF.exists(), "infra/outputs.tf must exist"


def test_project_subfolder_removed() -> None:
    assert not (INFRA_DIR / "project").exists(), "infra/project/ must be consolidated into infra/"


# --- Providers & backend -------------------------------------------------


def test_azapi_provider_declared() -> None:
    content = PROVIDERS_TF.read_text()
    assert 'source  = "azure/azapi"' in content, "azapi provider must be declared in providers.tf"


def test_azuread_provider_declared() -> None:
    content = PROVIDERS_TF.read_text()
    assert 'source  = "hashicorp/azuread"' in content, "azuread provider must be declared in providers.tf"


def test_remote_state_backend_configured() -> None:
    """State lives in the shared platform storage account, not on disk (ADR-015)."""
    content = PROVIDERS_TF.read_text()
    assert 'backend "azurerm"' in content, "Stack must configure the azurerm remote backend (ADR-015)"
    assert "stplatformydev" in content, "backend must point at the platform state account stplatformydev"


def test_no_stale_backend_storage_references() -> None:
    content = PROVIDERS_TF.read_text()
    for stale in ("rg-tfstate-hobby-ai", "stsentineltfstate"):
        assert stale not in content, f"Stale backend reference '{stale}' must be removed"


# --- Foundry account & project -------------------------------------------


def test_foundry_account_defined() -> None:
    content = MAIN_TF.read_text()
    assert '"foundry"' in content, "AIServices Foundry account (azapi_resource.foundry) must be defined"


def test_foundry_is_aiservices_kind() -> None:
    content = MAIN_TF.read_text()
    assert '"AIServices"' in content, "Foundry account must be of kind AIServices"


def test_foundry_allows_project_management() -> None:
    content = MAIN_TF.read_text()
    assert "allowProjectManagement = true" in content, "Foundry account must enable project management"


def test_foundry_project_defined() -> None:
    content = MAIN_TF.read_text()
    assert '"project"' in content, "Foundry project (azapi_resource.project) must be defined"


def test_system_assigned_identity() -> None:
    content = MAIN_TF.read_text()
    assert "SystemAssigned" in content, "Foundry account/project must use SystemAssigned managed identity"


# --- Model deployments ---------------------------------------------------


def test_model_deployments_defined() -> None:
    content = MAIN_TF.read_text()
    assert "azurerm_cognitive_deployment" in content, "Model deployments must be defined"


def test_model_deployments_global_standard_sku() -> None:
    content = MAIN_TF.read_text()
    assert '"GlobalStandard"' in content, "Model deployments must use the GlobalStandard SKU"


def test_model_deployments_variable() -> None:
    content = VARIABLES_TF.read_text()
    assert 'variable "model_deployments"' in content, "variables.tf must declare a model_deployments map"


def test_mistral_models_present() -> None:
    content = VARIABLES_TF.read_text()
    for dep in ("mistral-small-2503", "Mistral-Large-3", "Codestral-2501"):
        assert dep in content, f"model_deployments default must include {dep}"


# --- OIDC federated credential -------------------------------------------


def test_federated_identity_credential_defined() -> None:
    """CI authenticates via OIDC federation, not a stored secret (ADR-015)."""
    content = MAIN_TF.read_text()
    assert "azuread_application_federated_identity_credential" in content, (
        "OIDC federated credential must be defined on the application"
    )


def test_oidc_issuer_github_actions() -> None:
    content = MAIN_TF.read_text()
    assert "https://token.actions.githubusercontent.com" in content, (
        "OIDC issuer must be the GitHub Actions token endpoint"
    )


def test_oidc_subject_master_branch() -> None:
    content = MAIN_TF.read_text()
    assert "repo:ysuurme/azure_hello_world:ref:refs/heads/master" in content, (
        "OIDC subject must target the master branch of the repository"
    )


# --- CI principal: Storage Blob Data Contributor on tfstate --------------


def test_sp_tfstate_blob_contributor_defined() -> None:
    """CI principal needs write on tfstate for blob-lease locking during terraform apply."""
    content = MAIN_TF.read_text()
    assert '"Storage Blob Data Contributor"' in content, (
        "CI principal must be granted Storage Blob Data Contributor on the tfstate container"
    )


def test_sp_tfstate_platform_storage_referenced() -> None:
    content = MAIN_TF.read_text()
    assert "stplatformydev" in content, (
        "Storage Blob Data Contributor grant must reference the platform state account stplatformydev"
    )


# --- Service Principal & RBAC --------------------------------------------


def test_service_principal_defined() -> None:
    content = MAIN_TF.read_text()
    assert "azuread_service_principal" in content, "stack must define azuread_service_principal"


def test_sp_password_not_defined() -> None:
    """SP password eliminated: auth flows via managed identity (cloud) / az login (local) / OIDC (CI) — no long-lived secret in state."""
    content = MAIN_TF.read_text()
    assert "azuread_service_principal_password" not in content, (
        "SP password must not be defined — no extractable secret should land in Terraform state"
    )


def test_role_assignment_ai_developer() -> None:
    content = MAIN_TF.read_text()
    assert '"Azure AI Developer"' in content, "stack must assign the Azure AI Developer role"


def test_role_assignment_cognitive_user() -> None:
    content = MAIN_TF.read_text()
    assert '"Cognitive Services User"' in content, "stack must assign the Cognitive Services User role"


def test_rbac_scoped_to_foundry() -> None:
    content = MAIN_TF.read_text()
    assert "azapi_resource.foundry.id" in content, "RBAC must be scoped to the Foundry account"


# --- Naming & secrets hygiene --------------------------------------------


def test_rg_name_default_helloarch() -> None:
    content = VARIABLES_TF.read_text()
    assert "rg-helloarch-dev" in content, "RG default must follow helloarch CAF naming"


def test_sp_name_default_helloarch() -> None:
    content = VARIABLES_TF.read_text()
    assert "sp-helloarch-dev" in content, "SP default must follow helloarch CAF naming"


def test_location_default_swedencentral() -> None:
    content = VARIABLES_TF.read_text()
    assert "swedencentral" in content, "location default must be swedencentral"


def test_no_hardcoded_api_keys() -> None:
    """Reject any literal api_key or admin key assignments."""
    content = MAIN_TF.read_text()
    forbidden = re.compile(r'(api_key|admin_key|primary_access_key)\s*=\s*"[^"${\n]', re.IGNORECASE)
    match = forbidden.search(content)
    assert match is None, f"Hardcoded credential found: {match.group() if match else ''}"


def test_no_hardcoded_secrets_in_variables() -> None:
    content = VARIABLES_TF.read_text()
    forbidden = re.compile(r'default\s*=\s*"[A-Za-z0-9+/]{20,}={0,2}"')
    match = forbidden.search(content)
    assert match is None, "No base64-like secrets should appear as variable defaults"


# --- Outputs -------------------------------------------------------------


def test_foundry_project_endpoint_output() -> None:
    content = OUTPUTS_TF.read_text()
    assert "foundry_project_endpoint" in content, "outputs.tf must export foundry_project_endpoint"


def test_sp_client_id_output() -> None:
    content = OUTPUTS_TF.read_text()
    assert "sp_client_id" in content, "outputs.tf must export sp_client_id"


def test_sp_client_secret_output_absent() -> None:
    """No client-secret output: the SP secret was eliminated, so nothing secret-valued is exported."""
    content = OUTPUTS_TF.read_text()
    assert "sp_client_secret" not in content, (
        "sp_client_secret output must not exist — auth via managed identity, no secret to export"
    )


# --- Container Registry + Container Apps -----------------------------------


def test_container_registry_defined() -> None:
    content = MAIN_TF.read_text()
    assert "azurerm_container_registry" in content, "ACR must be defined"


def test_acr_admin_disabled() -> None:
    content = MAIN_TF.read_text()
    assert "admin_enabled       = false" in content, "ACR admin user must be disabled (use managed identity)"


def test_user_assigned_identity_defined() -> None:
    content = MAIN_TF.read_text()
    assert "azurerm_user_assigned_identity" in content, "Backend user-assigned managed identity must be defined"


def test_uami_acrpull_grant() -> None:
    content = MAIN_TF.read_text()
    assert '"AcrPull"' in content, "Backend identity must be granted AcrPull on the registry"


def test_container_app_environment_defined() -> None:
    content = MAIN_TF.read_text()
    assert "azurerm_container_app_environment" in content, "Container Apps environment must be defined"


def test_backend_container_app_defined() -> None:
    content = MAIN_TF.read_text()
    assert "azurerm_container_app" in content, "Backend Container App must be defined"


def test_backend_ingress_internal() -> None:
    content = MAIN_TF.read_text()
    assert "external_enabled = false" in content, "Backend ingress must be internal (not publicly exposed)"


def test_backend_uses_user_assigned_identity() -> None:
    content = MAIN_TF.read_text()
    assert 'type         = "UserAssigned"' in content, "Container App must use the user-assigned identity"


def test_backend_no_secret_env() -> None:
    """The cloud backend must rely on managed identity, never a client secret."""
    content = MAIN_TF.read_text()
    assert "AZURE_CLIENT_SECRET" not in content, "Container App must not inject a client secret (use managed identity)"


def test_backend_internal_fqdn_output() -> None:
    content = OUTPUTS_TF.read_text()
    assert "backend_internal_fqdn" in content, "outputs.tf must export backend_internal_fqdn"
