# Drill Advisor Functions rollback API

This .NET 8 isolated Functions project is retained as a rollback option after
the application moved to the .NET 10 ASP.NET Core host under `server/`. The new
host links the framework-neutral implementation files from this project, but
does not execute these Function entry points or trust SWA/Easy Auth headers.
Do not delete or deploy this rollback project as part of the ACA image build.

.NET 8 isolated Azure Functions backend exposing:

- anonymous browser chat at `POST /api/chat`; and
- anonymous offset analysis at `POST /api/offset-analysis` for
  `targets|candidates|compare` contract operations; and
- fixed-target streamable HTTP MCP relay at
  `POST|GET|DELETE /api/mcp/fabric-dataagent`.

## Security model

The browser supplies no token. `/api/chat` validates the linked Static Web Apps
anonymous principal from trusted platform headers and rejects direct Entra
callers. Local requests work only when `ALLOW_LOCAL_ANONYMOUS=true` and Azure
host markers are absent.

Public chat requests fail closed until an operator verifies Easy Auth plus
direct-origin blocking and explicitly sets
`TRUSTED_PLATFORM_AUTH_ENABLED=true`. The identity-restricted MCP route remains
available before public cutover so the backend chain can be validated.

The API uses one reusable `TokenCredential`: the configured user-assigned
managed identity in Azure and `AzureCliCredential` locally. Foundry tokens use
`https://ai.azure.com/.default`; caller tokens are never accepted or forwarded.
Offset analysis SQL reads use the same managed identity and request
`https://database.windows.net/.default`.

The MCP route requires the configured Foundry project managed identity object
ID and provider from trusted Easy Auth headers. Because app-only requests can
omit `X-MS-CLIENT-PRINCIPAL`, authorization requires the individual provider
and principal-ID headers and cross-checks the encoded principal when present.
Its target is only
`FABRIC_DATA_AGENT_MCP_ENDPOINT`. It strips inbound authorization and forwards
only `Accept`, content type, `MCP-Protocol-Version`, `MCP-Session-Id`, and
`Last-Event-ID`. The outbound Fabric token is acquired with a managed-identity
client assertion and `ClientAssertionCredential`. `FABRIC_TOKEN_SCOPE` accepts
only `https://api.fabric.microsoft.com/.default` or
`https://analysis.windows.net/powerbi/api/.default`; arbitrary caller or
configuration audiences are rejected at startup. There is no client secret or
certificate.

## Public controls

`PUBLIC_CHAT_ENABLED` defaults to false. The fixed-instance gate enforces a
2,000-character prompt limit, 3 requests/source/minute, source concurrency 1,
60 requests/minute globally, global concurrency 10, and 500 Foundry calls per
UTC day. Rejections include `Retry-After`.

The in-memory counters reset on restart and do not coordinate across instances.
Keep the Function App at one instance for this POC. Raw IPs, prompts, tokens,
and upstream results are never logged.

## Configuration and local run

Copy `local.settings.example.json` to ignored `local.settings.json`, fill the
identifier/endpoint placeholders, and explicitly set:

```json
{
  "PUBLIC_CHAT_ENABLED": "true",
  "ALLOW_LOCAL_ANONYMOUS": "true"
}
```

For offset analysis, also set:

```json
{
  "OFFSET_SQL_SERVER": "<sql-server-hostname>",
  "OFFSET_SQL_DATABASE": "<database-name>",
  "OFFSET_SQL_COMMAND_TIMEOUT_SECONDS": "30"
}
```

If SQL settings are missing, historical chat still runs; offset operations fail
closed with an explicit unavailable error.

Then authenticate Azure CLI for local Foundry access and run:

```bash
dotnet restore
dotnet build --no-restore
func start
```

The provider defaults are `anonymous` for the decoded SWA principal and linked
backend header, and `aad` for Foundry Easy Auth. Verify the actual linked
backend provider header and configure `SWA_BACKEND_IDENTITY_PROVIDER` if it
differs. Platform headers must not be trusted unless direct origin access is
blocked by the linked Function App's Easy Auth configuration.

## Live POC status

The API is deployed to `func-drill-advisor-wfrd-mx01.azurewebsites.net` with
both functions indexed. Easy Auth rejects anonymous direct-origin calls with
HTTP 401. The Foundry project identity reaches the MCP route and the relay
successfully authenticates the federated Fabric application, but the current
Fabric Data Agent call receives HTTP 401 when it queries the attached semantic
model. Public chat and trusted SWA header processing remain disabled, and the
Static Web App is intentionally unlinked. This is not a production-ready state.

## Validation

```bash
dotnet restore ../DrillAdvisor.Api.Tests/DrillAdvisor.Api.Tests.csproj
DOTNET_ROLL_FORWARD=Major dotnet build \
  ../DrillAdvisor.Api.Tests/DrillAdvisor.Api.Tests.csproj --no-restore
DOTNET_ROLL_FORWARD=Major dotnet test \
  ../DrillAdvisor.Api.Tests/DrillAdvisor.Api.Tests.csproj --no-build
dotnet format ../DrillAdvisor.Api.Tests/DrillAdvisor.Api.Tests.csproj \
  --verify-no-changes --no-restore
dotnet list ../DrillAdvisor.Api.Tests/DrillAdvisor.Api.Tests.csproj \
  package --vulnerable --include-transitive
```
