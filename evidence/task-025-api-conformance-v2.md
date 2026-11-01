# TASK-025 API Conformance — Microsoft Fabric Data Agent Definition

- **Plan reference:** `plan/process-task-025-remediation-reverification-1.md`, TASK-002; REQ-003 and REQ-007
- **Requested by:** Project requester
- **Research performed:** 2026-10-29
- **Endpoint page retrieved:** 2026-10-29T12:31:20Z (UTC, approximate local retrieval timestamp)
- **Research method:** Read-only retrieval of the current official Microsoft Learn endpoint page and its linked conceptual Data Agent definition page. No search-result snippets were used.

## Decision

The Data Agent-specific API reference documents a supported **POST request shape with no `format` query parameter**. The parameter is explicitly optional, and the official sample request omits it. Therefore, the exact no-format request shape is documentation-supported; its use is not a guessed request shape and does not require inventing a query value.

This evidence does **not** establish that the service defaults to JSON, specify the result format for an omitted parameter, or document any literal value for the optional `format` query parameter. Do not infer a default or guess a literal such as `json`. The response schema separately defines `DataAgentPublicDefinition.format` as a string. Capture that field if it is returned; it is evidence from the response, not an assumed default.

`LIVE_CALL_READINESS` remains **BLOCKED** for independent gates: intended caller/identity reconciliation and acceptance, a separate Jason-approved exact per-window manifest hash, required ACL and complete baseline prerequisites, and all other applicable operational approvals and bounds. The unresolved response-format/default question is **not** a blocker to the documented no-format request shape. This report grants no live-call authority; no live call was made.

## Conformance matrix

| Element | Current official documentation | Result |
|---|---|---|
| Endpoint, method, and path | **Items - Get Data Agent Definition - REST API (DataAgent)**, “Interface” and “Examples > Get a DataAgent public definition example > Sample request”: `POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/dataAgents/{dataAgentId}/getDefinition`. | Data Agent-specific endpoint and method are documented. |
| No-format request shape | The “Interface” section shows the route without a query string and says the `format` parameter is optional. The official “Sample request” uses the route without `?format=...`. | **Confirmed: the exact no-format request shape is documented and allowed.** This does not claim what result format omission produces. |
| `format` query literals/default | “URI Parameters” describes `format` as an optional query string of type `string` and says only “The format of the data agent public definition.” Neither the endpoint page nor its sample enumerates literal values or states an omitted-parameter default. | **Not documented.** Do not invent a literal or infer a default. If a nonempty `format` parameter is used in a future separately approved request, use only a literal officially documented or sanctioned by Microsoft/platform. |
| Response definition format | The “Definitions > DataAgentPublicDefinition” table lists `format` (string) and `parts` (`DataAgentPublicDefinitionPart[]`). The sample `200` response shows `definition.parts`, but does not show a `definition.format` property. | Capture `definition.format` if present in an actual response. Do not assume it is present or assume its value. |
| Definition response envelope | “Responses” and “Examples > Sample response” document `200 OK` with `DataAgentDefinitionResponse`; the example has `definition.parts` with `path`, `payload`, and `payloadType`, including `InlineBase64`. | The response contract documents `definition.parts`; validate actual responses and preserve unavailable/missing fields as required by the approved evidence schema. |
| Caller identity support | “Microsoft Entra supported identities” lists User and “Service principal and Managed identities” as supported (`Yes`). | Service principal and managed identity support is documented for this API. This does not verify the tenant’s actual caller chain or its effective authorization. |
| Required permissions | “Permissions” states the caller must have read and write permissions for the DataAgent. “Required Delegated Scopes” lists `Item.ReadWrite.All`. | Documented requirements only; no tenant permissions or grants were inspected. |
| Long-running operation | “Responses” documents `202 Accepted` with `Location`, `x-ms-operation-id`, and `Retry-After`; the example gives a `202` header example. The page identifies this API as supporting LRO. | LRO behavior is documented. Treat 202 as accepted/in progress, not the completed definition. Follow the documented LRO procedure and approved window limits. |
| Definition-part paths | Endpoint “Sample response” uses `DataAgentV1.json` and `.platform`. The linked conceptual page, **Data Agent item definition**, sections “Supported formats,” “Definition parts,” and “Definition example,” describes JSON and paths under `Files/Config/...`, including draft/published files and `Files/Config/publish_info.json`. | **Residual disagreement.** The part-path representations differ. Do not assume either list is authoritative for strict path validation pending sanctioned clarification. The conceptual page’s JSON statement does not document the endpoint’s omitted-query result behavior. |
| Initiating-call throttle | The endpoint “Responses” section documents `429 Too Many Requests` and `Retry-After`, but gives no numeric initiation-call limit. | No numeric initiating throttle is documented on the reviewed endpoint page. Do not apply a separate LRO polling limit to this initiation call. |

## Evidence provenance and limits

1. **Items - Get Data Agent Definition - REST API (DataAgent)** — https://learn.microsoft.com/en-us/rest/api/fabric/dataagent/items/get-data-agent-definition. Page title and sections cited above: “Permissions,” “Required Delegated Scopes,” “Microsoft Entra supported identities,” “Interface,” “URI Parameters,” “Responses,” “Examples,” “Definitions,” and “DataAgentPublicDefinition.” Page metadata reports `updated_at: 2026-10-19T22:06:00Z`; that is page metadata, not this retrieval time.
2. **Data Agent item definition - Microsoft Fabric REST APIs** — https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/data-agent-definition. Sections cited above: “Supported formats,” “Definition parts,” and “Definition example.” Its statement that Data Agent items support JSON describes conceptual definition structure and is not evidence for the endpoint’s omitted-query result behavior.

This documentation review did not inspect a tenant, authenticate, inspect effective permissions, make a Fabric request, or alter any resource.

## Historical observation

The previously observed 198-byte response is historical, unaccepted evidence. It was not reproduced during this review and is not treated as a valid empty definition or as proof of the response to the documented no-format request shape.

## Readiness and next gates

- `DATA_AGENT_NO_FORMAT_REQUEST_SHAPE`: **DOCUMENTATION-SUPPORTED**
- `FORMAT_LITERAL_OR_OMITTED_RESULT`: **NOT DOCUMENTED; NO DEFAULT INFERRED**
- `DEFINITION_PART_PATH_RECONCILIATION`: **UNRESOLVED**
- `LIVE_CALL_READINESS`: **BLOCKED** by independent identity reconciliation/acceptance, exact per-window Jason approval bound to the manifest SHA-256, ACL and complete-baseline prerequisites, and every other applicable gate.
- `LIVE_CALL_AUTHORITY`: **NONE GRANTED BY THIS REPORT**

Any future live call requires all independent gates to be met and must bind the exact documented no-format request shape to its separately approved manifest. If a nonempty `format` query parameter is proposed, its literal must first be documented or sanctioned; a guessed value is prohibited. No invocation is authorized here.
