updated_at: 2026-10-29T12:20:25.294-04:00
focus_area: Final live offset handoff on deployed ACA+Foundry+Fabric path (Fabric stays running)
active_issues:
  - Coordinator browser workflow validation is still in progress; do not mark end-to-end browser pass yet
  - `sourceCount` remains `0` in response payloads; historical totals were independently verified from deterministic SQL/evidence
  - Working tree remains intentionally uncommitted; no commit/push authorized for this session
current_next_actions:
  - Preserve current live stack and keep Fabric running with the deployed ACA revision/image
  - Complete final browser workflow check and capture any additional evidence only if requested
  - Hold state for user acceptance without further app/data/config mutations
---

# What We're Focused On

## Final deployment handoff status (2026-10-29)

- Active Container App revision is `ca-drill-advisor-wfrd-mx01--0000007` at
  `https://ca-drill-advisor-wfrd-mx01.icytree-3fa8fc52.centralus.azurecontainerapps.io`
  using image digest
  `sha256:220cf57b89e14413a7c2221668e6d93fce68e8d02a53e4a0ef256a27265fa3a2`.
- Fabric is intentionally running for live offset analysis (`12` targets, `100` wells,
  `3,288` target-section rows; v1.1.0).
- Yoo Jinho's semantic single-target slice repair prevents historical-value
  multiplication; Baek Yoonho independently confirmed corrected historical values
  (Cobalt `247512.3`, Driftwood `170381.6`).
- Woo Jinchul's frontend fetch-loop fix (stable default API singletons +
  `AppRoot` composition test) is approved; redeployed image is live.
- Security review reported no findings.
- Evidence anchors: `evidence/deployment-live-offset-redeploy-20261029.json` and
  `evidence/fabric_diag/semantic_revision_e2e_20261029_yoojinho.json`. Earlier
  known-bad evidence is retained as historical, not final.
- Final browser workflow verification is currently being executed by the
  coordinator and is not yet recorded as passed.

## Live Offset Well Analysis delivery (2026-10-29; current assignment)

Jason explicitly superseded the prior offline-only scope and chose live offset
analysis delivery on the existing architecture:

`anonymous browser -> ACA /api/chat -> Foundry orchestrator -> protected ACA MCP relay -> Fabric Data Agent`

This is still a synthetic historical-summary POC with strict fail-closed
evidence rules and no real-data, write, prediction, or recommendation scope.
No new services/frameworks were authorized. No commit/push/branch authorization
was granted.

## Current runtime configuration snapshot (read-only cloud check)

- Azure subscription context is available (`TSJasonFarrell-Sub`).
- Container App `ca-drill-advisor-wfrd-mx01` is deployed with:
  - `PUBLIC_CHAT_ENABLED=true`
  - `FOUNDRY_PROJECT_ENDPOINT=https://foundry-sandbox-swc-mx01.services.ai.azure.com/api/projects/drill-project`
  - `FOUNDRY_AGENT_NAME=welladvisor-fabric-orchestrator`
  - `FABRIC_DATA_AGENT_MCP_ENDPOINT=.../workspaces/4e1977a8-d7ff-487e-b42d-c4b3bc118f3d/dataagents/dd1cd69f-3b49-4575-932f-1d871f73d2e2/agent`
  - `maxReplicas=1`
- Fabric capacity `fabricwelladvisorcusmx01` is `Paused` (F8), which blocks
  live Fabric/Data Agent answers until a bounded resume window is approved and
  executed.
- Foundry project `foundry-sandbox-swc-mx01/drill-project` exists and is
  provisioned in Sweden Central; model/deployment wiring for
  `welladvisor-fabric-orchestrator` still requires explicit read-back evidence.

## Foundry MCP Container App cutover

The active path is:

`anonymous browser -> Azure Container Apps /api/chat -> managed identity -> Foundry agent v7 -> authenticated Container App MCP relay -> Fabric Data Agent`

The cutover completed without rollback. Foundry connection
`fabric-dataagent-mi-bridge` now targets
`https://ca-drill-advisor-wfrd-mx01.icytree-3fa8fc52.centralus.azurecontainerapps.io/api/mcp/fabric-dataagent`
with `ProjectManagedIdentity` and audience
`api://0e956ed5-6da6-477a-b508-3c6cdf5b2861`.

Foundry assigned immutable version **7** to
`welladvisor-fabric-orchestrator`. It preserves active version 4 except for the
MCP `server_url`; version 4 remains available for rollback. Version 7 is
active/latest and version numbering was accepted as platform-assigned state.

Direct Foundry validation returned HTTP 200 in 20.933 seconds. Public
`POST /api/chat` returned HTTP 200 in 25.525 seconds (server latency 24,184 ms);
the continuation request using the returned conversation ID returned HTTP 200
in 31.550 seconds (server latency 31,279 ms). Validation preserved the exact
synthetic disclosure, returned 100 wells and five quarantined runs, completed
the MCP list/call path, and produced a typed `kpi-grid`. Anonymous MCP access
remains denied with HTTP 401 (0.461 seconds).

## Prior chronology (historical; not current direction)

The synthetic summary release, Fabric Lakehouse publication, SQL views, semantic model `sm_drillrun_summary` (`ee7583b6-5be7-4802-83a8-530ce7dd8351`), governed 36-case evaluation set, sole-user identity boundary, retention rules, and prohibited-exposure controls remain unchanged. Architecture remains **CONDITIONAL PASS**.

Historical Data Agent `72a3a511-ad36-4df8-842b-d6c268b2ff8a` was published only for the approved calibration path. Preflight run `20261025T000831Z-fc192489` failed closed with `STOP_REQUIRED` reason `preflight_failure` before any question, agent tool call, or calibration case was sent. The root cause was local: MCP wire field `inputSchema` maps to Python SDK attribute `input_schema`, while the validator read only the wire-style name. The otherwise valid tool inventory was rejected and the teardown path wrapped the failure in an `ExceptionGroup`.

The approved deletion rollback completed at `2026-10-25T00:08:54Z`, request ID `c4f2a6c5-ee5d-48c9-b9a9-a78d01d0433d`. A subsequent list verified that no Data Agents remained. The old ID and its complete lifecycle are immutable historical evidence; the record must not imply that it never existed.

Remediation commit `8abece2090620becf882089ad3d37b0427c9e982` supports both MCP SDK attribute names and preserves the underlying failure reason through grouped teardown exceptions. It was independently approved after 120 tests plus 51 subtests, Bandit, and pip-audit.

The same approved draft definition was recreated as `da_drillrun_summary` with new ID `961c0db2-e7c4-42f8-887c-039085290338`. Creation operation `ccddbdd1-d002-4465-b25c-9afe2edee27a` succeeded. The workspace, semantic model, and intended source selection are unchanged. The description is calibration-only.

Repository source and runner identifiers were rebound at commit `2db841d68b91b87400db7715e1a87af8ec9545ee`; 120 tests and 51 subtests pass. The live replacement draft matches the approved one-model, four-table source exactly except Fabric's empty `children` normalization. The Data Agent, semantic-model, and workspace ACLs contain only the approved user under the existing temporary Admin/Write/ReShare exception. The MCP remediation at `8abece2090620becf882089ad3d37b0427c9e982`, hardened runner at `1578b2e4d8c23c1019484bef4ebfb50dde0d10a0`, and identity/source/ACL/definition/runner/security reviews pass.

Replacement agent `961c0db2-e7c4-42f8-887c-039085290338` published successfully at `2026-10-25T00:32:14Z`, request ID `3348cf9e-642f-4995-909b-1f24a9b399bf`. It remains unshared and calibration-only.

Postpublication Q1-Q5 all pass. The published definition contains the exact approved six parts plus `.platform`; draft/published configuration, one model, and four tables match source except Fabric's `children: []` normalization. Agent and model ACLs each contain only Project requester (`61a37498-9ab6-43d2-b70f-706fd58274e7`), and prior workspace sole-user evidence is unchanged. Preflight `20261025T003243Z-8128b459` returned 401 for unauthenticated and wrong-token probes and passed the current delegated-user handshake. Exactly one question tool is exposed, with no action, admin, or write capability and no tool call during preflight. Evidence-safety and identity-cleanup checks pass with no credentials, raw response bodies, or secret markers persisted.

The first calibration run `20261025T004054Z-b79eede4` started at `2026-10-25T00:40:54.748215Z`. It recorded 65 attempts across 22 cases: 64 `SUCCESS` results, followed by a hard-gate failure on `summary-v1.0.0-C10` attempt 2 at `2026-10-25T00:58:04.375033Z`. The failure reason was `missing_synthetic_label`. The failing response body was not persisted, and no secret or security failure was indicated. No further cases or attempts ran. The result is `FAIL_ROLLBACK_REQUIRED`; the calibration milestone did not pass.

The replacement agent was deleted immediately at `2026-10-25T00:58:30Z`, request ID `9ddea39f-7684-4725-8af5-fba5eb820441`. A subsequent `dataAgents` list verified that no Data Agents remain. Sanitized evidence is committed in `evidence/data-agent-calibration-failure-20261025.json`. Local run evidence remains uncommitted under the approved 90-day retention policy.

`publication_authorized_now`, `calibration_authorized_now`, and `questions_authorized_now` are all false. Remediation requires independent revision of the agent instructions, a new agent creation with source and ACL review, publication review, preflight, and a complete 36-by-3 calibration rerun from scratch. The prior 64 successes cannot be combined with a later run. Architecture remains **CONDITIONAL PASS**; the data layer, semantic model, and evaluation remain approved.

Failure evidence was committed at `c99a85ac96f1096508f26f9eb93b5b53c4afabc3`. The exact synthetic-label contract was remediated in commits `d368402ffd41eff3b970678d4f59d3f65c6cfd59` and `f4062d4f4704a154e02970fd49244c7c309aa116`. The remediation is approved after 136 tests, 51 subtests, TOM validation, and security review.

Create operation `a305cd2a-e750-4ca0-b315-b08ed0735bf4` succeeded for new draft v1.0.1 Data Agent `a23346c3-1ce7-4203-8ecf-9b9982c82a03`. It uses the same workspace `4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`, semantic model `ee7583b6-5be7-4802-83a8-530ce7dd8351`, and four tables (`Wells`, `Dataset Metadata`, `Data Quality`, and `Categories`). Its description is `v1.0.1`; it is unpublished and unshared, and no question or calibration attempt has been sent.

Repository source-ID rebinding commit `0dc114817bce6402c40c456e1557e0a16a7ffcab` and exact-label remediation commits `d368402ffd41eff3b970678d4f59d3f65c6cfd59` and `f4062d4f4704a154e02970fd49244c7c309aa116` are approved by Baek Yoonho and security. Validation passes 136 tests, 51 subtests, TOM validation, Bandit, and pip-audit. The approved runner remediation and security lineage remain applicable.

The live draft exactly matches the approved v1.0.1 source except Fabric's `children: []` normalization. It contains the exact v1.0.1 synthetic-label instructions, one semantic model, and the four approved tables. The live Data Agent, semantic-model, and workspace ACLs contain only approved user Project requester (`61a37498-9ab6-43d2-b70f-706fd58274e7`); the temporary sole-user Admin/model Write/ReShare exception is unchanged.

All prepublication gates passed, and exact agent ID `a23346c3-1ce7-4203-8ecf-9b9982c82a03` published successfully at `2026-10-25T01:26:55Z`, request ID `f5663fae-bd87-4846-808d-30f11028a3f8`. The published item remains unshared and calibration-only.

Fresh postpublication Q1-Q5 all pass. Q1 verified the live published definition exactly matches the approved v1.0.1 source except Fabric's `children: []` normalization, contains exactly one semantic model and the four approved tables, and retains the exact first-line instruction `SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY`. Q2 verified the Data Agent, semantic-model, and workspace ACLs contain only approved user Project requester (`61a37498-9ab6-43d2-b70f-706fd58274e7`).

Q3-Q5 preflight `20261025T012704Z-6a32549a` returned 401 for unauthenticated and wrong-token probes, passed the delegated-user handshake, exposed exactly one question tool, completed cleanup, and sent no question or tool call. Credentials and raw response bodies were not persisted.

At commit `d07d3edd04f634aed680d71cd565760457549efc`, Baek Yoonho designated-reviewer verdict is **APPROVE** for the full fresh v1.0.1 evaluation of 36 cases with 3 attempts per case. All Q1-Q5 remain `PASS`. `publication_authorized_now` is false because publication is complete; `calibration_authorized_now` and `questions_authorized_now` are true only for that exact from-scratch 36-by-3 evaluation. Calibration has not started, and no question has been sent. Neither deleted predecessor's attempts nor any prior run may transfer to or be combined with the v1.0.1 run.

At commit `d13acd17978199b1a36e558f8d8b34c610e6b126`, Thomas Andre's substantive final security verdict is **APPROVE**. All publication, Q1-Q5, designated-reviewer, and final security gates are complete. `calibration_authorized_now` and `questions_authorized_now` remain true only for the exact fresh v1.0.1 36-case by 3-attempt evaluation. Calibration has not started and no question has been sent at the time of approval.

The fail-closed response remains unchanged: stop immediately on any definition, source, identity, ACL, authorization, capability, or evidence-safety mismatch; disable or safely unpublish where available; and use deletion as the mandatory fallback. Sharing, additional sources, actions, writes, direct raw or curated access, real data, prediction, similarity, operational use, broader exposure, and production claims remain prohibited.

Fresh v1.0.1 calibration run `20261025T013559Z-2808cabd` completed all 108 invocations: 36 cases with 3 attempts each, all invocation calls successful, with no invocation hard stop. Baek Yoonho's offline grading found 13 critical factual failures, 19 scope violations, 0 security-disclosure failures, and 42 incorrect expected behaviors. Of 141 citation claims, 123 were present and 12 were valid. Repeat consistency was 32 of 36 cases, and every output used the exact required synthetic label.

The resulting score is citation presence 87.234%, citation validity 8.511%, clarification/refusal correctness 50%, repeat consistency 88.889%, p95 latency 31.836999 seconds, and cost `UNKNOWN`/`null`. The result is `FAIL_ROLLBACK_REQUIRED`; the conversational architecture does not pass the milestone. No unauthorized disclosure or security failure occurred.

Data Agent `a23346c3-1ce7-4203-8ecf-9b9982c82a03` was deleted at `2026-10-25T02:06:17Z`, request ID `3831710c-1a25-4a9f-a267-67afcc2d093e`, and a subsequent list verified that no Data Agents remain. Raw run and grading evidence remains local and ignored under the approved 90-day retention policy. The repository contains only the sanitized summary at `evidence/data-agent-calibration-failure-v1.0.1.json`.

`publication_authorized_now`, `calibration_authorized_now`, and `questions_authorized_now` are all false. The data layer, SQL views, semantic model, and evaluation specification remain approved, but the conversational architecture and milestone do not. The next gate is root-cause analysis followed by explicit approval of either v1.0.2 remediation or an architecture change. Prior attempts cannot count toward any future pass. Architecture remains **CONDITIONAL PASS**.

Weatherford has now selected the hybrid architecture change: Fabric Data Agent is the mandatory governed analytical data plane, while one Foundry orchestrator/application layer is the deterministic control plane. The orchestrator owns routing, clarification/refusal policy, the mandatory response envelope and exact synthetic-data label, evidence-citation requirements, the user-visible component trace, and final validation. No alternate analytical path or second orchestrator is approved.

Normal analytical answers—including summaries, paraphrases, and derived factual statements—require both a successful Fabric Data Agent contribution and a successful orchestrator validation. Evidence must resolve through the approved allowlists and support its associated claims. A Data Agent failure, timeout, refusal, malformed response, missing/invalid evidence, or failed validation must be shown explicitly in the response envelope and component trace. The orchestrator may clarify, refuse, or report unavailability, but it may not silently replace the Data Agent or generate a normal analytical answer through another path. The trace must be curated, minimized, access-appropriate, and redacted; it may not expose hidden prompts, credentials, restricted payloads, sensitive telemetry, internal reasoning, or unnecessary topology.

The prior v1.0.1 calibration remains the baseline: 108/108 invocation calls completed, but grading found 13 critical factual failures, 19 scope violations, 42 incorrect expected behaviors, 8.511% citation validity, 50% clarification/refusal correctness, 88.889% repeat consistency, 31.836999-second p95 latency, exact labeling on every output, zero security disclosures, and unknown cost. Agent `a23346c3-1ce7-4203-8ecf-9b9982c82a03` remains deleted, and the verified current Data Agent count is zero.

The new implementation gate is a source-controlled local mock proving spike, independently reviewed, before any new Data Agent or Foundry creation, publication, or deployment. It must prove deterministic routing, mandatory Data Agent participation, orchestrator-owned policy and envelope, allowlist-based claim-supporting citations, a minimized/redacted component trace, validation behavior, visible fail-closed handling without silent substitution, component latency, and an attributable local cost/usage proxy. A measurable cloud cost ceiling remains required before deployment because prior cost is unknown. A successful spike does not itself authorize cloud deployment.

Because the verified Data Agent count is zero, governed normal analytical responses are currently disabled; only explicit clarification, refusal, or unavailable/failed responses are permitted. Existing data-layer, SQL-view, semantic-model, and evaluation approvals remain bounded and do not authorize an ordinary-user conversational query path, application go-live, or production use. All current publication, calibration, and question authorizations remain false. Architecture remains **CONDITIONAL PASS**.

The user-approved provisioning target is a new Microsoft Foundry account and project in Central US within existing resource group `rg-welladvisor-mx01`; the Sweden Central projects must not be reused. The local hybrid proving-spike lineage is present in commits `e508f1d`, `24110cb`, `07dfbe8`, and `6d2517e`. Fabric Data Agent remains mandatory and integral, but no Data Agent is currently deployed.

The mandatory baseline is Foundry Managed VNet/outbound isolation plus a private endpoint. Public access is disabled by default and may not replace the private endpoint. If technically required for the bounded demo, it must be an explicitly documented, time-bounded exception restricted to the current developer IP and removed after the demo; unrestricted public access is prohibited. Authentication must use a system-assigned managed identity with least-privilege RBAC, and no secrets or keys may enter the repository.

This phase is limited to source-controlled Bicep and governance preparation with POC-appropriate diagnostics and monitoring, ownership and budget tags, and low operational overhead where compatible with the security baseline. It does not authorize model deployment, hosted agent deployment, Data Agent creation, application deployment, or cloud provisioning execution.

Deployment remains blocked until Bicep build and Azure what-if succeed; quota, provider-registration, RBAC, and policy checks pass; and independent architecture, security, cost, and implementation reviews approve the retained evidence. Architecture remains **CONDITIONAL PASS**.

## Current Container App / Foundry scope (supersedes prior current-state descriptions)

Effective `2026-10-27T10:41:02-04:00`, the approved development-only POC uses
the deployed Azure Container App, its anonymous rate-limited chat route, its
authenticated fixed-target MCP relay, Foundry prompt agent version 7, and the
published Fabric Data Agent. The relay uses managed identities and federated
application exchange; no browser token, API key, client secret, or
caller-selected MCP target is accepted.

The scope remains synthetic read-only historical summaries. Every analytical
answer requires the exact synthetic disclosure and Fabric MCP participation.
Real data, row-level export, prediction, similarity, operational
recommendations, writes, and administration remain prohibited. The connection
must remain pointed at the Container App route, version 7 must remain
active/latest, and version 4 must be retained for rollback. Rollback is
authorized only for a demonstrated functional or security failure, not because
the platform assigned version 7 rather than version 5.
