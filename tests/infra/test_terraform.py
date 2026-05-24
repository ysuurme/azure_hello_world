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


def test_remote_backend_azurerm() -> None:
    content = PROVIDERS_TF.read_text()
    assert 'backend "azurerm"' in content, "Remote azurerm backend must be configured in providers.tf"


def test_backend_has_storage_account() -> None:
    content = PROVIDERS_TF.read_text()
    assert "storage_account_name" in content, "Backend must specify storage_account_name"


def test_backend_has_container() -> None:
    content = PROVIDERS_TF.read_text()
    assert "container_name" in content, "Backend must specify container_name"


def test_consolidated_state_key() -> None:
    content = PROVIDERS_TF.read_text()
    assert "helloarch.tfstate" in content, "Stack must use the consolidated helloarch.tfstate state key"


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


# --- Service Principal & RBAC --------------------------------------------


def test_service_principal_defined() -> None:
    content = MAIN_TF.read_text()
    assert "azuread_service_principal" in content, "stack must define azuread_service_principal"


def test_sp_password_defined() -> None:
    content = MAIN_TF.read_text()
    assert "azuread_service_principal_password" in content, "stack must define the SP password"


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


def test_sp_client_secret_output_sensitive() -> None:
    content = OUTPUTS_TF.read_text()
    assert "sp_client_secret" in content, "outputs.tf must export sp_client_secret"
    assert "sensitive   = true" in content, "sp_client_secret output must be marked sensitive"
