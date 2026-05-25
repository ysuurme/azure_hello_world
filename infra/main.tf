data "azuread_client_config" "current" {}

resource "azurerm_resource_group" "helloarch" {
  name     = var.resource_group_name
  location = var.location
}

# --- Azure AI Foundry (AIServices account with project management) ---
resource "azapi_resource" "foundry" {
  type      = "Microsoft.CognitiveServices/accounts@2025-04-01-preview"
  name      = var.foundry_account_name
  location  = azurerm_resource_group.helloarch.location
  parent_id = azurerm_resource_group.helloarch.id

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "AIServices"
    sku  = { name = "S0" }
    properties = {
      allowProjectManagement = true
      customSubDomainName    = var.foundry_account_name
      publicNetworkAccess    = "Enabled"
    }
  }

  response_export_values = ["properties.endpoint"]
}

# --- Azure AI Foundry project ---
resource "azapi_resource" "project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview"
  name      = var.foundry_project_name
  location  = azurerm_resource_group.helloarch.location
  parent_id = azapi_resource.foundry.id

  identity {
    type = "SystemAssigned"
  }

  body = {
    properties = {
      displayName = var.foundry_project_display_name
    }
  }
}

# --- Model deployments (Mistral stack; non-OpenAI, OpenAI-client compatible) ---
resource "azurerm_cognitive_deployment" "models" {
  for_each             = var.model_deployments
  name                 = each.key
  cognitive_account_id = azapi_resource.foundry.id

  model {
    format  = each.value.format
    name    = each.value.name
    version = each.value.version
  }

  sku {
    name     = "GlobalStandard"
    capacity = 1
  }
}

# --- Service Principal (identity for the containerised app) ---
resource "azuread_application" "helloarch" {
  display_name = var.sp_name
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "helloarch" {
  client_id = azuread_application.helloarch.client_id
  owners    = [data.azuread_client_config.current.object_id]
}

# No client secret is provisioned: the app uses DefaultAzureCredential (az login
# locally, UAMI in the cloud). CI authenticates via the OIDC federated credential
# below — a short-lived token exchange, never a long-lived secret in state (ADR-015).

# --- OIDC federated credential for CI (GitHub Actions) ---
# The GitHub Actions OIDC token is exchanged for an Azure access token without any
# stored secret. Subject targets pull_request events because infra-plan.yml triggers
# on pull_request (not push). GitHub issues sub=...pull_request for that event type;
# ref:refs/heads/master would only match push-to-master triggers.
resource "azuread_application_federated_identity_credential" "ci_oidc" {
  application_id = azuread_application.helloarch.id
  display_name   = "github-ci-pr"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:ysuurme/azure_hello_world:pull_request"
}

# --- RBAC: CI principal → tfstate container (state read + blob-lease locking) ---
# Storage Blob Data Contributor (write) is required because terraform acquires a
# blob lease on the state file to prevent concurrent apply corruption.
data "azurerm_storage_account" "platform" {
  name                = "stplatformydev"
  resource_group_name = "rg-platformy-dev"
}

resource "azurerm_role_assignment" "sp_tfstate_blob_contributor" {
  scope                = "${data.azurerm_storage_account.platform.id}/blobServices/default/containers/tfstate"
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azuread_service_principal.helloarch.object_id
}

# --- RBAC: SP → Foundry account (project ops + inference) ---
resource "azurerm_role_assignment" "sp_ai_developer" {
  scope                = azapi_resource.foundry.id
  role_definition_name = "Azure AI Developer"
  principal_id         = azuread_service_principal.helloarch.object_id
}

resource "azurerm_role_assignment" "sp_cognitive_user" {
  scope                = azapi_resource.foundry.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azuread_service_principal.helloarch.object_id
}

# --- Container Registry ---
resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.helloarch.name
  location            = azurerm_resource_group.helloarch.location
  sku                 = "Basic"
  admin_enabled       = false
}

# --- User-assigned identity for the backend (ACR pull + Foundry inference) ---
resource "azurerm_user_assigned_identity" "api" {
  name                = var.api_identity_name
  resource_group_name = azurerm_resource_group.helloarch.name
  location            = azurerm_resource_group.helloarch.location
}

resource "azurerm_role_assignment" "api_acrpull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

resource "azurerm_role_assignment" "api_ai_developer" {
  scope                = azapi_resource.foundry.id
  role_definition_name = "Azure AI Developer"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

resource "azurerm_role_assignment" "api_cognitive_user" {
  scope                = azapi_resource.foundry.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

# --- Container Apps environment ---
resource "azurerm_container_app_environment" "cae" {
  name                = var.container_app_environment_name
  resource_group_name = azurerm_resource_group.helloarch.name
  location            = azurerm_resource_group.helloarch.location
}

# --- Backend Container App (internal ingress; UAMI for ACR pull + Foundry) ---
resource "azurerm_container_app" "api" {
  name                         = var.backend_app_name
  resource_group_name          = azurerm_resource_group.helloarch.name
  container_app_environment_id = azurerm_container_app_environment.cae.id
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api.id]
  }

  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.api.id
  }

  ingress {
    external_enabled = false
    target_port      = 8000
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name    = "api"
      image   = "${azurerm_container_registry.acr.login_server}/helloarch:${var.image_tag}"
      cpu     = 0.5
      memory  = "1Gi"
      command = ["uvicorn"]
      args    = ["src.main:app", "--host", "0.0.0.0", "--port", "8000"]

      env {
        name  = "AZURE_AAIF_PROJECT_ENDPOINT"
        value = "https://${var.foundry_account_name}.services.ai.azure.com/api/projects/${var.foundry_project_name}"
      }
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.api.client_id
      }
      env {
        name  = "AZURE_DIAGRAM_STORAGE_ACCOUNT"
        value = azurerm_storage_account.diagrams.name
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.api_acrpull,
    azurerm_role_assignment.api_ai_developer,
    azurerm_role_assignment.api_cognitive_user,
  ]
}

# --- Project storage: diagram working artifacts (ADR-016 project-local) ---
# Lives in rg-helloarch-dev (NOT the platform account): diagrams are project-scoped
# working artifacts, not cross-project knowledge. Accepted trade-off — this account
# is destroyed by `az group delete rg-helloarch-dev` (ADR-013 teardown).
resource "azurerm_storage_account" "diagrams" {
  name                = var.diagram_storage_account_name
  resource_group_name = azurerm_resource_group.helloarch.name
  location            = azurerm_resource_group.helloarch.location

  account_tier             = "Standard"
  account_replication_type = "LRS" # cheapest; single-region is fine for project working artifacts
  account_kind             = "StorageV2"
  access_tier              = "Hot"

  # Secretless, hardened (mirrors the state-account stance in ADR-015).
  shared_access_key_enabled       = false # Entra ID only — no account keys
  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"
  public_network_access_enabled   = true # dev: reachable from laptop; tighten with Private Link later (#10)
  allow_nested_items_to_be_public = false

  blob_properties {
    versioning_enabled = true # "blob is the version control" (ADR-016) — history for build-forward
    delete_retention_policy {
      days = 14 # soft-delete blobs (recover deleted diagrams)
    }
    container_delete_retention_policy {
      days = 7
    }
  }
}

# Container created via the MANAGEMENT plane (storage_account_id) so it works with
# account keys disabled, using your Owner rights rather than a data-plane key.
resource "azurerm_storage_container" "diagrams" {
  name                  = var.diagram_container_name
  storage_account_id    = azurerm_storage_account.diagrams.id
  container_access_type = "private"
}

# --- Data-plane RBAC (no keys): who can read/write blobs ---
# SP (local container dev) — read/write so the local app persists diagrams.
resource "azurerm_role_assignment" "sp_diagrams_blob" {
  scope                = azurerm_storage_account.diagrams.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azuread_service_principal.helloarch.object_id
}

# UAMI (cloud Container App) — read/write so the deployed app persists diagrams.
resource "azurerm_role_assignment" "api_diagrams_blob" {
  scope                = azurerm_storage_account.diagrams.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

# Note: the operator (your az login) holds "Storage Blob Data Contributor" at
# rg-helloarch-dev scope, granted out-of-band as a bootstrap (mirrors the KV
# Secrets Officer grant). It must pre-exist so the provider's AAD blob-service
# poll on account creation is authorized — RBAC created mid-apply propagates too
# late. Hence it is intentionally not declared here.
