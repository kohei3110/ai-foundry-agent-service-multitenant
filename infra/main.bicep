// Wrapper Bicep file for AZD compatibility
// This file references the actual pooled infrastructure

module pooledInfra '../pooled/infra/main.bicep' = {
  name: 'pooled-infrastructure'
  params: {
    environment: environmentName
    location: location
    resourceToken: resourceToken
    tags: tags
  }
}

// Parameters expected by AZD
@description('Environment name')
param environmentName string

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Resource group name (required by AZD but not used in template)')
#disable-next-line no-unused-params
param resourceGroupName string

@description('Resource token for unique naming')
param resourceToken string = uniqueString(subscription().id, resourceGroup().id, environmentName)

@description('Tags to apply to all resources')
param tags object = {
  environment: environmentName
  project: 'ai-foundry-agent-service'
  architecture: 'pooled'
  'azd-env-name': environmentName
}

// Re-export all outputs from the pooled infrastructure
output resourceGroupName string = pooledInfra.outputs.resourceGroupName
output location string = pooledInfra.outputs.location
output applicationInsightsConnectionString string = pooledInfra.outputs.applicationInsightsConnectionString
output applicationInsightsInstrumentationKey string = pooledInfra.outputs.applicationInsightsInstrumentationKey
output keyVaultUri string = pooledInfra.outputs.keyVaultUri
output keyVaultName string = pooledInfra.outputs.keyVaultName
output storageAccountName string = pooledInfra.outputs.storageAccountName
output storageAccountBlobEndpoint string = pooledInfra.outputs.storageAccountBlobEndpoint
output cosmosDbEndpoint string = pooledInfra.outputs.cosmosDbEndpoint
output cosmosDbAccountName string = pooledInfra.outputs.cosmosDbAccountName
output searchServiceEndpoint string = pooledInfra.outputs.searchServiceEndpoint
output searchServiceName string = pooledInfra.outputs.searchServiceName
output containerAppsEnvironmentName string = pooledInfra.outputs.containerAppsEnvironmentName
output agentServiceContainerAppName string = pooledInfra.outputs.agentServiceContainerAppName
output agentServiceUrl string = pooledInfra.outputs.agentServiceUrl
output userAssignedIdentityName string = pooledInfra.outputs.userAssignedIdentityName
output userAssignedIdentityClientId string = pooledInfra.outputs.userAssignedIdentityClientId
output userAssignedIdentityPrincipalId string = pooledInfra.outputs.userAssignedIdentityPrincipalId
output containerRegistryName string = pooledInfra.outputs.containerRegistryName
output containerRegistryLoginServer string = pooledInfra.outputs.containerRegistryLoginServer

// Additional outputs required by AZD
output RESOURCE_GROUP_ID string = resourceGroup().id
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = pooledInfra.outputs.containerRegistryLoginServer
