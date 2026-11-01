# Deployment Plan (sanitized summary)

## Status

- **v1.2 Offset Well Analysis is deployed and active** (existing-resource rollout; no new infrastructure provisioned).
- The loader, reference-well decision flow, and display corrections are deployed to the container app.
- Validation: unit/API/web/client tests and build passed; post-deploy health, static-asset, and offset/chat canary checks passed.
- Release rollout used a container image build in the registry and a new container app revision, verified by revision state and HTTP checks.

## Scope

- Region: Central US.
- Components: Container Apps web/API host, Azure Container Registry, Fabric lakehouse/SQL endpoint and notebook loader.
- Identifiers (subscription, tenant, resource names, item/job IDs) are intentionally omitted from this repository copy.

## Guardrails

- Managed Identity for service-to-service access; no secrets, keys, or connection strings in source or configuration.
- Fabric capacity pause is a manual operator action after verification.

## Operational history

Detailed deployment logs, request/response captures, and diagnostics are intentionally excluded from version control. Keep them in the private operations record.
