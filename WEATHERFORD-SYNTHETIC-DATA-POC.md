# Weatherford Synthetic Data POC

Last updated: 2026-10-26

Status: Fabric-only summary milestone approved as the target architecture.

## Purpose

Demonstrate governed historical summaries over fictional drilling-run data
without exposing operator data. Synthetic evidence can validate the workflow;
it cannot establish field accuracy, production readiness, operational benefit,
or safety.

## Approved milestone architecture

`authorized named Fabric user -> Fabric Data Agent -> semantic model -> Fabric Lakehouse/SQL`

The retained implementation consists of:

- deterministic synthetic well, section, and run history;
- release-aware Lakehouse transformations and SQL summary views;
- one summary semantic model;
- one Fabric Data Agent definition; and
- versioned calibration and evaluation contracts.

Foundry, hosted models or agents, custom orchestration, predictions, similarity,
and operational recommendations are outside this milestone.

No Fabric Data Agent currently exists, and Fabric capacity is paused. The
definition is retained source only. Future recreation and unshared publication
require explicit user approval, after which the newly approved UUID must be
bound explicitly before published-only MCP preflight and calibration start
from zero.

## Synthetic data principles

- Clearly label all records and results as synthetic.
- Generate documented, internally coherent relationships rather than
  independently randomized columns.
- Include normal conditions, sparse records, sensor-quality problems, and
  rare-event scenarios.
- Treat simulated event frequencies as generation choices, not estimates of
  real operating frequencies.
- Track generation assumptions and provenance. Do not imply that synthetic data
  derived from confidential real data is automatically safe to disclose.

## Evaluation and evidence controls

- Use only the approved summary model and selected tables.
- Preserve generator settings, dataset versions, model versions, and evaluation
  outputs.
- Evaluate factual accuracy, scope behavior, citations, required disclosures,
  repeatability, and latency against the versioned contract.
- Treat a failed gate as a failed milestone; do not select favorable examples.
- Require explicit approval before deployment, publication, or scope expansion.

## Claims and limitations

The POC is limited to development-only historical summaries. It does not
authorize real data, row-level exports, write actions, predictions, similarity,
operational decisions, production-readiness claims, or public release.

Access is limited to explicitly named Fabric users. No credentials, tokens, or
connection secrets may be stored in source. Every user-visible response must
begin with the exact synthetic label defined by the evaluation contract.

Fabric capacity `fabricwelladvisorcusmx01` remains paused outside an approved
test window. Each active window requires a budget, a pause plan, and milestone
owner approval. Passing repository tests does not itself authorize a live
deployment or milestone release.
