# Project Context

- **Owner:** Weatherford Drilling History Agent
- **Project:** Exploratory synthetic drilling-run demonstrator for explainable comparable-run selection and illustrative footage-per-run prediction.
- **Stack:** Microsoft Fabric is the approved target data platform, using a Fabric Lakehouse and OneLake/Delta-oriented architecture. Detailed implementation choices remain unapproved.
- **Created:** 2026-10-23T09:33:40.483-04:00

## Role Boundary

Own scope, architecture, interfaces, technical decisions, and integration. Guard the synthetic-demonstrator versus real-validation distinction. Do not independently approve model evidence.

## Learnings

- The POC is setup-only at initialization; implementation has not begun.
- Real-world claims require representative Weatherford-approved real-well holdouts and agreed acceptance criteria.
- Fabric platform architecture belongs to dedicated specialist Go Gunhee; Woo Jinchul retains drilling schemas and synthetic-data ownership.

📌 Team update (2026-10-27T14:30:22.990-04:00): Project requester approved a data-only v1.1.0 expansion for fictional proximity-capable wellhead coordinates and separate planned-target rows; preserve v1.0.0, make no operational claims, and do not add UI work — decided by Project requester
