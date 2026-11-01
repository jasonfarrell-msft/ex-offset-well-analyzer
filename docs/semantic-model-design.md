# Drill Run Historical Summary semantic model

## Scope and model boundary

`fabric/sm_drillrun_summary.SemanticModel` is the source-controlled definition
of the **Drill Run Historical Summary** Fabric semantic model. The model is
deployed in the Fabric development workspace
`ws-welladvisor-drillrunhistory-poc-dev`
(`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`) as semantic model
`ee7583b6-5be7-4802-83a8-530ce7dd8351`. The deployed model uses DirectQuery,
and its live DAX results were reconciled to the verified synthetic v1.0.0
summary release. This status establishes successful model import, metadata,
source-boundary, and deterministic-result verification only. No model
answer-quality evaluation has been executed or approved.

The model is the sole analytical source for the Fabric Data Agent definition.
No report, custom user interface, similarity capability, or prediction
capability is part of this milestone.

The model is limited to the synthetic, development-only historical summary
milestone. Its complete source boundary is the four active-release SQL views:

| Model table | SQL view | Grain |
|---|---|---|
| Wells | `serving.well_summary` | One row per well and dataset version |
| Dataset Metadata | `serving.dataset_summary` | One row per dataset version |
| Data Quality | `serving.quality_summary` | One row per dataset version, reason code, and severity |
| Categories | `serving.category_summary` | One row per dataset version, category name, and category value |

No curated table is added. The serving views already provide the required
release-aware grains. `Categories` exposes source-history counts for formation,
bit type, BHA type, split assignment, and entity quality status without
introducing a run-detail table or a many-to-many bridge. Formation counts come
from raw sections, while bit and BHA counts come from raw drilling runs.
Consequently, these category summaries can include quarantined runs and must
not be described as accepted-only history.

`Dataset Metadata` is the release dimension. It has a one-to-many,
single-direction relationship on Dataset Version to each of the three summary
facts. Dataset Version is unique in `serving.dataset_summary` by contract. The
design has no bidirectional relationship.

## Storage mode decision

All four tables use **DirectQuery**.

Direct Lake was considered first. The current Microsoft guidance distinguishes
Direct Lake on OneLake from Direct Lake on SQL:

- Direct Lake on OneLake requires a Delta table and does not support a table
  based on a non-materialized SQL view.
- Direct Lake on SQL can discover a SQL view, but a query against that view
  falls back to DirectQuery when fallback is enabled.

The active-release boundary is implemented as non-materialized SQL views that
join release-control tables. Reading the physical Delta tables directly would
bypass that boundary. Calling the result Direct Lake would therefore obscure
the actual execution mode. Explicit DirectQuery accurately represents the GA
behavior, preserves active-release enforcement, and avoids dependency on
fallback settings.

The trade-off is that visual queries execute against the Lakehouse SQL
analytics endpoint and can be slower or consume more endpoint capacity than
Direct Lake over physical Delta tables. This model is compact (100 well rows,
one dataset row, four quality rows, and 19 category rows in release v1.0.0), so
the correctness benefit outweighs the small-query overhead. If a future,
approved materialized serving boundary is published as Delta, storage mode can
be reconsidered.

Microsoft references reviewed on 2026-10-24:

- [Direct Lake overview](https://learn.microsoft.com/fabric/fundamentals/direct-lake-overview)
- [Develop Direct Lake semantic models](https://learn.microsoft.com/fabric/fundamentals/direct-lake-develop)
- [Power BI Desktop projects semantic model files](https://learn.microsoft.com/power-bi/developer/projects/projects-dataset)
- [TMDL overview and syntax](https://learn.microsoft.com/analysis-services/tmdl/tmdl-overview)
- [Understand star schema and the importance for Power BI](https://learn.microsoft.com/power-bi/guidance/star-schema)

## TMDL parser compatibility

TMDL descriptions are special syntax rather than ordinary colon-delimited
properties. Every table, column, and measure description is therefore placed
immediately above its declaration with `///`. A blank line must not separate
the description block from the declaration. The former indented
`description: ...` form is not valid in these object contexts and Fabric
rejects it as an unknown keyword before item creation.

The remaining syntax follows the current Microsoft TMDL examples: named
expressions carry Power Query parameter `meta` records on the expression;
partitions use `partition <name> = m`, `mode: directQuery`, and an indented
multiline `source =` expression; format strings are colon-delimited object
properties; annotations use `annotation <name> = <value>`; and relationships
use object declarations with colon-delimited cardinality, filter behavior, and
column references. In a TOM `SingleColumnRelationship`, TMDL `fromColumn` is
the many/child end and `toColumn` is the one/parent end. Each release
relationship therefore explicitly sets the child Dataset Version as
`fromColumn` with `fromCardinality: many`, and Dataset Metadata Dataset Version
as `toColumn` with `toCardinality: one`.

This endpoint order also gives the intended filter flow. Microsoft's TOM
documentation defines `OneDirection` as rows selected at the **To** end
automatically filtering scans at the **From** end. Thus
`crossFilteringBehavior: oneDirection` propagates Dataset Metadata filters from
the one-side To endpoint to each many-side child; reversing the endpoints is
not an equivalent spelling and is rejected by Analysis Services. The model was
deserialized and round-tripped with the official `TmdlSerializer`, then the TOM
`SingleColumnRelationship` objects were inspected for `FromCardinality`,
`ToCardinality`, `CrossFilteringBehavior`, `FromColumn`, and `ToColumn`.
Parser-oriented tests prohibit `description:` properties, require every
description to remain attached to its table, column, or measure, and pin both
relationship endpoints, cardinalities, and filter direction.

Microsoft TOM references:

- [`SingleColumnRelationship.FromCardinality`](https://learn.microsoft.com/dotnet/api/microsoft.analysisservices.tabular.singlecolumnrelationship.fromcardinality)
- [`SingleColumnRelationship.ToCardinality`](https://learn.microsoft.com/dotnet/api/microsoft.analysisservices.tabular.singlecolumnrelationship.tocardinality)
- [`Relationship.CrossFilteringBehavior`](https://learn.microsoft.com/dotnet/api/microsoft.analysisservices.tabular.relationship.crossfilteringbehavior)
- [`TmdlSerializer`](https://learn.microsoft.com/dotnet/api/microsoft.analysisservices.tabular.tmdlserializer)

## Source connection binding

The checked-in model has two Power Query parameters:

- `SqlEndpointDatabase = "lh_drillrun_summary"`
- `SqlEndpointHost = "SET-BY-DEPLOYMENT"`

Both are TMDL named expressions using Power Query parameter metadata
(`IsParameterQuery=true`, `Type="Text"`, and
`IsParameterQueryRequired=true`). Each table partition passes the expressions
directly to `Sql.Database`; no credential, connection string, or dynamically
constructed native query is stored in the model.

The database name is stable. The SQL endpoint hostname is intentionally an
environment binding rather than model logic. For the current development
deployment, the deployment process bound `SqlEndpointHost` to the connection
string host returned by the Lakehouse REST API
`properties.sqlEndpointProperties.connectionString` for Lakehouse
`964afbf5-6a33-46dc-98c1-be726d0f4999` in workspace
`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`. The deployed Fabric item therefore has
the development endpoint binding required for live DirectQuery, while the
checked-in portable definition intentionally retains `SET-BY-DEPLOYMENT`.
Neither location stores a credential, token, or connection string in source
control.

For any redeployment or deployment to another environment:

1. Confirm the target workspace and Lakehouse IDs.
2. Obtain the target SQL endpoint host with an in-memory Fabric access token.
3. Bind the host parameter through the deployment process without changing the
   portable source default.
4. Configure an organizational OAuth cloud connection for the semantic model.
5. Run a schema probe for the four approved views and compare columns with the
   TMDL `sourceColumn` properties.
6. Reconcile the required live DAX results to the target verified release.

## Author experience and audit fields

The model disables implicit measures and marks every source column
`summarizeBy: none`. Report authors should use the explicit measures. Technical
well keys, generation IDs, deterministic seeds, the manifest hash, and
transformation-contract fields remain in the model for audit queries but are
hidden from the ordinary field list.

The visible `Synthetic Dataset Label` measure returns a prominent
`SYNTHETIC DATA` warning with the active release's dataset version. The model
contract publishes exactly one active metadata row. The measure takes the
maximum nonblank version over that metadata column so a relationship-generated
unknown blank member in DirectQuery cannot be mistaken for a second release.
It displays `METADATA MISSING` if no nonblank metadata version exists; the
version itself is never hardcoded. Dataset Version and Is Synthetic are also
visible metadata.

## Explicit measures

The model includes:

- Well Count, Total Section Count, Total Source Run Count, Total Accepted Run
  Count, and Total Quarantined Run Count
- Total Footage, Average Footage per Run, and Total Quarantined Footage
- Total Duration, Average Duration per Run, and Total Quarantined Duration
- Wells with Quality Warnings and Wells with Quarantined Runs
- Data Quality Issue Count and selected-group affected well, section, and run
  counts
- Dataset warning and error issue counts, and Total Rejected Record Count
- Selected Category Record Count
- Synthetic Dataset Label

`Selected Category Record Count` returns a value only when exactly one category
family is selected. It returns blank when a context mixes families because
formation sections, raw runs, wells, and the union of entity quality statuses
are different grains. It is a source-category record count, not `Total
Accepted Run Count`. `Total Accepted Run Count` comes from
`serving.well_summary` and counts only runs retained by quality handling.

Selected-group affected-well, affected-section, and affected-run measures
remain separate. Each returns its source distinct count only for one
reason-and-severity quality group and returns blank across multiple groups,
where summing group-local distinct counts could double count an entity. The
model intentionally has no combined affected-entity total.

## Evaluation scope

Formation and bit/BHA aggregates from `serving.category_summary` are
source-history summaries and may include quarantined records because their
source sets are raw sections and raw runs. Any evaluation answer using those
aggregates must disclose that scope. An accepted-only category answer must use
an accepted-only serving measure if one is published in the future; this model
does not fabricate accepted-only category measures from unavailable data.

## Validation

Run:

```bash
python -m pytest tests/test_semantic_model.py
dotnet run --project tests/tom_tmdl_validation -- \
  fabric/sm_drillrun_summary.SemanticModel/definition
```

The Python tests parse the checked-in JSON and TMDL text and verify item structure,
table inventory, descriptions, required measures, hidden audit fields,
DirectQuery mode, approved source views, endpoint parameterization,
explicit many-From/one-To, parent-to-child single-direction relationships,
disabled implicit aggregation, table-scoped object-name uniqueness, scope
terms, and the absence of a Report item.
The .NET validation uses Microsoft's official TOM package and `TmdlSerializer`
to deserialize, serialize, and deserialize the definition, inspecting both
in-memory versions of every relationship and verifying that columns and
measures do not share names within a table. The full repository suite should
also pass before commit.
