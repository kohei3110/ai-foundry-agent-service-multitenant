# GitHub Actions Environment Setup Guide

This document explains how to set up CI/CD pipelines using GitHub Actions for the Azure AI Foundry Agent Service multi-tenant environment.

## 1. Prerequisites

- Azure subscriptio## 7. Deployment Procedures

### 7.1 In3. **Application Insights** - Verify application functionality
4. **Container Apps** - Check application deployment and health status

## 8. Troubleshootingstructure Deployment

1. **Push Triggers**:
   - Push changes to `pooled/infra/` → Triggers Pooled environment deployment
   - Push changes to `silo/infra/` → Triggers Silo environment deployment

2. **Manual Triggers**:
   - Go to GitHub Actions tab and select "Deploy Pooled Infrastructure" or "Deploy Silo Infrastructure"
   - Choose environment and tenant (for Silo) and run the workflow

### 7.2 Application Deployment

1. **Automated Triggers**:
   - Push changes to `pooled/app/` → Triggers Pooled application deployment
   - Push changes to `silo/app/` → Triggers Silo application deployment (when implemented)

2. **Manual Triggers**:
   - Go to GitHub Actions tab and select "Deploy Pooled Application"
   - Choose environment and run the workflow

### 7.3 Deployment Verificationpository administrator permissions
- Azure CLI (for local setup)

## 2. Azure Configuration

### 2.1 Service Principal Creation

```bash
# Login to Azure CLI
az login

# Create Service Principal
az ad sp create-for-rbac \
  --name "sp-fas-github-actions" \
  --role "Contributor" \
  --scopes "/subscriptions/{subscription-id}" \
  --json-auth

# Output example:
# {
#   "clientId": "12345678-1234-1234-1234-123456789012",
#   "clientSecret": "your-client-secret",
#   "subscriptionId": "87654321-4321-4321-4321-210987654321",
#   "tenantId": "11111111-1111-1111-1111-111111111111"
# }
```

### 2.2 Additional Role Assignments

```bash
# Resource Group Contributor permissions
az role assignment create \
  --assignee {clientId} \
  --role "Resource Group Contributor" \
  --scope "/subscriptions/{subscription-id}"

# User Access Administrator (for RBAC role assignments)
az role assignment create \
  --assignee {clientId} \
  --role "User Access Administrator" \
  --scope "/subscriptions/{subscription-id}"
```

## 3. GitHub Repository Configuration

### 3.1 Repository Variables Setup

Configure the following Variables in GitHub repository **Settings > Secrets and variables > Actions**:

| Variable Name | Value | Description |
|---------------|-------|-------------|
| `AZURE_CLIENT_ID` | Service Principal clientId | Azure authentication client ID |
| `AZURE_TENANT_ID` | Service Principal tenantId | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Service Principal subscriptionId | Azure subscription ID |

### 3.2 GitHub Environments Setup

Create the following Environments in your repository:

#### Pooled Environments
- `pooled-dev`
- `pooled-staging` 
- `pooled-prod`

#### Silo Environments
- `silo-contoso-dev`
- `silo-contoso-staging`
- `silo-contoso-prod`
- `silo-fabrikam-dev`
- `silo-fabrikam-staging`
- `silo-fabrikam-prod`

### 3.3 Environment Protection Rules

Configure the following protection rules for production environments (`*-prod`):

1. **Required reviewers**: Minimum 1 approver
2. **Wait timer**: 10-minute wait before deployment
3. **Deployment branches**: `main` branch only

## 4. Directory Structure and Parameter Files

### 4.1 Pooled Environment

```
pooled/
├── infra/
│   ├── main.bicep
│   ├── main.parameters.json          # Default parameters
│   ├── main.parameters.dev.json      # Development environment
│   ├── main.parameters.staging.json  # Staging environment
│   └── main.parameters.prod.json     # Production environment
└── app/
```

### 4.2 Silo Environment

```
silo/
├── infra/
│   ├── main.bicep
│   ├── main.parameters.json                    # Default parameters
│   ├── main.parameters.dev.json                # Development environment
│   ├── main.parameters.staging.json            # Staging environment
│   ├── main.parameters.prod.json               # Production environment
│   ├── main.parameters.contoso.dev.json        # Tenant-specific parameters
│   ├── main.parameters.contoso.staging.json
│   ├── main.parameters.contoso.prod.json
│   ├── main.parameters.fabrikam.dev.json
│   ├── main.parameters.fabrikam.staging.json
│   └── main.parameters.fabrikam.prod.json
└── app/
```

## 5. Parameter File Examples

### 5.1 Pooled Environment Parameter Example

`pooled/infra/main.parameters.dev.json`:
```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "projectName": {
      "value": "fas-pooled"
    },
    "environment": {
      "value": "dev"
    },
    "location": {
      "value": "Japan East"
    },
    "tenantConfigs": {
      "value": [
        {
          "id": "contoso",
          "name": "contoso",
          "displayName": "Contoso Corporation"
        },
        {
          "id": "fabrikam", 
          "name": "fabrikam",
          "displayName": "Fabrikam Inc."
        }
      ]
    },
    "containerCpuCore": {
      "value": "0.25"
    },
    "containerMemory": {
      "value": "0.5Gi"
    }
  }
}
```

### 5.2 Silo Environment Parameter Example

`silo/infra/main.parameters.contoso.dev.json`:
```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "projectName": {
      "value": "fas-silo"
    },
    "environment": {
      "value": "dev"
    },
    "tenantId": {
      "value": "contoso"
    },
    "tenantName": {
      "value": "Contoso Corporation"
    },
    "location": {
      "value": "Japan East"
    },
    "containerCpuCore": {
      "value": "0.5"
    },
    "containerMemory": {
      "value": "1Gi"
    }
  }
}
```

## 6. Application Deployment Workflows

In addition to infrastructure deployment, this repository includes CI/CD workflows for application deployment.

### 6.1 Pooled Application Deployment

The `deploy-pooled-app.yml` workflow handles the deployment of the Python container application in the `pooled/app` directory.

**Features:**
- Automatic testing (unit and integration tests)
- Docker image building with Azure Container Registry
- Deployment to Azure Container Apps
- Multi-environment support (dev/staging/prod)

**Triggers:**
- Push to any branch with changes in `pooled/app/`
- Pull requests to main/develop branches
- Manual workflow dispatch

**Prerequisites:**
- Infrastructure must be deployed first using `deploy-pooled-infra.yml`
- Required Azure resources: Container Registry, Container Apps Environment, Container App

For detailed setup instructions, see [POOLED-APP-SETUP.md](./POOLED-APP-SETUP.md).

## 7. Deployment Procedures

### 7.1 Automated Deployment

1. **Push Triggers**:
   - Push changes to `pooled/infra/` → Triggers Pooled environment deployment
   - Push changes to `silo/infra/` → Triggers Silo environment deployment

2. **Manual Triggers**:
   - Go to GitHub Actions tab and select "Deploy Pooled Infrastructure" or "Deploy Silo Infrastructure"
   - Choose environment and tenant (for Silo) and run the workflow

### 7.2 Deployment Verification

After deployment completion, verify the following:

1. **Azure Portal** - Confirm resources are created
2. **GitHub Actions** Summary - Check deployment results
3. **Application Insights** - Verify application functionality

## 8. Troubleshooting

### 8.1 Authentication Errors

```
Error: The client '...' with object id '...' does not have authorization to perform action '...'
```

**Solution**:
- Verify appropriate permissions are assigned to the Service Principal
- Check permissions at subscription and resource group levels

### 8.2 Parameter File Errors

```
❌ No parameters file found
```

**Solution**:
- Verify the environment-specific parameter file exists
- Check file naming conventions

### 8.3 Bicep Validation Errors

```
❌ main.bicep validation failed
```

**Solution**:
- Run `az bicep build --file main.bicep` locally to check for errors
- Verify Bicep syntax and resource definitions

## 9. Security Considerations

1. **Secret Management**:
   - Service Principal clientSecret is managed via GitHub Secrets (using Federated Identity in this setup)
   - Do not include sensitive information in parameter files

2. **Access Control**:
   - Set approvers for production environment deployments
   - Configure branch protection rules

3. **Auditing**:
   - All deployments are logged in GitHub Actions
   - Track resource changes via Azure Activity Log

## 10. Reference Links

- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Azure Service Principal](https://docs.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals)
- [Azure Bicep](https://docs.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [GitHub Actions Azure Login](https://github.com/Azure/login)
