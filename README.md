# Sree Saaj Events & Caterers — Platform

> Production-ready microservices platform for Sree Saaj Events and Caterers, Kerala.
> Demonstrates full cloud-native architecture: Docker · Kubernetes · Terraform · Ansible · GitHub Actions · Prometheus · Grafana

---

## Architecture

```
                         ┌─────────────┐
                         │   Browser   │
                         └──────┬──────┘
                                │ :80
                         ┌──────▼──────┐
                         │   NGINX     │  (frontend static files)
                         │  Frontend   │
                         └──────┬──────┘
                                │ /api/* proxy
                         ┌──────▼──────┐
                         │ API Gateway │  :8000  JWT validation · Rate limiting · Routing
                         └──────┬──────┘
              ┌─────────────────┼─────────────────────┐
              │                 │                     │
    ┌─────────▼──────┐  ┌───────▼───────┐  ┌─────────▼────────┐
    │ Auth Service   │  │ Event Service │  │Inventory Service │
    │    :8001       │  │    :8002      │  │    :8003         │
    └─────────┬──────┘  └───────┬───────┘  └─────────┬────────┘
              │                 │                     │
    ┌─────────▼──────┐  ┌───────▼───────┐  ┌─────────▼────────┐
    │  postgres-auth │  │ postgres-event│  │postgres-inventory│
    └────────────────┘  └───────────────┘  └──────────────────┘

    ┌────────────────┐  ┌───────────────┐  ┌──────────────────┐
    │Billing Service │  │Gallery Service│  │  Menu Service    │
    │    :8004       │  │    :8005      │  │    :8006         │
    └─────────┬──────┘  └───────┬───────┘  └─────────┬────────┘
              │                 │                     │
    ┌─────────▼──────┐  ┌───────▼───────┐  ┌─────────▼────────┐
    │postgres-billing│  │postgres-gallery│ │  postgres-menu   │
    └────────────────┘  └───────────────┘  └──────────────────┘

    ┌──────────────────────────────────┐
    │  Prometheus :9090 · Grafana :3000│
    └──────────────────────────────────┘
```

---

## Quick Start (Local Development)

### Prerequisites
- Docker Desktop
- Docker Compose v2

```bash
# Clone the repo
git clone https://github.com/your-org/sreesaaj.git
cd sreesaaj

# Start all services
docker-compose up --build

# Run in background
docker-compose up -d --build
```

### Service URLs

| Service           | URL                        | Description              |
|-------------------|----------------------------|--------------------------|
| Frontend          | http://localhost            | Public website           |
| API Gateway       | http://localhost:8000       | REST API entry point     |
| API Docs          | http://localhost:8000/api/docs | Swagger UI            |
| Auth Service      | http://localhost:8001       | Direct (dev only)        |
| Event Service     | http://localhost:8002       | Direct (dev only)        |
| Inventory Service | http://localhost:8003       | Direct (dev only)        |
| Billing Service   | http://localhost:8004       | Direct (dev only)        |
| Gallery Service   | http://localhost:8005       | Direct (dev only)        |
| Menu Service      | http://localhost:8006       | Direct (dev only)        |
| Prometheus        | http://localhost:9090       | Metrics                  |
| Grafana           | http://localhost:3000       | Dashboards               |

### Default Credentials

| System  | Username               | Password        |
|---------|------------------------|-----------------|
| App     | admin@sreesaaj.com     | Admin@123       |
| Grafana | admin                  | SreeSaaj@2024   |

---

## Project Structure

```
sreesaaj/
├── services/
│   ├── api-gateway/        # FastAPI gateway — JWT, rate limiting, proxy
│   ├── auth-service/       # User auth, JWT tokens, roles
│   ├── event-service/      # Events, bookings, calendar
│   ├── inventory-service/  # Item tracking per event
│   ├── billing-service/    # Invoices, payments, revenue
│   ├── gallery-service/    # Image upload and management
│   └── menu-service/       # Menu categories and items
├── frontend/               # Static HTML + TailwindCSS + Alpine.js
│   ├── index.html          # Home
│   ├── about.html
│   ├── services.html
│   ├── menu.html
│   ├── gallery.html
│   ├── booking.html
│   ├── estimator.html
│   ├── login.html
│   ├── admin/              # Admin dashboard
│   └── staff/              # Staff dashboard
├── infrastructure/
│   ├── nginx/              # nginx.conf for frontend container
│   ├── kubernetes/         # K8s manifests
│   ├── terraform/          # AWS EKS + VPC + ECR
│   └── ansible/            # Automation playbooks
├── monitoring/
│   ├── prometheus/         # Scrape config
│   └── grafana/            # Dashboards + provisioning
├── .github/workflows/      # CI/CD pipelines
└── docker-compose.yml      # Local dev stack
```

---

## Kubernetes Deployment

```bash
# Configure kubectl (AWS EKS)
aws eks update-kubeconfig --name sreesaaj-eks --region ap-south-1

# Deploy everything
kubectl apply -f infrastructure/kubernetes/namespace.yaml
kubectl apply -f infrastructure/kubernetes/secrets.yaml
kubectl apply -f infrastructure/kubernetes/configmap.yaml
kubectl apply -f infrastructure/kubernetes/deployments/
kubectl apply -f infrastructure/kubernetes/services/
kubectl apply -f infrastructure/kubernetes/ingress.yaml
kubectl apply -f infrastructure/kubernetes/hpa.yaml

# Check status
kubectl get pods -n sreesaaj
kubectl get services -n sreesaaj
```

---

## Terraform (AWS Infrastructure)

```bash
cd infrastructure/terraform

# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan

# Get cluster name
terraform output eks_cluster_name
```

---

## Ansible (Server Automation)

```bash
cd infrastructure/ansible

# Install Docker on all nodes
ansible-playbook -i inventory/hosts.yml playbooks/install-docker.yml

# Install Kubernetes
ansible-playbook -i inventory/hosts.yml playbooks/install-kubernetes.yml

# Deploy application
ansible-playbook -i inventory/hosts.yml playbooks/deploy-app.yml
```

---

## CI/CD Pipeline

| Pipeline | Trigger              | Steps                                          |
|----------|----------------------|------------------------------------------------|
| CI       | Push to main/develop | Lint → Test → Build Docker images → Push GHCR |
| CD       | CI success on main   | Pull images → kubectl apply → Rollout → Verify |

Required GitHub Secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `GITHUB_TOKEN` (auto-provided)

---

## Monitoring

Access Grafana at http://localhost:3000 (admin / SreeSaaj@2024)

The **Sree Saaj Platform Overview** dashboard shows:
- Service health status (UP/DOWN) for all 7 services
- HTTP request rate and response time (p95)
- CPU and memory usage
- Prometheus scrapes all services at `/metrics`

---

## API Reference

All requests go through the API Gateway at `/api/`:

```
POST   /api/auth/login          # Login (public)
POST   /api/auth/register       # Register staff (admin only)
GET    /api/auth/me             # Current user

GET    /api/events/             # List events (auth)
POST   /api/events/             # Create event (auth)
GET    /api/events/calendar     # Monthly calendar

POST   /api/bookings/           # Submit booking inquiry (PUBLIC)
GET    /api/bookings/           # List inquiries (auth)

GET    /api/inventory/          # List inventory (auth)
POST   /api/inventory/events/{id}/assign  # Assign items to event

POST   /api/invoices/           # Generate invoice
GET    /api/billing/summary     # Revenue summary

GET    /api/gallery/            # Gallery images (PUBLIC)
GET    /api/menu/categories     # Menu categories (PUBLIC)
GET    /api/menu/items          # Menu items (PUBLIC)

GET    /health                  # All service health check
```

---

## WhatsApp Integration

Floating WhatsApp button on all pages: **+91 98765 43210**

Cost estimator links directly to WhatsApp with pre-filled inquiry message.

---

*Built for Sree Saaj Events and Caterers, Kerala — crafting unforgettable moments since 2014.*
