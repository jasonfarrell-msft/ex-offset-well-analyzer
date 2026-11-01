# Project Context

- **Owner:** Weatherford Drilling History Agent
- **Project:** Exploratory synthetic drilling-run demonstrator for explainable comparable-run selection and illustrative footage-per-run prediction.
- **Stack:** Not approved or selected in the source brief.
- **Created:** 2026-10-23T09:33:40.483-04:00

## Role Boundary

Own APIs, workflow orchestration, dataset/model version endpoints, reproducible execution, persistence, and frontend integration. Do not redefine generator or model methodology.

## Learnings

- 2026-10-29 TASK-025 offline review: documented definition request is `POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/dataAgents/{dataAgentId}/getDefinition`, with `format` omitted, 200 or 202/LRO, and read/write permission. Body semantics, exact target/caller, LRO procedures, evidence artifacts, and bounded limits remain unresolved; the API shape is not execution approval. Jason chose to keep both historical Data Agent documents unchanged.

- Reproducibility requires generator settings, dataset/split/feature rules, model versions, tuning history, and evaluation outputs.
- No platform, framework, or deployment target has been approved.
