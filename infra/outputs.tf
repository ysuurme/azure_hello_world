output "resource_group_id" {
  description = "Resource ID of the Hello Architect resource group"
  value       = azurerm_resource_group.helloarch.id
}

output "foundry_account_endpoint" {
  description = "Base endpoint of the AIServices Foundry account"
  value       = azapi_resource.foundry.output.properties.endpoint
}

output "foundry_project_endpoint" {
  description = "Project inference endpoint — set as AZURE_AAIF_PROJECT_ENDPOINT"
  value       = "https://${var.foundry_account_name}.services.ai.azure.com/api/projects/${var.foundry_project_name}"
}

output "sp_client_id" {
  description = "Application (client) ID for sp-helloarch-dev — set as AZURE_CLIENT_ID"
  value       = azuread_service_principal.helloarch.client_id
}

output "sp_tenant_id" {
  description = "Tenant ID — set as AZURE_TENANT_ID"
  value       = data.azuread_client_config.current.tenant_id
}

output "acr_login_server" {
  description = "ACR login server for image pushes/pulls"
  value       = azurerm_container_registry.acr.login_server
}

output "api_identity_client_id" {
  description = "Client ID of the backend managed identity — used as AZURE_CLIENT_ID in the container"
  value       = azurerm_user_assigned_identity.api.client_id
}

output "backend_internal_fqdn" {
  description = "Internal ingress FQDN of the backend Container App"
  value       = azurerm_container_app.api.ingress[0].fqdn
}

output "diagram_storage_account_name" {
  description = "Project storage account for diagrams — set as AZURE_DIAGRAM_STORAGE_ACCOUNT"
  value       = azurerm_storage_account.diagrams.name
}
