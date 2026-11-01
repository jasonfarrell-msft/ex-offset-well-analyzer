/*
Source-controlled semantic views for the Fabric Lakehouse SQL analytics endpoint.

Run this script only after the physical release tables and control tables exist.
Each CREATE OR ALTER VIEW intentionally binds directly to its dependencies so
that a missing schema, table, or column stops deployment with a SQL error.
*/

CREATE OR ALTER VIEW [raw].[well]
AS
SELECT
    d.[well_id],
    d.[well_name],
    d.[operator_name],
    d.[basin_name],
    d.[field_name],
    d.[spud_date],
    d.[completion_date],
    d.[total_footage_ft],
    d.[total_duration_hours],
    d.[section_count],
    d.[run_count],
    d.[split_assignment],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [raw].[__well_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [raw].[section]
AS
SELECT
    d.[section_id],
    d.[well_id],
    d.[section_sequence],
    d.[hole_size_in],
    d.[start_md_ft],
    d.[end_md_ft],
    d.[footage_ft],
    d.[duration_hours],
    d.[formation_name],
    d.[formation_name_raw],
    d.[trajectory_profile],
    d.[run_count],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [raw].[__section_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [raw].[drilling_run]
AS
SELECT
    d.[run_id],
    d.[well_id],
    d.[section_id],
    d.[run_sequence_in_section],
    d.[start_time_utc],
    d.[end_time_utc],
    d.[start_md_ft],
    d.[end_md_ft],
    d.[footage_ft],
    d.[duration_hours],
    d.[formation_name],
    d.[formation_name_raw],
    d.[bit_type],
    d.[bit_size_in],
    d.[bit_iadc_code],
    d.[bha_type],
    d.[mud_type],
    d.[mud_weight_ppg],
    d.[mud_funnel_viscosity_sec],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [raw].[__drilling_run_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [raw].[run_event]
AS
SELECT
    d.[run_id],
    d.[well_id],
    d.[section_id],
    d.[event_type],
    d.[event_subtype],
    d.[event_count],
    d.[event_duration_hours],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [raw].[__run_event_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [raw].[quality_issue]
AS
SELECT
    d.[quality_issue_id],
    d.[entity_type],
    d.[entity_id],
    d.[well_id],
    d.[section_id],
    d.[run_id],
    d.[reason_code],
    d.[severity],
    d.[field_name],
    d.[observed_value],
    d.[expected_constraint],
    d.[handling],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [raw].[__quality_issue_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [raw].[split_assignment]
AS
SELECT
    d.[well_id],
    d.[split_assignment],
    d.[assignment_basis],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [raw].[__split_assignment_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [raw].[rejected_record]
AS
SELECT
    d.[dataset_version],
    d.[source_file],
    d.[source_row_number],
    d.[raw_payload],
    d.[rejection_stage],
    d.[rejection_reason_code],
    d.[rejection_detail],
    d.[_source_file_sha256],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [raw].[__rejected_record_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [curated].[well]
AS
SELECT
    d.[well_id],
    d.[well_name],
    d.[operator_name],
    d.[basin_name],
    d.[field_name],
    d.[spud_date],
    d.[completion_date],
    d.[total_footage_ft],
    d.[total_duration_hours],
    d.[section_count],
    d.[run_count],
    d.[split_assignment],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [curated].[__well_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [curated].[section]
AS
SELECT
    d.[section_id],
    d.[well_id],
    d.[section_sequence],
    d.[hole_size_in],
    d.[start_md_ft],
    d.[end_md_ft],
    d.[footage_ft],
    d.[duration_hours],
    d.[formation_name],
    d.[formation_name_raw],
    d.[trajectory_profile],
    d.[run_count],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [curated].[__section_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [curated].[drilling_run]
AS
SELECT
    d.[run_id],
    d.[well_id],
    d.[section_id],
    d.[run_sequence_in_section],
    d.[start_time_utc],
    d.[end_time_utc],
    d.[start_md_ft],
    d.[end_md_ft],
    d.[footage_ft],
    d.[duration_hours],
    d.[formation_name],
    d.[formation_name_raw],
    d.[bit_type],
    d.[bit_size_in],
    d.[bit_iadc_code],
    d.[bha_type],
    d.[mud_type],
    d.[mud_weight_ppg],
    d.[mud_funnel_viscosity_sec],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [curated].[__drilling_run_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [curated].[run_event]
AS
SELECT
    d.[run_id],
    d.[well_id],
    d.[section_id],
    d.[event_type],
    d.[event_subtype],
    d.[event_count],
    d.[event_duration_hours],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [curated].[__run_event_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [curated].[drilling_run_quarantine]
AS
SELECT
    d.[run_id],
    d.[well_id],
    d.[section_id],
    d.[run_sequence_in_section],
    d.[start_time_utc],
    d.[end_time_utc],
    d.[start_md_ft],
    d.[end_md_ft],
    d.[footage_ft],
    d.[duration_hours],
    d.[formation_name],
    d.[formation_name_raw],
    d.[bit_type],
    d.[bit_size_in],
    d.[bit_iadc_code],
    d.[bha_type],
    d.[mud_type],
    d.[mud_weight_ppg],
    d.[mud_funnel_viscosity_sec],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc],
    d.[quarantine_reason_code],
    d.[quality_issue_id]
FROM [curated].[__drilling_run_quarantine_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [curated].[quality_issue]
AS
SELECT
    d.[quality_issue_id],
    d.[entity_type],
    d.[entity_id],
    d.[well_id],
    d.[section_id],
    d.[run_id],
    d.[reason_code],
    d.[severity],
    d.[field_name],
    d.[observed_value],
    d.[expected_constraint],
    d.[handling],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [curated].[__quality_issue_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [curated].[split_assignment]
AS
SELECT
    d.[well_id],
    d.[split_assignment],
    d.[assignment_basis],
    d.[is_synthetic],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[deterministic_seed],
    d.[generated_at_utc],
    d.[scenario],
    d.[quality_status],
    d.[quality_reason_codes],
    d.[_source_file],
    d.[_source_file_sha256],
    d.[_source_row_number],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc]
FROM [curated].[__split_assignment_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [curated].[rejected_record]
AS
SELECT
    d.[dataset_version],
    d.[source_file],
    d.[source_row_number],
    d.[raw_payload],
    d.[rejection_stage],
    d.[rejection_reason_code],
    d.[rejection_detail],
    d.[_source_file_sha256],
    d.[_source_path],
    d.[_record_hash],
    d.[_transformation_contract_version],
    d.[_processed_at_utc],
    d.[curation_disposition]
FROM [curated].[__rejected_record_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [serving].[well_summary]
AS
SELECT
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[scenario],
    d.[deterministic_seed],
    d.[is_synthetic],
    d.[well_id],
    d.[well_name],
    d.[operator_name],
    d.[basin_name],
    d.[field_name],
    d.[spud_date],
    d.[completion_date],
    d.[split_assignment],
    d.[section_count],
    d.[source_run_count],
    d.[accepted_run_count],
    d.[quarantined_run_count],
    d.[warning_section_count],
    d.[warning_run_count],
    d.[error_run_count],
    d.[issue_count],
    d.[source_total_footage_ft],
    d.[accepted_footage_ft],
    d.[quarantined_footage_ft],
    d.[source_total_duration_hours],
    d.[accepted_duration_hours],
    d.[quarantined_duration_hours],
    d.[first_run_start_time_utc],
    d.[last_run_end_time_utc],
    d.[has_quality_warning],
    d.[has_quarantined_run],
    d.[_transformation_contract_version]
FROM [serving].[__well_summary_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [serving].[dataset_summary]
AS
SELECT
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[scenario],
    d.[deterministic_seed],
    d.[is_synthetic],
    d.[well_count],
    d.[section_count],
    d.[source_run_count],
    d.[accepted_run_count],
    d.[quarantined_run_count],
    d.[rejected_record_count],
    d.[quality_issue_count],
    d.[warning_issue_count],
    d.[error_issue_count],
    d.[source_total_footage_ft],
    d.[accepted_footage_ft],
    d.[quarantined_footage_ft],
    d.[source_total_duration_hours],
    d.[accepted_duration_hours],
    d.[quarantined_duration_hours],
    d.[manifest_sha256],
    d.[_transformation_contract_version]
FROM [serving].[__dataset_summary_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [serving].[quality_summary]
AS
SELECT
    d.[dataset_version],
    d.[generation_run_id],
    d.[scenario],
    d.[is_synthetic],
    d.[reason_code],
    d.[severity],
    d.[issue_count],
    d.[affected_well_count],
    d.[affected_section_count],
    d.[affected_run_count],
    d.[handling_text],
    d.[_transformation_contract_version]
FROM [serving].[__quality_summary_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [serving].[category_summary]
AS
SELECT
    d.[dataset_version],
    d.[generation_run_id],
    d.[scenario],
    d.[is_synthetic],
    d.[category_name],
    d.[category_value],
    d.[record_count],
    d.[_transformation_contract_version]
FROM [serving].[__category_summary_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [serving].[offset_run_config_summary]
AS
SELECT
    d.[_release_id],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[scenario],
    d.[deterministic_seed],
    d.[is_synthetic],
    d.[target_id],
    d.[target_name],
    d.[well_id],
    d.[well_name],
    d.[bit_type],
    d.[bha_type],
    d.[mud_type],
    d.[mud_weight_ppg],
    d.[mud_funnel_viscosity_sec],
    d.[accepted_run_count],
    d.[accepted_footage_ft],
    d.[accepted_duration_hours],
    d.[_transformation_contract_version]
FROM [serving].[__offset_run_config_summary_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

/*
Synthetic run-event context is separate from data-quality evidence.
`event_type`/`event_subtype` rows are synthetic operational history facts, not
quality issues, and must never be inferred from warning/error quality records.
*/
CREATE OR ALTER VIEW [serving].[offset_run_event_summary]
AS
SELECT
    d.[_release_id],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[scenario],
    d.[deterministic_seed],
    d.[is_synthetic],
    d.[target_id],
    d.[target_name],
    d.[well_id],
    d.[well_name],
    d.[section_id],
    d.[run_id],
    d.[event_type],
    d.[event_subtype],
    d.[event_count],
    d.[event_duration_hours],
    d.[_transformation_contract_version]
FROM [serving].[__offset_run_event_summary_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [serving].[planned_target_summary]
AS
SELECT
    d.[_release_id],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[scenario],
    d.[deterministic_seed],
    d.[is_synthetic],
    d.[target_id],
    d.[record_kind],
    d.[target_name],
    d.[target_basin_name] AS [basin_name],
    d.[target_field_name] AS [field_name],
    d.[expected_formation_name],
    d.[planned_trajectory_profile],
    d.[planned_hole_size_in],
    d.[planned_md_min_ft],
    d.[planned_md_max_ft],
    d.[planned_bit_type],
    d.[planned_bha_type],
    d.[planned_mud_type],
    d.[coordinate_frame_id],
    d.[location_semantics],
    CAST(N'ft' AS NVARCHAR(16)) AS [coordinate_units],
    d.[target_surface_x_ft] AS [surface_x_ft],
    d.[target_surface_y_ft] AS [surface_y_ft],
    d.[reference_dataset_version],
    d.[reference_manifest_sha256],
    d.[_transformation_contract_version]
FROM [serving].[__planned_target_summary_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [serving].[offset_section_summary]
AS
SELECT
    d.[_release_id],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[scenario],
    d.[deterministic_seed],
    d.[is_synthetic],
    d.[target_id],
    d.[target_name],
    d.[target_basin_name] AS [target_basin_name],
    d.[target_field_name] AS [target_field_name],
    d.[well_basin_name] AS [basin_name],
    d.[well_field_name] AS [field_name],
    d.[expected_formation_name],
    d.[planned_hole_size_in],
    d.[planned_md_min_ft],
    d.[planned_md_max_ft],
    d.[planned_trajectory_profile],
    d.[coordinate_frame_id],
    d.[location_semantics],
    CAST(N'ft' AS NVARCHAR(16)) AS [coordinate_units],
    d.[target_surface_x_ft] AS [target_surface_x_ft],
    d.[target_surface_y_ft] AS [target_surface_y_ft],
    d.[well_surface_x_ft] AS [surface_x_ft],
    d.[well_surface_y_ft] AS [surface_y_ft],
    d.[well_id],
    d.[well_name],
    d.[operator_name],
    d.[well_basin_name],
    d.[well_field_name],
    d.[well_surface_x_ft],
    d.[well_surface_y_ft],
    d.[section_id],
    d.[section_sequence],
    d.[section_formation_name] AS [formation_name],
    d.[section_hole_size_in] AS [hole_size_in],
    d.[section_start_md_ft] AS [start_md_ft],
    d.[section_end_md_ft] AS [end_md_ft],
    d.[section_trajectory_profile] AS [trajectory_profile],
    d.[source_run_count],
    d.[accepted_run_count],
    d.[quarantined_run_count],
    d.[warning_run_count],
    d.[error_run_count],
    CASE
        WHEN d.[warning_issue_count] > 0 THEN CAST(1 AS INT)
        ELSE CAST(0 AS INT)
    END AS [warning_section_count],
    d.[warning_issue_count],
    d.[error_issue_count],
    d.[accepted_footage_ft],
    d.[accepted_duration_hours],
    d.[distance_squared_ft2],
    d.[_transformation_contract_version]
FROM [serving].[__offset_section_summary_release_data] AS d
INNER JOIN [control].[dataset_release_pointer] AS p
    ON p.[dataset_name] = N'drill_run_history'
    AND p.[active_release_id] = d.[_release_id]
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

/*
Release-addressable serving views expose READY releases without requiring the
global active pointer to switch. They are used by contract-pinned consumers
that pass an explicit _release_id.
*/
CREATE OR ALTER VIEW [serving].[offset_run_config_summary_release]
AS
SELECT
    d.[_release_id],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[scenario],
    d.[deterministic_seed],
    d.[is_synthetic],
    d.[target_id],
    d.[target_name],
    d.[well_id],
    d.[well_name],
    d.[bit_type],
    d.[bha_type],
    d.[mud_type],
    d.[mud_weight_ppg],
    d.[mud_funnel_viscosity_sec],
    d.[accepted_run_count],
    d.[accepted_footage_ft],
    d.[accepted_duration_hours],
    d.[_transformation_contract_version]
FROM [serving].[__offset_run_config_summary_release_data] AS d
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = N'drill_run_history'
    AND r.[release_id] = d.[_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [serving].[offset_run_event_summary_release]
AS
SELECT
    d.[_release_id],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[scenario],
    d.[deterministic_seed],
    d.[is_synthetic],
    d.[target_id],
    d.[target_name],
    d.[well_id],
    d.[well_name],
    d.[section_id],
    d.[run_id],
    d.[event_type],
    d.[event_subtype],
    d.[event_count],
    d.[event_duration_hours],
    d.[_transformation_contract_version]
FROM [serving].[__offset_run_event_summary_release_data] AS d
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = N'drill_run_history'
    AND r.[release_id] = d.[_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [serving].[planned_target_summary_release]
AS
SELECT
    d.[_release_id],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[scenario],
    d.[deterministic_seed],
    d.[is_synthetic],
    d.[target_id],
    d.[record_kind],
    d.[target_name],
    d.[target_basin_name] AS [basin_name],
    d.[target_field_name] AS [field_name],
    d.[expected_formation_name],
    d.[planned_trajectory_profile],
    d.[planned_hole_size_in],
    d.[planned_md_min_ft],
    d.[planned_md_max_ft],
    d.[planned_bit_type],
    d.[planned_bha_type],
    d.[planned_mud_type],
    d.[coordinate_frame_id],
    d.[location_semantics],
    CAST(N'ft' AS NVARCHAR(16)) AS [coordinate_units],
    d.[target_surface_x_ft] AS [surface_x_ft],
    d.[target_surface_y_ft] AS [surface_y_ft],
    d.[reference_dataset_version],
    d.[reference_manifest_sha256],
    d.[_transformation_contract_version]
FROM [serving].[__planned_target_summary_release_data] AS d
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = N'drill_run_history'
    AND r.[release_id] = d.[_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

CREATE OR ALTER VIEW [serving].[offset_section_summary_release]
AS
SELECT
    d.[_release_id],
    d.[dataset_version],
    d.[generator_version],
    d.[generation_run_id],
    d.[scenario],
    d.[deterministic_seed],
    d.[is_synthetic],
    d.[target_id],
    d.[target_name],
    d.[target_basin_name] AS [target_basin_name],
    d.[target_field_name] AS [target_field_name],
    d.[well_basin_name] AS [basin_name],
    d.[well_field_name] AS [field_name],
    d.[expected_formation_name],
    d.[planned_hole_size_in],
    d.[planned_md_min_ft],
    d.[planned_md_max_ft],
    d.[planned_trajectory_profile],
    d.[coordinate_frame_id],
    d.[location_semantics],
    CAST(N'ft' AS NVARCHAR(16)) AS [coordinate_units],
    d.[target_surface_x_ft] AS [target_surface_x_ft],
    d.[target_surface_y_ft] AS [target_surface_y_ft],
    d.[well_surface_x_ft] AS [surface_x_ft],
    d.[well_surface_y_ft] AS [surface_y_ft],
    d.[well_id],
    d.[well_name],
    d.[operator_name],
    d.[well_basin_name],
    d.[well_field_name],
    d.[well_surface_x_ft],
    d.[well_surface_y_ft],
    d.[section_id],
    d.[section_sequence],
    d.[section_formation_name] AS [formation_name],
    d.[section_hole_size_in] AS [hole_size_in],
    d.[section_start_md_ft] AS [start_md_ft],
    d.[section_end_md_ft] AS [end_md_ft],
    d.[section_trajectory_profile] AS [trajectory_profile],
    d.[source_run_count],
    d.[accepted_run_count],
    d.[quarantined_run_count],
    d.[warning_run_count],
    d.[error_run_count],
    CASE
        WHEN d.[warning_issue_count] > 0 THEN CAST(1 AS INT)
        ELSE CAST(0 AS INT)
    END AS [warning_section_count],
    d.[warning_issue_count],
    d.[error_issue_count],
    d.[accepted_footage_ft],
    d.[accepted_duration_hours],
    d.[distance_squared_ft2],
    d.[_transformation_contract_version]
FROM [serving].[__offset_section_summary_release_data] AS d
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = N'drill_run_history'
    AND r.[release_id] = d.[_release_id]
    AND r.[release_state] = N'READY'
WHERE d.[_publication_state] = N'STAGED';
GO

/* Read-only deployment verification: view inventory. */
WITH expected_views ([schema_name], [view_name]) AS (
    SELECT N'raw', N'well' UNION ALL
    SELECT N'raw', N'section' UNION ALL
    SELECT N'raw', N'drilling_run' UNION ALL
    SELECT N'raw', N'run_event' UNION ALL
    SELECT N'raw', N'quality_issue' UNION ALL
    SELECT N'raw', N'split_assignment' UNION ALL
    SELECT N'raw', N'rejected_record' UNION ALL
    SELECT N'curated', N'well' UNION ALL
    SELECT N'curated', N'section' UNION ALL
    SELECT N'curated', N'drilling_run' UNION ALL
    SELECT N'curated', N'run_event' UNION ALL
    SELECT N'curated', N'drilling_run_quarantine' UNION ALL
    SELECT N'curated', N'quality_issue' UNION ALL
    SELECT N'curated', N'split_assignment' UNION ALL
    SELECT N'curated', N'rejected_record' UNION ALL
    SELECT N'serving', N'well_summary' UNION ALL
    SELECT N'serving', N'dataset_summary' UNION ALL
    SELECT N'serving', N'quality_summary' UNION ALL
    SELECT N'serving', N'category_summary' UNION ALL
    SELECT N'serving', N'offset_run_config_summary_release' UNION ALL
    SELECT N'serving', N'offset_run_event_summary_release' UNION ALL
    SELECT N'serving', N'planned_target_summary_release' UNION ALL
    SELECT N'serving', N'offset_section_summary_release' UNION ALL
    SELECT N'serving', N'offset_run_config_summary' UNION ALL
    SELECT N'serving', N'offset_run_event_summary' UNION ALL
    SELECT N'serving', N'planned_target_summary' UNION ALL
    SELECT N'serving', N'offset_section_summary'
)
SELECT
    e.[schema_name],
    e.[view_name],
    CASE WHEN v.[object_id] IS NULL THEN N'MISSING' ELSE N'PRESENT' END AS [inventory_status]
FROM expected_views AS e
LEFT JOIN sys.schemas AS s
    ON s.[name] = e.[schema_name]
LEFT JOIN sys.views AS v
    ON v.[schema_id] = s.[schema_id]
    AND v.[name] = e.[view_name]
ORDER BY e.[schema_name], e.[view_name];
GO

/* Read-only deployment verification: active pointer and contract row counts. */
SELECT
    p.[dataset_name],
    p.[active_release_id],
    r.[release_state]
FROM [control].[dataset_release_pointer] AS p
INNER JOIN [control].[dataset_release_registry] AS r
    ON r.[dataset_name] = p.[dataset_name]
    AND r.[release_id] = p.[active_release_id]
WHERE p.[dataset_name] = N'drill_run_history';

WITH active_release AS (
    SELECT p.[active_release_id]
    FROM [control].[dataset_release_pointer] AS p
    WHERE p.[dataset_name] = N'drill_run_history'
),
expected_counts ([logical_view], [expected_count]) AS (
    SELECT N'raw.well', CAST(100 AS BIGINT) UNION ALL
    SELECT N'raw.section', CAST(274 AS BIGINT) UNION ALL
    SELECT N'raw.drilling_run', CAST(937 AS BIGINT) UNION ALL
    SELECT N'raw.run_event', CAST(0 AS BIGINT) UNION ALL
    SELECT N'raw.quality_issue', CAST(20 AS BIGINT) UNION ALL
    SELECT N'raw.split_assignment', CAST(100 AS BIGINT) UNION ALL
    SELECT N'raw.rejected_record', CAST(0 AS BIGINT) UNION ALL
    SELECT N'curated.well', CAST(100 AS BIGINT) UNION ALL
    SELECT N'curated.section', CAST(274 AS BIGINT) UNION ALL
    SELECT N'curated.drilling_run', CAST(932 AS BIGINT) UNION ALL
    SELECT N'curated.run_event', CAST(0 AS BIGINT) UNION ALL
    SELECT N'curated.drilling_run_quarantine', CAST(5 AS BIGINT) UNION ALL
    SELECT N'curated.quality_issue', CAST(20 AS BIGINT) UNION ALL
    SELECT N'curated.split_assignment', CAST(100 AS BIGINT) UNION ALL
    SELECT N'curated.rejected_record', CAST(0 AS BIGINT) UNION ALL
    SELECT N'serving.well_summary', CAST(100 AS BIGINT) UNION ALL
    SELECT N'serving.dataset_summary', CAST(1 AS BIGINT) UNION ALL
    SELECT N'serving.quality_summary', CAST(4 AS BIGINT) UNION ALL
    SELECT N'serving.category_summary', CAST(19 AS BIGINT) UNION ALL
    SELECT N'serving.offset_run_config_summary', CAST(0 AS BIGINT) UNION ALL
    SELECT N'serving.offset_run_event_summary', CAST(0 AS BIGINT) UNION ALL
    SELECT N'serving.planned_target_summary', CAST(12 AS BIGINT) UNION ALL
    SELECT N'serving.offset_section_summary', CAST(3288 AS BIGINT)
),
observed_counts ([logical_view], [observed_count]) AS (
    SELECT N'raw.well', COUNT_BIG(*) FROM [raw].[well]
    UNION ALL SELECT N'raw.section', COUNT_BIG(*) FROM [raw].[section]
    UNION ALL SELECT N'raw.drilling_run', COUNT_BIG(*) FROM [raw].[drilling_run]
    UNION ALL SELECT N'raw.run_event', COUNT_BIG(*) FROM [raw].[run_event]
    UNION ALL SELECT N'raw.quality_issue', COUNT_BIG(*) FROM [raw].[quality_issue]
    UNION ALL SELECT N'raw.split_assignment', COUNT_BIG(*) FROM [raw].[split_assignment]
    UNION ALL SELECT N'raw.rejected_record', COUNT_BIG(*) FROM [raw].[rejected_record]
    UNION ALL SELECT N'curated.well', COUNT_BIG(*) FROM [curated].[well]
    UNION ALL SELECT N'curated.section', COUNT_BIG(*) FROM [curated].[section]
    UNION ALL SELECT N'curated.drilling_run', COUNT_BIG(*) FROM [curated].[drilling_run]
    UNION ALL SELECT N'curated.run_event', COUNT_BIG(*) FROM [curated].[run_event]
    UNION ALL SELECT N'curated.drilling_run_quarantine', COUNT_BIG(*) FROM [curated].[drilling_run_quarantine]
    UNION ALL SELECT N'curated.quality_issue', COUNT_BIG(*) FROM [curated].[quality_issue]
    UNION ALL SELECT N'curated.split_assignment', COUNT_BIG(*) FROM [curated].[split_assignment]
    UNION ALL SELECT N'curated.rejected_record', COUNT_BIG(*) FROM [curated].[rejected_record]
    UNION ALL SELECT N'serving.well_summary', COUNT_BIG(*) FROM [serving].[well_summary]
    UNION ALL SELECT N'serving.dataset_summary', COUNT_BIG(*) FROM [serving].[dataset_summary]
    UNION ALL SELECT N'serving.quality_summary', COUNT_BIG(*) FROM [serving].[quality_summary]
    UNION ALL SELECT N'serving.category_summary', COUNT_BIG(*) FROM [serving].[category_summary]
    UNION ALL SELECT N'serving.offset_run_config_summary', COUNT_BIG(*) FROM [serving].[offset_run_config_summary]
    UNION ALL SELECT N'serving.offset_run_event_summary', COUNT_BIG(*) FROM [serving].[offset_run_event_summary]
    UNION ALL SELECT N'serving.planned_target_summary', COUNT_BIG(*) FROM [serving].[planned_target_summary]
    UNION ALL SELECT N'serving.offset_section_summary', COUNT_BIG(*) FROM [serving].[offset_section_summary]
)
SELECT
    e.[logical_view],
    a.[active_release_id],
    N'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d' AS [expected_release_id],
    o.[observed_count],
    e.[expected_count],
    CASE
        WHEN a.[active_release_id] <> N'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d'
            THEN N'NOT_APPLICABLE_TO_ACTIVE_RELEASE'
        WHEN o.[observed_count] = e.[expected_count] THEN N'MATCH'
        ELSE N'MISMATCH'
    END AS [verification_status]
FROM expected_counts AS e
INNER JOIN observed_counts AS o
    ON o.[logical_view] = e.[logical_view]
CROSS JOIN active_release AS a
ORDER BY e.[logical_view];
GO
