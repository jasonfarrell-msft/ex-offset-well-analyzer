# Fabric Data Agent design

## Definition and source boundary

`fabric/da_drillrun_summary.DataAgent` is the source-controlled Microsoft
Fabric Data Agent definition. Its only source is semantic model
`sm_drillrun_summary` (`ee7583b6-5be7-4802-83a8-530ce7dd8351`) in workspace
`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`.

The source selection is explicit and limited to:

- `Wells`
- `Dataset Metadata`
- `Data Quality`
- `Categories`

There is no automatic discovery, second source, direct Lakehouse access, or
direct SQL access. Fabric does not currently enforce semantic-model column
selection, so the selected tables, hidden fields, explicit measures, source
instructions, and agent instructions together define the summary boundary.

`Categories` contains source-history summaries. Formation counts come from
source sections; bit, BHA, and other run-grain counts come from source runs.
These values may include quarantined source runs and must not be described as
accepted-only counts.

## Response contract

The first line of every response, including a clarification, refusal, error, or
partial answer, must be exactly:

`SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY`

No separator normalization, paraphrase, translation, alternate punctuation,
case change, leading text, or later-position substitute is accepted.

The agent may answer only development-only historical summary questions
supported by explicit semantic-model measures. It must clarify ambiguous
filters and refuse requests for raw records, individual run detail, deep
provenance, predictions, similarity, real-data claims, secrets, write actions,
administration, or operational recommendations.

The checked-in draft and published-stage definitions are identical. They add no
few-shots, actions, tools, or additional sources. Their presence in Git is not
authorization to publish or invoke a live item.

No Fabric Data Agent currently exists. The predecessor was deleted, and its ID
is not an operational target. Recreation and unshared publication are future
user-approved milestones; a newly approved item ID must be explicitly rebound
before the published-only MCP preflight or a zero-start calibration.

## Identity, publication, and capacity

Only an explicitly approved named Fabric user may create, publish, configure,
or invoke the Data Agent. Calibration requires the approved user's exact UPN and
object ID in local-only `DRILLRUN_APPROVED_USER_PRINCIPAL_NAME` and
`DRILLRUN_APPROVED_USER_OBJECT_ID`; both must match the independently approved
identity record. Missing or mismatched approval fails closed; no signed-in-user
default is accepted. Tokens and credentials remain in-memory and must not enter
source or evidence.

Fabric capacity `fabricwelladvisorcusmx01` remains paused outside an approved,
budgeted test window. Publishing, calibration, or milestone release requires a
separate recorded approval and post-publication source and ACL verification.

## Calibration

Use the versioned 36-case evaluation with a clean conversation for every
attempt. Verify exact labeling, summary facts, ambiguous-filter clarification,
category quarantine disclosures, scope refusals, citations, repeatability, and
latency. Grader-only fields must never enter the model input.

Any source, ACL, label, secret-handling, scope, or evaluation-gate failure stops
the run. A partial or failed run cannot be combined with a later run. Remediate,
rerun the complete evaluation, and obtain explicit milestone approval.
