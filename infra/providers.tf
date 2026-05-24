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
  }

  backend "azurerm" {
    resource_group_name  = "rg-tfstate-hobby-ai"
    storage_account_name = "stsentineltfstate"
    container_name       = "tfstate"
    key                  = "azure-hello-world.tfstate"
  }
}

provider "azurerm" {
  features {}
}

provider "azapi" {}
