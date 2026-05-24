variable "resource_group_name" {
  type        = string
  description = "Resource group for all Hello Architect resources (CAF: rg-<workload>-<env>)"
  default     = "rg-helloarch-dev"
}

variable "location" {
  type        = string
  description = "Azure region to deploy resources"
  default     = "swedencentral"
}

variable "foundry_account_name" {
  type        = string
  description = "AIServices (Azure AI Foundry) account name; also used as the custom subdomain"
  default     = "aaif-helloarch-dev"
}

variable "foundry_project_name" {
  type        = string
  description = "Foundry project sub-resource name (appears in the inference endpoint path)"
  default     = "helloarch"
}

variable "foundry_project_display_name" {
  type        = string
  description = "Friendly display name for the Foundry project"
  default     = "Hello Architect"
}

variable "sp_name" {
  type        = string
  description = "Display name of the Service Principal (CAF: sp-<workload>-<env>)"
  default     = "sp-helloarch-dev"
}

variable "model_deployments" {
  type = map(object({
    name    = string
    version = string
    format  = string
  }))
  description = "Model deployments on the Foundry account, keyed by deployment name."
  default = {
    "mistral-small-2503" = { name = "mistral-small-2503", version = "1", format = "Mistral AI" }
    "Mistral-Large-3"    = { name = "Mistral-Large-3", version = "1", format = "Mistral AI" }
    "Codestral-2501"     = { name = "Codestral-2501", version = "2", format = "Mistral AI" }
  }
}
