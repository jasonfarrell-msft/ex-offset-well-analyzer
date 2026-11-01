using System.Text.RegularExpressions;
using Azure.Core;
using Azure.Identity;
using Microsoft.Data.SqlClient;

var recoverLock = args.Contains("--recover-lock", StringComparer.OrdinalIgnoreCase);
string? applySqlPath = null;
var filteredArgs = new List<string>();
for (var i = 0; i < args.Length; i++)
{
    if (string.Equals(args[i], "--recover-lock", StringComparison.OrdinalIgnoreCase))
    {
        continue;
    }
    if (string.Equals(args[i], "--apply-sql", StringComparison.OrdinalIgnoreCase) && i + 1 < args.Length)
    {
        applySqlPath = args[i + 1];
        i++;
        continue;
    }
    filteredArgs.Add(args[i]);
}

var positionalArgs = filteredArgs.ToArray();
var server = positionalArgs.Length > 0 ? positionalArgs[0] : "ehmqx2iabzxu5od4oe3hb3rhx4-vb3rstx7257ernbnysz3yemphu.datawarehouse.fabric.microsoft.com";
var databaseCandidates = positionalArgs.Length > 1
    ? positionalArgs.Skip(1).ToArray()
    : new[] { "lh_drillrun_summary", "drillrun_summary", "master" };

var credential = new ChainedTokenCredential(
    new AzureCliCredential(),
    new VisualStudioCodeCredential());
var token = await credential.GetTokenAsync(new TokenRequestContext(new[] { "https://database.windows.net/.default" }));

if (recoverLock)
{
    Console.Error.WriteLine(
        "Lock recovery is disabled for Lakehouse SQL endpoint operations in this repository. " +
        "Use the existing Fabric notebook item and operator recovery controls from the Section 18 runbook."
    );
    Environment.Exit(3);
}

if (!string.IsNullOrWhiteSpace(applySqlPath) && !File.Exists(applySqlPath))
{
    Console.Error.WriteLine($"--apply-sql file not found: {applySqlPath}");
    Environment.Exit(4);
}

var applySql = !string.IsNullOrWhiteSpace(applySqlPath)
    ? await File.ReadAllTextAsync(applySqlPath!)
    : null;

if (!string.IsNullOrWhiteSpace(applySqlPath) && string.IsNullOrWhiteSpace(applySql))
{
    Console.Error.WriteLine($"--apply-sql file is empty: {applySqlPath}");
    Environment.Exit(5);
}

foreach (var database in databaseCandidates)
{
    Console.WriteLine($"=== database: {database} ===");
    try
    {
        var cs = new SqlConnectionStringBuilder
        {
            DataSource = $"tcp:{server},1433",
            InitialCatalog = database,
            Encrypt = true,
            TrustServerCertificate = false,
            ConnectTimeout = 30,
        };

        await using var conn = new SqlConnection(cs.ConnectionString)
        {
            AccessToken = token.Token,
        };
        await conn.OpenAsync();

        if (!string.IsNullOrWhiteSpace(applySql))
        {
            var batches = Regex.Split(applySql, @"^\s*GO\s*$", RegexOptions.Multiline | RegexOptions.IgnoreCase)
                .Select(batch => batch.Trim())
                .Where(batch => !string.IsNullOrWhiteSpace(batch))
                .ToArray();
            for (var batchIndex = 0; batchIndex < batches.Length; batchIndex++)
            {
                await using var applyCmd = conn.CreateCommand();
                applyCmd.CommandTimeout = 120;
                applyCmd.CommandText = batches[batchIndex];
                _ = await applyCmd.ExecuteNonQueryAsync();
            }
            Console.WriteLine($"APPLIED {applySqlPath} ON {database}");
            return;
        }

        await using var cmd = conn.CreateCommand();
        cmd.CommandText = @"
SELECT DB_NAME() AS current_db;
SELECT TOP (8) attempt_id, release_id, attempt_state, failure_message, requested_at_utc, completed_at_utc
FROM control.dataset_publication_attempt
ORDER BY requested_at_utc DESC;
SELECT dataset_name, attempt_id, attempt_application_id, acquired_at_utc
FROM control.dataset_publication_lock;
SELECT TOP (8) release_id, release_state, attempt_id, failure_message, staged_at_utc, reconciled_at_utc
FROM control.dataset_release_registry
ORDER BY staged_at_utc DESC;
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA='serving' AND TABLE_NAME IN ('planned_target_summary','offset_section_summary')
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION;
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA='serving' AND TABLE_NAME IN (
    '__planned_target_summary_release_data',
    '__offset_run_config_summary_release_data',
    '__offset_run_event_summary_release_data'
)
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION;
SELECT TOP (1) dataset_name, active_release_id, activated_at_utc FROM control.dataset_release_pointer;
SELECT
    COUNT(*) AS planned_target_count,
    CONVERT(VARCHAR(64), HASHBYTES('SHA2_256',
        STRING_AGG(CONCAT_WS('|', target_id, basin_name, field_name, coordinate_units, surface_x_ft, surface_y_ft, reference_manifest_sha256), ';')
        WITHIN GROUP (ORDER BY target_id)
    ), 2) AS planned_target_sha256
FROM serving.planned_target_summary
WHERE _release_id = 'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d';
SELECT
    COUNT(*) AS offset_section_count,
    CHECKSUM_AGG(BINARY_CHECKSUM(
        target_id, well_id, section_id, basin_name, field_name,
        coordinate_units, surface_x_ft, surface_y_ft, accepted_run_count, warning_issue_count
    )) AS offset_section_checksum
FROM serving.offset_section_summary
WHERE _release_id = 'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d';
SELECT TOP (1)
    target_id, record_kind, basin_name, field_name, expected_formation_name,
    planned_trajectory_profile, planned_hole_size_in, planned_md_min_ft, planned_md_max_ft,
    coordinate_frame_id, location_semantics, coordinate_units, surface_x_ft, surface_y_ft,
    reference_dataset_version, reference_manifest_sha256
FROM serving.planned_target_summary
WHERE _release_id = 'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d'
ORDER BY target_id;
SELECT TOP (1)
    target_id, well_id, well_name, basin_name, field_name, coordinate_frame_id,
    location_semantics, coordinate_units, surface_x_ft, surface_y_ft, section_id,
    formation_name, hole_size_in, start_md_ft, end_md_ft, trajectory_profile,
    accepted_run_count, accepted_footage_ft, accepted_duration_hours,
    quarantined_run_count, warning_run_count, warning_section_count, warning_issue_count
FROM serving.offset_section_summary
WHERE _release_id = 'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d'
ORDER BY target_id, well_id, section_id;
SELECT
    'raw.__run_event_release_data' AS table_name,
    COUNT(*) AS staged_rows
FROM [raw].[__run_event_release_data]
WHERE [_release_id] = 'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0'
  AND [_publication_state] = 'STAGED';
SELECT
    'curated.__run_event_release_data' AS table_name,
    COUNT(*) AS staged_rows
FROM [curated].[__run_event_release_data]
WHERE [_release_id] = 'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0'
  AND [_publication_state] = 'STAGED';
SELECT
    'serving.__planned_target_summary_release_data' AS table_name,
    COUNT(*) AS staged_rows
FROM [serving].[__planned_target_summary_release_data]
WHERE [_release_id] = 'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0'
  AND [_publication_state] = 'STAGED';
SELECT
    'serving.__offset_run_config_summary_release_data' AS table_name,
    COUNT(*) AS staged_rows
FROM [serving].[__offset_run_config_summary_release_data]
WHERE [_release_id] = 'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0'
  AND [_publication_state] = 'STAGED';
SELECT
    'serving.__offset_run_event_summary_release_data' AS table_name,
    COUNT(*) AS staged_rows
FROM [serving].[__offset_run_event_summary_release_data]
WHERE [_release_id] = 'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0'
  AND [_publication_state] = 'STAGED';
SELECT
    COUNT(*) AS planned_target_rows,
    SUM(CASE WHEN [planned_bit_type] IS NOT NULL AND [planned_bit_type] <> '' THEN 1 ELSE 0 END) AS planned_bit_type_populated_rows,
    SUM(CASE WHEN [planned_bha_type] IS NOT NULL AND [planned_bha_type] <> '' THEN 1 ELSE 0 END) AS planned_bha_type_populated_rows,
    SUM(CASE WHEN [planned_mud_type] IS NOT NULL AND [planned_mud_type] <> '' THEN 1 ELSE 0 END) AS planned_mud_type_populated_rows
FROM [serving].[__planned_target_summary_release_data]
WHERE [_release_id] = 'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0'
  AND [_publication_state] = 'STAGED';
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AS release_id, N'raw.__well_release_data' AS table_name, COUNT(*) AS staged_rows
FROM [raw].[__well_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'raw.__section_release_data', COUNT(*)
FROM [raw].[__section_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'raw.__drilling_run_release_data', COUNT(*)
FROM [raw].[__drilling_run_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'raw.__run_event_release_data', COUNT(*)
FROM [raw].[__run_event_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'raw.__quality_issue_release_data', COUNT(*)
FROM [raw].[__quality_issue_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'raw.__split_assignment_release_data', COUNT(*)
FROM [raw].[__split_assignment_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'raw.__rejected_record_release_data', COUNT(*)
FROM [raw].[__rejected_record_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'curated.__well_release_data', COUNT(*)
FROM [curated].[__well_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'curated.__section_release_data', COUNT(*)
FROM [curated].[__section_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'curated.__drilling_run_release_data', COUNT(*)
FROM [curated].[__drilling_run_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'curated.__run_event_release_data', COUNT(*)
FROM [curated].[__run_event_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'curated.__drilling_run_quarantine_release_data', COUNT(*)
FROM [curated].[__drilling_run_quarantine_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'curated.__quality_issue_release_data', COUNT(*)
FROM [curated].[__quality_issue_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'curated.__split_assignment_release_data', COUNT(*)
FROM [curated].[__split_assignment_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'curated.__rejected_record_release_data', COUNT(*)
FROM [curated].[__rejected_record_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'serving.__well_summary_release_data', COUNT(*)
FROM [serving].[__well_summary_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'serving.__dataset_summary_release_data', COUNT(*)
FROM [serving].[__dataset_summary_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'serving.__quality_summary_release_data', COUNT(*)
FROM [serving].[__quality_summary_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'serving.__category_summary_release_data', COUNT(*)
FROM [serving].[__category_summary_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'serving.__planned_target_summary_release_data', COUNT(*)
FROM [serving].[__planned_target_summary_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED'
UNION ALL
SELECT N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', N'serving.__offset_section_summary_release_data', COUNT(*)
FROM [serving].[__offset_section_summary_release_data]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0' AND [_publication_state] = N'STAGED';
SELECT
    [_release_id] AS release_id,
    [dataset_version],
    [generator_version],
    [generation_run_id],
    [scenario],
    [deterministic_seed],
    [is_synthetic],
    [_transformation_contract_version],
    COUNT(*) AS row_count
FROM [serving].[__offset_section_summary_release_data]
WHERE [_release_id] IN (
    N'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d',
    N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0'
)
GROUP BY
    [_release_id],
    [dataset_version],
    [generator_version],
    [generation_run_id],
    [scenario],
    [deterministic_seed],
    [is_synthetic],
    [_transformation_contract_version]
ORDER BY [_release_id], [generation_run_id];
SELECT N'serving.offset_run_config_summary_release' AS view_name, N'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d' AS release_id, COUNT_BIG(*) AS row_count
FROM [serving].[offset_run_config_summary_release]
WHERE [_release_id] = N'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d'
UNION ALL
SELECT N'serving.offset_run_config_summary_release', N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', COUNT_BIG(*)
FROM [serving].[offset_run_config_summary_release]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0'
UNION ALL
SELECT N'serving.offset_run_event_summary_release', N'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d', COUNT_BIG(*)
FROM [serving].[offset_run_event_summary_release]
WHERE [_release_id] = N'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d'
UNION ALL
SELECT N'serving.offset_run_event_summary_release', N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', COUNT_BIG(*)
FROM [serving].[offset_run_event_summary_release]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0'
UNION ALL
SELECT N'serving.planned_target_summary_release', N'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d', COUNT_BIG(*)
FROM [serving].[planned_target_summary_release]
WHERE [_release_id] = N'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d'
UNION ALL
SELECT N'serving.planned_target_summary_release', N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', COUNT_BIG(*)
FROM [serving].[planned_target_summary_release]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0'
UNION ALL
SELECT N'serving.offset_section_summary_release', N'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d', COUNT_BIG(*)
FROM [serving].[offset_section_summary_release]
WHERE [_release_id] = N'v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d'
UNION ALL
SELECT N'serving.offset_section_summary_release', N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0', COUNT_BIG(*)
FROM [serving].[offset_section_summary_release]
WHERE [_release_id] = N'v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0'
ORDER BY view_name, release_id;
";

        await using var reader = await cmd.ExecuteReaderAsync();
        var rs = 0;
        do
        {
            rs++;
            Console.WriteLine($"-- resultset {rs} --");
            var cols = Enumerable.Range(0, reader.FieldCount).Select(reader.GetName).ToArray();
            Console.WriteLine(string.Join("\t", cols));
            while (await reader.ReadAsync())
            {
                var vals = cols.Select((_, i) => reader.IsDBNull(i) ? "<null>" : Convert.ToString(reader.GetValue(i)) ?? "").ToArray();
                Console.WriteLine(string.Join("\t", vals));
            }
        } while (await reader.NextResultAsync());

        Console.WriteLine("SUCCESS");
        return;
    }
    catch (Exception ex)
    {
        Console.WriteLine($"FAILED {database}: {ex.GetType().Name}: {ex.Message}");
    }
}

Environment.Exit(2);
