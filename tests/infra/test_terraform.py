"""Content tests for Terraform infrastructure files in infra/."""

import re
from pathlib import Path

INFRA_DIR = Path(__file__).parent.parent.parent / "infra"
MAIN_TF = INFRA_DIR / "main.tf"
VARIABLES_TF = INFRA_DIR / "variables.tf"
OUTPUTS_TF = INFRA_DIR / "outputs.tf"


def test_main_tf_exists() -> None:
    assert MAIN_TF.exists(), "infra/main.tf must exist"


def test_variables_tf_exists() -> None:
    assert VARIABLES_TF.exists(), "infra/variables.tf must exist"


def test_outputs_tf_exists() -> None:
    assert OUTPUTS_TF.exists(), "infra/outputs.tf must exist"


def test_azapi_provider_declared() -> None:
    content = MAIN_TF.read_text()
    assert 'source  = "azure/azapi"' in content, "azapi provider must be declared in main.tf"


def test_remote_backend_azurerm() -> None:
    content = MAIN_TF.read_text()
    assert 'backend "azurerm"' in content, "Remote azurerm backend must be configured"


def test_backend_has_storage_account() -> None:
    content = MAIN_TF.read_text()
    assert "storage_account_name" in content, "Backend must specify storage_account_name"


def test_backend_has_container() -> None:
    content = MAIN_TF.read_text()
    assert "container_name" in content, "Backend must specify container_name"


def test_search_service_defined() -> None:
    content = MAIN_TF.read_text()
    assert "azurerm_search_service" in content, "azurerm_search_service must be defined"


def test_search_service_basic_sku() -> None:
    content = MAIN_TF.read_text()
    assert 'sku                 = "basic"' in content, "Search service must use 'basic' SKU"


def test_search_connection_defined() -> None:
    content = MAIN_TF.read_text()
    assert '"search_connection"' in content, "search_connection azapi_resource must be defined"


def test_search_connection_project_managed_identity() -> None:
    content = MAIN_TF.read_text()
    assert '"ProjectManagedIdentity"' in content, 'search_connection must use authType = "ProjectManagedIdentity"'


def test_capability_host_defined() -> None:
    content = MAIN_TF.read_text()
    assert '"capability_host"' in content, "capability_host azapi_resource must be defined"


def test_capability_host_kind_agents() -> None:
    content = MAIN_TF.read_text()
    assert '"Agents"' in content, 'capability_host must set capabilityHostKind = "Agents"'


def test_ai_hub_defined() -> None:
    content = MAIN_TF.read_text()
    assert '"ai_hub"' in content, "ai_hub azapi_resource must be defined"


def test_ai_project_defined() -> None:
    content = MAIN_TF.read_text()
    assert '"ai_project"' in content, "ai_project azapi_resource must be defined"


def test_system_assigned_identity_on_project() -> None:
    content = MAIN_TF.read_text()
    # SystemAssigned identity required for ProjectManagedIdentity auth to work
    assert "SystemAssigned" in content, "Resources must use SystemAssigned managed identity"


def test_no_hardcoded_api_keys() -> None:
    """Reject any literal api_key or admin key assignments."""
    content = MAIN_TF.read_text()
    forbidden = re.compile(r'(api_key|admin_key|primary_access_key)\s*=\s*"[^"${\n]', re.IGNORECASE)
    match = forbidden.search(content)
    assert match is None, f"Hardcoded credential found: {match.group() if match else ''}"


def test_no_hardcoded_api_keys_in_variables() -> None:
    content = VARIABLES_TF.read_text()
    forbidden = re.compile(r'default\s*=\s*"[A-Za-z0-9+/]{20,}={0,2}"')
    match = forbidden.search(content)
    assert match is None, "No base64-like secrets should appear as variable defaults"


def test_search_local_auth_disabled() -> None:
    content = MAIN_TF.read_text()
    assert "local_authentication_enabled = false" in content, (
        "Search service must disable local (key-based) auth to enforce Managed Identity"
    )


def test_environment_variable_declared() -> None:
    content = VARIABLES_TF.read_text()
    assert 'variable "environment"' in content, "variables.tf must declare an 'environment' variable"


def test_project_prefix_variable_declared() -> None:
    content = VARIABLES_TF.read_text()
    assert 'variable "project_prefix"' in content, "variables.tf must declare a 'project_prefix' variable"


def test_search_endpoint_output() -> None:
    content = OUTPUTS_TF.read_text()
    assert "search_service_endpoint" in content, "outputs.tf must export search_service_endpoint"


def test_ai_project_id_output() -> None:
    content = OUTPUTS_TF.read_text()
    assert "ai_project_id" in content, "outputs.tf must export ai_project_id"
