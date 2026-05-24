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

variable "environment" {
  type        = string
  description = "Deployment environment identifier (e.g. dev, prod)"
  default     = "dev"
}

variable "project_prefix" {
  type        = string
  description = "Short prefix used in resource names to identify the project"
  default     = "sentinel"
}
