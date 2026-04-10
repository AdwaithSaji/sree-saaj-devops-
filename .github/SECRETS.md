# GitHub Actions — Required Secrets

Configure these in: **GitHub → Settings → Secrets and variables → Actions**

## Azure Authentication

| Secret | How to get it |
|--------|--------------|
| `AZURE_CREDENTIALS` | See command below |
| `ACR_LOGIN_SERVER` | Terraform output: `acr_login_server` |
| `ACR_NAME` | Terraform output: `acr_name` |
| `AKS_RESOURCE_GROUP` | Terraform output: `resource_group_name` |
| `AKS_CLUSTER_NAME` | Terraform output: `aks_cluster_name` |

## Generate AZURE_CREDENTIALS

```bash
# Create a service principal with Contributor access on the resource group
az ad sp create-for-rbac \
  --name "sreesaaj-github-actions" \
  --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/sreesaaj-production-rg \
  --sdk-auth
```

Copy the entire JSON output as the value of `AZURE_CREDENTIALS`.

Also grant the SP the `AcrPush` role on ACR:
```bash
az role assignment create \
  --assignee <SP_CLIENT_ID> \
  --role AcrPush \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/sreesaaj-production-rg/providers/Microsoft.ContainerRegistry/registries/sreesaajproductionacr
```
