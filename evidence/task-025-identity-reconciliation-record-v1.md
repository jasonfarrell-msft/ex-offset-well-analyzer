# TASK-025 — Offline identity reconciliation record

**Version:** v1  
**Date:** 2026-10-29  
**Author:** Thomas Andre — Fabric Identity & Minimal POC Governance Architect  
**Revision:** 2026-10-29 — Go Gunhee; narrow correction of historical-scope reconciliation and API provenance after Baek Yoonho's REJECT; independent re-review pending. Original authorship retained.  
**Status:** OFFLINE DRAFT — pending independent review by Baek Yoonho.  
**Classification:** Internal — Synthetic POC; no real operator data.

## Authority and scope

Project requester explicitly selected **“Create the new offline record and review it (Recommended)”** in the 2026-10-29 Cycle 2 instruction. This authorizes creation of this file and independent review only. Both historical Data Agent documents remain unchanged, as do decisions, existing plans and evidence. This record neither changes their text nor claims that an existing reconciliation dependency has passed.

The accepted design preference is a non-user-specific workload identity with the minimum permissions required for the approved POC requirements. The 2026-10-28T11:09:39-04:00 decision initially applies that preference to Offset Well Analysis; the 2026-10-28T13:42:05-04:00 decision explicitly extends it to both Offset and historical Data Agent integration. Applicability to both scopes is therefore established, not an open question. Exact identity, source scope and grants are not established by that preference. [S1]

This is offline decision support, not principal selection, grant justification, an accepted governed baseline, an architecture approval, or live-action authorization. It does not accept the observed ACA-to-service-principal chain or either observed Data Agent item. It authorizes no queries, capacity transitions, cloud/API calls, permission changes, definition edits, publication, activation, deployment, commit or push.

## Evidence and authority reconciliation

| Classification | Dated or versioned evidence | Interpretation and limitation |
|---|---|---|
| Accepted user preference | S1: 2026-10-28 identity decisions cited above | Workload identity and minimum permissions are design constraints for both integrations. They do not approve a particular principal, existing chain, source or grant. |
| Historical accepted decision | S1: 2026-10-24 single-user calibration; S3 REQ-005 | Retains its original bounded user/source/calibration scope. The later preference does not retroactively alter that authorization. |
| Historical accepted decision | S1: 2026-10-26T14:30:45-04:00 Foundry-to-Fabric IQ integration | Delegated `UserEntraToken`, its recorded audience/scope and specific Data Agent binding belong to that integration's approval. They do not authorize a TASK-025 definition read-back or establish workload-identity permissions. |
| Dated historical directive and separate source path | S1: 2026-10-29T08:41:52.870-04:00 consolidated “Historical anonymous Drill Advisor directive and source-specific cutover gates,” recording the 2026-10-26T16:10:27.042-04:00 directive and subsequent checkpoints | The directive required anonymous visitor access with keyless managed/federated service-to-service identity. The recorded semantic-model path failed service-principal authorization; a separate `da_drillrun_public_summary` used the Lakehouse and four selected SQL views. Recorded tool success did not establish complete public cutover. These dated records neither verify current identities/grants/live state nor approve a TASK-025 caller or source. |
| Later recorded scope authority, not current verification | S8: “Current Container App / Foundry scope,” effective 2026-10-27T10:41:02-04:00 | Records the development-only anonymous rate-limited Container App route, authenticated fixed-target MCP relay, managed identities/federated exchange, Foundry version 7 and published Fabric Data Agent as superseding prior current-state descriptions. Its synthetic read-only historical-summary/disclosure/MCP constraints and version-4 rollback restriction remain recorded scope boundaries, not fresh proof of deployment, grants, effective access or acceptance of the observed identity chain. |
| Historical document assertions | S5 and S6, undated document snapshots read on 2026-10-29 | Named-user-only access and “no Fabric Data Agent currently exists” are historical assertions, not verified present state. Neither document is edited or silently treated as a current tenant inventory. |
| Later recorded observations, unaccepted | S2 v1.4 introduction; S7 v1 | Two live Data Agent items and an ACA managed-identity-to-Fabric-service-principal chain were reported. They conflict with treating the historical documents as current inventory/identity descriptions, but do not replace them with an accepted live baseline. S7 marks observation timestamps and other primary provenance unavailable; no observation date is invented here. |
| Offline static-code research, not deployed-state proof | S4, research cut-off 2026-10-28 | The supplied code report describes ACA managed identity as a workload-federation assertion source and a service principal as the Fabric-facing identity. It neither selects that design nor verifies deployment, token audience, current permissions or effective access. S4 remains awaiting independent reviewer approval. |
| Failed definition evidence, unaccepted | S2 introduction; S7 v1 | Two reported 198-byte responses exposed zero definition parts. Complete sources, selection descendants, part hashes and publication metadata were not established. This is an evidence failure, not proof that broad permissions caused the response or that a breach occurred. |
| Historical source boundary | S5 and S6; S4 semantic-model findings; S1 consolidated 2026-10-26 history; S8 later scope record | S5/S6 describe the preserved `sm_drillrun_summary` path and `Wells`, `Dataset Metadata`, `Data Quality`, `Categories`. S1 separately records `da_drillrun_public_summary` using Lakehouse `964afbf5-6a33-46dc-98c1-be726d0f4999` and only `serving.dataset_summary`, `serving.well_summary`, `serving.quality_summary`, `serving.category_summary`, without modifying the preserved semantic-model agent. S8 records the later Container App/Foundry scope; it does not independently verify that source binding today. Neither historical path nor its identifiers select a current diagnostic target. Offset serving-view candidates remain separate and unapproved as an extension. |

The conflict is recorded rather than resolved by assumption: S1's dated keyless directive and separate Lakehouse/SQL-agent history, followed by S8's later recorded Container App/Foundry scope, explain why S5/S6 cannot be treated as the sole current inventory or identity authority. They remain historical records, not present-state verification. The newer accepted preference establishes design intent, while the unaccepted observations establish neither present inventory nor intended authority. Current live existence, identity and capacity state remain unverified; no observed identity chain is accepted. Historical approvals remain limited to their recorded scopes. [S1–S8]

## Permissions are operation-specific

- **Definition read-back:** S4's control-plane table reports documented item **read and write** permission for Get Data Agent Definition, with required delegated scope `Item.ReadWrite.All`. The report lists User, Service Principal and Managed Identity support for that control-plane operation. This describes the cited documentation, not accepted caller-specific authorization or a grant recommendation.
- “Read-only” describes the proposed evidence operation's non-mutating intent. It does **not** mean the platform permits definition retrieval with a read-only item grant. Do not substitute metadata GET permissions, runtime MCP permissions or semantic-model Read for definition-read-back requirements.
- **Custom MCP runtime:** S4 reports the Fabric API scope and access prerequisites, but the exact MCP workspace role and service-principal item-sharing tier remain `NEEDS_PLATFORM_JUSTIFICATION`. Requirements from another transport must not be imported to fill those gaps.
- **Source access:** S4 reports semantic-model Read as sufficient for Data-Agent-mediated queries; direct Execute Queries Read-and-Build requirements are a separate operation. Neither finding authorizes a data query here or establishes the current source/ACL boundary.
- Observed Contributor, Lakehouse or Data Agent grants are not an approved baseline. Do not add, remove or change them to test a suspected cause. Definition permission requirements alone do not justify retaining broad runtime grants. [S2 REQ-002, REQ-010–012; S4]

## Exact unknowns and evidence still required

| Unresolved value | Evidence required before a concrete recommendation or live window |
|---|---|
| Intended caller and operator | Supported principal type; exact tenant, object/service-principal and application identifiers; operator identity; distinction between diagnostic caller and runtime caller; documented token exchange/audience requirements and approval for their use. No principal is selected here. |
| Target and resource scope | Approved exact workspace and Data Agent item identifiers for one diagnostic read; capacity resource identifier; source IDs/types and complete selection tree; source-specific boundaries and any distinction between historical summary and Offset. Historical IDs and display names are not substitutions for that decision. |
| Minimum and effective permissions | Caller- and operation-specific platform requirements; actual direct/inherited grants, groups and scope; authorization to inspect each ACL path; evidence separating necessary definition-export permissions from runtime needs. No effective-access conclusion follows from an assignment alone. |
| Current API support | S9 documents the Data-Agent-specific no-`format` POST request shape, caller/permission support and response/LRO/throttle contract with source URLs and retrieval provenance. It does not establish an omitted-parameter output default. The definition-part-path disagreement remains **UNRESOLVED**: the endpoint sample uses `DataAgentV1.json` and `.platform`, while the linked conceptual definition page uses `Files/Config/...`, including `Files/Config/publish_info.json`. Neither path list is accepted for strict validation pending sanctioned clarification. Required caller-specific support and complete baseline evidence remain unestablished; no URL, format or path contract is guessed. |
| Definition and exposure evidence | Complete sanctioned result and definition parts, strict decoded-byte hashes, source descendants/public fields, publication metadata and ACL/inheritance evidence. Missing or truncated content fails closed. |
| Governance acceptance | Independent Baek evidence review, applicable Thomas identity/exposure and Go Gunhee platform validation, and Jason's explicit decision on the supported reconciliation outcome. This draft cannot self-approve or waive S2's completed-reconciliation prerequisite. |
| Window and evidence handling | Exact ordered calls/procedures including capacity checks/transitions and any conditional LRO polling/result retrieval; concrete call/byte/duration/poll/retry/cost limits; absolute pause deadline; approved operator/reviewers and restricted/sanitized evidence destinations; success/stop and no-change conditions. None is supplied by this record. |

## Gate status and next permitted step

**TASK-025 is not complete. No canonical live manifest or manifest SHA-256 exists in this record. No live call is approved.**

S2 TASK-005 requires completed separately approved reconciliation, alongside confirmed API support and schemas, before its diagnosis window. S3 describes an older two-document-edit workflow; Jason's Cycle 2 instruction now permits this separate offline record while expressly preserving those documents. Creation of this draft is not completion or acceptance of that earlier workflow and does not amend S2 or S3. Independent review must assess whether this no-edit record can support a subsequent explicit acceptance decision, while preserving all unresolved identity/source/ACL gates. If it cannot, stop and return the dependency conflict to Jason rather than infer a waiver.

Request independent review from **Baek Yoonho**, the active Validation & Evidence Engineer. Review must check authority boundaries, dated provenance, least-privilege distinctions, redaction, unresolved claims and the absence of implied live authorization. Thomas, as author, does not supply that independent verdict.

Only after independent review and a supported, explicit acceptance decision may a complete candidate window be finalized. All unresolved operational values must be established, the exact canonical bytes hashed, and Jason must separately approve that actual SHA-256 under S2 REQ-013–020. Any manifest change invalidates its approval. A single diagnostic read would not establish the full TASK-025 baseline or permit TASK-026.

## Distinct evidence conclusions

- **Observed permissions:** Broad grants are reported only as unaccepted historical observations. Current grants were not checked.
- **Proven effective access:** The available record does not establish a complete accepted source/identity/ACL boundary. No access test occurred for this record.
- **Demonstrated breach:** No breach is demonstrated by the cited evidence. This is not a finding that a breach or unauthorized access is absent.

## Local sources

- **S1:** `.squad/decisions.md` — dated calibration/integration decisions and 2026-10-28T11:09:39-04:00 / 2026-10-28T13:42:05-04:00 identity preferences; also the 2026-10-29T08:41:52.870-04:00 consolidated “Historical anonymous Drill Advisor directive and source-specific cutover gates” (around lines 720–730), preserving the 2026-10-26T16:10:27.042-04:00 keyless directive and subsequent separate Lakehouse/SQL summary-agent checkpoints. Consolidation date is not a new deployment or verification date. Accepted decisions are scope-limited authority, not current-state verification.
- **S2:** `plan/process-task-025-remediation-reverification-1.md` — v1.4 revision provenance; Planned / pending independent re-review; introduction, REQ-002–020, SEC-001, canonical contracts and TASK-004–006. Plan requirements are not live authorization.
- **S3:** `plan/process-task-025-documentation-reconciliation-1.md` — v1.1, last updated 2026-10-28, Planned; REQ-001–008 and Phases 1–4. Its applicability question is answered by S1's later accepted decision; its document-edit workflow is not executed here.
- **S4:** `evidence/task-025-workload-identity-minimum-permissions-v1.md` — corrected offline research, cut-off 2026-10-28; awaiting independent reviewer approval; source retrieval batch `2026-10-28T17:35:20Z`; architecture, control-plane, runtime/source and observed-grant findings. Public documentation was not retrieved again for this record.
- **S5:** `docs/data-agent-security-posture.md` — undated historical baseline; Architecture, Access and data, Cost and approval. Preserved unchanged.
- **S6:** `docs/data-agent-design.md` — undated historical design; Definition and source boundary; Identity, publication, and capacity. Preserved unchanged.
- **S7:** `evidence/task-025-failure-record-v1.json` — v1 failure record; facts marked `OBSERVATION_UNACCEPTED`, with typed unavailable provenance. Preserved unchanged; not upgraded to accepted evidence.
- **S8:** `.squad/identity/now.md` — local snapshot read 2026-10-29; frontmatter `updated_at: 2026-10-28T16:13:44.641-04:00`; “Current Container App / Foundry scope (supersedes prior current-state descriptions),” effective 2026-10-27T10:41:02-04:00. Later recorded scope authority, not present live identity, grant or source verification.
- **S9:** `evidence/task-025-api-conformance-v2.md` — v2 local evidence file, research performed 2026-10-29; endpoint page retrieved approximately 2026-10-29T12:31:20Z. Conformance matrix and provenance cite the official endpoint and linked conceptual definition pages; definition-part-path reconciliation remains **UNRESOLVED**. Documentation-supported no-`format` request shape is not a default-format claim, accepted complete definition baseline or live authorization. No documentation was retrieved again for this revision.

## Preparation and review record

Preparation used local read tools and one addition of this file only. No CLI, network, Azure, Fabric or Foundry call was made; no other repository file was edited. No credentials, identity assertions, tokens, hidden instructions or restricted definition payloads are copied here. No historical hash or current cloud fact is fabricated.

The paragraph above records the original preparation. Go Gunhee's 2026-10-29 revision changed only this file using local file tools; a local `git status --short` inspection was also performed. No network, Azure, Fabric or Foundry call was made. Existing unrelated worktree changes were not revised. Baek's prior REJECT is not acceptance; the corrected record requires Baek's independent re-review.

**Independent reviewer requested:** Baek Yoonho.  
**Review outcome:** PENDING — no independent acceptance recorded.  
**Jason acceptance of reconciliation outcome:** PENDING — draft/review authorization is not outcome acceptance or live-window approval.
