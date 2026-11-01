# Offset Well Analysis v2 — additive run context contract

Status: **local contract and offline fixtures only**.

## Version pins

| Field | Exact value |
|---|---|
| `contractVersion`, `queryContractVersion` | `offset-well-analysis-v2` |
| `transformationContractVersion` | `1.2.0` |
| `datasetVersion` | `v1.2.0` |
| `manifestSha256` | `6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0` |
| `releaseId` | `v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0` |

`contractVersion` (`offset-well-analysis-v2`) names the API schema. It is
distinct from data release/version fields (`datasetVersion`, `releaseId`).

v2 preserves all v1 eligibility and metrics semantics. v1 remains unchanged and
strictly closed (unknown properties rejected by its schema/parser).

## Additive response fields

`target` (optional planned intent only, never inferred from observed history):
- `plannedBitType`
- `plannedBhaType`
- `plannedMudType`

`candidate` and `comparison` (optional):
- planned intent fields above
- `runConfigContext.runTuples[]`:
  `{ bitType, bhaType, mudType, mudWeightPpg, mudFunnelViscositySec, acceptedRunCount, acceptedFootageFt, acceptedDurationHours }`
- `eventContext`:
  - `totalEventCount`, `totalEventDurationHours`
  - `byType[{eventType,eventCount,eventDurationHours}]`
  - `bySubtype[{eventType,eventSubtype,eventCount,eventDurationHours}]`

Allowed `eventType`: `LOSSES`, `STUCK_PIPE`, `VIBRATION`, `NPT`, `TRIP`.
Event context is sourced from synthetic run-event records only, not from quality
warning/error signals. No event-rate or extra denominator fields are added.

## Serving view provenance

v2 context fields are sourced from:
- `serving.offset_run_config_summary`
- `serving.offset_run_event_summary`

Section-grain metrics and denominator semantics remain unchanged from v1.

## Grain caveat and decision workflow usage

- `metrics` remain scoped to `MATCHING_WHOLE_SECTIONS`.
- `runConfigContext` and `eventContext` are additive **well-wide** aggregates by
  `wellId` and do not share the same filtered denominator as matching-section
  metrics.
- The client decision workflow is human-led: compare selected wells, choose one
  explicit reference well, and generate a qualitative evidence brief. This
  workflow does **not** authorize prediction, transfer, or scaling of target
  footage, duration, ft/hour, events, or drilling parameter recommendations.

## Provenance rendering expectations (client)

- The existing Result provenance panel should present available evidence fields
  as returned (no inferred values): source views, grain, units, denominators,
  and quality caveats.
- Correlation identifiers (`toolCallId`, `resultId`, `contextHash`) are shown
  only when present in the response; missing identifiers must be labeled as
  unavailable.

## Schema

JSON Schema 2020-12: [offset-well-analysis-v2.schema.json](offset-well-analysis-v2.schema.json)
