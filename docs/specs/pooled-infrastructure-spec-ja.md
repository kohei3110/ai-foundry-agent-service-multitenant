# Pooled Multi-Tenant Infrastructure Specification

*Version 1.0 – 2025-06-20*

## 1. 概要

本仕様書は、Azure AI Foundry Agent Service (FAS) のPooled（共有）マルチテナント方式におけるインフラストラクチャの設計・実装仕様を定義します。Bicepを使用したInfrastructure as Code (IaC) による自動化されたデプロイメントを前提とします。

## 2. アーキテクチャ原則

### 2.1 リソース共有戦略
- **単一プロジェクト共有**: 1つのFASプロジェクトに複数テナントを収容
- **論理的分離**: タグ、RBAC/ABAC、パーティションキーによる境界維持
- **セキュリティ最優先**: ゼロトラスト原則に基づく多層防御

### 2.2 Bicep設計原則
- **モジュラー設計**: 機能別にBicepモジュールを分離
- **パラメーター化**: テナント固有の設定を外部化
- **条件付きデプロイ**: 環境・テナント要件に応じた柔軟なリソース構成

## 3. リソース構成

### 3.1 Resource Group 構成

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

### 3.2 Managed Identity 構成

各テナント専用のUser-Assigned Managed Identityを作成：

```bicep
// テナント別Managed Identity
resource tenantManagedIdentities 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = [for tenant in tenantConfigs: {
  name: 'mi-${tenant.name}-${environment}'
  location: location
  tags: {
    tenantId: tenant.id
    tenantName: tenant.name
  }
}]
```

### 3.3 Azure AI Foundry構成

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

### 3.4 Cosmos DB構成

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

### 3.5 Azure AI Search構成

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

### 3.6 Storage Account構成

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

// テナント別コンテナ
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

### 3.7 Key Vault構成

```bicep
// Key Vault per tenant (推奨)
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

### 3.8 API Management構成

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

## 4. RBAC/ABAC構成

### 4.1 ロール割り当てテンプレート

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

## 5. 監視・ログ構成

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

## 6. デプロイメント構成

### 6.1 パラメーターファイル例

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

### 6.2 デプロイメントスクリプト

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

## 7. セキュリティ要件

### 7.1 ネットワークセキュリティ
- Private Endpoints の実装（本番環境）
- NSG ルールによるトラフィック制御
- VNet統合による内部通信の暗号化

### 7.2 データ暗号化
- Transit: TLS 1.2 以上の強制
- At Rest: Customer-managed keys (CMK) の活用
- Key Vault での暗号化キー管理

### 7.3 監査・コンプライアンス
- Activity Log の全記録
- Diagnostic Settings の有効化
- Security Center 推奨事項の継続監視

## 8. 運用要件

### 8.1 バックアップ・DR
- Cosmos DB: 継続的バックアップの有効化
- Blob Storage: Geo-redundant storage (GRS) 構成
- Key Vault: ソフト削除・消去保護の有効化

### 8.2 スケーリング
- Cosmos DB: Request Units (RU) の自動スケーリング
- AI Search: レプリカ・パーティション数の動的調整
- APIM: 階層アップグレードによる容量拡張

## 9. 関連仕様書

- [Pooled Application Specification](./pooled-application-spec.md)
- [Security & Compliance Guidelines](./security-guidelines.md)
- [Operation & Monitoring Procedures](./operations-procedures.md)
