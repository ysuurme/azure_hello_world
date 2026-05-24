variable "resource_group_name" {
  type        = string
  description = "Resource group for helloarch project resources (CAF: rg-<workload>-<env>)"
  default     = "rg-helloarch-dev"
}

variable "location" {
  type        = string
  description = "Azure region to deploy resources"
  default     = "eastus"
}

variable "sp_name" {
  type        = string
  description = "Display name of the Service Principal (CAF: sp-<workload>-<env>)"
  default     = "sp-helloarch-dev"
}

variable "foundry_project_resource_id" {
  type = string
  description = <<-EOT
    Resource ID of the Azure AI Foundry project workspace scoped for the Azure AI Developer role.
    Obtain with: az ml workspace show --name <project-name> --resource-group <rg> --query id -o tsv
    Example: /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.MachineLearningServices/workspaces/<project>
  EOT
}
