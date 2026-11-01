# Task 025 — Workload identity minimum-permissions report

**Status: Corrected offline research; awaiting independent reviewer approval.**
**Research cut-off:** 2026-10-28
**Scope:** Static repository evidence as summarized in Go Gunhee's supplied research report, plus direct retrieval of the Microsoft Learn sources listed below.
**Use:** Decision support only. This report is not authorization, a live access review, or approval of any observed or proposed grant.

## Executive conclusion

For the repository's custom ACA relay → Fabric Data Agent MCP endpoint, the supplied static-code report describes ACA Managed Identity as the assertion source for workload identity federation; the Fabric-facing token is for a Service Principal. Microsoft's MCP documentation accepts a user or service-principal token, requires the `https://api.fabric.microsoft.com/.default` scope, and says the caller needs access to the target workspace and data agent. It does **not** state the MCP-specific minimum workspace role. Therefore, the exact workspace/item grant for this transport remains **`NEEDS_PLATFORM_JUSTIFICATION`**; do not infer it from another Data Agent flow.

For the approved Power BI semantic-model source, Microsoft documents **Read** as sufficient for Data-Agent-mediated queries; Build and workspace roles are not required for that model access. The separate direct Power BI Execute Queries API requires Read and Build and is not the path described here.

This report does not verify tenant settings, deployed configuration, current grants, or live Data Agent existence. Do not remove or change any observed grants based on this report. In particular, keep the contemplated offset-plan serving-view candidate separate from the approved semantic-model source.

## Scope and evidence limits

- No Azure, Fabric, Foundry, or tenant operation was performed. No resource, tenant, data, or permission query was made. No grants were changed; no code was changed; nothing was deployed, committed, or pushed.
- Microsoft Learn pages were directly fetched for this report. The sources and retrieval record are in [Source register](#source-register).
- Repository code observations below are transcribed from Go Gunhee's supplied research report, which records static reads and exact path/line citations. In accordance with the task scope, repository files were not reread for this report.
- Historical repository security documentation cited by Go reported no live Data Agent confirmed running. The supplied grant observations remain unaccepted historical observations. Neither those observations nor this offline research establishes current effective access, a breach, or a current live service state.
- `NEEDS_PLATFORM_JUSTIFICATION` means the cited documentation does not establish a safe exact minimum for the stated use. It is not a grant recommendation.

## Architecture and identity finding (static-code report)

Go's source report cites `Program.cs:146-154` and `ServiceTokenSources.cs:66-143`: in Azure, `ManagedIdentityCredential` supplies an assertion for workload identity federation; `ClientAssertionCredential` uses that assertion to mint a **Service Principal** token. The code report does not describe the ACA Managed Identity as the identity presented directly to Fabric.

The source report also cites:

- `Program.cs:58-61`: when `FABRIC_TOKEN_SCOPE` is unset, the fallback is `https://analysis.windows.net/powerbi/api/.default`.
- `local.settings.example.json:9`: the example explicitly sets `https://api.fabric.microsoft.com/.default`.
- `local.settings.example.json:13` and `FabricMcpRelayClient.cs:1-82`: the example endpoint follows the Fabric Data Agent MCP endpoint shape.

This is a **configuration-drift/authentication-failure risk only**: if a deployment relies on the fallback rather than configuring the MCP-documented scope, its token audience may not match the MCP endpoint. Deployment configuration was not checked. This is not an authorization-escalation finding, and no code or configuration change is recommended here.

## Operation and surface findings

### Custom ACA relay → Fabric Data Agent MCP runtime

| Question | Finding |
|---|---|
| Surface | Custom ACA relay calling the published Data Agent MCP endpoint; the repository uses this custom relay rather than Foundry's native Fabric tool. |
| Supported caller | The MCP Learn page says the token can represent a user or a Service Principal. |
| Required token scope | `https://api.fabric.microsoft.com/.default`. Keep this distinct from the Power BI resource scope documented for the separate SP client-credentials Data Agent flow below. |
| Access requirement | Token must have permission to access the target workspace and Data Agent. The caller must also have read access to the configured data source. |
| Exact minimum workspace role | **Not specified for MCP transport. `NEEDS_PLATFORM_JUSTIFICATION`.** Do not infer the role from the separate SP client-credentials article or another surface. |
| Other prerequisites | Data Agent must be published; capacity and applicable cross-geo tenant settings are prerequisites. Current tenant settings and deployment state are unknown. |
| Data handling | The MCP source warns responses might leave Fabric's compliance boundary or geographic region and be handled under the MCP client's terms and policies. |

### Separate Data Agent service-principal client-credentials flow

| Question | Finding |
|---|---|
| Surface | The dedicated Data Agent Service Principal article's natural-language query/client-credentials path; it is not proof of the minimum role or token scope for the custom MCP transport. |
| Supported caller and limitation | The article supports a Service Principal and explicitly says Managed Identity is not currently supported as the direct Fabric-facing Data Agent authentication identity. |
| Workspace role | The article specifies **Member or Contributor** for the Service Principal; Admin is only required if it must manage the workspace. Do not treat this as the established MCP-specific minimum. |
| Source access | Read access to every attached source is required. |
| Token scope | `https://analysis.windows.net/powerbi/api/.default`. This differs from the MCP-specific Fabric API scope above. |
| Tenant prerequisite | The article requires the Fabric tenant setting **Service principals can use Fabric APIs**. Whether it is enabled in the relevant tenant was not verified. |

### Power BI semantic model accessed through a Fabric Data Agent

| Question | Finding |
|---|---|
| Source in scope | The approved source is the `sm_drillrun_summary` Power BI semantic-model path, as identified in Go's report from the contract/security-posture documents. |
| Documented minimum | **Read** on the semantic model. The sharing article states Read is sufficient for Data-Agent-mediated semantic-model queries; Build and workspace roles are not required for this model access. |
| Boundary | This is the source permission for the approved model path. It does not answer the separate permission needed to access the published Data Agent/workspace through MCP. |
| Not in scope | The contemplated offset-plan serving views are a different, unapproved source candidate. Do not infer, authorize, or extend this model permission finding to that serving-view scope. TASK-013 and Jason's source decisions govern it. |

### Direct Power BI Execute Queries REST API (contrast only)

| Question | Finding |
|---|---|
| Surface | Direct `POST .../datasets/{datasetId}/executeQueries`, not a Data-Agent-mediated query. |
| Documented permissions | Dataset Read **and Build**, plus the `Dataset Execute Queries REST API` tenant setting. The page also notes the Power BI service-principal tenant setting for SP use. |
| Why separate | These requirements do not replace or raise the documented minimum for a query made through a Fabric Data Agent. Do not apply this API's Build requirement to the approved Data-Agent-mediated model path. |

### Foundry native Microsoft Fabric data agent tool

| Question | Finding |
|---|---|
| Status on report date | **Scheduled for deprecation on November 6, 2026; not yet deprecated as of October 28, 2026.** The page directs readers to Fabric IQ. |
| Identity documentation | The prerequisites say “Use user identity authentication or service principal,” while the “Identity passthrough and access control” section says the integration uses OBO, to use user identity, and that Service Principal authentication is not supported. This is an internal contradiction in the page. Do not state a definite identity conclusion for this native tool without clarification. |
| Relevance | This is a separate Foundry-native integration and is not the custom ACA MCP relay path described by the supplied static-code report. Its contradictory identity guidance must not be used to determine the custom MCP caller's support. |

### Foundry Fabric IQ tool

| Question | Finding |
|---|---|
| Documentation status | The Fabric IQ Learn page exists and its `updated_at` is 2026-10-23. Go's earlier report claim that the page was a 404/unknown is stale and corrected here. |
| Identity/access statement | For the Fabric Data Agent item, the page says the calling user or Service Principal needs read access to the Data Agent and each source. It describes Foundry connections that can reuse incoming user context or establish a separate OAuth session; direct clients of the published Data Agent MCP endpoint can use a user or Service Principal token. |
| Relevance | Fabric IQ is a different Foundry tool surface. It is not the repo's custom ACA MCP relay, and its connection behavior does not establish the MCP-specific workspace role for that relay. |

### Data Agent control-plane reads (not runtime query permission)

| Operation | Item permission | Required delegated scope | Identity support | Boundary |
|---|---|---|---|---|
| Get Data Agent metadata | Read | `Item.Read.All` or `Item.ReadWrite.All` | User, Service Principal, and Managed Identity | Metadata GET only; does not establish runtime MCP permission. |
| Get Data Agent definition | Read and write | `Item.ReadWrite.All` | User, Service Principal, and Managed Identity | Definition GET only; does not establish runtime MCP permission. |

Do not conflate these control-plane API permissions with runtime execution. In particular, the definition endpoint's read-and-write item permission is not a requirement established for querying the published agent through MCP.

## Observed grants and disposition

The supplied source report describes Contributor, Lakehouse, and Data Agent grants as unaccepted observations, not an accepted baseline. No live grant state was checked. The historical security documentation cited by Go reported no live Data Agent confirmed running; that historical statement is not current tenant verification.

| Observation category (if present) | Offline conclusion | Disposition |
|---|---|---|
| Contributor/workspace grant | The separate SP client-credentials article documents Member or Contributor; the MCP article does not specify the exact minimum role. Whether a grant is needed for runtime, maintenance, or another use is not verified. | **Do not remove or change.** Exact MCP role and current purpose remain `NEEDS_PLATFORM_JUSTIFICATION`. |
| Lakehouse/serving-view grant | The currently approved source is the semantic model, not the contemplated serving-view candidate. The model's Read finding does not justify or refute a separate Lakehouse grant. | **Do not remove or change.** Keep the serving-view scope unauthorized unless Jason's source decision changes it. |
| Data Agent item grant | The sharing article describes published-query-only sharing separately from View details and Edit and view details. The sources reviewed do not establish which exact sharing tier maps to a Service Principal calling this MCP endpoint. | **Do not remove or change.** MCP-specific item grant remains `NEEDS_PLATFORM_JUSTIFICATION`. |

No permission-removal recommendation is made. Any minimum not explicitly established for the exact operation remains `NEEDS_PLATFORM_JUSTIFICATION`; the platform owner must establish the actual purpose and live requirement before any grant decision.

## Final conclusions

1. **Identity design, static only:** the supplied code research describes ACA Managed Identity as the WIF assertion source and a Service Principal as the Fabric-facing identity. This supports a non-user-specific design for the custom path, but does not verify a deployment or its effective access.
2. **Custom MCP runtime:** use the MCP-documented Fabric API scope and provide the caller access to the target workspace and Data Agent plus source read access. The exact MCP-specific workspace role is undocumented in the sources reviewed; keep it `NEEDS_PLATFORM_JUSTIFICATION`. Do not infer Member/Contributor from the separate client-credentials article.
3. **Approved source:** Read on the semantic model is sufficient for Data-Agent-mediated queries. Do not add a Build or workspace-role requirement by conflating it with direct Execute Queries.
4. **Different Foundry surfaces:** the native Fabric tool is scheduled for deprecation, with contradictory identity statements on its page. Fabric IQ exists and documents user/SP read access, but is a separate surface; neither changes the custom relay finding.
5. **Control plane differs from runtime:** metadata GET and definition GET have distinct documented item permissions/scopes and do not determine runtime query permissions.
6. **No live authorization conclusion:** no tenant setting, deployed scope, effective grant, or live Data Agent was verified. No existing grant is approved, disproved, or recommended for removal by this report.

## Source register

All sources below are first-party Microsoft Learn pages directly retrieved for this report. `updated_at` is the page's published metadata; it is not the retrieval time. **Direct retrieval batch recorded:** `2026-10-28T17:35:20Z` (UTC). Each entry was fetched in that batch; no third-party source is used.

| Source title | URL | `updated_at` (UTC) | Retrieval time (UTC) |
|---|---|---|---|
| Use the Microsoft Fabric data agent with Foundry agents | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/fabric | `2026-10-14T22:16:00Z` | `2026-10-28T17:35:20Z` |
| Connect agents to Microsoft Fabric with Fabric IQ (preview) | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/fabric-iq | `2026-10-23T22:13:00Z` | `2026-10-28T17:35:20Z` |
| Data agent as Model Context Protocol server | https://learn.microsoft.com/en-us/fabric/data-science/data-agent-mcp-server | `2026-09-04T11:03:00Z` | `2026-10-28T17:35:20Z` |
| Use service principal authentication with Fabric data agent | https://learn.microsoft.com/en-us/fabric/data-science/data-agent-service-principal | `2026-09-29T05:57:00Z` | `2026-10-28T17:35:20Z` |
| Fabric data agent sharing and permission management | https://learn.microsoft.com/en-us/fabric/data-science/data-agent-sharing | `2026-06-23T22:07:00Z` | `2026-10-28T17:35:20Z` |
| Items - Get Data Agent Definition - REST API (DataAgent) | https://learn.microsoft.com/en-us/rest/api/fabric/dataagent/items/get-data-agent-definition | `2026-10-19T22:06:00Z` | `2026-10-28T17:35:20Z` |
| Items - Get Data Agent - REST API (DataAgent) | https://learn.microsoft.com/en-us/rest/api/fabric/dataagent/items/get-data-agent | `2026-10-22T22:05:00Z` | `2026-10-28T17:35:20Z` |
| Datasets - Execute Queries - REST API (Power BI Power BI REST APIs) | https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/execute-queries | `2026-09-15T22:05:00Z` | `2026-10-28T17:35:20Z` |
