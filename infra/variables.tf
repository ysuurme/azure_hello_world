variable "resource_group_name" {
  type        = string
  description = "The name of the resource group"
  default     = "rg-hobby-ai-dev"
}

variable "location" {
  type        = string
  description = "The Azure region to deploy to"
  default     = "eastus"
}
