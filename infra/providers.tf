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

  # Remote state in the shared platform resource group (ADR-015). The backing
  # storage outlives any single project's `az group delete`, so tearing down
  # rg-helloarch-dev never destroys its own state. Bootstrap the account once
  # (see README → Cloud Deployment), then `terraform init -migrate-state`.
  backend "azurerm" {
    resource_group_name  = "rg-platformy-dev"
    storage_account_name = "stplatformydev"
    container_name       = "tfstate"
    key                  = "helloarch/terraform.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  features {}

  # Skip subscription-wide auto-registration (needs subscription-level perms and
  # can hang on API latency), but explicitly register exactly the namespaces this
  # stack uses. If the logged-in identity lacks /register/action, register them by
  # hand instead: az provider register --namespace "Microsoft.App"
  resource_provider_registrations = "none"
  resource_providers_to_register = [
    "Microsoft.CognitiveServices",  # Foundry (AIServices) account + model deployments
    "Microsoft.App",                # Container Apps + managed environment
    "Microsoft.ContainerRegistry",  # ACR
    "Microsoft.ManagedIdentity",    # user-assigned identity
    "Microsoft.OperationalInsights" # Container Apps environment logs
  ]
}

provider "azapi" {}

provider "azuread" {}
