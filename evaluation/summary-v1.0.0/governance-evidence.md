# Summary evaluation governance evidence

Version: `1.0.0`

This immutable excerpt contains only verbatim approved-source excerpts. It
does not create new access, deployment, disclosure, or encoding policy.
Stable evidence IDs below are citation targets. The catalog records the exact
source heading, source excerpt, and SHA-256 digest for every quoted claim.

## GOV-SCOPE-001 — Historical summary milestone boundary

Milestone one is limited to grounded summarization of synthetic historical drilling data in Microsoft Fabric. It includes the data contract, deterministic generator, Fabric ingestion and transformation, governed semantic definitions, summary-question evaluation, citations, synthetic-data disclosure, and a curated activity receipt. Comparable-run retrieval, similarity scoring, and prediction are deferred to later milestones and must not be introduced into milestone-one scope.

## GOV-SYNTHETIC-LIMITS-001 — Synthetic evidence limitations

Synthetic data may demonstrate workflow behavior, reproducibility, data-quality controls, and recovery of specified simulated relationships. It does not establish real-well predictive accuracy, operational recommendations, production readiness, safety, cost savings, or regulatory compliance.

## GOV-DATA-ACCESS-001 — Verified serving-source boundary

The model may use only the verified active-release `serving` SQL analytics endpoint views in endpoint `7d5ceff0-e27e-4459-9ca7-37043dd3e91c`, as evidenced by `evidence/fabric-summary-publication-v1.0.0.json`.

Use only read access to the verified `serving` views for development and validation. This authorization does not permit mutation of published Lakehouse data or expansion to unverified sources.

## GOV-EXPORT-001 — Sharing and export controls

The existing governance controls remain binding: Central US residency; classification `Internal — Synthetic POC; no real operator data`; indefinite retention for reuse; external sharing disabled; exports restricted to project administrators; and no secrets.

## GOV-SECRETS-001 — Explicit credential and secret controls

Define the correlation identifiers and safe field mapping between them without exposing hidden prompts, credentials, sensitive telemetry, or internal reasoning.

Managed identity is the default. Secrets are prohibited in code and configuration; Key Vault is used only when identity-based access is unavailable.

Hardcoded API keys, tokens, passwords, connection strings

Secrets in environment variable defaults or config templates

## GOV-PROMPT-001 — Safety-bypass instructions

Instructions that bypass AI safety guidelines or content filters

## GOV-FABRIC-001 — Authorized Fabric verification boundary

Read-only verification queries, model refresh testing, and metadata validation are authorized.

Use only read access to the verified `serving` views for development and validation. This authorization does not permit mutation of published Lakehouse data or expansion to unverified sources.

This authorization does not permit a Fabric Data Agent, Foundry agents, custom UI, prediction, similarity, a validation workspace, real data, external sharing, new capacity, production-readiness or business-performance claims, or public release.

User identity and authorization must survive each service boundary without shared credentials, privilege expansion, or loss of row-level policy context.

## GOV-AUTHORIZATION-001 — Explicitly approved authorization

After the approved Fabric summary publication was recorded, the user explicitly instructed the team to proceed to the next step and specified the authorized and prohibited scope captured below.

Authorize local, source-controlled development of one summary-only semantic model and deployment of that single model to the existing Fabric development workspace `ws-welladvisor-drillrunhistory-poc-dev` (`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`). The model may use only the verified active-release `serving` SQL analytics endpoint views in endpoint `7d5ceff0-e27e-4459-9ca7-37043dd3e91c`, as evidenced by `evidence/fabric-summary-publication-v1.0.0.json`. Read-only verification queries, model refresh testing, and metadata validation are authorized. Drafting an objective summary-answer question set and proposed numerical evaluation thresholds is also authorized.
