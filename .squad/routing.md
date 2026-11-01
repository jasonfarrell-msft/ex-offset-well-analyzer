# Work Routing

How to decide who handles what.

## Operative Named-Member Routing

This JSON block is the explicit current allowlist for named-member spawning and
`squad:{member}` issue routing. Only `active_members` are routable. Every
`inactive_members` name or label, and every name or `squad:*` label absent from
`active_members`, fails closed to the coordinator for a scope decision and must
not spawn an agent.

```json
{
  "coordinator": "sung-jinwoo",
  "issue_label_pattern": "squad:{member-id}",
  "active_members": [
    "sung-jinwoo",
    "go-gunhee",
    "woo-jinchul",
    "min-byung-gyu",
    "cha-hae-in",
    "yoo-jinho",
    "baek-yoonho",
    "thomas-andre",
    "igris",
    "beru"
  ],
  "inactive_members": [
    "choi-jong-in"
  ],
  "inactive_or_unlisted_action": "route_to_coordinator"
}
```

## Routing Table

| Work Type | Route To | Examples |
|-----------|----------|----------|
| Live offset scope, architecture, and milestone governance | Sung Jinwoo | End-to-end bounded delivery decisions, ownership splits, evidence gates, rollback safety |
| Microsoft Fabric, Lakehouse, SQL, and semantic model | Go Gunhee | OneLake/Lakehouse organization, notebook and SQL contracts, semantic model, fixed workspace binding, capacity-aware Fabric design |
| Drilling schema and synthetic data | Woo Jinchul | Run-level schema, coherent deterministic generation, units, quality defects, provenance, dataset versions |
| Offset-well engineering and comparison requirements | Min Byung-Gyu | Comparable intervals, drilling method/bit/BHA, drilling fluids, target-versus-offset context, historical performance definitions and lessons |
| Backend/Data Agent integration and fail-closed orchestration contracts | Yoo Jinho | Typed operation contracts, request/context correlation, Data Agent/Fabric relay integration, no mock fallback |
| Independent validation and evidence | Baek Yoonho | Data controls, schema/JSON/TMDL checks, reproducibility, calibration contracts, evidence and claim review |
| Live Offset UI and context presentation | Cha Hae-In | Target/filter/selection/comparison UX on existing app, context lifecycle handling, disclosures and evidence presentation |
| Foundry orchestration and MCP tool policy wiring | Beru | Foundry tool behavior, context-safe prompts/contracts, single-orchestrator policy for live offset chat |
| Fabric identity and minimal POC governance | Thomas Andre | Named-user least privilege, source/ACL boundaries, secret handling, retention, synthetic-only controls |
| Validation automation and capacity governance | Igris | Local CI/security checks, dependency audit, budgeted capacity windows, deploy/rollback verification |
| Session logging | Scribe | Automatic; never needs routing |
| Work queue monitoring | Ralph | Board scans and continuous work-loop coordination when activated |
| RAI review | Rai | Content safety, bias checks, credential detection, ethical review |
| Claim verification | Fact Checker | Source checks, counter-hypotheses, anti-fabrication, external claim verification |

## Dormant / Future Specialties

These specialists remain useful, but they receive no current milestone work:

| Specialty | Owner | Current status |
|-----------|-------|----------------|
| Prediction and similarity methodology | Choi Jong-In | Dormant; explicitly outside the Fabric-only historical-summary milestone |
| Broader demonstrator UI and frontend explainability beyond approved live offset slice | Cha Hae-In | Live offset UX is active; prediction/similarity or non-synthetic expansion remains gated |
| Foundry agents and custom orchestration beyond approved single-orchestrator path | Beru | Active only for approved live offset wiring; broader multi-agent expansion remains out of scope |

## Issue Routing

| Label or request | Action | Who |
|------------------|--------|-----|
| `squad` | Triage and assign only a label in `active_members` | Sung Jinwoo |
| Active name or label derived from `active_members` and `issue_label_pattern` | Pick up issue and complete the work | Allowlisted active member |
| Inactive or unlisted name / `squad:*` label | Reject named-member routing; do not spawn; send for scope decision | Sung Jinwoo |

## Rules

1. **Allowlist before eagerness** — resolve every named-member request and `squad:*` label against `active_members` in the operative JSON block before spawning. Inactive or unlisted values fail closed to Sung Jinwoo for a scope decision.
2. **Eager within the allowlist** — spawn active agents who could usefully start work, including anticipatory downstream work, but never bypass the operative allowlist.
3. **Scribe always runs** after substantial work as `mode: "background"` and never blocks.
4. **Quick facts stay direct** — the coordinator answers without unnecessary delegation.
5. **Primary-domain routing** — when two agents could handle work, route to the owner of the primary concern.
6. **Team fan-out** — "Team, ..." routes only to relevant `active_members` in parallel.
7. **Anticipate validation** — engage Baek Yoonho early enough to define independent checks, but never assign Baek authorship of the artifact Baek will independently review.
8. **Method owners stay in lane** — Woo Jinchul owns drilling and synthetic-data semantics; Go Gunhee owns Fabric and semantic-model contracts; Yoo Jinho owns Data Agent/calibration integration; Baek Yoonho independently validates their artifacts.
9. **Fabric ownership is dedicated** — route Fabric platform architecture to Go Gunhee, not Woo Jinchul or another domain owner. Woo owns drilling semantics and synthetic-data definitions; Go Gunhee owns how those data products are organized and operated in Fabric.
10. **Fabric collaboration contracts** — Go Gunhee collaborates with Woo Jinchul on drilling schemas and synthetic-data layout, Yoo Jinho on the Data Agent and calibration boundary, Baek Yoonho on validation evidence, and Sung Jinwoo on architecture decisions.
11. **Fabric boundaries** — Go Gunhee does not absorb drilling-domain ownership, calibration implementation, or independent validation. Platform guidance must reflect current GA Microsoft Fabric capabilities and official Microsoft guidance; preview-only capabilities are out of scope unless explicitly identified as such.
12. **Independent evidence gate** — Baek Yoonho validates artifacts produced by others. Sung Jinwoo integrates findings but cannot overrule an evidence rejection without new evidence and re-review.
13. **Synthetic-only claim guard** — no route may convert synthetic demonstration results into real-world predictive, operational, safety, cost, compliance, or production-readiness claims.
14. **Reviewer rejection lockout** — when Baek Yoonho rejects evidence, or Rai issues a Red verdict, the original author is locked out from revising that rejected artifact. The coordinator assigns a different qualified agent; the rejecting reviewer provides guidance and re-reviews.
15. **Fact-checking gate** — a contradicted factual claim in a user-facing artifact blocks shipment and follows the same reviewer-rejection protocol.
16. **Issue routing** — Sung Jinwoo triages the base `squad` label. Only allowlisted active labels route directly; inactive or unlisted names and labels route to Sung Jinwoo without spawning.
17. **Minimal governance ownership** — Thomas Andre owns the current named-user identity, least-privilege ACL, secret-handling, retention, and synthetic-only governance boundaries. Private-network and cross-service architecture are not current routes.
18. **Identity and secret defaults** — use the explicitly approved named Fabric user for this bounded POC. Do not place secrets in code, configuration, logs, or evidence.
19. **Superseding live-offset authorization (2026-10-29)** — Jason explicitly authorized live offset wiring/deployment scope including required Foundry/Fabric changes within existing architecture. Prior offline-only and Foundry dormancy restrictions do not apply to this delivery.
20. **Data Agent state** — runtime is configured to use fixed Fabric Data Agent endpoint `.../dataagents/dd1cd69f-3b49-4575-932f-1d871f73d2e2/agent`; continue published-only, explicit rebinding, fail-closed behavior, and no implicit mock fallback.
21. **Capability maturity** — use current GA Fabric capabilities by default. Any preview dependency requires explicit recorded acceptance and an exit strategy before implementation.
22. **Operational ownership** — Igris owns local validation automation and paused-capacity/budget-window controls, but not architecture approval, Data Agent behavior, Fabric data modeling, or independent analytical validation.
23. **Paused-capacity gate** — `fabricwelladvisorcusmx01` is currently paused. Capacity resume and live Fabric validation/execution still require a bounded budget window and explicit operator controls before rollout verification.
24. **Current milestone gate** — this milestone now includes live offset backend/frontend wiring through existing ACA+Foundry+Fabric path; implementation remains bounded to synthetic historical summary scope and existing infrastructure.
25. **No unapproved Git mutation** — commit, push, and branch creation remain unauthorized unless Jason explicitly authorizes them.
