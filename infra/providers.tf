terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
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

  # Single state key for the consolidated Hello Architect stack.
  backend "azurerm" {
    resource_group_name  = "rg-tfstate-hobby-ai"
    storage_account_name = "stsentineltfstate"
    container_name       = "tfstate"
    key                  = "helloarch.tfstate"
  }
}

provider "azurerm" {
  features {}
}

provider "azapi" {}

provider "azuread" {}
