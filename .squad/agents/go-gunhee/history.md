# Project Context

- **Owner:** Weatherford Drilling History Agent
- **Project:** Exploratory synthetic drilling-run demonstrator for explainable comparable-run selection and illustrative footage-per-run prediction.
- **Stack:** Microsoft Fabric is the approved target data platform, using a Fabric Lakehouse and OneLake/Delta-oriented architecture. Detailed implementation choices remain unapproved.
- **Created:** 2026-10-23T13:50:58.101-04:00

## Role Boundary

Own Fabric target architecture, OneLake/Lakehouse organization, medallion layers, Delta design, performance and capacity conventions, shortcuts, SQL analytics endpoint usage, lineage, workspace and security boundaries, deployment patterns, and Power BI handoffs. Do not absorb drilling-domain ownership, model methodology, backend or frontend implementation, or independent validation.

## Learnings

- The active platform decision selects Microsoft Fabric rather than SQL Server as the primary target; SQL remains an implementation convenience where Fabric supports it.
- Fabric ownership is intentionally separate from Woo Jinchul's drilling-schema and synthetic-data responsibilities.
- The POC remains governance- and architecture-only at this stage; no implementation, Fabric resources, notebooks, schemas, deployment files, or application code have begun.
- Platform recommendations must use current GA Microsoft Fabric capabilities and official Microsoft guidance; preview-only claims are out of scope unless explicitly identified.
