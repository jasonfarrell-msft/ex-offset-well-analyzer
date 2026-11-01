# Fabric Data Agent POC baseline

**Classification:** Internal — synthetic POC; no real operator data

## Architecture

`authorized named Fabric user -> Fabric Data Agent -> sm_drillrun_summary -> Fabric Lakehouse/SQL`

No Fabric Data Agent currently exists, and Fabric capacity is paused. The
source-controlled definition does not authorize recreation, publication, or
invocation. Any future recreated item must remain unshared, receive explicit
user approval, be published before MCP use, and be bound by exact validated
UUID with no default or mock fallback.

The source-controlled Data Agent may use only semantic model
`sm_drillrun_summary` (`ee7583b6-5be7-4802-83a8-530ce7dd8351`) in workspace
`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`, limited to the `Wells`, `Dataset
Metadata`, `Data Quality`, and `Categories` tables. It may not attach a second
model or a direct Lakehouse, SQL, file, website, or API source.

## Access and data

Calibration requires the approved Fabric user's exact UPN and object ID in the
local-only `DRILLRUN_APPROVED_USER_PRINCIPAL_NAME` and
`DRILLRUN_APPROVED_USER_OBJECT_ID` environment variables. Both values must match
the independently approved identity record. Missing or mismatched configuration
fails closed; approval is never inferred from the signed-in account. Additions
or substitutions require explicit approval and an ACL review. Shared identities,
anonymous access, and public sharing are not part of this POC.

All data is fictional and development-only. The agent is summary-only and must
not return raw records, predictions, similarity results, or operational
recommendations. Every response must begin with:

`SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY`

Credentials, tokens, connection strings, and secrets must never be committed or
written to calibration evidence. Grader-only fields must not enter agent input.
Each calibration case starts a clean conversation.

## Cost and approval

Fabric capacity `fabricwelladvisorcusmx01` remains paused outside an explicitly
approved test window. Before resuming it, record the budget, responsible named
user, test scope, and pause time. Repository validation does not authorize
publication, calibration, sharing, or milestone release.

Any source, ACL, label, scope, secret-handling, or evaluation-gate failure stops
the run. Remediation requires a complete rerun and explicit milestone approval.
