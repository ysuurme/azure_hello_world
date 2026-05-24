terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 2.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
  }

  # Local state for now (no remote backend provisioned). Local state files
  # are gitignored. A remote backend can be added later as its own step.
}

provider "azurerm" {
  features {}
}

provider "azapi" {}

provider "azuread" {}
