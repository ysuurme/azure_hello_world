resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

# --- Azure AI Hub (AI Foundry Hub workspace) ---
resource "azapi_resource" "ai_hub" {
  type      = "Microsoft.MachineLearningServices/workspaces@2024-10-01"
  name      = "hub-${var.project_prefix}-${var.environment}"
  location  = azurerm_resource_group.rg.location
  parent_id = azurerm_resource_group.rg.id

  identity {
    type = "SystemAssigned"
  }

  body = jsonencode({
    kind = "Hub"
    properties = {
      friendlyName        = "AI Hub ${var.project_prefix}"
      publicNetworkAccess = "Enabled"
    }
    sku = {
      name = "Basic"
    }
  })
}

# --- Azure AI Foundry Project ---
resource "azapi_resource" "ai_project" {
  type      = "Microsoft.MachineLearningServices/workspaces@2024-10-01"
  name      = "proj-${var.project_prefix}-${var.environment}"
  location  = azurerm_resource_group.rg.location
  parent_id = azurerm_resource_group.rg.id

  identity {
    type = "SystemAssigned"
  }

  response_export_values = ["identity.principalId"]

  body = jsonencode({
    kind = "Project"
    properties = {
      friendlyName  = "Sentinel Project"
      hubResourceId = azapi_resource.ai_hub.id
    }
    sku = {
      name = "Basic"
    }
  })
}

# --- Azure AI Search (Basic SKU) ---
resource "azurerm_search_service" "search" {
  name                = "srch-${var.project_prefix}-${var.environment}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "basic"

  local_authentication_enabled = false

  identity {
    type = "SystemAssigned"
  }
}

# --- RBAC: Project MI → Search Service ---
resource "azurerm_role_assignment" "project_search_contributor" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azapi_resource.ai_project.output.identity.principalId
}

resource "azurerm_role_assignment" "project_search_reader" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = azapi_resource.ai_project.output.identity.principalId
}

# --- Search Connection (Project Managed Identity, no hardcoded keys) ---
resource "azapi_resource" "search_connection" {
  type      = "Microsoft.MachineLearningServices/workspaces/connections@2024-10-01"
  name      = "search-connection"
  parent_id = azapi_resource.ai_project.id

  body = jsonencode({
    properties = {
      category      = "CognitiveSearch"
      target        = "https://${azurerm_search_service.search.name}.search.windows.net"
      authType      = "ProjectManagedIdentity"
      isSharedToAll = true
      metadata = {
        ApiType    = "Azure"
        ResourceId = azurerm_search_service.search.id
      }
    }
  })

  depends_on = [
    azurerm_role_assignment.project_search_contributor,
    azurerm_role_assignment.project_search_reader,
  ]
}

# --- Capability Host (Agent Service tool execution) ---
resource "azapi_resource" "capability_host" {
  type      = "Microsoft.MachineLearningServices/workspaces/capabilityHosts@2025-01-01-preview"
  name      = "default"
  parent_id = azapi_resource.ai_project.id

  body = jsonencode({
    properties = {
      capabilityHostKind     = "Agents"
      vectorStoreConnections = [azapi_resource.search_connection.name]
    }
  })
}
