variable "project_name" {
  description = "Project name — used as a prefix for all Azure resource names"
  type        = string
  default     = "sreesaaj"
}

variable "environment" {
  description = "Deployment environment: dev | staging | production"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment must be one of: dev, staging, production."
  }
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "southindia"
}

# ── Networking ────────────────────────────────────────────────────────────────

variable "vnet_cidr" {
  description = "Address space for the Virtual Network"
  type        = string
  default     = "10.0.0.0/8"
}

variable "aks_subnet_cidr" {
  description = "CIDR block for the AKS node subnet (must be inside vnet_cidr)"
  type        = string
  default     = "10.240.0.0/16"
}

# ── AKS ───────────────────────────────────────────────────────────────────────

variable "kubernetes_version" {
  description = "Kubernetes version for the AKS cluster"
  type        = string
  default     = "1.28"
}

variable "node_vm_size" {
  description = "Azure VM size for the AKS system node pool"
  type        = string
  default     = "Standard_D2s_v3"
  # Standard_D2s_v3 = 2 vCPU / 8 GiB — sufficient for dev/staging
  # Use Standard_D4s_v3 (4 vCPU / 16 GiB) for production workloads
}

variable "node_count" {
  description = "Initial number of nodes in the system node pool"
  type        = number
  default     = 2
}

variable "node_min_count" {
  description = "Minimum node count for the cluster autoscaler"
  type        = number
  default     = 2
}

variable "node_max_count" {
  description = "Maximum node count for the cluster autoscaler"
  type        = number
  default     = 5
}
