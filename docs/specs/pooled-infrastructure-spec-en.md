# Pooled Multi-Tenant Infrastructure Specification

*Version 1.0 – 2025-06-20*

## 1. Overview

This specification defines the design and implementation specifications for the infrastructure of the Azure AI Foundry Agent Service (FAS) pooled multi-tenant approach. It assumes automated deployment through Infrastructure as Code (IaC) using Bicep.

## 2. Architecture Principles

### 2.1 Resource Sharing Strategy
- **Single Project Sharing**: Accommodate multiple tenants in one FAS project
- **Logical Isolation**: Maintain boundaries through tags, RBAC/ABAC, and partition keys
- **Security First**: Multi-layered defense based on Zero Trust principles

### 2.2 Bicep Design Principles
- **Modular Design**: Separate Bicep modules by functionality
- **Parameterization**: Externalize tenant-specific configurations
- **Conditional Deployment**: Flexible resource configuration based on environment and tenant requirements

## 3. Resource Configuration

### 3.1 Resource Group Configuration

```bicep
// Resource Group Structure
targetScope = 'subscription'

resource rgShared 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'rg-fas-pooled-${environment}'
  location: location
  tags: {
    tenantScope: 'shared'
    environment: environment
    architecture: 'pooled'
  }
}
```

### 3.2 Managed Identity Configuration

Create dedicated User-Assigned Managed Identity for each tenant:

```bicep
// Tenant-specific Managed Identity
resource tenantManagedIdentities 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = [for tenant in tenantConfigs: {
  name: 'mi-${tenant.name}-${environment}'
  location: location
  tags: {
    tenantId: tenant.id
    tenantName: tenant.name
  }
}]
```

### 3.3 Azure AI Foundry Configuration

```bicep
// AI Foundry Service (Cognitive Services Account)
resource aiFoundryService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: 'cog-${projectName}-${environment}'
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: 'aifoundry-${projectName}-${environment}'
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    publicNetworkAccess: 'Enabled'
  }
  tags: {
    tenantScope: 'shared'
  }
}
```

### 3.4 Cosmos DB Configuration

```bicep
// Cosmos DB Account
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: 'cosmos-${projectName}-${environment}'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
  tags: {
    tenantScope: 'shared'
  }
}

// Database
resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmosAccount
  name: 'agents'
  properties: {
    resource: {
      id: 'agents'
    }
  }
}

// Containers with partition key on tenantId
var containerConfigs = [
  { name: 'threads', partitionKey: '/tenantId' }
  { name: 'messages', partitionKey: '/tenantId' }
  { name: 'runs', partitionKey: '/tenantId' }
  { name: 'files', partitionKey: '/tenantId' }
]

resource cosmosContainers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = [for config in containerConfigs: {
  parent: cosmosDatabase
  name: config.name
  properties: {
    resource: {
      id: config.name
      partitionKey: {
        paths: [config.partitionKey]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
      }
    }
  }
}]
```

### 3.5 Azure AI Search Configuration

```bicep
// Azure AI Search Service
resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: 'search-${projectName}-${environment}'
  location: location
  sku: {
    name: 'standard'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    networkRuleSet: {
      ipRules: []
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: {
    tenantScope: 'shared'
  }
}
```

### 3.6 Storage Account Configuration

```bicep
// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'sa${replace(projectName, '-', '')}${environment}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
  tags: {
    tenantScope: 'shared'
  }
}

// Blob Service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

// Tenant-specific containers
resource tenantBlobContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [for tenant in tenantConfigs: {
  parent: blobService
  name: tenant.name
  properties: {
    publicAccess: 'None'
    metadata: {
      tenantId: tenant.id
      tenantName: tenant.name
    }
  }
}]
```

### 3.7 Key Vault Configuration

```bicep
// Key Vault per tenant (recommended)
resource tenantKeyVaults 'Microsoft.KeyVault/vaults@2023-07-01' = [for tenant in tenantConfigs: {
  name: 'kv-${tenant.name}-${environment}'
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: []
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
  tags: {
    tenantId: tenant.id
    tenantName: tenant.name
  }
}]
```

### 3.8 API Management Configuration

```bicep
// API Management Service
resource apimService 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: 'apim-${projectName}-${environment}'
  location: location
  sku: {
    name: 'Developer'
    capacity: 1
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: {
    tenantScope: 'shared'
  }
}

// JWT Validation Policy
resource jwtValidationPolicy 'Microsoft.ApiManagement/service/policies@2023-05-01-preview' = {
  parent: apimService
  name: 'policy'
  properties: {
    value: '''
    <policies>
      <inbound>
        <validate-jwt header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized">
          <openid-config url="${jwtValidationUrl}" />
          <required-claims>
            <claim name="extension_tenantId" match="any">
              <value>contoso</value>
              <value>fabrikam</value>
            </claim>
          </required-claims>
        </validate-jwt>
        <set-header name="x-tenant-id" exists-action="override">
          <value>@(context.Request.Headers.GetValueOrDefault("Authorization","")
                    .Replace("Bearer ","")
                    .AsJwt()?.Claims?.GetValueOrDefault("extension_tenantId", ""))</value>
        </set-header>
      </inbound>
    </policies>
    '''
  }
}
```

## 4. RBAC/ABAC Configuration

### 4.1 Role Assignment Template

```bicep
// Storage Blob Data Reader with ABAC conditions
resource storageRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (tenant, i) in tenantConfigs: {
  name: guid(storageAccount.id, tenantManagedIdentities[i].id, 'Storage Blob Data Reader')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1') // Storage Blob Data Reader
    principalId: tenantManagedIdentities[i].properties.principalId
    principalType: 'ServicePrincipal'
    condition: '@Resource.tag.tenantId == "${tenant.id}"'
    conditionVersion: '2.0'
  }
}]

// Cosmos DB Built-in Data Contributor
resource cosmosRoleAssignments 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-11-15' = [for (tenant, i) in tenantConfigs: {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, tenantManagedIdentities[i].id, 'Cosmos DB Built-in Data Contributor')
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002' // Built-in Data Contributor
    principalId: tenantManagedIdentities[i].properties.principalId
    scope: cosmosAccount.id
  }
}]
```

## 5. Monitoring and Logging Configuration

### 5.1 Application Insights

```bicep
// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'ai-${projectName}-${environment}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    RetentionInDays: 90
  }
  tags: {
    tenantScope: 'shared'
  }
}

// Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-${projectName}-${environment}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
  tags: {
    tenantScope: 'shared'
  }
}
```

## 6. Deployment Configuration

### 6.1 Parameter File Example

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
    "publisherEmail": {
      "value": "admin@example.com"
    },
    "publisherName": {
      "value": "AI Foundry Admin"
    },
    "jwtValidationUrl": {
      "value": "https://login.microsoftonline.com/common/v2.0/.well-known/openid_configuration"
    }
  }
}
```

### 6.2 Deployment Script

```bash
#!/bin/bash
# Deploy Pooled Multi-Tenant Infrastructure

SUBSCRIPTION_ID="your-subscription-id"
RESOURCE_GROUP="rg-fas-pooled-dev"
TEMPLATE_FILE="main.bicep"
PARAMETERS_FILE="main.parameters.json"

# Login to Azure
az login

# Set subscription
az account set --subscription $SUBSCRIPTION_ID

# Create resource group
az group create --name $RESOURCE_GROUP --location "Japan East"

# Deploy infrastructure
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file $TEMPLATE_FILE \
  --parameters @$PARAMETERS_FILE \
  --verbose

echo "Deployment completed successfully"
```

## 7. Security Requirements

### 7.1 Network Security
- Implementation of Private Endpoints (production environment)
- Traffic control through NSG rules
- Encryption of internal communication through VNet integration

### 7.2 Data Encryption
- Transit: Enforce TLS 1.2 or higher
- At Rest: Utilize Customer-managed keys (CMK)
- Encryption key management through Key Vault

### 7.3 Audit and Compliance
- Complete recording of Activity Logs
- Enable Diagnostic Settings
- Continuous monitoring of Security Center recommendations

## 8. Operational Requirements

### 8.1 Backup and DR
- Cosmos DB: Enable continuous backup
- Blob Storage: Configure Geo-redundant storage (GRS)
- Key Vault: Enable soft delete and purge protection

### 8.2 Scaling
- Cosmos DB: Auto-scaling of Request Units (RU)
- AI Search: Dynamic adjustment of replica and partition counts
- APIM: Capacity expansion through tier upgrades

## 9. Related Specifications

- [Pooled Application Specification](./pooled-application-spec.md)
- [Security & Compliance Guidelines](./security-guidelines.md)
- [Operation & Monitoring Procedures](./operations-procedures.md)
