# Project Context

- **Owner:** Weatherford Drilling History Agent
- **Project:** Exploratory synthetic drilling-run demonstrator for explainable comparable-run selection and illustrative footage-per-run prediction.
- **Stack:** Microsoft Fabric is the approved target data platform; Microsoft Foundry agent capabilities remain subject to the nine pre-implementation decisions and current GA availability.
- **Created:** 2026-10-23T13:58:26.155-04:00

## Role Boundary

Own Microsoft Entra application architecture, delegated/OBO flows, managed identity, least-privilege RBAC, Conditional Access integration, private networking, threat modeling, egress controls, Purview/DLP, classification, residency, retention, and cross-service security boundaries. Do not implement the application, define Fabric topology or model methodology, or perform independent empirical validation.

## Learnings

- Architecture status is CONDITIONAL PASS and not approved for implementation.
- Managed identity is the default; secrets are prohibited in code and configuration, with Key Vault reserved for cases where identity-based access is unavailable.
- Security and data-governance ownership are combined for the synthetic POC; a dedicated privacy or governance authority may be required when real operator data enters scope.
- The synthetic-only evidence guard and Baek Yoonho's independent evidence authority remain active.

- 2026-10-29 TASK-025 offline review: no approval-ready hash-bound manifest exists. TASK-005 identity/documentation reconciliation, exact caller/target/permissions, bounded workload/cost/deadline, and independent approval of the minimum-permissions report remain unresolved. No live operation is authorized by the review. Jason chose to keep both historical Data Agent documents unchanged.
