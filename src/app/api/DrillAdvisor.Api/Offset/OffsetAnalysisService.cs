using System.Data.Common;
using System.Data.SqlClient;
using System.Globalization;
using Azure.Core;
using DrillAdvisor.Api.Configuration;
using Microsoft.Extensions.Options;
using Microsoft.AspNetCore.Http;

namespace DrillAdvisor.Api.Offset;

public interface IOffsetAnalysisDataSource
{
    Task<IReadOnlyList<TargetRow>> ReadTargetsAsync(
        OffsetContractSpec contract,
        CancellationToken cancellationToken);

    Task<IReadOnlyList<OffsetSectionRow>> ReadOffsetSectionsAsync(
        OffsetContractSpec contract,
        string targetId,
        CancellationToken cancellationToken);

    Task<IReadOnlyList<OffsetRunConfigurationRow>> ReadRunConfigurationsAsync(
        OffsetContractSpec contract,
        string targetId,
        CancellationToken cancellationToken);

    Task<IReadOnlyList<OffsetRunEventRow>> ReadRunEventsAsync(
        OffsetContractSpec contract,
        string targetId,
        CancellationToken cancellationToken);
}

public interface IOffsetAnalysisService
{
    Task<OffsetAnalysisResponse> ExecuteAsync(
        OffsetOperationRequest request,
        CancellationToken cancellationToken);

    Task<IReadOnlyList<OffsetChatWellSummary>> BuildChatContextAsync(
        OffsetContractSpec contract,
        OffsetContext context,
        CancellationToken cancellationToken);

    Task<IReadOnlyList<OffsetChatWellSummary>> BuildChatContextAsync(
        OffsetContext context,
        CancellationToken cancellationToken);
}

public sealed class SqlOffsetAnalysisDataSource(
    TokenCredential tokenCredential,
    IOptions<OffsetAnalysisSqlOptions> options)
    : IOffsetAnalysisDataSource
{
    private const string SqlScope = "https://database.windows.net/.default";
    private const string ReadyPlannedTargetSummaryView = "serving.planned_target_summary_release";
    private const string ReadyOffsetSectionSummaryView = "serving.offset_section_summary_release";
    private const string ReadyOffsetRunConfigSummaryView = "serving.offset_run_config_summary_release";
    private const string ReadyOffsetRunEventSummaryView = "serving.offset_run_event_summary_release";
    private readonly TokenCredential _tokenCredential =
        tokenCredential ?? throw new ArgumentNullException(nameof(tokenCredential));
    private readonly OffsetAnalysisSqlOptions _options =
        options?.Value ?? throw new ArgumentNullException(nameof(options));

    public Task<IReadOnlyList<TargetRow>> ReadTargetsAsync(
        OffsetContractSpec contract,
        CancellationToken cancellationToken) =>
        ExecuteTargetsAsync(contract, cancellationToken);

    public Task<IReadOnlyList<OffsetSectionRow>> ReadOffsetSectionsAsync(
        OffsetContractSpec contract,
        string targetId,
        CancellationToken cancellationToken) =>
        ExecuteSectionsAsync(contract, targetId, cancellationToken);

    public Task<IReadOnlyList<OffsetRunConfigurationRow>> ReadRunConfigurationsAsync(
        OffsetContractSpec contract,
        string targetId,
        CancellationToken cancellationToken) =>
        ExecuteRunConfigurationsAsync(contract, targetId, cancellationToken);

    public Task<IReadOnlyList<OffsetRunEventRow>> ReadRunEventsAsync(
        OffsetContractSpec contract,
        string targetId,
        CancellationToken cancellationToken) =>
        ExecuteRunEventsAsync(contract, targetId, cancellationToken);

    private async Task<IReadOnlyList<TargetRow>> ExecuteTargetsAsync(
        OffsetContractSpec contract,
        CancellationToken cancellationToken)
    {
        using var connection = await OpenConnectionAsync(cancellationToken).ConfigureAwait(false);
        var includePlannedFields = contract == OffsetContractVersions.V2;
        return await ExecuteTargetsQueryAsync(
                connection,
                contract,
                contract.ReleaseId,
                includePlannedFields,
                cancellationToken)
            .ConfigureAwait(false);
    }

    private async Task<IReadOnlyList<OffsetSectionRow>> ExecuteSectionsAsync(
        OffsetContractSpec contract,
        string targetId,
        CancellationToken cancellationToken)
    {
        using var connection = await OpenConnectionAsync(cancellationToken).ConfigureAwait(false);
        using var command = connection.CreateCommand();
        command.CommandTimeout = _options.CommandTimeoutSeconds;
        var sectionSummaryView = ResolveOffsetSectionSummaryView(contract);
        command.CommandText =
            $"""
            SELECT
                target_id,
                well_id,
                well_name,
                basin_name,
                field_name,
                coordinate_frame_id,
                location_semantics,
                coordinate_units,
                surface_x_ft,
                surface_y_ft,
                section_id,
                formation_name,
                hole_size_in,
                start_md_ft,
                end_md_ft,
                trajectory_profile,
                accepted_run_count,
                accepted_footage_ft,
                accepted_duration_hours,
                quarantined_run_count,
                warning_run_count,
                warning_section_count,
                warning_issue_count
            FROM {sectionSummaryView}
            WHERE _release_id = @releaseId
              AND target_id = @targetId
            ORDER BY well_id ASC, section_id ASC;
            """;
        _ = command.Parameters.AddWithValue("@releaseId", contract.ReleaseId);
        _ = command.Parameters.AddWithValue("@targetId", targetId);
        using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);

        var rows = new List<OffsetSectionRow>();
        while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
        {
            rows.Add(
                new OffsetSectionRow(
                    GetString(reader, "target_id"),
                    GetString(reader, "well_id"),
                    GetString(reader, "well_name"),
                    GetString(reader, "basin_name"),
                    GetString(reader, "field_name"),
                    GetString(reader, "coordinate_frame_id"),
                    GetString(reader, "location_semantics"),
                    GetString(reader, "coordinate_units"),
                    DecimalString(reader, "surface_x_ft"),
                    DecimalString(reader, "surface_y_ft"),
                    GetNullableString(reader, "section_id"),
                    GetNullableString(reader, "formation_name"),
                    NullableDecimalString(reader, "hole_size_in"),
                    NullableDecimalString(reader, "start_md_ft"),
                    NullableDecimalString(reader, "end_md_ft"),
                    GetNullableString(reader, "trajectory_profile"),
                    GetInt32(reader, "accepted_run_count"),
                    NullableDecimalString(reader, "accepted_footage_ft"),
                    NullableDecimalString(reader, "accepted_duration_hours"),
                    GetInt32(reader, "quarantined_run_count"),
                    GetInt32(reader, "warning_run_count"),
                    GetInt32(reader, "warning_section_count"),
                    GetInt32(reader, "warning_issue_count")));
        }

        return rows;
    }

    private async Task<IReadOnlyList<OffsetRunConfigurationRow>> ExecuteRunConfigurationsAsync(
        OffsetContractSpec contract,
        string targetId,
        CancellationToken cancellationToken)
    {
        using var connection = await OpenConnectionAsync(cancellationToken).ConfigureAwait(false);
        using var command = connection.CreateCommand();
        command.CommandTimeout = _options.CommandTimeoutSeconds;
        var runConfigSummaryView = ResolveOffsetRunConfigSummaryView(contract);
        command.CommandText =
            $"""
            SELECT
                target_id,
                well_id,
                bit_type,
                bha_type,
                mud_type,
                mud_weight_ppg,
                mud_funnel_viscosity_sec,
                accepted_run_count,
                accepted_footage_ft,
                accepted_duration_hours
            FROM {runConfigSummaryView}
            WHERE _release_id = @releaseId
              AND target_id = @targetId
            ORDER BY well_id ASC, bit_type ASC, bha_type ASC, mud_type ASC, mud_weight_ppg ASC, mud_funnel_viscosity_sec ASC;
            """;
        _ = command.Parameters.AddWithValue("@releaseId", contract.ReleaseId);
        _ = command.Parameters.AddWithValue("@targetId", targetId);
        using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);

        var rows = new List<OffsetRunConfigurationRow>();
        while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
        {
            rows.Add(
                new OffsetRunConfigurationRow(
                    GetString(reader, "target_id"),
                    GetString(reader, "well_id"),
                    GetNullableString(reader, "bit_type"),
                    GetNullableString(reader, "bha_type"),
                    GetNullableString(reader, "mud_type"),
                    NullableDecimalString(reader, "mud_weight_ppg"),
                    NullableDecimalString(reader, "mud_funnel_viscosity_sec"),
                    GetInt32(reader, "accepted_run_count"),
                    NullableDecimalString(reader, "accepted_footage_ft"),
                    NullableDecimalString(reader, "accepted_duration_hours")));
        }

        return rows;
    }

    private async Task<IReadOnlyList<OffsetRunEventRow>> ExecuteRunEventsAsync(
        OffsetContractSpec contract,
        string targetId,
        CancellationToken cancellationToken)
    {
        using var connection = await OpenConnectionAsync(cancellationToken).ConfigureAwait(false);
        using var command = connection.CreateCommand();
        command.CommandTimeout = _options.CommandTimeoutSeconds;
        var runEventSummaryView = ResolveOffsetRunEventSummaryView(contract);
        command.CommandText =
            $"""
            SELECT
                target_id,
                well_id,
                event_type,
                event_subtype,
                event_count,
                event_duration_hours
            FROM {runEventSummaryView}
            WHERE _release_id = @releaseId
              AND target_id = @targetId
            ORDER BY well_id ASC, event_type ASC, event_subtype ASC;
            """;
        _ = command.Parameters.AddWithValue("@releaseId", contract.ReleaseId);
        _ = command.Parameters.AddWithValue("@targetId", targetId);
        using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);

        var rows = new List<OffsetRunEventRow>();
        while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
        {
            rows.Add(
                new OffsetRunEventRow(
                    GetString(reader, "target_id"),
                    GetString(reader, "well_id"),
                    GetString(reader, "event_type"),
                    GetString(reader, "event_subtype"),
                    GetInt32(reader, "event_count"),
                    DecimalString(reader, "event_duration_hours")));
        }

        return rows;
    }

    private async Task<IReadOnlyList<TargetRow>> ExecuteTargetsQueryAsync(
        SqlConnection connection,
        OffsetContractSpec contract,
        string releaseId,
        bool includePlannedFields,
        CancellationToken cancellationToken)
    {
        using var command = connection.CreateCommand();
        command.CommandTimeout = _options.CommandTimeoutSeconds;
        command.CommandText = BuildTargetsCommandText(contract, includePlannedFields);
        _ = command.Parameters.AddWithValue("@releaseId", releaseId);
        using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);

        var rows = new List<TargetRow>();
        while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
        {
            rows.Add(
                new TargetRow(
                    GetString(reader, "target_id"),
                    GetString(reader, "record_kind"),
                    GetString(reader, "basin_name"),
                    GetString(reader, "field_name"),
                    GetString(reader, "expected_formation_name"),
                    GetString(reader, "planned_trajectory_profile"),
                    DecimalString(reader, "planned_hole_size_in"),
                    DecimalString(reader, "planned_md_min_ft"),
                    DecimalString(reader, "planned_md_max_ft"),
                    GetString(reader, "coordinate_frame_id"),
                    GetString(reader, "location_semantics"),
                    GetString(reader, "coordinate_units"),
                    DecimalString(reader, "surface_x_ft"),
                    DecimalString(reader, "surface_y_ft"),
                    GetString(reader, "reference_dataset_version"),
                    GetString(reader, "reference_manifest_sha256"),
                    GetBool(reader, "is_synthetic"),
                    GetNullableString(reader, "planned_bit_type"),
                    GetNullableString(reader, "planned_bha_type"),
                    GetNullableString(reader, "planned_mud_type")));
        }

        return rows;
    }

    internal static string BuildTargetsCommandText(
        OffsetContractSpec contract,
        bool includePlannedFields)
    {
        var plannedTargetSummaryView = ResolvePlannedTargetSummaryView(contract);
        return $"""
            SELECT
                target_id,
                record_kind,
                basin_name,
                field_name,
                expected_formation_name,
                planned_trajectory_profile,
                planned_hole_size_in,
                planned_md_min_ft,
                planned_md_max_ft,
                coordinate_frame_id,
                location_semantics,
                coordinate_units,
                surface_x_ft,
                surface_y_ft,
                reference_dataset_version,
                reference_manifest_sha256,
                is_synthetic,
                {(includePlannedFields
                    ? """
                planned_bit_type,
                planned_bha_type,
                planned_mud_type
                """
                    : """
                CAST(NULL AS NVARCHAR(64)) AS planned_bit_type,
                CAST(NULL AS NVARCHAR(64)) AS planned_bha_type,
                CAST(NULL AS NVARCHAR(64)) AS planned_mud_type
                """)}
            FROM {plannedTargetSummaryView}
            WHERE _release_id = @releaseId
            ORDER BY target_id ASC;
            """;
    }

    internal static string ResolvePlannedTargetSummaryView(OffsetContractSpec contract) =>
        ReadyPlannedTargetSummaryView;

    internal static string ResolveOffsetSectionSummaryView(OffsetContractSpec contract) =>
        ReadyOffsetSectionSummaryView;

    internal static string ResolveOffsetRunConfigSummaryView(OffsetContractSpec contract) =>
        ReadyOffsetRunConfigSummaryView;

    internal static string ResolveOffsetRunEventSummaryView(OffsetContractSpec contract) =>
        ReadyOffsetRunEventSummaryView;

    private async Task<SqlConnection> OpenConnectionAsync(CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(_options.Server)
            || string.IsNullOrWhiteSpace(_options.Database))
        {
            throw new InvalidOperationException(
                "Offset SQL settings are missing. Configure OFFSET_SQL_SERVER and OFFSET_SQL_DATABASE.");
        }

        var token = await _tokenCredential
            .GetTokenAsync(
                new TokenRequestContext([SqlScope]),
                cancellationToken)
            .ConfigureAwait(false);
        var connection = new SqlConnection(
            $"Server=tcp:{_options.Server},1433;Database={_options.Database};Encrypt=True;TrustServerCertificate=False;");
        connection.AccessToken = token.Token;
        await connection.OpenAsync(cancellationToken).ConfigureAwait(false);
        return connection;
    }

    private static string GetString(DbDataReader reader, string name)
    {
        var ordinal = reader.GetOrdinal(name);
        return reader.GetString(ordinal);
    }

    private static string? GetNullableString(DbDataReader reader, string name)
    {
        var ordinal = reader.GetOrdinal(name);
        return reader.IsDBNull(ordinal) ? null : reader.GetString(ordinal);
    }

    private static string DecimalString(DbDataReader reader, string name)
    {
        var ordinal = reader.GetOrdinal(name);
        var value = reader.GetValue(ordinal);
        return value switch
        {
            decimal d => OffsetFormats.CanonicalDecimal(d),
            string s => OffsetFormats.CanonicalDecimal(OffsetContextHasher.ParseDecimal(s)),
            _ => OffsetFormats.CanonicalDecimal(Convert.ToDecimal(value, CultureInfo.InvariantCulture)),
        };
    }

    private static string? NullableDecimalString(DbDataReader reader, string name)
    {
        var ordinal = reader.GetOrdinal(name);
        if (reader.IsDBNull(ordinal))
        {
            return null;
        }

        return DecimalString(reader, name);
    }

    private static int GetInt32(DbDataReader reader, string name)
    {
        var ordinal = reader.GetOrdinal(name);
        return reader.GetInt32(ordinal);
    }

    private static bool GetBool(DbDataReader reader, string name)
    {
        var ordinal = reader.GetOrdinal(name);
        return reader.GetBoolean(ordinal);
    }
}

public sealed class OffsetAnalysisResponse
{
    public required object Body { get; init; }

    public required int StatusCode { get; init; }
}

public sealed class OffsetChatContextException : Exception
{
    public OffsetChatContextException(
        int statusCode,
        string code,
        string message)
        : base(message)
    {
        StatusCode = statusCode;
        Code = code;
    }

    public int StatusCode { get; }

    public string Code { get; }
}

public sealed class OffsetAnalysisService(
    IOffsetAnalysisDataSource dataSource,
    TimeProvider timeProvider)
    : IOffsetAnalysisService
{
    private static readonly HashSet<string> AllowedEventTypes = new(
        ["LOSSES", "STUCK_PIPE", "VIBRATION", "NPT", "TRIP"],
        StringComparer.Ordinal);

    private readonly IOffsetAnalysisDataSource _dataSource =
        dataSource ?? throw new ArgumentNullException(nameof(dataSource));
    private readonly TimeProvider _timeProvider =
        timeProvider ?? throw new ArgumentNullException(nameof(timeProvider));

    public async Task<OffsetAnalysisResponse> ExecuteAsync(
        OffsetOperationRequest request,
        CancellationToken cancellationToken)
    {
        try
        {
            var contract = request.Contract;
            var targets = await _dataSource.ReadTargetsAsync(contract, cancellationToken).ConfigureAwait(false);
            if (request.Operation == "targets")
            {
                if (contract == OffsetContractVersions.V2)
                {
                    var rows = targets.Select(ToV2TargetRow).ToArray();
                    return SuccessResponse(
                        BuildAnalyticalResponse(
                            contract,
                            request.Operation,
                            "success",
                            null,
                            null,
                            rows,
                            rows.Length,
                            [],
                            [BuildTargetSource(contract)]));
                }

                var v1Rows = targets.Select(ToV1TargetRow).ToArray();
                return SuccessResponse(
                    BuildAnalyticalResponse(
                        contract,
                        request.Operation,
                        "success",
                        null,
                        null,
                        v1Rows,
                        v1Rows.Length,
                        [],
                        [BuildTargetSource(contract)]));
            }

            var context = request.Context!;
            var target = targets.SingleOrDefault(row =>
                string.Equals(row.TargetId, context.TargetId, StringComparison.Ordinal));
            if (target is null)
            {
                return Failure(contract, "error", request.Operation, context, "INVALID_REQUEST", false);
            }

            var sections = await _dataSource
                .ReadOffsetSectionsAsync(contract, target.TargetId, cancellationToken)
                .ConfigureAwait(false);
            var runConfigurations = contract == OffsetContractVersions.V2
                ? await _dataSource.ReadRunConfigurationsAsync(contract, target.TargetId, cancellationToken).ConfigureAwait(false)
                : [];
            var runEvents = contract == OffsetContractVersions.V2
                ? await _dataSource.ReadRunEventsAsync(contract, target.TargetId, cancellationToken).ConfigureAwait(false)
                : [];
            var candidateSet = ComputeCandidates(target, sections, context.Criteria);
            if (request.Operation == "candidates")
            {
                if (contract == OffsetContractVersions.V2)
                {
                    var v2Rows = candidateSet.Rows.Select(
                            row => ToV2CandidateRow(
                                row,
                                target,
                                runConfigurations,
                                runEvents))
                        .ToArray();
                    return SuccessResponse(
                        BuildAnalyticalResponse(
                            contract,
                            request.Operation,
                            v2Rows.Length == 0 ? "empty" : "success",
                            context,
                            OffsetContextHasher.Hash(context, request.ReleaseId, request.ContractVersion),
                            v2Rows,
                            v2Rows.Length,
                            candidateSet.Exclusions,
                            BuildCandidateSources(contract)));
                }

                var v1Rows = candidateSet.Rows.ToArray();
                return SuccessResponse(
                    BuildAnalyticalResponse(
                        contract,
                        request.Operation,
                        v1Rows.Length == 0 ? "empty" : "success",
                        context,
                        OffsetContextHasher.Hash(context, request.ReleaseId, request.ContractVersion),
                        v1Rows,
                        v1Rows.Length,
                        candidateSet.Exclusions,
                        BuildCandidateSources(contract)));
            }

            var selected = context.SelectedWellIds;
            var candidatesById = BuildCandidatesById(candidateSet.Rows);
            if (!AllSelectedWellIdsAreEligible(selected, candidatesById))
            {
                return Failure(contract, "stale", request.Operation, context, "CONTEXT_MISMATCH", false);
            }

            if (request.Operation == "compare")
            {
                var baseRows = selected
                    .Select(wellId =>
                    {
                        var candidate = candidatesById[wellId];
                        return new ComparisonRow(
                            candidate.WellId,
                            candidate.MatchingSections,
                            candidate.Metrics);
                    })
                    .ToArray();
                if (contract == OffsetContractVersions.V2)
                {
                    var rows = baseRows.Select(
                            row => ToV2ComparisonRow(
                                row,
                                target,
                                runConfigurations,
                                runEvents))
                        .ToArray();
                    return SuccessResponse(
                        BuildAnalyticalResponse(
                            contract,
                            request.Operation,
                            "success",
                            context,
                            OffsetContextHasher.Hash(context, request.ReleaseId, request.ContractVersion),
                            rows,
                            rows.Length,
                            [],
                            BuildCandidateSources(contract)));
                }

                return SuccessResponse(
                    BuildAnalyticalResponse(
                        contract,
                        request.Operation,
                        "success",
                        context,
                        OffsetContextHasher.Hash(context, request.ReleaseId, request.ContractVersion),
                        baseRows,
                        baseRows.Length,
                        [],
                        BuildCandidateSources(contract)));
            }

            throw new InvalidOperationException("Unsupported operation.");
        }
        catch (InvalidOperationException exception) when (IsConfigurationError(exception))
        {
            return Failure(request.Contract, "unavailable", request.Operation, request.Context, "CAPABILITY_UNPROVEN", false);
        }
        catch (SqlException)
        {
            return Failure(request.Contract, "unavailable", request.Operation, request.Context, "UPSTREAM_UNAVAILABLE", true);
        }
    }

    public async Task<IReadOnlyList<OffsetChatWellSummary>> BuildChatContextAsync(
        OffsetContractSpec contract,
        OffsetContext context,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(contract);

        if (context.SelectedWellIds.Count is < 1 or > 5)
        {
            throw new OffsetChatContextException(
                StatusCodes.Status400BadRequest,
                "invalid_request",
                "The supplied offset context must include 1-5 selected wells.");
        }

        var targets = await _dataSource.ReadTargetsAsync(contract, cancellationToken).ConfigureAwait(false);
        var target = targets.SingleOrDefault(row =>
            string.Equals(row.TargetId, context.TargetId, StringComparison.Ordinal));
        if (target is null)
        {
            throw new OffsetChatContextException(
                StatusCodes.Status400BadRequest,
                "invalid_request",
                "The supplied offset target is invalid.");
        }

        var sections = await _dataSource
            .ReadOffsetSectionsAsync(contract, target.TargetId, cancellationToken)
            .ConfigureAwait(false);
        var candidatesById = BuildCandidatesById(
            ComputeCandidates(target, sections, context.Criteria).Rows);
        if (!AllSelectedWellIdsAreEligible(context.SelectedWellIds, candidatesById))
        {
            throw new OffsetChatContextException(
                StatusCodes.Status409Conflict,
                "offset_context_stale",
                "The supplied offset context is stale. Refresh candidates and compare again.");
        }

        return context.SelectedWellIds
            .Select(wellId =>
            {
                var row = candidatesById[wellId];
                return new OffsetChatWellSummary(
                    row.WellId,
                    row.DistanceFt,
                    row.Metrics.AcceptedRunCount,
                    row.Metrics.AcceptedFootageFt,
                    row.Metrics.AcceptedDurationHours,
                    row.Metrics.SummaryPenetrationRateFtPerHour);
            })
            .ToArray();
    }

    public Task<IReadOnlyList<OffsetChatWellSummary>> BuildChatContextAsync(
        OffsetContext context,
        CancellationToken cancellationToken) =>
        BuildChatContextAsync(OffsetContractVersions.V1, context, cancellationToken);

    private static Dictionary<string, CandidateRow> BuildCandidatesById(IReadOnlyList<CandidateRow> rows) =>
        rows.ToDictionary(row => row.WellId, StringComparer.Ordinal);

    private static bool AllSelectedWellIdsAreEligible(
        IReadOnlyList<string> selectedWellIds,
        IReadOnlyDictionary<string, CandidateRow> candidatesById) =>
        selectedWellIds.All(candidatesById.ContainsKey);

    private static bool IsConfigurationError(InvalidOperationException exception) =>
        exception.Message.Contains("OFFSET_SQL_SERVER", StringComparison.Ordinal)
        || exception.Message.Contains("OFFSET_SQL_DATABASE", StringComparison.Ordinal)
        || exception.Message.Contains("Unsupported event type", StringComparison.Ordinal);

    private static SourceEnvelope BuildCandidateSectionSource(OffsetContractSpec contract) =>
        new(
            "serving.offset_section_summary_release",
            [
                "_release_id", "target_id", "well_id", "well_name", "section_id", "formation_name",
                "hole_size_in", "start_md_ft", "end_md_ft", "trajectory_profile", "surface_x_ft",
                "surface_y_ft", "accepted_run_count", "accepted_footage_ft", "accepted_duration_hours",
                "quarantined_run_count", "warning_run_count", "warning_section_count", "warning_issue_count",
            ]);

    private static SourceEnvelope BuildRunConfigSource(OffsetContractSpec contract) =>
        new(
            "serving.offset_run_config_summary_release",
            [
                "_release_id", "target_id", "well_id", "bit_type", "bha_type", "mud_type",
                "mud_weight_ppg", "mud_funnel_viscosity_sec", "accepted_run_count",
                "accepted_footage_ft", "accepted_duration_hours",
            ]);

    private static SourceEnvelope BuildRunEventSource(OffsetContractSpec contract) =>
        new(
            "serving.offset_run_event_summary_release",
            [
                "_release_id", "target_id", "well_id", "event_type", "event_subtype", "event_count",
                "event_duration_hours",
            ]);

    private static SourceEnvelope BuildTargetSource(OffsetContractSpec contract) =>
        new(
            "serving.planned_target_summary_release",
            contract == OffsetContractVersions.V2
                ? [
                    "_release_id", "target_id", "record_kind", "basin_name", "field_name",
                    "expected_formation_name", "planned_trajectory_profile", "planned_hole_size_in",
                    "planned_md_min_ft", "planned_md_max_ft", "coordinate_frame_id",
                    "location_semantics", "surface_x_ft", "surface_y_ft",
                    "reference_dataset_version", "reference_manifest_sha256", "is_synthetic",
                    "planned_bit_type", "planned_bha_type", "planned_mud_type",
                ]
                : [
                    "_release_id", "target_id", "record_kind", "basin_name", "field_name",
                    "expected_formation_name", "planned_trajectory_profile", "planned_hole_size_in",
                    "planned_md_min_ft", "planned_md_max_ft", "coordinate_frame_id",
                    "location_semantics", "surface_x_ft", "surface_y_ft",
                    "reference_dataset_version", "reference_manifest_sha256", "is_synthetic",
                ]);

    private static IReadOnlyList<SourceEnvelope> BuildCandidateSources(OffsetContractSpec contract) =>
        contract == OffsetContractVersions.V2
            ? [BuildCandidateSectionSource(contract), BuildRunConfigSource(contract), BuildRunEventSource(contract)]
            : [BuildCandidateSectionSource(contract)];

    private static OffsetAnalysisResponse SuccessResponse(object response) =>
        new()
        {
            Body = response,
            StatusCode = StatusCodes.Status200OK,
        };

    private static OffsetAnalysisResponse Failure(
        OffsetContractSpec contract,
        string status,
        string? operation,
        OffsetContext? context,
        string code,
        bool retryable)
    {
        var body = new FailureEnvelope
        {
            ContractVersion = contract.ContractVersion,
            QueryContractVersion = contract.ContractVersion,
            TransformationContractVersion = contract.TransformationContractVersion,
            DatasetVersion = contract.DatasetVersion,
            ReleaseId = contract.ReleaseId,
            ManifestSha256 = contract.ManifestSha256,
            Operation = operation,
            Status = status,
            Context = context,
            ContextHash = null,
            Evidence = null,
            Error = new ErrorEnvelope(code, retryable),
        };
        return new OffsetAnalysisResponse
        {
            Body = body,
            StatusCode = code == "INVALID_REQUEST"
                ? StatusCodes.Status400BadRequest
                : StatusCodes.Status503ServiceUnavailable,
        };
    }

    private static AnalyticalEnvelope<T> BuildAnalyticalResponse<T>(
        OffsetContractSpec contract,
        string operation,
        string status,
        OffsetContext? context,
        string? contextHash,
        IReadOnlyList<T> rows,
        int totalCount,
        IReadOnlyList<ExclusionRow> exclusions,
        IReadOnlyList<SourceEnvelope> sources)
    {
        return new AnalyticalEnvelope<T>
        {
            ContractVersion = contract.ContractVersion,
            QueryContractVersion = contract.ContractVersion,
            TransformationContractVersion = contract.TransformationContractVersion,
            DatasetVersion = contract.DatasetVersion,
            ReleaseId = contract.ReleaseId,
            ManifestSha256 = contract.ManifestSha256,
            Operation = operation,
            Status = status,
            Context = context,
            ContextHash = contextHash,
            Rows = rows,
            TotalCount = totalCount,
            Truncated = false,
            Exclusions = exclusions,
            Evidence = EvidenceEnvelope.Create(sources),
        };
    }

    private static CandidateSet ComputeCandidates(
        TargetRow target,
        IReadOnlyList<OffsetSectionRow> rows,
        OffsetCriteria criteria)
    {
        var radius = OffsetContextHasher.ParseDecimal(criteria.RadiusFt);
        var radiusSquared = radius * radius;
        var byWell = rows
            .GroupBy(row => row.WellId, StringComparer.Ordinal)
            .OrderBy(group => group.Key, StringComparer.Ordinal);
        var candidates = new List<CandidateRow>();
        var exclusions = new List<ExclusionRow>();
        foreach (var group in byWell)
        {
            var first = group.First();
            var reasons = new List<string>();
            if (!string.Equals(first.CoordinateFrameId, OffsetContract.CoordinateFrameId, StringComparison.Ordinal)
                || !string.Equals(first.LocationSemantics, OffsetContract.LocationSemantics, StringComparison.Ordinal)
                || !string.Equals(first.CoordinateUnits, OffsetContract.CoordinateUnits, StringComparison.Ordinal))
            {
                reasons.Add("INCOMPATIBLE_COORDINATES");
            }

            var distanceSquared = DistanceSquared(target, first);
            if (reasons.Count == 0 && distanceSquared > radiusSquared)
            {
                reasons.Add("OUTSIDE_RADIUS");
            }

            var matchingRows = group
                .Where(row => row.SectionId is not null && MatchesSection(row, target, criteria))
                .ToArray();
            var matchingSections = matchingRows
                .OrderBy(row => row.SectionId, StringComparer.Ordinal)
                .Select(ToMatchingSection)
                .ToArray();

            if (reasons.Count == 0 && matchingSections.Length == 0)
            {
                reasons.Add("NO_MATCHING_SECTION");
            }

            var metrics = BuildMetrics(matchingRows);
            if (reasons.Count == 0 && metrics.AcceptedRunCount == 0)
            {
                reasons.Add("NO_ACCEPTED_RUNS");
            }

            if (reasons.Count > 0)
            {
                exclusions.Add(new ExclusionRow(first.WellId, reasons));
                continue;
            }

            candidates.Add(
                new CandidateRow(
                    first.WellId,
                    first.WellName,
                    first.BasinName,
                    first.FieldName,
                    first.CoordinateFrameId,
                    first.LocationSemantics,
                    first.CoordinateUnits,
                    OffsetFormats.CanonicalDecimal(distanceSquared),
                    OffsetFormats.DistanceOne(distanceSquared),
                    matchingSections,
                    metrics));
        }

        candidates.Sort((left, right) =>
        {
            var comparison = OffsetContextHasher.ParseDecimal(left.DistanceSquaredFt2)
                .CompareTo(OffsetContextHasher.ParseDecimal(right.DistanceSquaredFt2));
            return comparison != 0
                ? comparison
                : StringComparer.Ordinal.Compare(left.WellId, right.WellId);
        });
        exclusions.Sort((left, right) => StringComparer.Ordinal.Compare(left.WellId, right.WellId));
        return new CandidateSet(candidates, exclusions);
    }

    private static decimal DistanceSquared(TargetRow target, OffsetSectionRow row)
    {
        var targetX = OffsetContextHasher.ParseDecimal(target.SurfaceXFt);
        var targetY = OffsetContextHasher.ParseDecimal(target.SurfaceYFt);
        var wellX = OffsetContextHasher.ParseDecimal(row.SurfaceXFt);
        var wellY = OffsetContextHasher.ParseDecimal(row.SurfaceYFt);
        var dx = targetX - wellX;
        var dy = targetY - wellY;
        return dx * dx + dy * dy;
    }

    private static bool MatchesSection(
        OffsetSectionRow row,
        TargetRow target,
        OffsetCriteria criteria)
    {
        if (criteria.FormationMatch)
        {
            if (string.IsNullOrWhiteSpace(row.FormationName)
                || !string.Equals(
                    row.FormationName,
                    target.ExpectedFormationName,
                    StringComparison.Ordinal))
            {
                return false;
            }
        }

        if (criteria.HoleSizeMatch)
        {
            if (string.IsNullOrWhiteSpace(row.HoleSizeIn))
            {
                return false;
            }

            if (OffsetContextHasher.ParseDecimal(row.HoleSizeIn)
                != OffsetContextHasher.ParseDecimal(target.PlannedHoleSizeIn))
            {
                return false;
            }
        }

        if (!criteria.MdOverlap)
        {
            return true;
        }

        if (row.StartMdFt is null || row.EndMdFt is null)
        {
            return false;
        }

        var sectionStart = OffsetContextHasher.ParseDecimal(row.StartMdFt);
        var sectionEnd = OffsetContextHasher.ParseDecimal(row.EndMdFt);
        var targetStart = OffsetContextHasher.ParseDecimal(target.PlannedMdMinFt);
        var targetEnd = OffsetContextHasher.ParseDecimal(target.PlannedMdMaxFt);
        return Math.Max(sectionStart, targetStart) < Math.Min(sectionEnd, targetEnd);
    }

    private static MatchingSectionRow ToMatchingSection(OffsetSectionRow row) =>
        new(
            row.SectionId!,
            row.FormationName,
            row.HoleSizeIn,
            row.StartMdFt,
            row.EndMdFt,
            row.TrajectoryProfile);

    private static MetricsRow BuildMetrics(OffsetSectionRow[] matchingRows)
    {
        var acceptedRunCount = matchingRows.Sum(row => row.AcceptedRunCount);
        var reasons = new SortedSet<string>(StringComparer.Ordinal);
        decimal? footage = null;
        decimal? duration = null;
        if (acceptedRunCount == 0)
        {
            reasons.Add("NO_ACCEPTED_RUNS");
        }
        else
        {
            if (matchingRows.Any(row => row.AcceptedFootageFt is null)
                || matchingRows.Any(row => row.AcceptedDurationHours is null))
            {
                reasons.Add("MISSING_ACCEPTED_QUANTITY");
            }
            else
            {
                footage = matchingRows
                    .Select(row => OffsetContextHasher.ParseDecimal(row.AcceptedFootageFt!))
                    .Sum();
                duration = matchingRows
                    .Select(row => OffsetContextHasher.ParseDecimal(row.AcceptedDurationHours!))
                    .Sum();
            }

            if (matchingRows.Any(row =>
                    row.AcceptedRunCount > 0
                    && row.AcceptedDurationHours is not null
                    && OffsetContextHasher.ParseDecimal(row.AcceptedDurationHours) <= 0))
            {
                reasons.Add("NON_POSITIVE_DURATION");
            }
        }

        return new MetricsRow(
            matchingRows.Length,
            acceptedRunCount,
            footage is null ? null : OffsetFormats.CanonicalDecimal(footage.Value),
            duration is null ? null : OffsetFormats.CanonicalDecimal(duration.Value),
            footage is null ? null : OffsetFormats.RatioSix(footage.Value, acceptedRunCount),
            footage is null || duration is null || reasons.Contains("NON_POSITIVE_DURATION")
                ? null
                : OffsetFormats.RatioSix(footage.Value, duration.Value),
            matchingRows.Sum(row => row.QuarantinedRunCount),
            matchingRows.Sum(row => row.WarningRunCount),
            matchingRows.Sum(row => row.WarningSectionCount),
            matchingRows.Sum(row => row.WarningIssueCount),
            "MATCHING_WHOLE_SECTIONS",
            reasons.ToArray());
    }

    private sealed record CandidateSet(
        IReadOnlyList<CandidateRow> Rows,
        IReadOnlyList<ExclusionRow> Exclusions);

    private static TargetRowV1 ToV1TargetRow(TargetRow row) =>
        new(
            row.TargetId,
            row.RecordKind,
            row.BasinName,
            row.FieldName,
            row.ExpectedFormationName,
            row.PlannedTrajectoryProfile,
            row.PlannedHoleSizeIn,
            row.PlannedMdMinFt,
            row.PlannedMdMaxFt,
            row.CoordinateFrameId,
            row.LocationSemantics,
            row.CoordinateUnits,
            row.SurfaceXFt,
            row.SurfaceYFt,
            row.ReferenceDatasetVersion,
            row.ReferenceManifestSha256,
            row.IsSynthetic);

    private static TargetRowV2 ToV2TargetRow(TargetRow row) =>
        new(
            row.TargetId,
            row.RecordKind,
            row.BasinName,
            row.FieldName,
            row.ExpectedFormationName,
            row.PlannedTrajectoryProfile,
            row.PlannedHoleSizeIn,
            row.PlannedMdMinFt,
            row.PlannedMdMaxFt,
            row.CoordinateFrameId,
            row.LocationSemantics,
            row.CoordinateUnits,
            row.SurfaceXFt,
            row.SurfaceYFt,
            row.ReferenceDatasetVersion,
            row.ReferenceManifestSha256,
            row.IsSynthetic,
            row.PlannedBitType,
            row.PlannedBhaType,
            row.PlannedMudType);

    private static CandidateRowV2 ToV2CandidateRow(
        CandidateRow row,
        TargetRow target,
        IReadOnlyList<OffsetRunConfigurationRow> runConfigurations,
        IReadOnlyList<OffsetRunEventRow> runEvents) =>
        new(
            row.WellId,
            row.WellName,
            row.BasinName,
            row.FieldName,
            row.CoordinateFrameId,
            row.LocationSemantics,
            row.CoordinateUnits,
            row.DistanceSquaredFt2,
            row.DistanceFt,
            row.MatchingSections,
            row.Metrics,
            target.PlannedBitType,
            target.PlannedBhaType,
            target.PlannedMudType,
            BuildRunConfigContext(row.WellId, runConfigurations),
            BuildEventContext(row.WellId, runEvents));

    private static ComparisonRowV2 ToV2ComparisonRow(
        ComparisonRow row,
        TargetRow target,
        IReadOnlyList<OffsetRunConfigurationRow> runConfigurations,
        IReadOnlyList<OffsetRunEventRow> runEvents) =>
        new(
            row.WellId,
            row.MatchingSections,
            row.Metrics,
            target.PlannedBitType,
            target.PlannedBhaType,
            target.PlannedMudType,
            BuildRunConfigContext(row.WellId, runConfigurations),
            BuildEventContext(row.WellId, runEvents));

    private static RunConfigContextRow? BuildRunConfigContext(
        string wellId,
        IReadOnlyList<OffsetRunConfigurationRow> runConfigurations)
    {
        var tuples = runConfigurations
            .Where(row => string.Equals(row.WellId, wellId, StringComparison.Ordinal))
            .Select(
                row => new RunTupleRow(
                    row.BitType,
                    row.BhaType,
                    row.MudType,
                    row.MudWeightPpg,
                    row.MudFunnelViscositySec,
                    row.AcceptedRunCount,
                    row.AcceptedFootageFt,
                    row.AcceptedDurationHours))
            .ToArray();
        return tuples.Length == 0
            ? null
            : new RunConfigContextRow(tuples);
    }

    private static EventContextRow? BuildEventContext(
        string wellId,
        IReadOnlyList<OffsetRunEventRow> runEvents)
    {
        var rows = runEvents
            .Where(row => string.Equals(row.WellId, wellId, StringComparison.Ordinal))
            .ToArray();
        if (rows.Length == 0)
        {
            return null;
        }

        foreach (var row in rows)
        {
            if (!AllowedEventTypes.Contains(row.EventType))
            {
                throw new InvalidOperationException(
                    $"Unsupported event type '{row.EventType}' in offset run event summary.");
            }
        }

        var totalEventCount = rows.Sum(row => row.EventCount);
        var totalEventDuration = rows
            .Select(row => OffsetContextHasher.ParseDecimal(row.EventDurationHours))
            .Sum();
        var byType = rows
            .GroupBy(row => row.EventType, StringComparer.Ordinal)
            .OrderBy(group => group.Key, StringComparer.Ordinal)
            .Select(
                group => new EventByTypeRow(
                    group.Key,
                    group.Sum(item => item.EventCount),
                    OffsetFormats.CanonicalDecimal(
                        group.Select(item => OffsetContextHasher.ParseDecimal(item.EventDurationHours)).Sum())))
            .ToArray();
        var bySubtype = rows
            .GroupBy(row => new { row.EventType, row.EventSubtype })
            .OrderBy(group => group.Key.EventType, StringComparer.Ordinal)
            .ThenBy(group => group.Key.EventSubtype, StringComparer.Ordinal)
            .Select(
                group => new EventBySubtypeRow(
                    group.Key.EventType,
                    group.Key.EventSubtype,
                    group.Sum(item => item.EventCount),
                    OffsetFormats.CanonicalDecimal(
                        group.Select(item => OffsetContextHasher.ParseDecimal(item.EventDurationHours)).Sum())))
            .ToArray();
        return new EventContextRow(
            totalEventCount,
            OffsetFormats.CanonicalDecimal(totalEventDuration),
            byType,
            bySubtype);
    }
}

public sealed record OffsetChatWellSummary(
    string WellId,
    string DistanceFt,
    int AcceptedRunCount,
    string? AcceptedFootageFt,
    string? AcceptedDurationHours,
    string? SummaryPenetrationRateFtPerHour);

public sealed class AnalyticalEnvelope<T>
{
    public required string ContractVersion { get; init; }

    public required string QueryContractVersion { get; init; }

    public required string TransformationContractVersion { get; init; }

    public required string DatasetVersion { get; init; }

    public required string ReleaseId { get; init; }

    public required string ManifestSha256 { get; init; }

    public required string Operation { get; init; }

    public required string Status { get; init; }

    public required OffsetContext? Context { get; init; }

    public required string? ContextHash { get; init; }

    public required IReadOnlyList<T> Rows { get; init; }

    public required int TotalCount { get; init; }

    public required bool Truncated { get; init; }

    public required IReadOnlyList<ExclusionRow> Exclusions { get; init; }

    public required EvidenceEnvelope Evidence { get; init; }
}

public sealed class FailureEnvelope
{
    public required string ContractVersion { get; init; }

    public required string QueryContractVersion { get; init; }

    public required string TransformationContractVersion { get; init; }

    public required string DatasetVersion { get; init; }

    public required string ReleaseId { get; init; }

    public required string ManifestSha256 { get; init; }

    public required string? Operation { get; init; }

    public required string Status { get; init; }

    public required OffsetContext? Context { get; init; }

    public required string? ContextHash { get; init; }

    public required object? Evidence { get; init; }

    public required ErrorEnvelope Error { get; init; }
}

public sealed record ErrorEnvelope(
    string Code,
    bool Retryable);

public sealed record CandidateRow(
    string WellId,
    string WellName,
    string BasinName,
    string FieldName,
    string CoordinateFrameId,
    string LocationSemantics,
    string CoordinateUnits,
    string DistanceSquaredFt2,
    string DistanceFt,
    IReadOnlyList<MatchingSectionRow> MatchingSections,
    MetricsRow Metrics);

public sealed record CandidateRowV2(
    string WellId,
    string WellName,
    string BasinName,
    string FieldName,
    string CoordinateFrameId,
    string LocationSemantics,
    string CoordinateUnits,
    string DistanceSquaredFt2,
    string DistanceFt,
    IReadOnlyList<MatchingSectionRow> MatchingSections,
    MetricsRow Metrics,
    string? PlannedBitType,
    string? PlannedBhaType,
    string? PlannedMudType,
    RunConfigContextRow? RunConfigContext,
    EventContextRow? EventContext);

public sealed record ComparisonRow(
    string WellId,
    IReadOnlyList<MatchingSectionRow> MatchingSections,
    MetricsRow Metrics);

public sealed record ComparisonRowV2(
    string WellId,
    IReadOnlyList<MatchingSectionRow> MatchingSections,
    MetricsRow Metrics,
    string? PlannedBitType,
    string? PlannedBhaType,
    string? PlannedMudType,
    RunConfigContextRow? RunConfigContext,
    EventContextRow? EventContext);

public sealed record TargetRowV1(
    string TargetId,
    string RecordKind,
    string BasinName,
    string FieldName,
    string ExpectedFormationName,
    string PlannedTrajectoryProfile,
    string PlannedHoleSizeIn,
    string PlannedMdMinFt,
    string PlannedMdMaxFt,
    string CoordinateFrameId,
    string LocationSemantics,
    string CoordinateUnits,
    string SurfaceXFt,
    string SurfaceYFt,
    string ReferenceDatasetVersion,
    string ReferenceManifestSha256,
    bool IsSynthetic);

public sealed record TargetRowV2(
    string TargetId,
    string RecordKind,
    string BasinName,
    string FieldName,
    string ExpectedFormationName,
    string PlannedTrajectoryProfile,
    string PlannedHoleSizeIn,
    string PlannedMdMinFt,
    string PlannedMdMaxFt,
    string CoordinateFrameId,
    string LocationSemantics,
    string CoordinateUnits,
    string SurfaceXFt,
    string SurfaceYFt,
    string ReferenceDatasetVersion,
    string ReferenceManifestSha256,
    bool IsSynthetic,
    string? PlannedBitType,
    string? PlannedBhaType,
    string? PlannedMudType);

public sealed record RunTupleRow(
    string? BitType,
    string? BhaType,
    string? MudType,
    string? MudWeightPpg,
    string? MudFunnelViscositySec,
    int AcceptedRunCount,
    string? AcceptedFootageFt,
    string? AcceptedDurationHours);

public sealed record RunConfigContextRow(
    IReadOnlyList<RunTupleRow> RunTuples);

public sealed record EventByTypeRow(
    string EventType,
    int EventCount,
    string EventDurationHours);

public sealed record EventBySubtypeRow(
    string EventType,
    string EventSubtype,
    int EventCount,
    string EventDurationHours);

public sealed record EventContextRow(
    int TotalEventCount,
    string TotalEventDurationHours,
    IReadOnlyList<EventByTypeRow> ByType,
    IReadOnlyList<EventBySubtypeRow> BySubtype);

public sealed record MatchingSectionRow(
    string SectionId,
    string? FormationName,
    string? HoleSizeIn,
    string? StartMdFt,
    string? EndMdFt,
    string? TrajectoryProfile);

public sealed record MetricsRow(
    int MatchingSectionCount,
    int AcceptedRunCount,
    string? AcceptedFootageFt,
    string? AcceptedDurationHours,
    string? AverageFootagePerRunFt,
    string? SummaryPenetrationRateFtPerHour,
    int QuarantinedRunCount,
    int WarningRunCount,
    int WarningSectionCount,
    int WarningIssueCount,
    string Scope,
    IReadOnlyList<string> UnavailableReasons);

public sealed record ExclusionRow(
    string WellId,
    IReadOnlyList<string> Reasons);

public sealed record SourceEnvelope(
    string View,
    IReadOnlyList<string> Columns,
    IReadOnlyList<string>? Measures = null);

public sealed class EvidenceEnvelope
{
    public required string ReceiptId { get; init; }

    public required string RequestId { get; init; }

    public required string ToolCallId { get; init; }

    public required string ResultId { get; init; }

    public required IReadOnlyList<SourceEnvelope> Sources { get; init; }

    public required string Grain { get; init; }

    public required object Units { get; init; }

    public required object Denominators { get; init; }

    public required IReadOnlyList<string> QualityCaveats { get; init; }

    public required string Completion { get; init; }

    public static EvidenceEnvelope Create(
        IReadOnlyList<SourceEnvelope> sources)
    {
        static string Identifier(string prefix) =>
            $"{prefix}_{Guid.NewGuid():N}";

        return new EvidenceEnvelope
        {
            ReceiptId = Identifier("receipt"),
            RequestId = Identifier("request"),
            ToolCallId = Identifier("toolcall"),
            ResultId = Identifier("result"),
            Sources = sources,
            Grain = "RELEASE_TARGET_WELL_MATCHING_SECTIONS",
            Units = new
            {
                distanceSquaredFt2 = "ft^2",
                distanceFt = "ft",
                acceptedFootageFt = "ft",
                acceptedDurationHours = "hours",
                averageFootagePerRunFt = "ft/run",
                summaryPenetrationRateFtPerHour = "ft/hour",
                counts = "entities_at_named_grain",
            },
            Denominators = new
            {
                averageFootagePerRunFt = "acceptedRunCount",
                summaryPenetrationRateFtPerHour = "acceptedDurationHours",
            },
            QualityCaveats =
            [
                "Fictional surface proximity only; PASS/WARNING accepted; ERROR excluded.",
            ],
            Completion = "VALIDATED_AUTHENTICATED_RESULT",
        };
    }
}
