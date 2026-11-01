using System.Text.Json;

namespace DrillAdvisor.Api.Models;

/// <summary>
/// Represents the safe, parsed subset of a Foundry response used by the API.
/// </summary>
public sealed record FoundryReply(
    string ConversationId,
    string MessageId,
    string Markdown,
    DateTimeOffset CreatedAtUtc,
    IReadOnlyList<JsonElement> Visuals,
    IReadOnlyList<ToolCallSummary> ToolCalls,
    IReadOnlyList<SourceSummary> Sources,
    UsageSummary? Usage);
