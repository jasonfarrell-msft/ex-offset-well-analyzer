# TASK-002 API Conformance Documentation Review — Fabric Data Agent Definition Read-back/Export

- **Plan reference:** `plan/process-task-025-remediation-reverification-1.md`, TASK-002; requirements REQ-003 and REQ-007
- **Requested by:** Project requester
- **Research performed:** 2026-10-28
- **Research method:** Read-only retrieval of the current official Microsoft Learn pages listed below. No search-result snippets were used as evidence.

## Decisive summary

| Decision | Result |
|---|---|
| `DATA_AGENT_ENDPOINT_DOCUMENTATION` | `CONFIRMED` |
| `LIVE_CALL_READINESS` | `BLOCKED` |
| `PROCEDURAL_OUTCOME` for a live definition call | `DIAGNOSIS_BLOCKED_DOCUMENTATION` |
| TASK-002 exit | **NOT MET — do not label `SUPPORTED`** |

Official, Data Agent-specific documentation establishes a dedicated definition API surface and documents service-principal/managed-identity support for that API. It does **not** resolve the supported omitted/default behavior or exact literal value for the optional `format` query parameter. Under approved-plan REQ-003/REQ-007, a live definition call must not proceed until Microsoft/platform confirms that behavior. Independent per-window approval is also absent. Documentation confirmation is not live-call authorization, and no live call is authorized by this task.

The initiation-call throttle limit is a separate residual: Learn documents a `429`/`Retry-After` response but does not publish a specific throttle number for the Data Agent definition initiation call. The exact expected definition-part paths are also not settled: the operation response example and the conceptual part manifest differ. Do not use an assumed path list as a hard validator pending sanctioned clarification.

## Scope and activity boundary

This review covers public Microsoft Learn documentation only. **No live tenant, Azure, Fabric, or Data Agent operation was performed.** No API call to a tenant/resource, data query, authentication, permission inspection or change, deployment, definition edit, publication, commit, or push was performed. Public Learn pages were retrieved read-only. This report contains no tenant response payloads, tokens, keys, workspace IDs, item IDs, or other tenant data.

## Conformance matrix

| # | Element | Current official documentation | Result for TASK-002 |
|---|---|---|---|
| 1 | Data Agent-specific endpoint | The Data Agent operation page specifies `POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/dataAgents/{dataAgentId}/getDefinition` (S3). | **Documented / confirmed.** This is a Data Agent-specific route. |
| 2 | Generic Items endpoint | Generic `POST /v1/workspaces/{workspaceId}/items/{itemId}/getDefinition` documentation says support depends on item type and directs readers to the corresponding API (S1). | **Conditional only.** Do not use this generic page as proof of Data Agent support or substitute it for S3. |
| 3 | Format support and invocation behavior | The conceptual Data Agent page says, “Data Agent items support the JSON format” (S4). The operation page describes the optional `format` query parameter only as “The format of the data agent public definition”; it does not enumerate values or state a default (S3). | **Residual blocker.** The supported omitted/default behavior and exact literal query value remain unresolved. “JSON” does not establish a literal token such as `json`, nor what happens when the parameter is omitted. Do not guess or invoke. |
| 4 | Service principal / managed identity support | S3’s identity table lists “Service principal and Managed identities” as “Yes.” S5 independently lists “Yes” for the Data Agent metadata operation. | **Documented for these specific APIs.** This is not a verification of any tenant’s setting, caller configuration, or effective authorization. |
| 5 | Required permissions and scope | S3 says, “The caller must have read and write permissions for the DataAgent,” and lists delegated scope `Item.ReadWrite.All`. | **Documented requirement only.** No actual tenant permissions were checked. The delegated-scope listing does not prove that a service principal has effective access. |
| 6 | Tenant setting and actual access | Fabric identity guidance says the tenant setting “Service principals can use Fabric APIs” must be enabled by a Fabric administrator (S9). | **Unverified.** This documentation review did not inspect the tenant-specific setting, assignments, effective permissions, or successful access. |
| 7 | 200 response | S3 documents `200 OK` with `DataAgentDefinitionResponse`, whose definition contains parts with `path`, `payload`, and `payloadType`; `InlineBase64` is the documented payload type. | **Documented response contract.** This does not resolve which conflicting sample/manifest path list should be enforced. |
| 8 | Definition-part path consistency | The S3 response example uses `DataAgentV1.json` and `.platform`. S4 instead lists `Files/Config/data_agent.json`, draft configuration/data-source paths, published-stage/data-source paths, and `Files/Config/publish_info.json` when published. | **Inconsistency explicitly retained.** Do not assume either list is authoritative or use the conceptual list as a hard validator without sanctioned clarification. |
| 9 | 202 / LRO behavior | S3 says the API supports LRO and documents `202 Accepted` with an empty body and `Location`, `x-ms-operation-id`, and `Retry-After` headers. The generic LRO guide describes these headers and polling (S6). | **Documented.** Treat 202 only as operation acceptance, not as the definition response. |
| 10 | LRO terminal status / result | S6 describes polling operation state until `Succeeded` or `Failed`; after `Succeeded`, retrieve the result through the documented operation-result API. S7 documents the state endpoint and S8 the result endpoint. | **Documented shared LRO behavior.** It does not authorize an invocation and cannot cure the unresolved `format` behavior. |
| 11 | Throttling | S3 documents `429 Too Many Requests` with `Retry-After`. S7 and S8 list 500 calls/min for the Long-Running Operations API endpoints. | **Initiation throttle residual.** The 500 calls/min figures apply to the LRO state/result APIs, not the Data Agent initiation call. No numeric initiation-call limit was found on S3. |
| 12 | Error contract | S3 documents `429` and `Retry-After`, and lists `OperationNotSupportedForItem` under other status codes. | **Documented contract.** No live error response was collected. |
| 13 | Pagination | The operation is a single-item definition request; the reviewed operation page documents no pagination. | **Not applicable as documented.** Do not infer this as proof of a particular response's completeness. |
| 14 | Prior broad permissions / breach | The documentation states requirements and identity support; it does not report tenant assignments or access outcomes. | **Not established here.** Broad prior permission observations, if any, prove neither effective access nor a breach. This review establishes no tenant-specific permission state and no breach. |

## Required distinctions and residuals

1. **Documentation versus readiness:** `DATA_AGENT_ENDPOINT_DOCUMENTATION=CONFIRMED` describes the public API reference only. `LIVE_CALL_READINESS=BLOCKED` follows because REQ-003/REQ-007 require confirmation of the supported format/default behavior before any invocation. Thus the TASK-002 exit criteria are unmet; the correct procedural outcome for a prospective live definition call is `DIAGNOSIS_BLOCKED_DOCUMENTATION`, not `SUPPORTED`.
2. **Endpoint identity versus generic API:** The Data Agent-specific route and its identity table are the supporting references. The generic Items endpoint remains conditional on item type and is not evidence that the Data Agent operation can be called using a generic route.
3. **Documented identity support versus tenant authorization:** Data Agent API reference pages document service principal/managed identity support. The tenant setting, identity chain, actual grants, and effective permissions were not verified. Required permissions in documentation are not proof those permissions exist or that access succeeds.
4. **Permissions versus access or breach:** Broad permission observations alone do not prove which data or metadata is effectively accessible, and do not prove a breach. This documentation-only review established neither.
5. **Definition-part mismatch:** The operation example paths (`DataAgentV1.json`, `.platform`) conflict in form and content with the conceptual page’s `Files/Config/...` manifest, including draft/published paths and `publish_info`. Do not select one as authoritative or validate exact expected paths until Microsoft/platform provides sanctioned clarification.
6. **Remaining documentation residuals:** (a) supported literal/default/omitted `format` behavior, which blocks invocation under REQ-003/REQ-007; and (b) the numeric throttle for the initiating Data Agent definition call, which is not stated in the operation page. The documented LRO polling limit must not be applied to the initiation call.

## Official Microsoft Learn sources

`Retrieved at` is the exact UTC time at which this report’s read-only retrieval completed. `updated_at` is the separate Microsoft Learn page metadata value; it is not a retrieval time. No earlier fetch time is asserted.

1. **Items — Get Item Definition — REST API (Core):** https://learn.microsoft.com/en-us/rest/api/fabric/core/items/get-item-definition. `updated_at`: 2026-10-19. `Retrieved at`: **2026-10-28T17:06:55Z**. Generic reference only. Quote: “This API is supported for a number of item types” and “Check the corresponding API for the item type you're calling, to see if your call is supported.”
2. **Overview of item definitions — Microsoft Fabric REST APIs:** https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/item-definition-overview. `updated_at`: 2026-10-26. `Retrieved at`: **2026-10-28T17:06:56Z**. General definition overview; not used to infer Data Agent invocation behavior.
3. **Items — Get Data Agent Definition — REST API (DataAgent):** https://learn.microsoft.com/en-us/rest/api/fabric/dataagent/items/get-data-agent-definition. `updated_at`: 2026-10-19. `Retrieved at`: **2026-10-28T17:09:03Z**. Data Agent-specific method/path, optional `format` parameter, permissions, delegated scope, identity support, response examples, and response/LRO/error contracts.
4. **Data Agent item definition — Microsoft Fabric REST APIs:** https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/data-agent-definition. `updated_at`: 2026-02-11. `Retrieved at`: **2026-10-28T17:06:56Z**. Conceptual JSON format statement and Data Agent part manifest, including draft/published paths and `publish_info.json`.
5. **Items — Get Data Agent — REST API (DataAgent):** https://learn.microsoft.com/en-us/rest/api/fabric/dataagent/items/get-data-agent. `updated_at`: 2026-10-22. `Retrieved at`: **2026-10-28T17:06:56Z**. Sibling metadata operation; identity support and permission/scope details are not substituted for definition-call readiness.
6. **Long running operations — Microsoft Fabric REST APIs:** https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation. `updated_at`: 2025-07-02. `Retrieved at`: **2026-10-28T17:06:56Z**. Quote: “HTTP status code 202 Accepted - The response body is empty.” Documents LRO headers and polling guidance.
7. **Long Running Operations — Get Operation State — REST API (Core):** https://learn.microsoft.com/en-us/rest/api/fabric/core/long-running-operations/get-operation-state. `updated_at`: 2026-09-24. `Retrieved at`: **2026-10-28T17:06:57Z**. Operation-state route, terminal states, and 500 calls/min LRO endpoint limit.
8. **Long Running Operations — Get Operation Result — REST API (Core):** https://learn.microsoft.com/en-us/rest/api/fabric/core/long-running-operations/get-operation-result. `updated_at`: 2026-09-24. `Retrieved at`: **2026-10-28T17:06:57Z**. Operation-result route and 500 calls/min LRO endpoint limit.
9. **Identity support for logging into Microsoft Fabric:** https://learn.microsoft.com/en-us/rest/api/fabric/articles/identity-support. `updated_at`: 2026-04-08. `Retrieved at`: **2026-10-28T17:06:57Z**. Quote: “Each API's reference page lists whether the API supports service principals and managed identities.” Documents the tenant setting requirement.
10. **Microsoft Fabric REST APIs scopes:** https://learn.microsoft.com/en-us/rest/api/fabric/articles/scopes. `updated_at`: 2025-07-02. `Retrieved at`: **2026-10-28T17:06:57Z**. Clarifies generic/specific item scopes and that direct service-principal/managed-identity access is restricted by Fabric admin controls and artifact permissions.

## Sanctioned next step

Do not make a live definition call under this task. Before an invocation is considered, obtain current, sanctioned Microsoft/platform confirmation of the exact supported `format` literal or omitted/default behavior and clarify which definition-part paths are authoritative for validation. Separately obtain an explicit Jason-approved per-window manifest and satisfy all other applicable approvals and gates. The initiation-call throttle question should also be raised with Microsoft/platform; do not treat the documented LRO polling quota as its answer.
