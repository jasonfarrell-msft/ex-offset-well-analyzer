using System.Net;
using System.Text;
using System.Text.Json;
using DrillAdvisor.Api.Fabric;
using DrillAdvisor.Api.Foundry;
using DrillAdvisor.Api.Offset;
using DrillAdvisor.Api.Models;

namespace DrillAdvisor.Web.Tests;

internal sealed class StubFoundryClient : IFoundryClient
{
    private static readonly JsonElement Visual = JsonSerializer.Deserialize<JsonElement>(
        """{"type":"bar","title":"Run comparison","data":[{"label":"A","value":12}]}""");

    public int CallCount { get; private set; }

    public string? LastMessage { get; private set; }

    public string? LastConversationId { get; private set; }

    public string? LastAdditionalInstructions { get; private set; }

    public Task<FoundryReply> SendAsync(
        string message,
        string? conversationId,
        string? additionalInstructions,
        CancellationToken cancellationToken)
    {
        CallCount++;
        LastMessage = message;
        LastConversationId = conversationId;
        LastAdditionalInstructions = additionalInstructions;
        return Task.FromResult(
            new FoundryReply(
                conversationId ?? "resp_new_conversation",
                "msg_test",
                "**Synthetic answer**",
                new DateTimeOffset(2026, 10, 27, 12, 0, 0, TimeSpan.Zero),
                [Visual],
                [
                    new ToolCallSummary(
                        "mcp_call",
                        "tool_1",
                        "query_data",
                        "fabric-dataagent",
                        "completed",
                        null),
                ],
                [new SourceSummary("drill_runs", ["Average ROP"])],
                new UsageSummary(20, 10, 30)));
    }
}

internal sealed class StubFabricMcpRelayClient : IFabricMcpRelayClient
{
    public int CallCount { get; private set; }

    public List<string> Methods { get; } = [];

    public Task<HttpResponseMessage> ForwardAsync(
        HttpRequest request,
        CancellationToken cancellationToken)
    {
        CallCount++;
        Methods.Add(request.Method);
        return Task.FromResult(
            new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(
                    """{"jsonrpc":"2.0","result":{}}""",
                    Encoding.UTF8,
                    "application/json"),
            });
    }
}

internal sealed class CapturingHttpMessageHandler : HttpMessageHandler
{
    public Uri? RequestUri { get; private set; }

    public string? AuthorizationParameter { get; private set; }

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        RequestUri = request.RequestUri;
        AuthorizationParameter = request.Headers.Authorization?.Parameter;
        return Task.FromResult(new HttpResponseMessage(HttpStatusCode.Accepted));
    }
}

internal sealed class StubOffsetAnalysisDataSource : IOffsetAnalysisDataSource
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
                null,
                null,
                null),
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
                "SYN-WELL-0025",
                "Fictional Atlas Well 0025",
                "Synthetic North Basin",
                "Fictional Aurora Field",
                "SYN-LOCAL-FT-V1",
                "SYNTHETIC_SURFACE_WELLHEAD",
                "ft",
                "-699450",
                "-600800",
                "SYN-SEC-0025-01",
                "Synthetic Ember",
                "17.5",
                "0",
                "4200",
                "HORIZONTAL",
                2,
                "1200.0",
                "55.00",
                0,
                0,
                0,
                0),
        ];

        private static readonly IReadOnlyList<OffsetRunConfigurationRow> RunConfigurations =
        [
            new OffsetRunConfigurationRow(
                "SYN-TARGET-0001",
                "SYN-WELL-0019",
                "PDC",
                "ROTARY",
                "WBM",
                "9.8",
                "42.0",
                2,
                "2209.3",
                "71.65"),
        ];

        private static readonly IReadOnlyList<OffsetRunEventRow> RunEvents =
        [
            new OffsetRunEventRow(
                "SYN-TARGET-0001",
                "SYN-WELL-0019",
                "NPT",
                "CONNECTION",
                1,
                "1.25"),
        ];

        public Task<IReadOnlyList<TargetRow>> ReadTargetsAsync(
            OffsetContractSpec contract,
            CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            ArgumentNullException.ThrowIfNull(contract);
            return Task.FromResult(Targets);
        }

        public Task<IReadOnlyList<OffsetSectionRow>> ReadOffsetSectionsAsync(
            OffsetContractSpec contract,
            string targetId,
            CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            ArgumentNullException.ThrowIfNull(contract);
            return Task.FromResult(
                (IReadOnlyList<OffsetSectionRow>)Rows.Where(row =>
                    string.Equals(row.TargetId, targetId, StringComparison.Ordinal)).ToArray());
        }

        public Task<IReadOnlyList<OffsetRunConfigurationRow>> ReadRunConfigurationsAsync(
            OffsetContractSpec contract,
            string targetId,
            CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            ArgumentNullException.ThrowIfNull(contract);
            return Task.FromResult(
                (IReadOnlyList<OffsetRunConfigurationRow>)RunConfigurations.Where(row =>
                    string.Equals(row.TargetId, targetId, StringComparison.Ordinal)).ToArray());
        }

        public Task<IReadOnlyList<OffsetRunEventRow>> ReadRunEventsAsync(
            OffsetContractSpec contract,
            string targetId,
            CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            ArgumentNullException.ThrowIfNull(contract);
            return Task.FromResult(
                (IReadOnlyList<OffsetRunEventRow>)RunEvents.Where(row =>
                    string.Equals(row.TargetId, targetId, StringComparison.Ordinal)).ToArray());
        }
}

internal sealed class SpyOffsetAnalysisService : IOffsetAnalysisService
{
    private static readonly IReadOnlyList<OffsetChatWellSummary> DefaultSummaries =
    [
        new OffsetChatWellSummary(
            "SYN-WELL-0019",
            "30.8",
            2,
            "2209.3",
            "71.65",
            "30.834613"),
    ];

    private readonly IReadOnlyList<OffsetChatWellSummary> _summaries;

    public SpyOffsetAnalysisService(IReadOnlyList<OffsetChatWellSummary>? summaries = null)
    {
        _summaries = summaries ?? DefaultSummaries;
    }

    public int ContractOverloadCallCount { get; private set; }

    public int LegacyOverloadCallCount { get; private set; }

    public IReadOnlyList<OffsetContractSpec> Contracts => _contracts;

    private readonly List<OffsetContractSpec> _contracts = [];

    public Task<OffsetAnalysisResponse> ExecuteAsync(
        OffsetOperationRequest request,
        CancellationToken cancellationToken) =>
        throw new NotSupportedException("ExecuteAsync is not expected in chat endpoint tests.");

    public Task<IReadOnlyList<OffsetChatWellSummary>> BuildChatContextAsync(
        OffsetContractSpec contract,
        OffsetContext context,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        ArgumentNullException.ThrowIfNull(contract);
        ArgumentNullException.ThrowIfNull(context);
        ContractOverloadCallCount++;
        _contracts.Add(contract);
        return Task.FromResult(_summaries);
    }

    public Task<IReadOnlyList<OffsetChatWellSummary>> BuildChatContextAsync(
        OffsetContext context,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        ArgumentNullException.ThrowIfNull(context);
        LegacyOverloadCallCount++;
        return Task.FromResult(_summaries);
    }
}
