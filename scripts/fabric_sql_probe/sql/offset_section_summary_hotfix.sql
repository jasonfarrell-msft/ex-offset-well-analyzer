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
