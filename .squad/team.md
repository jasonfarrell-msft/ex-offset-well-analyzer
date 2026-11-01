# Squad Team

> Weatherford Drilling History Agent — synthetic drilling-run analytical demonstrator

## Coordinator

| Name | Role | Notes |
|------|------|-------|
| Squad | Coordinator | Routes work, enforces domain boundaries, handoffs, and reviewer gates. |

## Members

| Name | Role | Charter | Status |
|------|------|---------|--------|
| Sung Jinwoo | POC Lead / Solution Architect | [charter](agents/sung-jinwoo/charter.md) | Active |
| Go Gunhee | Microsoft Fabric & Lakehouse Architect | [charter](agents/go-gunhee/charter.md) | Active |
| Woo Jinchul | Drilling & Synthetic Data Engineer | [charter](agents/woo-jinchul/charter.md) | Active |
| Min Byung-Gyu | Offset Well Analysis & Drilling Engineering Specialist | [charter](agents/min-byung-gyu/charter.md) | Active — domain guidance for target-versus-offset comparisons |
| Choi Jong-In | Applied ML & Similarity Scientist | [charter](agents/choi-jong-in/charter.md) | Inactive / dormant — prediction and similarity are outside the current milestone |
| Cha Hae-In | Frontend & Explainability Engineer | [charter](agents/cha-hae-in/charter.md) | Active — live Offset Well Analysis frontend integration on existing app path |
| Yoo Jinho | Calibration & Contract Integration Engineer | [charter](agents/yoo-jinho/charter.md) | Active |
| Baek Yoonho | Validation & Evidence Engineer | [charter](agents/baek-yoonho/charter.md) | Active |
| Thomas Andre | Fabric Identity & Minimal POC Governance Architect | [charter](agents/thomas-andre/charter.md) | Active |
| Beru | Microsoft Foundry Agent & Orchestration Engineer | [charter](agents/beru/charter.md) | Active — Foundry orchestration and context wiring for live offset flow |
| Igris | Validation Automation & Fabric Capacity Governance Engineer | [charter](agents/igris/charter.md) | Active |
| Scribe | Session Logger, Memory Manager & Decision Merger | [charter](agents/scribe/charter.md) | Built-in / background |
| Ralph | Work Monitor | [charter](agents/ralph/charter.md) | Built-in / monitor |
| Rai | Responsible AI Reviewer | [charter](agents/rai/charter.md) | Built-in / background |
| Fact Checker | Devil's Advocate & Verification Agent | [charter](agents/fact-checker/charter.md) | Built-in / verifier |

## Project Context

- **Owner / display name:** Weatherford Drilling History Agent
- **Project:** Weatherford Synthetic Data POC
- **Created:** 2026-10-23T09:33:40.483-04:00
- **Current milestone:** Wire and deploy live Offset Well Analysis (historical run chat + selected offset analysis) through the existing ACA host, Foundry orchestrator, and Fabric Data Agent.
- **Constraint:** Synthetic data may demonstrate workflow behavior, reproducibility, data-quality controls, and recovery of specified simulated relationships. It does not establish real-well predictive accuracy, operational recommendations, production readiness, safety, cost savings, or regulatory compliance.
- **Evidence gate:** Real-world claims require Weatherford-approved representative real-well holdouts and agreed acceptance criteria. The team must not invent thresholds.
- **Active architecture:** `anonymous browser -> ACA /api/chat -> Foundry agent -> authenticated ACA MCP relay -> Fabric Data Agent -> approved Fabric serving layer`.
- **Retained implementation:** Deterministic synthetic generator, Fabric Lakehouse notebook and SQL, summary semantic model, Data Agent definition, Foundry-backed chat host, offset contracts/plans, and minimal POC governance.
- **Future gate:** Capacity resume window controls, source/evidence validation, staged offset contract wiring, and rollout verification remain required; no real-data, write, or recommendation expansion is authorized.
- **Non-current domains:** Prediction/similarity scoring, private-network redesign, real data, writes, and operational recommendations.
- **Security defaults:** Named-user least privilege, no secrets in source or evidence, published-only MCP access, exact synthetic labeling, no implicit mock fallback, and fail-closed validation.
- **Squad state:** Preserve the existing local state backend.
- **Superseding scope decision (2026-10-29):** Jason explicitly chose live offset analysis delivery, including required Fabric/Foundry wiring changes, superseding prior offline-only and Fabric-only dormancy restrictions for this delivery. No commit/push/branch authorization was granted.
- **Source brief:** [`WEATHERFORD-SYNTHETIC-DATA-POC.md`](../WEATHERFORD-SYNTHETIC-DATA-POC.md), sourced from a local attachment (path omitted).