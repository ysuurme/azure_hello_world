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
      customSubDomainName     = var.foundry_account_name
      publicNetworkAccess     = "Enabled"
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
