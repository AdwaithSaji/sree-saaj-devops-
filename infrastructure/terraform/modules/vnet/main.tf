# ── Variables ─────────────────────────────────────────────────────────────────
variable "project_name"        {}
variable "environment"         {}
variable "resource_group_name" {}
variable "location"            {}
variable "vnet_cidr"           {}
variable "aks_subnet_cidr"     {}
variable "tags"                { type = map(string) }

# ── Virtual Network ───────────────────────────────────────────────────────────
resource "azurerm_virtual_network" "main" {
  name                = "${var.project_name}-${var.environment}-vnet"
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = [var.vnet_cidr]

  tags = var.tags
}

# ── AKS Node Subnet ───────────────────────────────────────────────────────────
resource "azurerm_subnet" "aks" {
  name                 = "aks-nodes-subnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.aks_subnet_cidr]
}

# ── Network Security Group for AKS subnet ────────────────────────────────────
resource "azurerm_network_security_group" "aks" {
  name                = "${var.project_name}-${var.environment}-aks-nsg"
  resource_group_name = var.resource_group_name
  location            = var.location

  # Allow inbound HTTPS (Kubernetes API)
  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }

  # Allow inbound HTTP (Ingress Controller)
  security_rule {
    name                       = "AllowHTTP"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }

  tags = var.tags
}

resource "azurerm_subnet_network_security_group_association" "aks" {
  subnet_id                 = azurerm_subnet.aks.id
  network_security_group_id = azurerm_network_security_group.aks.id
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "vnet_id"       { value = azurerm_virtual_network.main.id }
output "vnet_name"     { value = azurerm_virtual_network.main.name }
output "aks_subnet_id" { value = azurerm_subnet.aks.id }
