output "resource_group_id" {
  value = azurerm_resource_group.rg.id
}

output "search_service_endpoint" {
  description = "HTTPS endpoint for the Azure AI Search service"
  value       = "https://${azurerm_search_service.search.name}.search.windows.net"
}

output "ai_project_id" {
  description = "Resource ID of the Azure AI Foundry project workspace"
  value       = azapi_resource.ai_project.id
}

output "ai_hub_id" {
  description = "Resource ID of the Azure AI Hub workspace"
  value       = azapi_resource.ai_hub.id
}
