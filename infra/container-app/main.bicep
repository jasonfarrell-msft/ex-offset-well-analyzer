targetScope = 'resourceGroup'

@description('Azure region for all regional resources.')
param location string

@description('Name of the existing Azure Container Registry created by the registry stage.')
@minLength(5)
@maxLength(50)
param containerRegistryName string

@description('Log Analytics workspace name.')
@minLength(4)
@maxLength(63)
param logAnalyticsWorkspaceName string

@description('Container Apps managed environment name.')
param managedEnvironmentName string

@description('Container App name.')
param containerAppName string

@description('Required immutable ACR image reference in <login-server>/<repository>@sha256:<digest> format.')
@minLength(1)
param containerImage string

@description('Full resource ID of the existing user-assigned managed identity.')
param managedIdentityResourceId string

@description('Object ID (principal ID) of the existing user-assigned managed identity.')
param managedIdentityPrincipalId string

@description('Microsoft Entra tenant ID used by the application.')
param entraTenantId string

@description('Client ID of the existing user-assigned managed identity.')
param managedIdentityClientId string

@description('Client ID of the Microsoft Fabric application.')
param fabricAppClientId string

@description('Object ID of the Azure AI Foundry project principal.')
param foundryProjectPrincipalId string

@description('Client ID of the Azure AI Foundry project.')
param foundryProjectClientId string

@description('Microsoft Entra application ID URI accepted as the MCP audience.')
param mcpAudience string

@description('Azure AI Foundry project endpoint.')
param foundryProjectEndpoint string

@description('Azure AI Foundry agent name.')
param foundryAgentName string

@description('Microsoft Fabric Data Agent MCP endpoint.')
param fabricDataAgentMcpEndpoint string

@description('Microsoft Fabric token scope.')
param fabricTokenScope string

@description('Whether the public chat feature is enabled.')
@allowed([
  'true'
  'false'
])
param publicChatEnabled string

@description('Tags applied to all resources that support tags.')
param tags object

var acrPullRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
)
var containerRegistryLoginServer = '${containerRegistryName}.azurecr.io'

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2025-11-01' existing = {
  name: containerRegistryName
}

resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, managedIdentityPrincipalId, acrPullRoleDefinitionId)
  scope: containerRegistry
  properties: {
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRoleDefinitionId
  }
}

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2025-07-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  tags: tags
  properties: {
    features: {
      // Diagnostic settings use Azure Monitor ingestion and do not require workspace keys.
      disableLocalAuth: true
      enableLogAccessUsingOnlyResourcePermissions: true
      immediatePurgeDataOn30Days: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
    // Bound POC ingestion cost while preserving operational visibility.
    workspaceCapping: {
      dailyQuotaGb: 1
    }
  }
}

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' = {
  name: managedEnvironmentName
  location: location
  tags: tags
  properties: {
    // Azure Monitor routing avoids embedding or retrieving a Log Analytics shared key.
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    peerAuthentication: {
      mtls: {
        enabled: false
      }
    }
    peerTrafficConfiguration: {
      encryption: {
        enabled: false
      }
    }
    publicNetworkAccess: 'Enabled'
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    zoneRedundant: false
  }
}

resource managedEnvironmentDiagnostics 'Microsoft.Insights/diagnosticSettings@2016-09-01' = {
  name: 'service'
  scope: managedEnvironment
  location: location
  properties: {
    workspaceId: logAnalyticsWorkspace.id
    logs: [
      {
        category: 'ContainerAppConsoleLogs'
        enabled: true
        retentionPolicy: {
          days: 0
          enabled: false
        }
      }
      {
        category: 'ContainerAppSystemLogs'
        enabled: true
        retentionPolicy: {
          days: 0
          enabled: false
        }
      }
      {
        category: 'ContainerAppHTTPLogs'
        enabled: false
        retentionPolicy: {
          days: 0
          enabled: false
        }
      }
      {
        category: 'AppEnvSpringAppConsoleLogs'
        enabled: false
        retentionPolicy: {
          days: 0
          enabled: false
        }
      }
      {
        category: 'AppEnvSessionConsoleLogs'
        enabled: false
        retentionPolicy: {
          days: 0
          enabled: false
        }
      }
      {
        category: 'AppEnvSessionPoolEventLogs'
        enabled: false
        retentionPolicy: {
          days: 0
          enabled: false
        }
      }
      {
        category: 'AppEnvSessionLifeCycleLogs'
        enabled: false
        retentionPolicy: {
          days: 0
          enabled: false
        }
      }
    ]
    // The GA API returns a metric category that is absent from its Bicep type definition.
    metrics: [
      any({
        category: 'AllMetrics'
        enabled: false
        retentionPolicy: {
          days: 0
          enabled: false
        }
        timeGrain: 'PT1M'
      })
    ]
  }
}

resource containerApp 'Microsoft.App/containerApps@2026-01-01' = {
  name: containerAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityResourceId}': {}
    }
  }
  properties: {
    environmentId: managedEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      identitySettings: [
        {
          identity: managedIdentityResourceId
          lifecycle: 'All'
        }
      ]
      ingress: {
        // The public POC endpoint redirects HTTP to HTTPS at the managed ingress edge.
        external: true
        allowInsecure: false
        exposedPort: 0
        targetPort: 8080
        transport: 'auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: containerRegistryLoginServer
          identity: managedIdentityResourceId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'drill-advisor'
          image: containerImage
          env: [
            {
              name: 'ENTRA_TENANT_ID'
              value: entraTenantId
            }
            {
              name: 'MANAGED_IDENTITY_CLIENT_ID'
              value: managedIdentityClientId
            }
            {
              name: 'FABRIC_APP_CLIENT_ID'
              value: fabricAppClientId
            }
            {
              name: 'FOUNDRY_PROJECT_PRINCIPAL_ID'
              value: foundryProjectPrincipalId
            }
            {
              name: 'FOUNDRY_PROJECT_CLIENT_ID'
              value: foundryProjectClientId
            }
            {
              name: 'MCP_AUDIENCE'
              value: mcpAudience
            }
            {
              name: 'FOUNDRY_PROJECT_ENDPOINT'
              value: foundryProjectEndpoint
            }
            {
              name: 'FOUNDRY_AGENT_NAME'
              value: foundryAgentName
            }
            {
              name: 'FABRIC_DATA_AGENT_MCP_ENDPOINT'
              value: fabricDataAgentMcpEndpoint
            }
            {
              name: 'FABRIC_TOKEN_SCOPE'
              value: fabricTokenScope
            }
            {
              name: 'PUBLIC_CHAT_ENABLED'
              value: publicChatEnabled
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/healthz'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/readyz'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
              successThreshold: 1
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        // Scale-to-zero and a single replica minimize idle and burst cost for the POC.
        cooldownPeriod: 300
        minReplicas: 0
        maxReplicas: 1
        pollingInterval: 30
      }
    }
  }
  dependsOn: [
    acrPullRoleAssignment
  ]
}

output containerRegistryId string = containerRegistry.id
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.id
output managedEnvironmentId string = managedEnvironment.id
output containerAppId string = containerApp.id
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
