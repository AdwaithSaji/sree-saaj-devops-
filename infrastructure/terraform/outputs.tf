output "resource_group_name" {
  description = "Azure Resource Group name"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Azure region where resources are deployed"
  value       = azurerm_resource_group.main.location
}

# ── ACR ───────────────────────────────────────────────────────────────────────

output "acr_name" {
  description = "Azure Container Registry resource name"
  value       = azurerm_container_registry.main.name
}

output "acr_login_server" {
  description = "ACR login server — use this as the image registry prefix"
  value       = azurerm_container_registry.main.login_server
}

# ── AKS ───────────────────────────────────────────────────────────────────────

output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = module.aks.cluster_name
}

output "aks_cluster_fqdn" {
  description = "AKS API server FQDN"
  value       = module.aks.cluster_fqdn
  sensitive   = true
}

output "kubeconfig_command" {
  description = "Run this command to configure kubectl after apply"
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${module.aks.cluster_name}"
}

output "acr_push_command" {
  description = "Authenticate Docker to ACR"
  value       = "az acr login --name ${azurerm_container_registry.main.name}"
}
