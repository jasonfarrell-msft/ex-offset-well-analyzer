targetScope = 'resourceGroup'

@description('Azure region for the registry.')
param location string

@description('Globally unique Azure Container Registry name.')
@minLength(5)
@maxLength(50)
param containerRegistryName string

@description('Tags applied to the registry.')
param tags object

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2025-11-01' = {
  name: containerRegistryName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    // POC access stays public, but all registry credential-based access is disabled.
    adminUserEnabled: false
    anonymousPullEnabled: false
    dataEndpointEnabled: false
    encryption: {
      status: 'disabled'
    }
    networkRuleBypassAllowedForTasks: false
    publicNetworkAccess: 'Enabled'
    // AcrPull is enforced at registry scope by the app stage.
    roleAssignmentMode: 'LegacyRegistryPermissions'
  }
}

output containerRegistryId string = containerRegistry.id
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
