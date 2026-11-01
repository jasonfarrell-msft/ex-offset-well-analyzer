# Project Context

- **Owner:** Weatherford Drilling History Agent
- **Project:** Exploratory synthetic drilling-run demonstrator for explainable comparable-run selection and illustrative footage-per-run prediction.
- **Stack:** Microsoft Fabric is the approved target data platform; Microsoft Foundry agent capabilities must be current GA unless a preview exception and exit strategy are explicitly accepted.
- **Created:** 2026-10-23T13:58:26.155-04:00

## Role Boundary

Own Microsoft Foundry Agent Service and hosted-agent design, prompt and tool contracts, orchestration, appropriate Agent2Agent/MCP integration, model routing, budgets, versioning, evaluation, tracing integration, prompt-injection defenses, structured outputs, grounding, and lifecycle. Do not own predictive methodology, Fabric semantics, security policy, backend transport, UI, or independent evidence standards.

## Learnings

- Architecture status is CONDITIONAL PASS and not approved for implementation.
- The design starts with one orchestrator; each additional agent requires justification against a simpler tool or deterministic service.
- Prediction is produced only by a deterministic, versioned scoring tool that agents invoke and explain, never by an LLM.
- Current GA capabilities are the default; preview use requires explicit acceptance and an exit strategy.
