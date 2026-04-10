terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47"
    }
  }

  # ── Remote state in Azure Blob Storage ──────────────────────────────────────
  # Before running `terraform init`, create the storage account once:
  #
  #   az group create -n sreesaaj-tfstate-rg -l southindia
  #   az storage account create \
  #     --name sreesaajtfstate \
  #     --resource-group sreesaaj-tfstate-rg \
  #     --sku Standard_LRS \
  #     --allow-blob-public-access false
  #   az storage container create \
  #     --name tfstate \
  #     --account-name sreesaajtfstate
  #
  backend "azurerm" {
    resource_group_name  = "sreesaaj-tfstate-rg"
    storage_account_name = "sreesaajtfstate"
    container_name       = "tfstate"
    key                  = "production/terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    resource_group {
      # Prevent accidental deletion of a non-empty resource group
      prevent_deletion_if_contains_resources = true
    }
  }
}

# ── Resource Group ────────────────────────────────────────────────────────────
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location

  tags = local.common_tags
}

# ── Virtual Network ───────────────────────────────────────────────────────────
module "vnet" {
  source = "./modules/vnet"

  project_name        = var.project_name
  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  vnet_cidr           = var.vnet_cidr
  aks_subnet_cidr     = var.aks_subnet_cidr
  tags                = local.common_tags
}

# ── Azure Container Registry (ACR) ───────────────────────────────────────────
# Naming: alphanumeric only, globally unique, 5-50 chars
resource "azurerm_container_registry" "main" {
  name                = "${replace(var.project_name, "-", "")}${var.environment}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
  admin_enabled       = false  # Use managed identity — never admin credentials

  tags = local.common_tags
}

# ── AKS Cluster ───────────────────────────────────────────────────────────────
module "aks" {
  source = "./modules/aks"

  project_name        = var.project_name
  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  kubernetes_version  = var.kubernetes_version
  aks_subnet_id       = module.vnet.aks_subnet_id
  node_vm_size        = var.node_vm_size
  node_count          = var.node_count
  node_min_count      = var.node_min_count
  node_max_count      = var.node_max_count
  tags                = local.common_tags
}

# ── Grant AKS kubelet identity permission to pull images from ACR ─────────────
# This replaces the need for imagePullSecrets in every namespace
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = module.aks.kubelet_identity_object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.main.id
  skip_service_principal_aad_check = true
}

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Owner       = "Sree Saaj Events and Caterers"
  }
}
