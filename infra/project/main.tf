data "azuread_client_config" "current" {}

# --- Resource Group ---
resource "azurerm_resource_group" "helloarch" {
  name     = var.resource_group_name
  location = var.location
}

# --- App Registration (identity anchor) ---
resource "azuread_application" "helloarch" {
  display_name = var.sp_name
  owners       = [data.azuread_client_config.current.object_id]
}

# --- Service Principal ---
resource "azuread_service_principal" "helloarch" {
  client_id = azuread_application.helloarch.client_id
  owners    = [data.azuread_client_config.current.object_id]
}

# --- Service Principal Password (1-year rotation) ---
resource "azuread_service_principal_password" "helloarch" {
  service_principal_id = azuread_service_principal.helloarch.object_id
  end_date_relative    = "8760h"
}

# --- RBAC: SP → Azure AI Developer on the Foundry project ---
resource "azurerm_role_assignment" "sp_ai_developer" {
  scope                = var.foundry_project_resource_id
  role_definition_name = "Azure AI Developer"
  principal_id         = azuread_service_principal.helloarch.object_id
}
