# Offset Well Analysis v1 — proposed wire and query contract

Status: **local contract and offline fixtures only** (TASK-006/007/008).
Not an existing Data Agent API, approved product defaults, deployed endpoint,
or proof of end-to-end capability. No cloud calls are required to validate it.

## Versions, authority and compatibility

| Field | Exact value |
|---|---|
| `contractVersion`, `queryContractVersion` | `offset-well-analysis-v1` |
| `transformationContractVersion` | `1.1.0` |
| `datasetVersion` | `v1.1.0` |
| `manifestSha256` | `904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d` |
| `releaseId` | `v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d` |

The [v1.1.0 transformation appendix](../data-transformation-contract.md#9-additive-offset-contract-v110--local-specification-only)
defines source types, precision, nullability and proposed products. The immutable
archive schema enumerates every raw field. Wire names are explicitly camelCase;
they are not aliases to arbitrary model-generated source fields. Unknown
versions and extra properties fail closed. No version coercion or "latest".
v1.0.0 continues its existing interface/disclosure and has no target/location
products; it is independently graded offline, never joined to v1.1.0 by ID.

Stable source keys are `(_release_id,well_id)`, `(_release_id,section_id)`,
`(_release_id,run_id)`, `(_release_id,quality_issue_id)` and
`(_release_id,target_id)`. Run-to-section checks release, section **and well**.
Duplicate IDs or invalid references reject the release/result, never
deduplicate measurement facts to conceal errors. Issue IDs are deduplicated
before joining independently aggregated issue counts; contradictory copies fail.
The target's `referenceDatasetVersion` and `referenceManifestSha256` identify
v1.0.0 provenance only. Identical well IDs in two releases do not authorize a join.

## Planning and historical fields

`target` in the schema exposes only safe planning fields: `targetId`,
`recordKind`, `basinName`, `fieldName`, `expectedFormationName`,
`plannedTrajectoryProfile`, `plannedHoleSizeIn`, `plannedMdMinFt`,
`plannedMdMaxFt`, `coordinateFrameId`, `locationSemantics`, `coordinateUnits`,
`surfaceXFt`, `surfaceYFt`, `referenceDatasetVersion`,
`referenceManifestSha256`, `isSynthetic`. Release/version provenance comes from
the containing envelope. All target values are required and non-null for this
release. No realized footage/duration/run/quality/split/outcome properties are
allowed on targets. No target is a historical well or training example.

Historical canonical formation and trajectory may be unknown in future result
rows: use explicit `null`, never empty/zero/invented labels. The actual archive
allows null section/run formation and raw formation, null run bit IADC, and null
issue observed value/section/run references. This extension does not alter those
source rules or make current required trajectory data nullable at ingestion.
Keep canonical `formation_name` and raw `formation_name_raw` separate; the archive
already carries aliases (e.g. `syn_brimstone` → `Synthetic Brimstone`). Do not
re-normalize raw text or guess canonical labels. `UNKNOWN` is a presentation
state, not a formation that can satisfy equality. Neither trajectory nor basin/
field is a hidden predicate. Planned trajectory is never an observed outcome.

## Deterministic eligibility

1. Require finite surface coordinates, identical `SYN-LOCAL-FT-V1` frames,
   `ft` units and `SYNTHETIC_SURFACE_WELLHEAD` semantics. Axes are abstract;
   there is no east/north, latitude/longitude, EPSG, subsurface distance,
   geological similarity or trajectory inference.
2. Compute exact decimal
   `distanceSquaredFt2 = (targetXFt-wellXFt)^2 + (targetYFt-wellYFt)^2`.
   Include iff `distanceSquaredFt2 <= radiusFt^2`, **before rounding**.
   Radius zero includes only compatible coincident coordinates.
   `distanceFt` is the square root rounded half-up to one decimal for display.
3. Filter a historical section by **all** enabled criteria: canonical formation
   equals target expected formation; exact decimal hole size equals planned
   size; and, only if `mdOverlap=true`,
   `max(startMdFt,plannedMdMinFt) < min(endMdFt,plannedMdMaxFt)`.
   Missing operands fail the enabled predicate. Touching MD endpoints do not
   overlap. Malformed/reversed/nonfinite intervals are invalid, not matches.
4. Aggregate whole matching sections once per well. Do not prorate quantities to
   an MD overlap. A candidate needs at least one matching section and positive
   accepted run count across matching sections. An all-quarantined section can
   contribute quarantine coverage to another eligible well's matching scope,
   but an all-quarantined well is ineligible.
5. Order eligible candidates by exact `distanceSquaredFt2`, then `wellId`
   ascending (ordinal ASCII). This is **proximity ordering, not similarity
   ranking**. All compatible exclusions/unknowns have explicit coverage reasons;
   no automatic widening, hidden filtering or default selection.

## Metrics and quality

All metrics are per selected well over the **identical matching whole sections**
used for eligibility, within exactly one release/target/criteria context.
Accepted means run `quality_status` in `PASS`,`WARNING`; `ERROR` is quarantined.
Source well/section totals include errors and are not accepted totals.

| Field | Definition / unit |
|---|---|
| `matchingSectionCount` | Count of distinct matching sections, including an all-quarantined matching section |
| `acceptedRunCount` | Count of distinct accepted runs in matching sections / runs |
| `acceptedFootageFt` | SUM accepted `footage_ft` / ft |
| `acceptedDurationHours` | SUM accepted `duration_hours` / hours |
| `averageFootagePerRunFt` | accepted footage / accepted run count / ft/run |
| `summaryPenetrationRateFtPerHour` | accepted footage / accepted duration / ft/hour; ratio of recorded summary quantities, **not instantaneous ROP** |
| `quarantinedRunCount` | Distinct ERROR runs in matching sections / runs |
| `warningRunCount`, `warningSectionCount` | Distinct WARNING entities at each named grain |
| `warningIssueCount` | Distinct WARNING issue IDs attached to matching sections/runs / issues, not runs |

Aggregate runs → section → well; divide sums, never average section/run ratios.
Do not join whole-well totals or sum target-expanded pairs across targets.
No accepted runs yields count zero, null footage/duration/ratios and
`NO_ACCEPTED_RUNS`; zero is not substituted for unknown measurements. Any missing
accepted quantity makes its sum and dependent ratio null with
`MISSING_ACCEPTED_QUANTITY`; never SQL-SUM away unknown quantities. Known zero
footage with positive duration produces true zero ratios. Any accepted
nonpositive duration is a quality failure: rate null with
`NON_POSITIVE_DURATION`, even if another run makes the total positive.
Negative accepted footage is invalid. Corrupt accepted measurements make a live
analytical operation unavailable; local edge fixtures describe the null behavior,
not permission to return invalid successful performance results.

### v1 response immutability

`offset-well-analysis-v1` responses and schema remain unchanged, strict, closed,
and immutable for this contract version. v1 does not include additive run-context
shapes.

Any richer run-context fields (for example run-configuration or event-context
blocks) are defined only in the separate
[`offset-well-analysis-v2`](offset-well-analysis-v2.md) contract.

Source decimal strings parse invariantly, without floats. Wire decimals are
strings, counts integers and booleans actual booleans. Hole sizes retain three
decimals (`6.125`); no rounding before aggregation/filtering. Ratios serialize
to six decimal places half-up, distance display to one; canonical decimal text
has no exponent, plus sign, whitespace or negative zero. Nullable metrics use
JSON `null`. A null must carry a reason in `unavailableReasons`.

## Approved M1/M2 product profile — not production authorization

Jason approved GUD-001–005 exactly as written for this local contract and the
separately gated M2 staged proof: initial radius `10000 ft`; formation and hole
size matching enabled; MD overlap disabled; show basin/field and planned/
observed trajectory labels without hidden predicates; maximum radius
`3000000 ft`; 100 candidates total, 25 displayed per page only after validating
the complete candidate set, 1–5 manually selected wells and 12 release targets;
no auto-selection or auto-widening; invalidate context/continuation when target,
filters, selection or release changes; and the exact approved label
`SYNTHETIC DATA • v1.1.0 • DEVELOPMENT / OFFSET COMPARISON ONLY`.

Requests supply every criterion; there are no silent defaults. These bounds and
defaults are approved for M1/M2 contract/oracle work and use only within each
separately authorized M2 window exactly as gated. They are not production
implementation, deployment, source/field exposure, or live-query authorization.
Changes require a new explicit decision and consistent schema/fixture updates.

## Typed operations and context lifecycle

[JSON Schema 2020-12](offset-well-analysis-v1.schema.json) is a closed tagged
union of request/response definitions with executable examples. It constrains
wire types, required fields and shapes; cross-field semantics below also need
future server validation. The stdlib tests validate the used schema vocabulary
and semantic request rules independently; they are not a general schema engine.

| Route (proposed, not wired) | Operation | Request / response rows |
|---|---|---|
| `POST /api/offset-analysis` | `targets` | contract/release only / `target[]` |
| same | `candidates` | unselected `context` / `candidate[]` |
| same | `compare` | selected `context` / `comparison[]` |
| `POST /api/chat` extension | `chat` | selected `context`, `message`, optional `conversationId` / prose and `claims[]` |

Existing legacy chat shape remains unchanged when no typed offset context is
supplied. Do not route legacy prose to the offset union by inference.
The future offset extension carries `operation:"chat"` and the same release/
contract/context fields as comparison. Only user text is untrusted prose;
structured caller data never carries metrics, row data, SQL, query templates,
endpoints, evidence receipts or a caller-authoritative context hash.

Requests are UTF-8 JSON, maximum 8192 bytes and chat message 1–2000 Unicode
characters (also reject whitespace-only); the request-size limit is measured in
UTF-8 bytes. Reject duplicate JSON member names before schema validation. IDs
follow exact release-specific patterns and must exist in the
active approved release. Compare/chat require 1–5 sorted unique eligible well
IDs; candidates require an empty selection. Context includes a nonnegative
safe-integer `contextRevision`, selected IDs and all criteria.

The future server normalizes decimal strings, criteria and sorted selection,
then hashes UTF-8 compact JSON (`sort_keys=true`, no insignificant whitespace,
ASCII IDs) of contractVersion, releaseId, targetId, criteria, selectedWellIds
and contextRevision. Radius normalization removes insignificant trailing zeros.
Only the server produces `contextHash`; a client echo proves nothing.
Any target/criteria/selection/release change creates a fresh context and
continuation; unchanged context can reuse a server-bound continuation.
Do not accept an arbitrary `previous_response_id` as authorization. Continuations
must be bound to the browser session capability, release, context and receipts;
restart/expiry/foreign context fails closed as `stale`, without old evidence.
Old conversations remain readable only. ContextRevision alone is not identity.

## Response union and evidence proof obligation

`success` and `empty` analytical envelopes carry fixed version pins, operation,
normalized context (null for targets), server context hash (null for targets),
rows, `totalCount`, `truncated:false`, exclusions and an evidence receipt.
`success` has nonempty rows; `empty` is valid only for candidates, with zero rows.
Compare requires exactly the selected eligible set, never a partial success.
Targets require exactly the twelve unique targets. Candidate IDs must be unique
and fully proximity-ordered. Comparison rows follow sorted selected IDs.
Candidate and comparison rows include `matchingSections`, ordered by section ID,
with canonical formation, hole size, MD endpoints and descriptive observed
trajectory labels. Their unique section IDs must agree with
`matchingSectionCount`; these are section summaries, not individual runs.
Chat success carries selected context, prose, resolvable claim references and
evidence; no invented numeric answer. Error responses carry no rows/claims/
evidence and status `unavailable`, `stale` or `error` with a safe typed code.
For an unparseable/unsupported request, failure `operation` and `context` are
null, not an echoed arbitrary operation or a guessed valid context.
No partial-result envelope exists. `CLAIM_NOT_GROUNDED`, `INCOMPLETE_RESULT`,
`CONTEXT_MISMATCH`, `INVALID_REQUEST`, `CAPABILITY_UNPROVEN` and
`UPSTREAM_UNAVAILABLE` are safe codes, not raw upstream errors.

Exclusions are one row per excluded historical well, with unique reason codes:
incompatible coordinates, outside radius, no matching section or no accepted
runs. They contain no individual run data. **This proposed well-ID/reason
exposure requires approval**; do not silently widen existing public sources.
Unknown-value coverage can accompany `NO_MATCHING_SECTION` using
`UNKNOWN_FORMATION`, `UNKNOWN_HOLE_SIZE`, `UNKNOWN_MD`. A complete successful
candidate envelope accounts for all 100 historical wells exactly once across
candidates/exclusions; received row count alone still cannot certify completeness.

Evidence includes a safe opaque `receiptId`, server `requestId`, `toolCallId`,
`resultId`, operation/context association and fixed release/hash/query versions
in the parent envelope; authorized view/columns or semantic measures; metric
grain, units, denominators, and quality caveats. Source references are allowlisted
serving summaries only; raw, curated, control, physical tables and individual
runs are never public evidence. Each chat claim resolves to a receipt/source
index and selected well IDs; numerical claims must match authenticated values.
No tokens, hidden prompts, unrestricted SQL or session capabilities are exposed.

Receipts are created **only after** authenticated actual tool-result validation:
allowlisted source, schema/types, full-set completion, release/target/criteria/
selection, uniqueness/order, units/denominators and server-owned request→tool→
result binding. A successful `mcp_call`, model-authored `totalCount`,
`truncated:false`, source name or echoed context **is not authority**. Neither
this schema nor an offline fixture proves authentication, completeness or
correlation. Source authentication alone is insufficient to bind request context.
The server validates evidence, never recomputes local CSV/SQL analytics to fill
missing results or certify completeness.

## Source binding and next gate

Only the plan's recorded architecture is assumed: browser → existing ACA
orchestrator → Foundry → authenticated fixed MCP relay → Fabric Data Agent →
approved serving views. Recorded source: existing direct-view public Data Agent;
the separate semantic calibration agent is not an implicit replacement.
This task did not inspect/export live IDs, prompts, permissions or source trees.
The plan records Foundry v7 and selected descendants of excluded parents;
effective bindings, ACLs and structured transport remain **unknown**, not proven.

TASK-025 must separately authorize baseline export/read-back and effective
descendant exposure verification. TASK-026 then proves authenticated structured
results, complete unchanged-view answers, and server-owned request/context/tool/
result correlation against the v1.0.0 offline oracle; TASK-028 proves staged
offset sets/metrics against all twelve v1.1.0 targets. Stop on missing authority,
partial/mixed-context evidence or failed cost/exposure gate. No fallback, cloud
resume, publication, infrastructure or source expansion is authorized here.

Prediction, similarity/engineering ranking, predicted deltas, optimization and
operational drilling advice are excluded. Proposed offset assistant first line:
`SYNTHETIC DATA • v1.1.0 • DEVELOPMENT / OFFSET COMPARISON ONLY`.
It applies even to prose refusals/errors and must not relabel legacy answers.
Keep persistent fictional-surface and planned-versus-observed caveats.

## Offline validation

Run `python3.13 -m unittest discover -s tests -p test_offset_analysis.py -v`
or `python3.13 -m pytest -q tests/test_offset_analysis.py`.
Tests read both supplied immutable archives, never regenerate them, import no
production analytics and require no new packages. Expected sets, ratios and
hashes stay grader-only in tests, not in application prompts or runtime sources.
Observed offline distribution under the proposed 10000-ft formation/hole
profile: **12 nonempty, 0 empty** targets; enabling strict MD overlap gives
**8 nonempty, 4 empty** targets. These are fixture observations, not promises
of live matches or engineering suitability.
Missing archives fail with their exact required path; a clean clone must obtain
the separately approved immutable archives. Local success is not deployed
feature completion or live capability acceptance.
