terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
  }

  # Dedicated state key for this stack — shares the same remote backend as infra/
  backend "azurerm" {
    resource_group_name  = "rg-tfstate-hobby-ai"
    storage_account_name = "stsentineltfstate"
    container_name       = "tfstate"
    key                  = "helloarch-project.tfstate"
  }
}

provider "azurerm" {
  features {}
}

provider "azuread" {}
