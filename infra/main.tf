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

  body = jsonencode({
    kind = "AIServices"
    sku  = { name = "S0" }
    properties = {
      allowProjectManagement = true
      customSubDomainName    = var.foundry_account_name
      publicNetworkAccess    = "Enabled"
    }
  })

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

  body = jsonencode({
    properties = {
      displayName = var.foundry_project_display_name
    }
  })
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

resource "azuread_service_principal_password" "helloarch" {
  service_principal_id = azuread_service_principal.helloarch.object_id
  end_date_relative    = "8760h"
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
    min_replicas = 1
    max_replicas = 1

    container {
      name    = "api"
      image   = "${azurerm_container_registry.acr.login_server}/helloarch:latest"
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
    }
  }

  depends_on = [
    azurerm_role_assignment.api_acrpull,
    azurerm_role_assignment.api_ai_developer,
    azurerm_role_assignment.api_cognitive_user,
  ]
}
