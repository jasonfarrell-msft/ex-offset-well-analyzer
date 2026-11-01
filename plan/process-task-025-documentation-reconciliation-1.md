---
goal: Reconcile historical Data Agent documentation without expanding prior approvals
version: '1.1'
date_created: '2026-10-28'
last_updated: '2026-10-28'
owner: Thomas Andre
status: 'Planned'
tags: [process, task-025, documentation, identity, fabric, foundry, least-privilege]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This proposal defines a gated, documentation-only reconciliation of `docs/data-agent-security-posture.md` and `docs/data-agent-design.md`. It does not itself authorize changes to those documents, select an identity, accept observations, or authorize live evidence collection. Work begins only after Project requester approves the reconciliation scope and confirms whether his Offset Well Analysis POC workload-identity preference applies to the historical Data Agent integration. Exact identity and access values remain unknown until supported by offline least-privilege analysis, current official documentation, and any separately authorized evidence.

## 1. Requirements & Constraints

- **REQ-001**: Obtain Project requester's explicit approval of the reconciliation work and its scope before beginning analysis. Ask whether the Offset Well Analysis POC preference applies to the historical Data Agent integration; do not assume that it does.
- **REQ-002**: Do not ask Jason to choose or authorize a principal, tenant, workspace, item/source scope, or grant before the evidence supports a concrete recommendation. Keep each unresolved value explicitly marked unknown.
- **REQ-003**: Thomas Andre must complete offline least-privilege analysis against the approved requirements, already available authorized evidence, and current official documentation before presenting a recommendation.
- **REQ-004**: Present a source-cited recommendation and its remaining unknowns to Jason for a separate decision before revising either historical document.
- **REQ-005**: Preserve the scope of the existing decisions. The 2026-10-24 single-user calibration approval applies to its bounded calibration, including its named user and source scope. The 2026-10-26 Foundry delegated-`UserEntraToken` decision applies to its specified Foundry-to-Fabric IQ integration, audience, scope, and Data Agent ID. Neither decision is automatically superseded, broadened, or changed by Jason's 2026-10-28 Offset Well Analysis POC workload-identity preference.
- **REQ-006**: Preserve the fact that the failure record contains two observed live Data Agent items and an observed ACA-to-Fabric service-principal chain, all unaccepted. Do not select or recommend that chain merely because it was observed.
- **REQ-007**: State that the broad observed permission set does not prove effective access or a breach. Do not assert either access or absence of a breach without supporting evidence.
- **REQ-008**: Do not assert an exact principal, tenant/workspace, item/source scope, or required grant until each value is supported by cited evidence and a least-privilege rationale. No identity or permission change is in scope.
- **SEC-001**: If an answer requires live evidence, stop. Obtain separate, explicit, operation- and manifest-specific approval before any evidence-collection activity; this proposal grants none.
- **CON-001**: This work is offline and documentation-only. No Azure, Fabric, or Foundry tenant operations; data queries; API calls; permission or group changes; item creation, deletion, publication, activation, or deployment; commit; or push.
- **CON-002**: For this revision, modify only `plan/process-task-025-documentation-reconciliation-1.md`. Do not modify the historical target documents or any other file.
- **GUD-001**: Label each statement as an accepted decision, an unaccepted observation, a documented fact, a proposed recommendation, or an unresolved unknown.
- **GUD-002**: Treat public Microsoft Learn material as documentation sources only. For each relied-on requirement, record the exact page title, URL, access date, relevant statement, and how it applies; do not treat documentation as tenant-specific evidence.
- **PAT-001**: Use approval gates in order: Jason scope/applicability approval; Thomas offline analysis; Jason decision on the supported recommendation; only then document revision and review by Thomas and Baek Yoonho.

## 2. Implementation Steps

### Implementation Phase 1 — Approve scope and applicability

- GOAL-001: Obtain Jason's approval to perform this reconciliation, its two-document scope, and an explicit answer about whether the Offset-specific workload-identity preference applies to the historical Data Agent integration. This is not a request for exact identity or grant authorization.
- **Completion criteria**: Jason's recorded response approves or declines the work; identifies the in-scope historical integration(s); and explicitly states whether the Offset-specific preference applies to each. No identity, scope, or grant values are requested at this gate. If Jason declines or leaves applicability unclear, stop without proceeding to Phase 2.

| Task | Description | Owner | Reviewer | Depends on | Completed | Date |
|------|-------------|-------|----------|------------|-----------|------|
| TASK-001 | Request Project requester's approval for offline reconciliation of only `docs/data-agent-security-posture.md` and `docs/data-agent-design.md`, and ask whether the Offset Well Analysis POC workload-identity preference applies to the historical Data Agent integration. Do not request exact principal, tenant, workspace, item/source, or grant choices. Record the scope decision through the existing approval process; do not edit another repository file. | Thomas Andre | Baek Yoonho | None | | |

### Implementation Phase 2 — Perform offline identity and least-privilege analysis

- GOAL-002: Analyze only the integration scope approved in Phase 1 using offline materials, available authorized evidence, and current official documentation; establish what is supported and retain unsupported values as unknown.
- **Completion criteria**: Thomas produces a source-cited analysis for every approved integration in the review record. It distinguishes principal types and integration hops, lists candidate identity patterns without selecting an unapproved observed chain, maps each proposed operation to the minimum documented permission and scope, and lists missing evidence as unknown. Every cited public source includes title, URL, and access date. No tenant is contacted and no live evidence is collected.

| Task | Description | Owner | Reviewer | Depends on | Completed | Date |
|------|-------------|-------|----------|------------|-----------|------|
| TASK-002 | Compare the approved historical decisions in `.squad/decisions.md`, the observations in `evidence/task-025-failure-record-v1.json`, and the two target documents. Preserve the 2026-10-24 calibration scope and 2026-10-26 delegated-user integration as separate, scope-limited decisions. Record that the two observed items and ACA-to-Fabric service-principal chain are unaccepted, and that broad observed permissions prove neither effective access nor a breach. | Thomas Andre | Baek Yoonho | TASK-001 | | |
| TASK-003 | Consult current official Microsoft documentation relevant to the approved integration's identity mechanism, authentication flow, Fabric/Data Agent permissions, and source/item boundaries. Record page title, exact URL, access date, applicable documented requirement, and limits of applicability in the review record. Do not use tenant-specific tools or make API calls. | Thomas Andre | Baek Yoonho | TASK-001 | | |
| TASK-004 | Complete an offline least-privilege map from each approved POC operation to the minimum documented grant and narrowest documented scope. Separately list supported facts, candidate options, evidence gaps, and unknown principal, tenant/workspace, item/source scope, and grants. Do not infer access from assignments, display names, broad permissions, or the observed ACA-to-Fabric chain. | Thomas Andre | Baek Yoonho | TASK-002, TASK-003 | | |

### Implementation Phase 3 — Present recommendation for Jason's decision

- GOAL-003: Present only recommendations supported by Phase 2 evidence and request Jason's decision without implying that this plan or the historical approvals authorize identity or permission changes.
- **Completion criteria**: Jason receives the analysis, citations, least-privilege rationale, unresolved unknowns, and separate treatment of prior approvals. His response either accepts, rejects, or requests more analysis of the recommendation for the approved integration. If a necessary value remains unsupported, it remains unknown and the plan stops before document revision.

| Task | Description | Owner | Reviewer | Depends on | Completed | Date |
|------|-------------|-------|----------|------------|-----------|------|
| TASK-005 | Present Thomas's Phase 2 analysis to Project requester as a recommendation, not an authorization request for unsupported values. Identify each supported option and its evidence, the minimum documented permissions, all remaining unknowns, and whether the Offset preference applies to this historical integration. Ask Jason to accept or reject the supported recommendation and separately approve proceeding to documentation edits. | Thomas Andre | Baek Yoonho | TASK-004 | | |
| TASK-006 | If the recommendation depends on tenant-specific or other live evidence, stop and request separate approval identifying the exact evidence manifest, operation, scope, and time window. Resume only after that approval and completion of the separately authorized evidence procedure; otherwise retain unknowns. | Thomas Andre | Baek Yoonho | TASK-004 | | |

### Implementation Phase 4 — Revise and independently review the historical documents

- GOAL-004: After all previous gates pass, revise only the two approved historical documents to reconcile supported current design guidance while preserving prior scope-limited decisions and labeling unknowns.
- **Completion criteria**: The edits are limited to `docs/data-agent-security-posture.md` and `docs/data-agent-design.md`; every new identity or permission claim traces to an accepted decision or cited evidence; the older calibration and delegated-user approvals retain their original scope; Thomas and Baek independently approve the document diff; and Jason approves the final wording. If any gate fails, make no target-document change.

| Task | Description | Owner | Reviewer | Depends on | Completed | Date |
|------|-------------|-------|----------|------------|-----------|------|
| TASK-007 | Revise only `docs/data-agent-security-posture.md` and `docs/data-agent-design.md` to reflect Jason's Phase 1 scope decision and Phase 3 decision, with explicit authority/evidence labels. Keep exact principal, tenant/workspace, item/source scope, or grants unknown wherever evidence does not resolve them. Do not make any Azure, Fabric, or Foundry change. | Thomas Andre | Baek Yoonho | TASK-005, TASK-006 if live evidence is required | | |
| TASK-008 | Review the two-document diff for evidence provenance, accurate decision scope, least-privilege support, and absence of implied effective access, breach conclusions, or unapproved identity/grant selection. Thomas and Baek Yoonho each record an explicit independent review outcome; Jason approves final authority wording. Revise only the two target documents if reviewers identify corrections. | Thomas Andre | Baek Yoonho; Project requester | TASK-007 | | |

## 3. Alternatives

- **ALT-001**: Ask Jason to choose an exact principal, tenant, workspace, scope, or grant before evidence exists. Rejected because it solicits unsupported authorization and reverses the required analysis-before-decision order.
- **ALT-002**: Treat the Offset POC workload-identity preference as automatically superseding the 2026-10-24 calibration approval and the 2026-10-26 Foundry delegated-user decision. Rejected because Jason's direction is scoped to the Offset Well Analysis POC and does not state that it changes either prior approval.
- **ALT-003**: Adopt the observed ACA-to-Fabric service-principal chain and broad observed permissions as the target architecture. Rejected because the chain and two observed items are unaccepted, and observed permissions do not prove effective access or breach.
- **ALT-004**: Revise the historical documents immediately and annotate unresolved values later. Rejected because supported analysis and Jason's decision must precede document changes.
- **ALT-005**: Collect live evidence as part of this proposal. Rejected because this proposal authorizes no live operations; any such evidence requires separate manifest-specific approval.

## 4. Dependencies

- **DEP-001**: Project requester's explicit approval of the reconciliation scope and answer on whether his Offset-specific workload-identity preference applies to the historical Data Agent integration.
- **DEP-002**: Thomas Andre's offline analysis of accepted decisions, authorized evidence, and current official Microsoft documentation, with unknowns preserved.
- **DEP-003**: Project requester's separate decision on a concrete, evidence-supported recommendation and approval to proceed with the two-document edits.
- **DEP-004**: If live evidence is indispensable, separate manifest-, operation-, scope-, and time-window-specific authorization and its completion. This proposal is not that authorization.
- **DEP-005**: Independent review by Thomas Andre and Baek Yoonho, followed by Project requester's approval of final authority wording.

## 5. Files

- **FILE-001**: `plan/process-task-025-documentation-reconciliation-1.md` — this proposal; the only file permitted to change during this revision.
- **FILE-002**: `docs/data-agent-security-posture.md` — historical target; do not modify until Phases 1–3 are approved and Phase 4 begins.
- **FILE-003**: `docs/data-agent-design.md` — historical target; do not modify until Phases 1–3 are approved and Phase 4 begins.
- **FILE-004**: `.squad/decisions.md` — read-only authority source for this plan; no edit is authorized.
- **FILE-005**: `plan/process-task-025-remediation-reverification-1.md` — read-only related plan; no edit is authorized.
- **FILE-006**: `evidence/task-025-failure-record-v1.json` — read-only record of unaccepted observations; no edit is authorized.

## 6. Testing

- **TEST-001**: Validate that the proposal has valid YAML front matter containing `goal`, `version`, `date_created`, `last_updated`, `owner`, `status`, and `tags`; status is one of `Completed`, `In progress`, `Planned`, `Deprecated`, or `On Hold`.
- **TEST-002**: Validate the exact top-level headings and order: `# Introduction`, then `## 1. Requirements & Constraints` through `## 8. Related Specifications / Further Reading`.
- **TEST-003**: Validate each implementation phase has a measurable completion criterion and a task table containing `Task`, `Description`, `Completed`, and `Date`, with owner, reviewer, and dependency information also present.
- **TEST-004**: Search the proposal for unsupported selection or certainty: it must state that exact principal, tenant/workspace, item/source scope, and required grants remain unresolved until supported; that two observed items and ACA-to-Fabric SP are unaccepted; and that observed broad permissions prove neither access nor breach.
- **TEST-005**: Verify the only file changed for this revision is `plan/process-task-025-documentation-reconciliation-1.md`. Verify no cloud operation, query, API call, permission change, deployment, commit, or push was performed.
- **TEST-006**: Before Phase 4 completion, verify the historical decision scopes remain distinct and the only target-document paths in the Phase 4 diff are `docs/data-agent-security-posture.md` and `docs/data-agent-design.md`.

## 7. Risks & Assumptions

- **RISK-001**: Available offline evidence and official documentation may not support an exact identity or grant. Mitigation: keep the value unknown and stop before document revision rather than infer it.
- **RISK-002**: The observed ACA-to-Fabric service-principal chain or broad permissions may be mistaken for approved configuration or effective access. Mitigation: label them unaccepted observations and explicitly state their evidentiary limits.
- **RISK-003**: The Offset-specific direction may be incorrectly applied to historical Data Agent work. Mitigation: require Jason's scope/applicability decision before analysis and preserve the historical calibration and Foundry approvals independently.
- **RISK-004**: A live-evidence requirement may be mistaken for authorization to perform a query or operation. Mitigation: stop and require separate manifest-specific approval.
- **ASSUMPTION-001**: Jason's 2026-10-28 direction is a design constraint for the Offset Well Analysis POC only unless he explicitly confirms that it applies to the historical Data Agent integration.
- **ASSUMPTION-002**: The 2026-10-24 single-user calibration approval and 2026-10-26 Foundry delegated-user decision remain limited to their recorded scopes; this proposal does not repeal, expand, or supersede them.
- **ASSUMPTION-003**: No exact principal, tenant/workspace, item/source scope, or required grant has been selected by Jason for this reconciliation.

## 8. Related Specifications / Further Reading

- `.squad/decisions.md` — accepted decision history, including the 2026-10-24 calibration approval, 2026-10-26 Foundry delegated-user decision, and 2026-10-28 Offset POC workload-identity preference.
- `plan/process-task-025-remediation-reverification-1.md` — related remediation and reverification plan.
- `evidence/task-025-failure-record-v1.json` — unaccepted failure-record observations and their stated limitations.
- `docs/data-agent-security-posture.md` — historical security posture to reconcile only after all approval gates.
- `docs/data-agent-design.md` — historical design to reconcile only after all approval gates.
- [Microsoft Learn: Managed identities for Azure resources](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview) — consult only if relevant to the integration approved in Phase 1; Thomas must verify the page is current and cite the applicable content and access date.
- [Microsoft Learn: Service principal authentication for Microsoft Fabric](https://learn.microsoft.com/en-us/fabric/security/service-principal-authentication) — consult only if relevant to the integration approved in Phase 1; Thomas must verify the page is current and cite the applicable content and access date.
- Current Microsoft Learn documentation specific to the approved Data Agent and authentication flow — Thomas records the exact page titles, URLs, relevant statements, and access dates in the Phase 2 review record before relying on them.
