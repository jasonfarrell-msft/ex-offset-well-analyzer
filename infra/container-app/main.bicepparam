using './main.bicep'

param location = 'centralus'
param containerRegistryName = 'acrdrilladvisormx01'
param logAnalyticsWorkspaceName = 'log-drill-advisor-wfrd-mx01'
param managedEnvironmentName = 'cae-drill-advisor-wfrd-mx01'
param containerAppName = 'ca-drill-advisor-wfrd-mx01'

param containerImage = 'acrdrilladvisormx01.azurecr.io/drill-advisor@sha256:15b1104cb9581fb757e9e0d9b5c46b40182995063d96bb69a64ff39908df3bbc'

param managedIdentityResourceId = '/subscriptions/bb4b2781-6739-4fa1-994e-4ad6ce55c59c/resourceGroups/rg-welladvisor-mx01/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-drill-advisor-wfrd-mx01'
param managedIdentityPrincipalId = '882c8c40-02e1-479f-8fbc-93d39412a571'
param entraTenantId = 'e90bd921-0e00-4e6f-b87c-713670ee27bf'
param managedIdentityClientId = '56715a5f-8b03-47bc-9d64-787b96ba56ae'
param fabricAppClientId = 'cd20994e-2072-4680-97be-1ba6ae8a911b'
param foundryProjectPrincipalId = 'f9b86896-cc12-4a2f-92ff-edf9d5e570ef'
param foundryProjectClientId = '92d21e37-1914-4f61-aa00-19b5d26c8064'
param mcpAudience = 'api://0e956ed5-6da6-477a-b508-3c6cdf5b2861'
param foundryProjectEndpoint = 'https://foundry-sandbox-swc-mx01.services.ai.azure.com/api/projects/drill-project'
param foundryAgentName = 'welladvisor-fabric-orchestrator'
param fabricDataAgentMcpEndpoint = 'https://api.fabric.microsoft.com/v1/mcp/workspaces/4e1977a8-d7ff-487e-b42d-c4b3bc118f3d/dataagents/dd1cd69f-3b49-4575-932f-1d871f73d2e2/agent'
param fabricTokenScope = 'https://api.fabric.microsoft.com/.default'
param publicChatEnabled = 'true'

param tags = {
  application: 'Drill Advisor'
  environment: 'poc'
  dataClassification: 'synthetic'
  SecurityControl: 'Ignore'
}
