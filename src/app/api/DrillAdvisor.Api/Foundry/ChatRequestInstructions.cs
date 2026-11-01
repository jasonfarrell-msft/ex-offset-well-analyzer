using DrillAdvisor.Api.Offset;

namespace DrillAdvisor.Api.Foundry;

internal static class ChatRequestInstructions
{
    internal const string HistoricalDisclosure =
        "SYNTHETIC DATA • DEVELOPMENT / HISTORICAL SUMMARY ONLY";

    private const string VersionNeutralOffsetDisclosure =
        "SYNTHETIC DATA • DEVELOPMENT / OFFSET COMPARISON ONLY";

    internal static string HistoricalSummary() =>
        """
        Reply requirements (must follow exactly):
        1) First line must be exactly: SYNTHETIC DATA • DEVELOPMENT / HISTORICAL SUMMARY ONLY
        2) If release cannot be validated from returned data, report release as null/unknown and say why.
        3) For any "total accepted runs" answer, count accepted-only runs from curated source rows using COUNT(DISTINCT run_id) at the requested scope after applying required filters.
        4) Never derive accepted run totals from pre-aggregated mud/event/section slices or target-expanded cross-target joins because those can double-count.
        5) If tool output is truncated, incomplete, or cannot prove accepted-only DISTINCT run_id counting at the requested scope, do not infer a total; return null/unknown.
        6) Keep claims grounded strictly in returned fields.
        """;

    internal static string OffsetComparison(OffsetContractSpec? contract)
    {
        var disclosure = contract?.Disclosure ?? VersionNeutralOffsetDisclosure;
        return
            $$"""
            Reply requirements (must follow exactly):
            1) First line must be exactly: {{disclosure}}
            2) Use only trusted server-provided offset context and tool-returned values.
            3) If release/version fields are unavailable in tool output, say they are unknown instead of inferring.
            """;
    }
}
