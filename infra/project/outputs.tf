output "resource_group_id" {
  description = "Resource ID of the helloarch resource group"
  value       = azurerm_resource_group.helloarch.id
}

output "sp_client_id" {
  description = "Application (client) ID for sp-helloarch-dev — set as AZURE_CLIENT_ID"
  value       = azuread_service_principal.helloarch.client_id
}

output "sp_tenant_id" {
  description = "Tenant ID — set as AZURE_TENANT_ID"
  value       = data.azuread_client_config.current.tenant_id
}

output "sp_client_secret" {
  description = "Client secret for sp-helloarch-dev — set as AZURE_CLIENT_SECRET"
  value       = azuread_service_principal_password.helloarch.value
  sensitive   = true
}
