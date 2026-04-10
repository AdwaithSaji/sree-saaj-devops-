# ── Variables ─────────────────────────────────────────────────────────────────
variable "project_name"        {}
variable "environment"         {}
variable "resource_group_name" {}
variable "location"            {}
variable "kubernetes_version"  {}
variable "aks_subnet_id"       {}
variable "node_vm_size"        {}
variable "node_count"          { type = number }
variable "node_min_count"      { type = number }
variable "node_max_count"      { type = number }
variable "tags"                { type = map(string) }

# ── AKS Cluster ───────────────────────────────────────────────────────────────
resource "azurerm_kubernetes_cluster" "main" {
  name                = "${var.project_name}-${var.environment}-aks"
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = "${var.project_name}-${var.environment}"
  kubernetes_version  = var.kubernetes_version

  # ── System node pool ──────────────────────────────────────────────────────
  default_node_pool {
    name                 = "systempool"
    vm_size              = var.node_vm_size
    vnet_subnet_id       = var.aks_subnet_id
    enable_auto_scaling  = true
    node_count           = var.node_count
    min_count            = var.node_min_count
    max_count            = var.node_max_count
    os_disk_size_gb      = 50
    type                 = "VirtualMachineScaleSets"

    # Taint system pool so only system pods run here
    only_critical_addons_enabled = true

    upgrade_settings {
      max_surge = "10%"
    }
  }

  # ── Managed identity (no service principal needed) ─────────────────────────
  identity {
    type = "SystemAssigned"
  }

  # ── Networking ────────────────────────────────────────────────────────────
  network_profile {
    network_plugin    = "azure"      # Azure CNI — pods get VNet IPs
    network_policy    = "azure"      # Built-in network policy enforcement
    load_balancer_sku = "standard"
    service_cidr      = "10.0.0.0/16"
    dns_service_ip    = "10.0.0.10"
  }

  # ── Cluster autoscaler tuning ─────────────────────────────────────────────
  auto_scaler_profile {
    balance_similar_node_groups = true
    skip_nodes_with_system_pods = true
    scale_down_delay_after_add  = "10m"
    scale_down_unneeded         = "10m"
  }

  # ── Add-ons ───────────────────────────────────────────────────────────────
  azure_policy_enabled             = false
  http_application_routing_enabled = false  # Use NGINX Ingress instead

  # ── Monitoring (Azure Monitor) ────────────────────────────────────────────
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  tags = var.tags
}

# ── App node pool for workloads (separate from system pool) ───────────────────
resource "azurerm_kubernetes_cluster_node_pool" "app" {
  name                  = "apppool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.node_vm_size
  vnet_subnet_id        = var.aks_subnet_id
  enable_auto_scaling   = true
  node_count            = var.node_count
  min_count             = var.node_min_count
  max_count             = var.node_max_count
  os_disk_size_gb       = 50

  node_labels = {
    "role" = "app"
  }

  upgrade_settings {
    max_surge = "10%"
  }

  tags = var.tags
}

# ── Log Analytics workspace for AKS monitoring ────────────────────────────────
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_name}-${var.environment}-logs"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "cluster_name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "cluster_fqdn" {
  value = azurerm_kubernetes_cluster.main.fqdn
}

output "kubelet_identity_object_id" {
  description = "Object ID of the kubelet managed identity — used for AcrPull role assignment"
  value       = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
}

output "kube_config_raw" {
  description = "Raw kubeconfig — store securely, never commit"
  value       = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive   = true
}
