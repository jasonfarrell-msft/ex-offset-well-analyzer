# Data Transformation Contract: Historical Summary v1.0.0

## 1. Purpose and authorization boundary

This contract defines the only authorized `raw` → `curated` → `serving` Delta
transformation for the historical summary milestone.

- **Execution boundary:** existing Fabric development workspace
  `ws-welladvisor-drillrunhistory-poc-dev`
  (`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`) and existing Lakehouse
  `lh_drillrun_summary` (`964afbf5-6a33-46dc-98c1-be726d0f4999`) only.
- **Source boundary:** the verified synthetic release `v1.0.0` at
  `Files/landing/synthetic/drill_run/v1.0.0`.
- **Evidence authority:** `evidence/first-fabric-load-v1.0.0.json`, the uploaded
  bytes, and the release manifest/hash set are the source of truth.
- **Allowed outcome:** deterministic historical summary Delta tables.
- **Excluded:** prediction fields or outputs, similarity, agents, UI, telemetry,
  a validation workspace, real data, external sharing, new capacity, and
  production or business-performance claims.
- **Implementation status:** the repository contains a static notebook
  implementation of this contract. It has not been imported into or executed
  in Fabric as part of this revision.

Baek Yoonho must independently approve this contract and the resulting
validation evidence before transformed outputs are treated as approved.

## 2. Authoritative release

| Property | Required value |
|---|---|
| Dataset version | `v1.0.0` |
| Generator version | `1.0.0` |
| Generation run ID | `50fd91b6-e350-5a55-9f47-3dc043e78d2e` |
| Deterministic seed | `20261023` |
| Generated at | `2026-10-23T19:40:25Z` |
| Scenario | `summary-only-fabric-milestone` |
| Synthetic flag | `true` on every row |
| Manifest SHA-256 | `f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9` |
| Source inventory SHA-256 | `0474206f9b9a6400243b3542b5ea97d86ba2b78382f66bc3e56716a4c203c9f4` |
| Aggregate source SHA-256 | `1e3abd9659b923948c93ba5e28dade20d3f61ed3c92e0111734c94415852edab` |

The transformation must fail closed before table writes if the landing
inventory or any hash differs from the following set:

| File | Rows | SHA-256 |
|---|---:|---|
| `wells.csv` | 100 | `4a71825bf6b99f33fa3fe8f9b5b571c08723d4d768a2d589a1059f2bfcb3c7f3` |
| `sections.csv` | 274 | `fd6e9e55ea79d2956437fc1384a580359f1379400789e88a55727b8b8f56679b` |
| `drilling_runs.csv` | 937 | `499705406f4479196845eb57ebd360afaacaad83551e360243372d782e23d58e` |
| `quality_issues.csv` | 20 | `c71d0e7c9cfeac97f047e5988fa75fb780302783628101fbbcaa050f96f9ec75` |
| `split_assignments.csv` | 100 | `cf2a3ee384c7a191c0f18f0af7ca5e3b7a70ba1a5534035d5c00c9a6179e4d41` |
| `schema.json` | — | `e269e8540d9513d7c45023d18e8ccb3e5ae52646239b46d1076956fdb58d6965` |
| `data_dictionary.md` | — | `912b9a919d4be6ba2ab95dac78bc69f66deec45aa34662cc6fb2413ac481cd26` |
| `generator_config.json` | — | `62020fd960e8c940cbed9a94be572e8acf113ea0602cf3224d1891bb2a61b944` |
| `source_fingerprint_inventory.json` | — | `0474206f9b9a6400243b3542b5ea97d86ba2b78382f66bc3e56716a4c203c9f4` |

## 3. Common conventions

### 3.1 Delta schemas and naming

The published contract exposes the following logical views:

- `raw.well`, `raw.section`, `raw.drilling_run`, `raw.quality_issue`,
  `raw.split_assignment`, `raw.rejected_record`
- `curated.well`, `curated.section`, `curated.drilling_run`,
  `curated.drilling_run_quarantine`, `curated.quality_issue`,
  `curated.split_assignment`, `curated.rejected_record`
- `serving.well_summary`, `serving.dataset_summary`,
  `serving.quality_summary`, `serving.category_summary`

Each logical view reads its corresponding internal Delta table named
`<schema>.__<table>_release_data`. Internal rows carry `_release_id` and
`_publication_state='STAGED'`; those two implementation columns are not exposed
by the logical views. The implementation also creates:

- `control.dataset_release_registry`, one row per dataset release, with
  `STAGING`, `READY`, or `FAILED` lifecycle state; and
- `control.dataset_release_pointer`, exactly one active release pointer per
  dataset name; and
- `control.dataset_publication_lock`, one non-expiring dataset-scoped
  single-writer lock;
- `control.dataset_publication_attempt`, the immutable attempt identity and
  terminal status history;
- `control.dataset_publication_recovery_audit`, operator attestations and
  reasons for manually clearing abandoned locks; and
- `control.dataset_publication_evidence`, append-only, versioned JSON evidence
  written and read back while the publication lock is still held.

The logical names, columns, grain, keys, and behavior in this contract must not
change. Internal physical tables and control tables are implementation details
and are not consumer contracts.

The SQL analytics endpoint views are the semantic and Data Agent serving boundary
for SQL endpoint consumers. They are source-controlled in
`fabric/sql/create_active_release_views.sql` and must be deployed after the
release-scoped physical Delta tables and control tables exist. Spark logical
views alone are not sufficient for SQL endpoint consumers because notebook-
created Spark views are not guaranteed to appear in the SQL analytics endpoint
catalog. The SQL endpoint views therefore enumerate the contract columns and
resolve only the active, reconciled release; consumers must not use the
release-scoped physical tables directly.

### 3.2 Types

| Contract type | Delta type |
|---|---|
| `string` | `STRING` |
| `boolean` | `BOOLEAN` |
| `integer` | `INT` |
| `long` | `BIGINT` |
| `decimal` | `DECIMAL(18,2)` |
| `date` | `DATE` |
| `timestamp` | `TIMESTAMP` interpreted as UTC |

No rounding is permitted before aggregation. Source decimal text is parsed to
`DECIMAL(18,2)`. Summary decimals use `DECIMAL(20,2)`.

An empty CSV token maps to `NULL` only for fields marked nullable in
`schema.json`: section/run `formation_name`, section/run `formation_name_raw`,
run `bit_iadc_code`, issue `observed_value`, issue `section_id`, and issue
`run_id`. An empty `quality_reason_codes` token remains an empty string because
the source schema defines blank as the valid PASS representation. `_record_hash`
always uses the original field strings, including empty tokens.

### 3.3 Provenance columns

Every `raw` and `curated` business table ends with these columns:

| Column | Type | Rule |
|---|---|---|
| `_source_file` | string | Exact source filename. |
| `_source_file_sha256` | string | Required hash from section 2. |
| `_source_row_number` | long | One-based data-row number after the CSV header. |
| `_source_path` | string | Exact landing path plus filename. |
| `_record_hash` | string | Lowercase SHA-256 of the ordered, unmodified source field strings using length-prefixed field encoding. |
| `_transformation_contract_version` | string | Constant `1.0.0`. |
| `_processed_at_utc` | timestamp | Execution timestamp; audit-only and excluded from deterministic content comparisons. |

Business output is deterministic when all columns except `_processed_at_utc`
are identical across reruns. Source business columns and `_record_hash` must
never be overwritten with cleaned values.

## 4. Raw tables

Raw tables preserve the source values after type parsing. Column names map
one-to-one to the same-named CSV fields; no trimming, case conversion,
imputation, label replacement, or quality repair is allowed.

### 4.1 `raw.well`

- **Source:** `wells.csv`
- **Grain:** one row per fictional well
- **Primary key:** `(dataset_version, well_id)`
- **Expected rows:** 100

| Columns in source order | Type |
|---|---|
| `well_id`, `well_name`, `operator_name`, `basin_name`, `field_name` | string |
| `spud_date`, `completion_date` | date |
| `total_footage_ft`, `total_duration_hours` | decimal |
| `section_count`, `run_count` | integer |
| `split_assignment` | string |
| `is_synthetic` | boolean |
| `dataset_version`, `generator_version`, `generation_run_id` | string |
| `deterministic_seed` | integer |
| `generated_at_utc` | timestamp |
| `scenario`, `quality_status`, `quality_reason_codes` | string |
| Provenance columns from section 3.3 | specified above |

### 4.2 `raw.section`

- **Source:** `sections.csv`
- **Grain:** one row per hole section within a well
- **Primary key:** `(dataset_version, section_id)`
- **Foreign key:** `(dataset_version, well_id)` → `raw.well`
- **Expected rows:** 274

| Columns in source order | Type |
|---|---|
| `section_id`, `well_id` | string |
| `section_sequence` | integer |
| `hole_size_in`, `start_md_ft`, `end_md_ft`, `footage_ft`, `duration_hours` | decimal |
| `formation_name`, `formation_name_raw`, `trajectory_profile` | string, nullable where source schema permits |
| `run_count` | integer |
| `is_synthetic` | boolean |
| `dataset_version`, `generator_version`, `generation_run_id` | string |
| `deterministic_seed` | integer |
| `generated_at_utc` | timestamp |
| `scenario`, `quality_status`, `quality_reason_codes` | string |
| Provenance columns from section 3.3 | specified above |

### 4.3 `raw.drilling_run`

- **Source:** `drilling_runs.csv`
- **Grain:** one row per drilling run within a section
- **Primary key:** `(dataset_version, run_id)`
- **Foreign keys:** `(dataset_version, well_id)` → `raw.well`;
  `(dataset_version, section_id)` → `raw.section`
- **Expected rows:** 937

| Columns in source order | Type |
|---|---|
| `run_id`, `well_id`, `section_id` | string |
| `run_sequence_in_section` | integer |
| `start_time_utc`, `end_time_utc` | timestamp |
| `start_md_ft`, `end_md_ft`, `footage_ft`, `duration_hours` | decimal |
| `formation_name`, `formation_name_raw` | string, nullable |
| `bit_type` | string |
| `bit_size_in` | decimal |
| `bit_iadc_code` | string, nullable |
| `bha_type`, `mud_type` | string |
| `is_synthetic` | boolean |
| `dataset_version`, `generator_version`, `generation_run_id` | string |
| `deterministic_seed` | integer |
| `generated_at_utc` | timestamp |
| `scenario`, `quality_status`, `quality_reason_codes` | string |
| Provenance columns from section 3.3 | specified above |

### 4.4 `raw.quality_issue`

- **Source:** `quality_issues.csv`
- **Grain:** one row per intentional data-quality issue
- **Primary key:** `(dataset_version, quality_issue_id)`
- **Expected rows:** 20

| Columns in source order | Type |
|---|---|
| `quality_issue_id`, `entity_type`, `entity_id`, `well_id`, `section_id`, `run_id` | string; `section_id` and `run_id` nullable |
| `reason_code`, `severity`, `field_name`, `observed_value`, `expected_constraint`, `handling` | string; `observed_value` nullable |
| `is_synthetic` | boolean |
| `dataset_version`, `generator_version`, `generation_run_id` | string |
| `deterministic_seed` | integer |
| `generated_at_utc` | timestamp |
| `scenario`, `quality_status`, `quality_reason_codes` | string |
| Provenance columns from section 3.3 | specified above |

Entity references must resolve according to `entity_type`: `SECTION` requires a
matching section; `DRILLING_RUN` requires a matching run. `well_id` must always
resolve.

### 4.5 `raw.split_assignment`

- **Source:** `split_assignments.csv`
- **Grain:** one deterministic assignment per well
- **Primary key:** `(dataset_version, well_id)`
- **Foreign key:** `(dataset_version, well_id)` → `raw.well`
- **Expected rows:** 100

| Columns in source order | Type |
|---|---|
| `well_id`, `split_assignment`, `assignment_basis` | string |
| `is_synthetic` | boolean |
| `dataset_version`, `generator_version`, `generation_run_id` | string |
| `deterministic_seed` | integer |
| `generated_at_utc` | timestamp |
| `scenario`, `quality_status`, `quality_reason_codes` | string |
| Provenance columns from section 3.3 | specified above |

### 4.6 `raw.rejected_record`

- **Grain:** one source row that cannot be represented in its typed raw table
- **Primary key:** `(dataset_version, source_file, source_row_number)`
- **Expected rows for verified `v1.0.0`:** 0

| Column | Type | Rule |
|---|---|---|
| `dataset_version` | string | Landing release being processed. |
| `source_file` | string | Source filename. |
| `source_row_number` | long | One-based data-row number. |
| `raw_payload` | string | Complete original CSV row serialization. |
| `rejection_stage` | string | `RAW_PARSE` or `RAW_CONTRACT`. |
| `rejection_reason_code` | string | Deterministic code such as `TYPE_PARSE_FAILED`, `COLUMN_COUNT_MISMATCH`, `DUPLICATE_PRIMARY_KEY`, or `RELEASE_CONSTANT_MISMATCH`. |
| `rejection_detail` | string | Deterministic detail without secrets. |
| `_source_file_sha256`, `_source_path`, `_record_hash`, `_transformation_contract_version` | string | As section 3.3. |
| `_processed_at_utc` | timestamp | Audit timestamp. |

Any raw rejection causes the release transformation to fail. Rejected rows are
preserved for diagnosis but are never silently dropped or promoted.

## 5. Curated tables and quality routing

### 5.1 Routing rules

1. A row that cannot satisfy the raw structural contract is **rejected** into
   `raw.rejected_record` and `curated.rejected_record`; the run fails.
2. A structurally valid drilling run with `quality_status='ERROR'` is
   **quarantined** in `curated.drilling_run_quarantine`.
3. Structurally valid rows with `quality_status IN ('PASS','WARNING')` are
   **accepted**. Warnings remain unchanged and their reason codes are retained.
4. `quality_issue` rows are evidence, not measurement facts. All 20 valid issue
   rows are accepted into `curated.quality_issue`, including the five
   `severity='ERROR'` records.
5. No field is imputed. `formation_name`, `formation_name_raw`, and
   `bit_iadc_code` remain exactly as supplied, including blanks/nulls and
   inconsistent labels.
6. `NON_POSITIVE_DURATION` rows remain in raw and quarantine. They are excluded
   from accepted-run measures but included in source totals and quarantine
   measures.

Expected routing for `v1.0.0`:

| Entity | Accepted | Quarantined | Rejected |
|---|---:|---:|---:|
| Wells | 100 | 0 | 0 |
| Sections | 274 (264 PASS, 10 WARNING) | 0 | 0 |
| Drilling runs | 932 (912 PASS, 20 WARNING) | 5 ERROR | 0 |
| Quality issues | 20 evidence rows | 0 | 0 |
| Split assignments | 100 | 0 | 0 |

### 5.2 `curated.well`, `curated.section`, and `curated.split_assignment`

Each table has the same columns, types, grain, keys, values, and provenance as
its corresponding raw table. Mapping is same-name direct copy. No derived or
repaired business columns are added.

Additional curated relationship rules:

- every well has exactly one split assignment;
- `well.split_assignment = split_assignment.split_assignment`;
- section sequences are contiguous from 1 per well;
- `well.section_count` equals child section count;
- `well.run_count` equals descendant raw drilling-run count.

### 5.3 `curated.drilling_run`

Same columns, types, grain, key, values, and provenance as
`raw.drilling_run`, filtered to `quality_status IN ('PASS','WARNING')`.
Expected rows: 932.

### 5.4 `curated.drilling_run_quarantine`

Same columns, types, grain, key, values, and provenance as
`raw.drilling_run`, filtered to `quality_status='ERROR'`. It adds:

| Column | Type | Mapping |
|---|---|---|
| `quarantine_reason_code` | string | Exact `quality_reason_codes`; `NON_POSITIVE_DURATION` for `v1.0.0`. |
| `quality_issue_id` | string | Matching `raw.quality_issue.quality_issue_id` by `run_id` and reason code. |

Expected rows: 5. Expected quarantined run IDs are
`SYN-RUN-0013-01-05`, `SYN-RUN-0021-01-02`,
`SYN-RUN-0064-03-02`, `SYN-RUN-0069-04-03`, and
`SYN-RUN-0071-02-01`.

### 5.5 `curated.quality_issue`

Same columns, types, grain, key, values, and provenance as
`raw.quality_issue`. Expected rows and reason counts:

| Reason code | Severity | Rows |
|---|---|---:|
| `MISSING_FORMATION` | `WARNING` | 5 |
| `INCONSISTENT_FORMATION_LABEL` | `WARNING` | 5 |
| `MISSING_BIT_IADC_CODE` | `WARNING` | 5 |
| `NON_POSITIVE_DURATION` | `ERROR` | 5 |

### 5.6 `curated.rejected_record`

Same columns and rows as `raw.rejected_record`, plus
`curation_disposition STRING` with constant `BLOCKED`. Expected rows: 0.

## 6. Serving tables

Serving tables contain historical descriptive summaries only. They must not
contain predictions, scores, recommendations, similarity measures, inferred
labels, or telemetry.

### 6.1 `serving.well_summary`

- **Grain:** one row per `(dataset_version, well_id)`
- **Primary key:** `(dataset_version, well_id)`
- **Expected rows:** 100

| Column | Type | Source/rule |
|---|---|---|
| `dataset_version`, `generator_version`, `generation_run_id`, `scenario` | string | `curated.well`, unchanged |
| `deterministic_seed` | integer | `curated.well`, unchanged |
| `is_synthetic` | boolean | Constant from source; must be `true` |
| `well_id`, `well_name`, `operator_name`, `basin_name`, `field_name` | string | `curated.well`, unchanged |
| `spud_date`, `completion_date` | date | `curated.well`, unchanged |
| `split_assignment` | string | `curated.well`, verified against `curated.split_assignment` |
| `section_count` | integer | Count of `curated.section`; must equal source well count |
| `source_run_count` | integer | Count of `raw.drilling_run` |
| `accepted_run_count` | integer | Count of `curated.drilling_run` |
| `quarantined_run_count` | integer | Count of `curated.drilling_run_quarantine` |
| `warning_section_count` | integer | Sections with `quality_status='WARNING'` |
| `warning_run_count` | integer | Accepted runs with `quality_status='WARNING'` |
| `error_run_count` | integer | Quarantined runs with `quality_status='ERROR'` |
| `issue_count` | integer | Count of `curated.quality_issue` for the well |
| `source_total_footage_ft` | decimal | `curated.well.total_footage_ft`; reconciles to all raw runs |
| `accepted_footage_ft` | decimal | Sum accepted run `footage_ft` |
| `quarantined_footage_ft` | decimal | Sum quarantined run `footage_ft` |
| `source_total_duration_hours` | decimal | `curated.well.total_duration_hours`; reconciles to all raw runs |
| `accepted_duration_hours` | decimal | Sum accepted run `duration_hours` |
| `quarantined_duration_hours` | decimal | Sum quarantined run `duration_hours` |
| `first_run_start_time_utc` | timestamp | Minimum raw run start |
| `last_run_end_time_utc` | timestamp | Maximum raw run end |
| `has_quality_warning` | boolean | `warning_section_count + warning_run_count > 0` |
| `has_quarantined_run` | boolean | `quarantined_run_count > 0` |
| `_transformation_contract_version` | string | Constant `1.0.0` |

### 6.2 `serving.dataset_summary`

- **Grain:** one row per `(dataset_version, generation_run_id)`
- **Primary key:** `(dataset_version, generation_run_id)`
- **Expected rows:** 1

| Column | Type | Expected `v1.0.0` value/rule |
|---|---|---|
| `dataset_version` | string | `v1.0.0` |
| `generator_version` | string | `1.0.0` |
| `generation_run_id` | string | `50fd91b6-e350-5a55-9f47-3dc043e78d2e` |
| `scenario` | string | `summary-only-fabric-milestone` |
| `deterministic_seed` | integer | `20261023` |
| `is_synthetic` | boolean | `true` |
| `well_count` | integer | 100 |
| `section_count` | integer | 274 |
| `source_run_count` | integer | 937 |
| `accepted_run_count` | integer | 932 |
| `quarantined_run_count` | integer | 5 |
| `rejected_record_count` | integer | 0 |
| `quality_issue_count` | integer | 20 |
| `warning_issue_count` | integer | 15 |
| `error_issue_count` | integer | 5 |
| `source_total_footage_ft` | decimal | 914297.60 |
| `accepted_footage_ft` | decimal | 909010.20 |
| `quarantined_footage_ft` | decimal | 5287.40 |
| `source_total_duration_hours` | decimal | 22358.76 |
| `accepted_duration_hours` | decimal | 22358.76 |
| `quarantined_duration_hours` | decimal | 0.00 |
| `manifest_sha256` | string | Authoritative manifest hash from section 2 |
| `_transformation_contract_version` | string | `1.0.0` |

### 6.3 `serving.quality_summary`

- **Grain:** one row per
  `(dataset_version, reason_code, severity)`
- **Primary key:** `(dataset_version, reason_code, severity)`
- **Expected rows:** 4

| Column | Type | Source/rule |
|---|---|---|
| `dataset_version`, `generation_run_id`, `scenario` | string | `curated.quality_issue` grouping constants |
| `is_synthetic` | boolean | Must be `true` |
| `reason_code`, `severity` | string | Grouping fields |
| `issue_count` | integer | Count of issue rows |
| `affected_well_count` | integer | Distinct `well_id` |
| `affected_section_count` | integer | Distinct non-null `section_id` |
| `affected_run_count` | integer | Distinct non-null `run_id` |
| `handling_text` | string | The single distinct source `handling`; fail if more than one exists in a group |
| `_transformation_contract_version` | string | `1.0.0` |

### 6.4 `serving.category_summary`

- **Grain:** one row per `(dataset_version, category_name, category_value)`
- **Primary key:** `(dataset_version, category_name, category_value)`
- **Expected rows:** 19

| Column | Type | Source/rule |
|---|---|---|
| `dataset_version`, `generation_run_id`, `scenario` | string | Release grouping constants |
| `is_synthetic` | boolean | Must be `true` |
| `category_name` | string | `FORMATION_NAME`, `BHA_TYPE`, `BIT_TYPE`, `SPLIT_ASSIGNMENT`, or `ENTITY_QUALITY_STATUS` |
| `category_value` | string | Exact source value; null formation is represented only in this serving column as `(missing)` |
| `record_count` | integer | Count from the source set defined below |
| `_transformation_contract_version` | string | `1.0.0` |

Source sets and expected values:

| Category | Source set | Expected counts |
|---|---|---|
| `FORMATION_NAME` | `raw.section.formation_name` | `(missing)` 5; `Synthetic Aster` 37; `Synthetic Brimstone` 56; `Synthetic Cobalt` 41; `Synthetic Driftwood` 50; `Synthetic Ember` 40; `Synthetic Flint` 45 |
| `BHA_TYPE` | `raw.drilling_run.bha_type` | `MOTOR` 311; `ROTARY` 301; `RSS` 325 |
| `BIT_TYPE` | `raw.drilling_run.bit_type` | `HYBRID` 313; `PDC` 308; `TRICONE` 316 |
| `SPLIT_ASSIGNMENT` | `curated.well.split_assignment` | `TRAIN` 70; `VALIDATION` 15; `TEST` 15 |
| `ENTITY_QUALITY_STATUS` | Union of raw well, section, and drilling-run status | `PASS` 1276; `WARNING` 30; `ERROR` 5 |

The `(missing)` value is a serving presentation label only. It must not be
written back to raw or curated formation fields.

## 7. Determinism and idempotency

1. The input is selected only by the exact landing path and hash set in section
   2; “latest file” discovery is prohibited.
2. Before any raw, curated, or serving data write, the release registry must
   contain the deterministic release ID in non-active `STAGING` state. A
   registry row does not publish data.
3. Rerunning the same contract against the same hash set must not increase row
   counts or create duplicate keys.
4. The ordered business content and `_record_hash` values must be identical
   across reruns. `_processed_at_utc` is the only permitted differing value.
5. Aggregations use exact decimal arithmetic and explicit key ordering where
   ordering affects serialization.
6. A rerun may delete and replace only inactive physical rows having the
   deterministic release ID for `v1.0.0`. It must not alter landing files,
   another release ID, or the release currently selected by the active pointer.
7. Failure before activation leaves the previous pointer unchanged. On the
   first release, the pointer table remains empty, so every logical view returns
   zero rows. Failed or incomplete physical rows are never consumer-visible.
8. No cross-table ACID transaction is claimed. The 17 physical Delta tables are
   staged sequentially and remain inactive while staged. Publication occurs
   only through the separate single-table activation boundary defined below.

### 7.1 Staging and reconciliation protocol

The deterministic release ID is
`v1.0.0:f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9`.
The notebook must:

1. validate the authorized input bytes and complete all in-memory contract
   checks before creating a release attempt;
2. create a unique attempt ID and acquire the non-expiring dataset publication
   lock with one conditional Delta `UPDATE` of the pre-created
   `drill_run_history` sentinel row from unowned to owned; concurrent attempts
   update the same Delta row/file, so optimistic concurrency permits one commit
   and every loser receives a transaction conflict or explicit ownership
   failure;
3. atomically merge the release registry row to `STAGING` before any physical
   raw, curated, or serving data write;
4. when the active pointer does not already select this release, delete only
   stale inactive rows for this release ID and append all 17 physical tables
   with `_publication_state='STAGED'`;
5. read every physical release slice back and reconcile its row count, key
   uniqueness, deterministic business-content hash, routing, relationships,
   measures, issue counts, category counts, and all section 8 criteria;
6. deploy or update the source-controlled SQL analytics endpoint views whose
   predicates join both the active pointer and a `READY` registry row (Spark
   logical views created by the notebook do not satisfy this SQL consumer
   boundary); and
7. move the registry row from `STAGING` to `READY`. `READY` means reconciled
   and eligible for activation, not published;
8. verify the same attempt still owns the lock before every cleanup, physical
   append, registry transition, view definition, activation, and evidence
   write; and
9. release the lock only after activation, active-view verification, evidence
   persistence and read-back verification, and attempt completion all succeed.

Raw parsing rejection occurs before this protocol and must fail without writing
rejected records into a published or physical release table. Rejection details
may be displayed as execution evidence.

### 7.2 Atomic activation boundary

After all 17 physical release slices and all reconciliation checks succeed, the
notebook performs exactly one Delta `MERGE` into
`control.dataset_release_pointer`. That merge inserts or replaces the one
`drill_run_history` pointer with the reconciled release ID. Delta atomicity for
that single control-table commit is the publication boundary.

SQL endpoint consumers and Data Agents must query only the logical `raw`,
`curated`, and `serving` views created by
`fabric/sql/create_active_release_views.sql`. Every view joins physical rows to
`control.dataset_release_pointer.active_release_id`, joins the matching
`control.dataset_release_registry` row with `release_state='READY'`, and
requires `_publication_state='STAGED'`. Consumers must not query internal
`__*_release_data` tables directly. Notebook-created Spark logical views may
support Spark-side validation, but they are not the semantic serving boundary
and are not sufficient evidence that the SQL analytics endpoint exposes the
contract.

Before acquiring the publication lock, the notebook must inspect every
logical contract name. If any name is an existing physical table rather than a
view, it fails with `LEGACY_DIRECT_TABLE_REQUIRES_ONE_TIME_MIGRATION` before
writing release data. This fail-closed guard prevents silently treating tables
from the rejected direct-publication design as pointer-controlled views. A
separately approved one-time migration must quarantine or remove those legacy
objects before this protocol is first run; this notebook does not rely on
sequential renames to perform that migration.

This design does not assert an unsupported multi-table transaction. A session
termination before the pointer merge can leave zero or more staged physical
tables and a `STAGING` or `READY` registry row, but cannot expose that release.
A session termination after the pointer commit exposes the fully reconciled
release. The lock deliberately remains until post-activation verification and
evidence writes finish; therefore a failure after activation cannot permit a
second writer to append or activate.

### 7.3 Durable publication evidence

`control.dataset_publication_evidence` is the authoritative publication record.
It contains one append-only row per attempt with:

- `dataset_name`, `attempt_id`, and `release_id`;
- `evidence_schema_version` and `evidence_written_at_utc`;
- `payload_sha256`, the SHA-256 of the final persisted JSON bytes, as a query
  aid; and
- `payload_json`, a canonical, key-sorted UTF-8 JSON document.

`payload_json` is authoritative and self-describing; table columns and
properties remain query aids for filtering and discovery, but do not define how
the evidence is interpreted. The JSON payload must include:

- an `evidence_contract` object containing evidence schema version `1.0.0`,
  retention period `400` days, maximum payload size `1048576` bytes, canonical
  serialization rules, and the payload integrity contract;
- every authorized manifest/file SHA-256 value observed by the notebook;
- the dataset fingerprint, source inventory fingerprint, and aggregate source
  fingerprint;
- every physical table name, the Delta snapshot version observed during
  reconciliation, row count, and deterministic business-content hash;
- source-file, raw, curated, and serving row counts;
- accepted, quarantined, and rejected routing counts and stable evidence-table
  references;
- each quarantined run ID, linked quality issue ID, and reason code;
- summary reconciliation measures;
- the publication attempt ID, generation run ID, Spark application ID, and
  current Fabric execution user;
- the Fabric workspace ID, Lakehouse ID/name, notebook name, and release ID;
- whether activation was performed or the existing active release was verified,
  the active pointer result, pointer table, and pointer Delta version; and
- evidence schema version, result, contract version, and UTC timestamps.

The non-recursive integrity scheme is unambiguous: set
`evidence_contract.integrity.content_sha256` to JSON `null`, serialize the
complete payload as UTF-8 JSON with keys sorted, no insignificant whitespace,
and non-ASCII characters emitted directly, then compute SHA-256 over those
bytes. Store that hexadecimal digest in `content_sha256` and serialize the
final payload with the same canonical rules. Read-back verification parses the
persisted payload, validates its embedded schema/retention/size metadata, resets
only `content_sha256` to `null`, canonicalizes again, and compares a newly
computed digest to the embedded digest. It also independently verifies the
final JSON bytes against the `payload_sha256` query-aid column.

The notebook begins one fail-closed evidence boundary immediately after pointer
activation and active-view validation. While still owning the non-expiring
lock, that boundary includes pointer-history collection, quarantine collection,
payload construction, canonical serialization, the 1 MiB UTF-8 size check,
both hash calculations, table append, read-back, and all metadata/content/hash
verification. Only then may it mark the attempt `SUCCEEDED` and release the
lock.

Any exception in that entire boundary triggers a best-effort attempt transition
to `FAILED` with a sanitized exception type only. The transition is itself
guarded: if it also fails, no recursive recovery is attempted. Execution still
raises `EVIDENCE_PERSISTENCE_FAILED_LOCK_RETAINED`, whose sanitized message
reports both the evidence error type and failure-mark error type, chains the
original evidence exception as its cause, and never releases the lock. The lock
therefore remains held for manual operator recovery in every evidence failure
path. Console/display output occurs after lock release and merely mirrors the
persisted JSON; it is not evidence authority.

The evidence table is append-only. The notebook records table metadata declaring
schema version `1.0.0`, maximum payload size 1 MiB, and a minimum retention
period of 400 days. Evidence deletion or archival is outside this notebook and
requires a separately approved operator policy. This bounds each row while
preserving audit history; expanding the evidence schema requires an explicit
control-table migration rather than silent widening.

### 7.4 Recovery and rerun behavior

- Locks never expire and normal execution has no renewal, timeout, stealing,
  takeover, or automatic cleanup path. A failed or terminated session leaves
  its lock in place and blocks every later publication attempt.
- Recovery is an explicit operator-controlled mode. Before enabling it, the
  operator must independently confirm that the Fabric Spark application ID
  recorded in the lock is terminal. Recovery requires the operator identity,
  a non-empty reason, and that exact terminal application ID.
- Recovery first appends an immutable audit row recording who cleared the lock,
  why, and which job was confirmed terminal. It then marks the interrupted
  attempt `FAILED`, verifies that state, and deletes only that attempt's exact
  lock row. Only after those steps may a new unique attempt acquire the lock.
  Normal notebook execution never deletes another attempt's lock.
- If the active pointer already selects the deterministic release ID, a normal
  rerun that encounters the retained lock fails with
  `ACTIVE_RELEASE_LOCK_CLEANUP_REQUIRED`. After safe operator recovery, the new
  attempt verifies all physical hashes/counts and active-only views, writes
  evidence, and releases its own lock without deleting or appending release
  rows or changing the pointer.
- If activation succeeds but evidence persistence, evidence read-back,
  attempt completion, or lock release fails, the active release remains visible
  and the non-expiring lock remains. A subsequent run must follow the preceding
  operator recovery procedure; it must not restage or append the already-active
  release.
- If failure occurs before activation, the active pointer remains unchanged and
  all staged rows remain inactive. After operator recovery, a new lock owner
  may return the inactive release to `STAGING`, delete only that release ID's
  inactive physical slices, and rebuild them.

## 8. Reconciliation and approval criteria

All criteria are mandatory:

### 8.1 Source and raw

- exact file inventory and all SHA-256 values match section 2;
- raw row counts are 100 wells, 274 sections, 937 drilling runs, 20 quality
  issues, and 100 split assignments;
- primary keys are non-null and unique;
- release constants match section 2 on every row;
- `is_synthetic=true` on every row;
- all foreign keys and issue entity references resolve;
- no raw rejected records exist.

### 8.2 Curated routing

- for each entity, `raw = accepted + quarantined + rejected`;
- drilling runs reconcile `937 = 932 + 5 + 0`;
- the five quarantine IDs match section 5.4;
- warning rows remain accepted without value changes;
- all 20 issue rows and exact 5/5/5/5 reason counts are preserved;
- raw and canonical formation fields remain separate and unchanged;
- no null is imputed and no source error is silently corrected.

### 8.3 Measures

- all-run footage equals `914297.60`;
- accepted plus quarantined footage equals
  `909010.20 + 5287.40 = 914297.60`;
- all-run duration equals `22358.76`;
- accepted plus quarantined duration equals
  `22358.76 + 0.00 = 22358.76`;
- section footage/duration reconcile to child raw runs;
- well footage/duration and counts reconcile to descendant raw runs and
  sections;
- the serving dataset summary equals the release manifest for the source-level
  counts and totals;
- serving category counts exactly equal the release manifest's formation, BHA,
  bit, split, and entity-quality-status counts;
- serving well summaries aggregate exactly to the serving dataset summary.

### 8.4 Idempotency and evidence

- two consecutive executions against the same inputs produce identical
  business-content hashes and row counts;
- no duplicate keys or extra partitions appear;
- validation evidence records input hashes, Delta table names/versions, row
  counts, reconciliation values, rejected/quarantined keys, execution identity,
  workspace/Lakehouse/release identifiers, activation result, timestamps, and
  result in the authoritative `control.dataset_publication_evidence` row;
- displayed JSON may mirror the persisted evidence but is never authoritative;
- no real-data, production, performance, prediction, or quality claims are
  inferred from the synthetic results;
- Baek Yoonho records independent approval. A rejection invokes reviewer
  lockout and requires a different qualified author to revise the rejected
  artifact.

After successful validation, all transformation source must be committed to the
existing local Git repository. Generated data and secrets must not be committed.

## 9. Additive offset contract v1.1.0 — local specification only

This appendix does not amend the v1.0.0 authorization, source hashes, tables,
measures, disclosure, or publication history above. The current task authorizes
local contracts/schema/tests only, **not** the execution, commit, or deployment
instructions in the historical material. No v1.1.0 transformation, serving
publication, source expansion, or application capability is established here.

The normative offset data/API specification and worked wire examples are
[offset-well-analysis-v1.md](contracts/offset-well-analysis-v1.md) and
[offset-well-analysis-v1.schema.json](contracts/offset-well-analysis-v1.schema.json).
They define transformation contract `1.1.0`, query/API contract
`offset-well-analysis-v1`, and the following immutable release:

| Property | Required value |
|---|---|
| Dataset version | `v1.1.0` |
| Manifest SHA-256 | `904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d` |
| Release ID | `v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d` |
| Generation run ID | `13188ed2-899a-5335-ab49-939dbdc961e0` |
| Generator / seed | `1.1.0` / `20261023` |
| Generated at | `2026-10-27T18:36:12Z` |
| Historical source counts | 100 wells, 274 sections, 937 runs, 20 issues, 100 splits |
| Planning targets | 12, separate from every historical measure and split |
| Accepted / quarantined runs | 932 (`PASS`/`WARNING`) / 5 (`ERROR`) |

### 9.1 Source and proposed raw/curated additions

`data/releases/v1.1.0/schema.json` is the authoritative source-field inventory.
Hash the exact manifest bytes against the pin above, then every entry in its
`sha256` inventory before parsing. Do not regenerate either archive.
The offline tests verify both archived manifests and all listed artifacts.

Existing well rows add `coordinate_frame_id STRING`, `location_semantics STRING`,
`surface_x_ft INT`, and `surface_y_ft INT`. These fields are required for
v1.1.0; additive older-release columns are nullable, with no coordinate backfill.
Units are feet, frame `SYN-LOCAL-FT-V1`, semantics
`SYNTHETIC_SURFACE_WELLHEAD`, coordinate bounds `[-1000000,1000000]` on each
abstract axis. No geographic orientation is asserted.

New proposed `raw.planned_target` and `curated.planned_target` have identical
business values and one row per `(_release_id,target_id)`:

| Source fields | Typed raw/curated representation |
|---|---|
| `target_id`, `record_kind` | STRING; `SYN-TARGET-NNNN`, `PLANNED_TARGET` |
| `basin_name`, `field_name`, `expected_formation_name` | STRING; fictional planning labels |
| `planned_trajectory_profile` | STRING; `VERTICAL`, `BUILD_AND_HOLD`, `HORIZONTAL` |
| `planned_hole_size_in` | DECIMAL(18,3); `17.5`, `12.25`, `8.5`, `6.125` |
| `planned_md_min_ft`, `planned_md_max_ft` | INT feet; `0 <= min < max` |
| `coordinate_frame_id`, `location_semantics` | STRING; constants above |
| `surface_x_ft`, `surface_y_ft` | INT feet; bounds above |
| `reference_dataset_version`, `reference_manifest_sha256` | STRING; `v1.0.0`, `f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9` |
| `is_synthetic` | BOOLEAN; true |
| `dataset_version`, `generator_version`, `generation_run_id` | STRING; pinned constants above |
| `deterministic_seed`, `generated_at_utc`, `scenario` | INT, UTC TIMESTAMP, STRING (`synthetic-proximity-planning-v1`) |
| Existing source/hash/row/path/record-hash/process provenance | Section 3.3 rules; transformation version `1.1.0` |

Every target source field is non-null; blank required labels fail structural
validation. Targets have **no** actual footage, duration, run counts, quality
status, split assignment, or realized drilling outcome fields. The reference
release is provenance only, never a cross-release join key.

Hole/bit size must retain source precision (including `6.125 in`): use
DECIMAL(18,3) for these v1.1.0 columns, not v1.0.0's generic DECIMAL(18,2).
Historical footage/duration/MD retain exact source decimals at scale 2;
surface coordinates are integral feet; squared distances use DECIMAL(38,12)
or an exact wider decimal with no pre-filter rounding. Radius supports six
fractional places in the approved M1/M2 wire profile. Ratios are computed from
unrounded sums, then serialized to six fractional places, half-up; distance
display alone is rounded half-up to one decimal foot. No binary float filtering.
This precision extension is additive and must not rewrite v1.0.0 partitions.

### 9.2 Proposed products, routing and reconciliation

- `serving.planned_target_summary`: `(_release_id,target_id)`, planning-only
  approved fields, no addition to historical well counts.
- `serving.offset_candidate_summary`: `(_release_id,target_id,well_id)`;
  compatible surface pairs and exact squared distance, at most 1200 pairs.
- `serving.offset_section_summary`:
  `(_release_id,target_id,well_id,section_id)`; canonical formation, exact hole
  size, MD endpoints, descriptive trajectory, accepted section sums/counts and
  distinct quality coverage; at most 3288 rows before exclusions. In this
  section-grain view, generic `basin_name`/`field_name` and
  `surface_x_ft`/`surface_y_ft` denote historical well coordinates while
  `target_basin_name`/`target_field_name` and
  `target_surface_x_ft`/`target_surface_y_ft` retain planning-target metadata.
- Aggregate run facts to sections **before** joining target pairs; never sum
  target-expanded rows across targets. Include `_release_id` in every join;
  run-to-section additionally checks `well_id`. Reject duplicate keys,
  mixed/unsupported releases and invalid parent references.
- Preserve `PASS` and `WARNING` measurements unchanged. Exclude `ERROR` runs
  from performance metrics, retain them in quarantine counts, preserve all 20
  issue evidence rows. Deduplicate issue IDs at issue grain before aggregation.
- Formation/hole/optional strict MD predicates apply conjunctively to each
  section. A well needs positive accepted run count over its matching sections.
  Selection metrics aggregate those same whole sections, not whole-well totals.
  Unknowns do not satisfy enabled equality predicates; no imputation.
- Existing active-pointer/READY registry, STAGED isolation, single-writer
  publication, reconciliation, evidence and rollback safeguards still apply to
  any future implementation. Logical exposure of a release identifier is a
  proposed additive public-field change requiring separate approval.

`tests/test_offset_analysis.py` is a stdlib-only, grader-only reference oracle,
not an application source or transformation implementation. Its archive checks,
boundary fixtures and all-target expected answers do not prove Spark execution,
effective access, authenticated structured transport or complete live results.
The next capability gate remains separately authorized TASK-025/026/028 with
independent exposure/evidence acceptance; no deployment or runtime fallback is
authorized by passing local tests.

## 10. Additive offset contract v1.2.0 — local SQL/view scope only

This additive scope preserves every v1.0.0/v1.1.0 contract behavior and extends
active-release SQL endpoint projections for release `v1.2.0` only. It is local
contract/view work only; it is not cloud execution authorization.

### 10.1 Run-level additive fields

`raw.drilling_run`, `curated.drilling_run`, and
`curated.drilling_run_quarantine` add:

- `mud_weight_ppg` (observed run-level mud weight, ppg)
- `mud_funnel_viscosity_sec` (observed run-level funnel viscosity, sec/quart)

The existing run tuple dimensions (`bit_type`, `bha_type`, `mud_type`) remain
unchanged and must stay tied to the same run grain as these observed fields.

### 10.2 Synthetic run-event additive source

`run_events.csv` is modeled at one row per
`(_release_id, well_id, section_id, run_id, event_type, event_subtype)` with:

- `event_count`
- `event_duration_hours`

Allowed `event_type` values are `LOSSES`, `STUCK_PIPE`, `VIBRATION`, `NPT`,
and `TRIP`. These records are synthetic operational-event context and are
explicitly separate from `quality_issue` evidence; quality warnings/errors are
not event proxies.

### 10.3 Additive SQL serving projections for offset context

The serving boundary adds:

- `serving.offset_run_config_summary`
  - tuple grain preserving same-run co-occurrence:
    `(_release_id,target_id,well_id,bit_type,bha_type,mud_type,mud_weight_ppg,mud_funnel_viscosity_sec)`
  - measures: `accepted_run_count`, `accepted_footage_ft`,
    `accepted_duration_hours`
- `serving.offset_run_event_summary`
  - event-context grain:
    `(_release_id,target_id,well_id,section_id,run_id,event_type,event_subtype)`
  - measures: `event_count`, `event_duration_hours`

Serving/API context must derive from these same-run/event grains:

- Run config tuple shape:
  `{ bitType, bhaType, mudType, mudWeightPpg, mudFunnelViscositySec, acceptedRunCount, acceptedFootageFt, acceptedDurationHours }`
- Event context shape:
  - totals: `totalEventCount`, `totalEventDurationHours`
  - by type: `byType[{eventType,eventCount,eventDurationHours}]`
  - by subtype: `bySubtype[{eventType,eventSubtype,eventCount,eventDurationHours}]`

No event-rate fields or custom denominator fields are added. Existing section-
grain metrics and denominator semantics remain unchanged.
