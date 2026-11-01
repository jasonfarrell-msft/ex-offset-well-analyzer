using System.Data.SqlClient;
using System.Runtime.CompilerServices;
using DrillAdvisor.Api.Offset;
using Microsoft.AspNetCore.Http;

namespace DrillAdvisor.Api.Tests;

public sealed class OffsetAnalysisServiceTests
{
    [Fact]
    public async Task Candidates_UsesOracleParityValues_ForKnownRows()
    {
        var service = new OffsetAnalysisService(
            new StubOffsetDataSource(),
            TimeProvider.System);
        var request = new OffsetOperationRequest(
            "candidates",
            OffsetContractVersions.V1.ContractVersion,
            OffsetContractVersions.V1.ReleaseId,
            OffsetContractVersions.V1,
            new OffsetContext(
                "SYN-TARGET-0001",
                new OffsetCriteria("10000", true, true, false),
                [],
                0),
            null,
            null);

        var response = await service.ExecuteAsync(request, CancellationToken.None);

        Assert.Equal(StatusCodes.Status200OK, response.StatusCode);
        var body = Assert.IsType<AnalyticalEnvelope<CandidateRow>>(response.Body);
        Assert.Equal("success", body.Status);
        Assert.Equal(2, body.TotalCount);
        Assert.Equal("SYN-WELL-0019", body.Rows[0].WellId);
        Assert.Equal("14210", body.Rows[0].DistanceSquaredFt2);
        Assert.Equal("119.2", body.Rows[0].DistanceFt);
        Assert.Equal("30.834613", body.Rows[0].Metrics.SummaryPenetrationRateFtPerHour);
        Assert.Equal("SYN-WELL-0099", body.Rows[1].WellId);
        Assert.Equal("1265960", body.Rows[1].DistanceSquaredFt2);
        Assert.Equal("1125.1", body.Rows[1].DistanceFt);
        Assert.Equal("38.142451", body.Rows[1].Metrics.SummaryPenetrationRateFtPerHour);
    }

    [Fact]
    public async Task Compare_RequiresEligibleSelection()
    {
        var service = new OffsetAnalysisService(
            new StubOffsetDataSource(),
            TimeProvider.System);
        var request = new OffsetOperationRequest(
            "compare",
            OffsetContractVersions.V1.ContractVersion,
            OffsetContractVersions.V1.ReleaseId,
            OffsetContractVersions.V1,
            new OffsetContext(
                "SYN-TARGET-0001",
                new OffsetCriteria("10000", true, true, false),
                ["SYN-WELL-0100"],
                1),
            null,
            null);

        var response = await service.ExecuteAsync(request, CancellationToken.None);

        Assert.Equal(StatusCodes.Status503ServiceUnavailable, response.StatusCode);
        var body = Assert.IsType<FailureEnvelope>(response.Body);
        Assert.Equal("CONTEXT_MISMATCH", body.Error.Code);
    }

    [Fact]
    public async Task BuildChatContext_RequiresEligibleSelection()
    {
        var service = new OffsetAnalysisService(
            new StubOffsetDataSource(),
            TimeProvider.System);
        var context = new OffsetContext(
            "SYN-TARGET-0001",
            new OffsetCriteria("10000", true, true, false),
            ["SYN-WELL-0100"],
            2);

        var exception = await Assert.ThrowsAsync<OffsetChatContextException>(() =>
            service.BuildChatContextAsync(context, CancellationToken.None));

        Assert.Equal(StatusCodes.Status409Conflict, exception.StatusCode);
        Assert.Equal("offset_context_stale", exception.Code);
    }

    [Fact]
    public async Task BuildChatContext_RequiresSelection()
    {
        var service = new OffsetAnalysisService(
            new StubOffsetDataSource(),
            TimeProvider.System);
        var context = new OffsetContext(
            "SYN-TARGET-0001",
            new OffsetCriteria("10000", true, true, false),
            [],
            2);

        var exception = await Assert.ThrowsAsync<OffsetChatContextException>(() =>
            service.BuildChatContextAsync(context, CancellationToken.None));

        Assert.Equal(StatusCodes.Status400BadRequest, exception.StatusCode);
        Assert.Equal("invalid_request", exception.Code);
    }

    [Fact]
    public async Task Candidates_Radius_DefaultZeroAndBoundary_MatchOracleDistances()
    {
        var service = new OffsetAnalysisService(
            new StubOffsetDataSource(),
            TimeProvider.System);

        static OffsetOperationRequest BuildRequest(string radiusFt) =>
            new(
                "candidates",
                OffsetContractVersions.V1.ContractVersion,
                OffsetContractVersions.V1.ReleaseId,
                OffsetContractVersions.V1,
                new OffsetContext(
                    "SYN-TARGET-0001",
                    new OffsetCriteria(radiusFt, true, true, false),
                    [],
                    0),
                null,
                null);

        var defaultRadius = await service.ExecuteAsync(BuildRequest("10000"), CancellationToken.None);
        var defaultBody = Assert.IsType<AnalyticalEnvelope<CandidateRow>>(defaultRadius.Body);
        Assert.Equal(StatusCodes.Status200OK, defaultRadius.StatusCode);
        Assert.Equal(["SYN-WELL-0019", "SYN-WELL-0099"], defaultBody.Rows.Select(row => row.WellId).ToArray());
        Assert.Equal(["14210", "1265960"], defaultBody.Rows.Select(row => row.DistanceSquaredFt2).ToArray());

        var zeroRadius = await service.ExecuteAsync(BuildRequest("0"), CancellationToken.None);
        var zeroBody = Assert.IsType<AnalyticalEnvelope<CandidateRow>>(zeroRadius.Body);
        Assert.Equal(StatusCodes.Status200OK, zeroRadius.StatusCode);
        Assert.Empty(zeroBody.Rows);
        Assert.Contains(
            zeroBody.Exclusions,
            exclusion => exclusion.WellId == "SYN-WELL-0019"
                && exclusion.Reasons.Contains("OUTSIDE_RADIUS", StringComparer.Ordinal));

        var justInsideBoundary = await service.ExecuteAsync(BuildRequest("119.21"), CancellationToken.None);
        var boundaryBody = Assert.IsType<AnalyticalEnvelope<CandidateRow>>(justInsideBoundary.Body);
        Assert.Equal(StatusCodes.Status200OK, justInsideBoundary.StatusCode);
        Assert.Equal(["SYN-WELL-0019"], boundaryBody.Rows.Select(row => row.WellId).ToArray());
        Assert.Equal("14210", boundaryBody.Rows[0].DistanceSquaredFt2);
    }

    [Fact]
    public async Task Compare_V2_ContainsPlannedIntent_RunConfiguration_AndEventContext()
    {
        var service = new OffsetAnalysisService(
            new StubOffsetDataSource(),
            TimeProvider.System);
        var request = new OffsetOperationRequest(
            "compare",
            OffsetContractVersions.V2.ContractVersion,
            OffsetContractVersions.V2.ReleaseId,
            OffsetContractVersions.V2,
            new OffsetContext(
                "SYN-TARGET-0001",
                new OffsetCriteria("10000", true, true, false),
                ["SYN-WELL-0019"],
                1),
            null,
            null);

        var response = await service.ExecuteAsync(request, CancellationToken.None);

        Assert.Equal(StatusCodes.Status200OK, response.StatusCode);
        var body = Assert.IsType<AnalyticalEnvelope<ComparisonRowV2>>(response.Body);
        Assert.Equal("offset-well-analysis-v2", body.ContractVersion);
        Assert.Equal("v1.2.0", body.DatasetVersion);
        var row = Assert.Single(body.Rows);
        Assert.Equal("PDC", row.PlannedBitType);
        Assert.Equal("RSS", row.PlannedBhaType);
        Assert.Equal("WATER_BASED_SYNTHETIC", row.PlannedMudType);

        var runConfig = Assert.IsType<RunConfigContextRow>(row.RunConfigContext);
        var tuple = Assert.Single(runConfig.RunTuples);
        Assert.Equal("PDC", tuple.BitType);
        Assert.Equal("RSS", tuple.BhaType);
        Assert.Equal("WATER_BASED_SYNTHETIC", tuple.MudType);
        Assert.Equal("10.4", tuple.MudWeightPpg);
        Assert.Equal("41", tuple.MudFunnelViscositySec);
        Assert.Equal(2, tuple.AcceptedRunCount);

        var eventContext = Assert.IsType<EventContextRow>(row.EventContext);
        Assert.Equal(5, eventContext.TotalEventCount);
        Assert.Equal("6.2", eventContext.TotalEventDurationHours);
        Assert.Equal(
            ["LOSSES", "VIBRATION"],
            eventContext.ByType.Select(value => value.EventType).ToArray());
    }

    [Fact]
    public void TargetQuery_V2ReadsPlannedFieldsFromPinnedV12Schema()
    {
        Assert.Equal("v1.2.0", OffsetContractVersions.V2.DatasetVersion);
        var commandText = SqlOffsetAnalysisDataSource.BuildTargetsCommandText(
            OffsetContractVersions.V2,
            includePlannedFields: true);

        Assert.Contains("planned_bit_type,", commandText, StringComparison.Ordinal);
        Assert.Contains("planned_bha_type,", commandText, StringComparison.Ordinal);
        Assert.Contains("planned_mud_type", commandText, StringComparison.Ordinal);
        Assert.Contains("FROM serving.planned_target_summary_release", commandText, StringComparison.Ordinal);
        Assert.DoesNotContain("CAST(NULL", commandText, StringComparison.Ordinal);
    }

    [Fact]
    public void TargetQuery_V1DoesNotRequireV2PlannedColumns()
    {
        var commandText = SqlOffsetAnalysisDataSource.BuildTargetsCommandText(
            OffsetContractVersions.V1,
            includePlannedFields: false);

        Assert.Contains("CAST(NULL AS NVARCHAR(64)) AS planned_bit_type", commandText, StringComparison.Ordinal);
        Assert.Contains("FROM serving.planned_target_summary_release", commandText, StringComparison.Ordinal);
        Assert.DoesNotContain(
            "planned_bit_type,\n    planned_bha_type,\n    planned_mud_type",
            commandText,
            StringComparison.Ordinal);
    }

    [Fact]
    public void V2ReleaseQueriesUseReadyReleaseViews()
    {
        Assert.Equal(
            "serving.planned_target_summary_release",
            SqlOffsetAnalysisDataSource.ResolvePlannedTargetSummaryView(OffsetContractVersions.V2));
        Assert.Equal(
            "serving.offset_section_summary_release",
            SqlOffsetAnalysisDataSource.ResolveOffsetSectionSummaryView(OffsetContractVersions.V2));
        Assert.Equal(
            "serving.offset_run_config_summary_release",
            SqlOffsetAnalysisDataSource.ResolveOffsetRunConfigSummaryView(OffsetContractVersions.V2));
        Assert.Equal(
            "serving.offset_run_event_summary_release",
            SqlOffsetAnalysisDataSource.ResolveOffsetRunEventSummaryView(OffsetContractVersions.V2));
    }

    [Fact]
    public void V1ReleaseQueriesAlsoUseReadyReleaseViews()
    {
        Assert.Equal(
            "serving.planned_target_summary_release",
            SqlOffsetAnalysisDataSource.ResolvePlannedTargetSummaryView(OffsetContractVersions.V1));
        Assert.Equal(
            "serving.offset_section_summary_release",
            SqlOffsetAnalysisDataSource.ResolveOffsetSectionSummaryView(OffsetContractVersions.V1));
        Assert.Equal(
            "serving.offset_run_config_summary_release",
            SqlOffsetAnalysisDataSource.ResolveOffsetRunConfigSummaryView(OffsetContractVersions.V1));
        Assert.Equal(
            "serving.offset_run_event_summary_release",
            SqlOffsetAnalysisDataSource.ResolveOffsetRunEventSummaryView(OffsetContractVersions.V1));
    }

    [Fact]
    public async Task ExecuteAsync_V2PropagatesSqlFaultAsUpstreamUnavailable()
    {
        var sqlException = (SqlException)RuntimeHelpers.GetUninitializedObject(typeof(SqlException));
        var service = new OffsetAnalysisService(
            new SqlFaultOffsetDataSource(sqlException),
            TimeProvider.System);
        var request = new OffsetOperationRequest(
            "candidates",
            OffsetContractVersions.V2.ContractVersion,
            OffsetContractVersions.V2.ReleaseId,
            OffsetContractVersions.V2,
            new OffsetContext(
                "SYN-TARGET-0001",
                new OffsetCriteria("10000", true, true, false),
                [],
                0),
            null,
            null);

        var response = await service.ExecuteAsync(request, CancellationToken.None);

        Assert.Equal(StatusCodes.Status503ServiceUnavailable, response.StatusCode);
        var body = Assert.IsType<FailureEnvelope>(response.Body);
        Assert.Equal("UPSTREAM_UNAVAILABLE", body.Error.Code);
    }

    [Fact]
    public async Task Candidates_V1_DoesNotExposeV2ContextShapes()
    {
        var service = new OffsetAnalysisService(
            new StubOffsetDataSource(),
            TimeProvider.System);
        var request = new OffsetOperationRequest(
            "candidates",
            OffsetContractVersions.V1.ContractVersion,
            OffsetContractVersions.V1.ReleaseId,
            OffsetContractVersions.V1,
            new OffsetContext(
                "SYN-TARGET-0001",
                new OffsetCriteria("10000", true, true, false),
                [],
                0),
            null,
            null);

        var response = await service.ExecuteAsync(request, CancellationToken.None);

        var body = Assert.IsType<AnalyticalEnvelope<CandidateRow>>(response.Body);
        Assert.All(
            body.Rows,
            row => Assert.Null(
                row.GetType().GetProperty("RunConfigContext")));
        Assert.All(
            body.Rows,
            row => Assert.Null(
                row.GetType().GetProperty("EventContext")));
    }

    private sealed class StubOffsetDataSource : IOffsetAnalysisDataSource
    {
        private static readonly IReadOnlyList<TargetRow> Targets =
        [
            new TargetRow(
                "SYN-TARGET-0001",
                "PLANNED_TARGET",
                "Synthetic North Basin",
                "Fictional Aurora Field",
                "Synthetic Brimstone",
                "BUILD_AND_HOLD",
                "17.5",
                "7250",
                "13000",
                "SYN-LOCAL-FT-V1",
                "SYNTHETIC_SURFACE_WELLHEAD",
                "ft",
                "-699419",
                "-600579",
                "v1.0.0",
                "f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9",
                true,
                "PDC",
                "RSS",
                "WATER_BASED_SYNTHETIC"),
        ];

        private static readonly IReadOnlyList<OffsetSectionRow> Rows =
        [
            new OffsetSectionRow(
                "SYN-TARGET-0001",
                "SYN-WELL-0019",
                "Fictional Atlas Well 0019",
                "Synthetic North Basin",
                "Fictional Aurora Field",
                "SYN-LOCAL-FT-V1",
                "SYNTHETIC_SURFACE_WELLHEAD",
                "ft",
                "-699300",
                "-600572",
                "SYN-SEC-0019-01",
                "Synthetic Brimstone",
                "17.5",
                "0",
                "4087.6",
                "VERTICAL",
                2,
                "2209.3",
                "71.65",
                0,
                0,
                0,
                0),
            new OffsetSectionRow(
                "SYN-TARGET-0001",
                "SYN-WELL-0099",
                "Fictional Atlas Well 0099",
                "Synthetic North Basin",
                "Fictional Aurora Field",
                "SYN-LOCAL-FT-V1",
                "SYNTHETIC_SURFACE_WELLHEAD",
                "ft",
                "-699261",
                "-599465",
                "SYN-SEC-0099-01",
                "Synthetic Brimstone",
                "17.5",
                "0",
                "4100",
                "VERTICAL",
                2,
                "1611.9",
                "42.26",
                0,
                1,
                0,
                1),
            new OffsetSectionRow(
                "SYN-TARGET-0001",
                "SYN-WELL-0100",
                "Fictional Atlas Well 0100",
                "Synthetic North Basin",
                "Fictional Aurora Field",
                "SYN-LOCAL-FT-V1",
                "SYNTHETIC_SURFACE_WELLHEAD",
                "ft",
                "-680000",
                "-500000",
                "SYN-SEC-0100-01",
                "Synthetic Ember",
                "17.5",
                "0",
                "4100",
                "VERTICAL",
                1,
                "100.0",
                "10.00",
                0,
                0,
                0,
                0),
        ];

        private static readonly IReadOnlyList<OffsetRunConfigurationRow> RunConfigurations =
        [
            new(
                "SYN-TARGET-0001",
                "SYN-WELL-0019",
                "PDC",
                "RSS",
                "WATER_BASED_SYNTHETIC",
                "10.4",
                "41",
                2,
                "2209.3",
                "71.65"),
        ];

        private static readonly IReadOnlyList<OffsetRunEventRow> RunEvents =
        [
            new("SYN-TARGET-0001", "SYN-WELL-0019", "LOSSES", "SEEPAGE", 2, "1.2"),
            new("SYN-TARGET-0001", "SYN-WELL-0019", "VIBRATION", "TORSIONAL", 3, "5.0"),
        ];

        public Task<IReadOnlyList<TargetRow>> ReadTargetsAsync(
            OffsetContractSpec contract,
            CancellationToken cancellationToken) =>
            Task.FromResult(Targets);

        public Task<IReadOnlyList<OffsetSectionRow>> ReadOffsetSectionsAsync(
            OffsetContractSpec contract,
            string targetId,
            CancellationToken cancellationToken) =>
            Task.FromResult(
                (IReadOnlyList<OffsetSectionRow>)Rows.Where(row =>
                    string.Equals(row.TargetId, targetId, StringComparison.Ordinal)).ToArray());

        public Task<IReadOnlyList<OffsetRunConfigurationRow>> ReadRunConfigurationsAsync(
            OffsetContractSpec contract,
            string targetId,
            CancellationToken cancellationToken) =>
            Task.FromResult(
                (IReadOnlyList<OffsetRunConfigurationRow>)RunConfigurations.Where(row =>
                    string.Equals(row.TargetId, targetId, StringComparison.Ordinal)).ToArray());

        public Task<IReadOnlyList<OffsetRunEventRow>> ReadRunEventsAsync(
            OffsetContractSpec contract,
            string targetId,
            CancellationToken cancellationToken) =>
            Task.FromResult(
                (IReadOnlyList<OffsetRunEventRow>)RunEvents.Where(row =>
                    string.Equals(row.TargetId, targetId, StringComparison.Ordinal)).ToArray());
    }

    private sealed class SqlFaultOffsetDataSource(SqlException exception) : IOffsetAnalysisDataSource
    {
        public Task<IReadOnlyList<TargetRow>> ReadTargetsAsync(
            OffsetContractSpec contract,
            CancellationToken cancellationToken) =>
            Task.FromException<IReadOnlyList<TargetRow>>(exception);

        public Task<IReadOnlyList<OffsetSectionRow>> ReadOffsetSectionsAsync(
            OffsetContractSpec contract,
            string targetId,
            CancellationToken cancellationToken) =>
            Task.FromResult<IReadOnlyList<OffsetSectionRow>>([]);

        public Task<IReadOnlyList<OffsetRunConfigurationRow>> ReadRunConfigurationsAsync(
            OffsetContractSpec contract,
            string targetId,
            CancellationToken cancellationToken) =>
            Task.FromResult<IReadOnlyList<OffsetRunConfigurationRow>>([]);

        public Task<IReadOnlyList<OffsetRunEventRow>> ReadRunEventsAsync(
            OffsetContractSpec contract,
            string targetId,
            CancellationToken cancellationToken) =>
            Task.FromResult<IReadOnlyList<OffsetRunEventRow>>([]);
    }
}
