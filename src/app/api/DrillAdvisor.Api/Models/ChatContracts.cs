using System.Text.Json;
using System.Text.Json.Serialization;

namespace DrillAdvisor.Api.Models;

/// <summary>
/// Represents a Drill Advisor chat request.
/// </summary>
public sealed record ChatRequest(
    [property: JsonPropertyName("message")] string? Message,
    [property: JsonPropertyName("conversationId")] string? ConversationId);

/// <summary>
/// Represents the stable Drill Advisor chat response.
/// </summary>
public sealed record ChatResponse(
    [property: JsonPropertyName("conversationId")] string ConversationId,
    [property: JsonPropertyName("message")] AssistantMessage Message,
    [property: JsonPropertyName("visuals")] IReadOnlyList<JsonElement> Visuals,
    [property: JsonPropertyName("toolCalls")] IReadOnlyList<ToolCallSummary> ToolCalls,
    [property: JsonPropertyName("sources")] IReadOnlyList<SourceSummary> Sources,
    [property: JsonPropertyName("usage")] UsageSummary? Usage,
    [property: JsonPropertyName("latencyMs")] long LatencyMs);

/// <summary>
/// Represents the final assistant message returned by Drill Advisor.
/// </summary>
public sealed record AssistantMessage(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("role")] string Role,
    [property: JsonPropertyName("markdown")] string Markdown,
    [property: JsonPropertyName("createdAtUtc")] DateTimeOffset CreatedAtUtc);

/// <summary>
/// Represents a safe summary of a Foundry MCP list or call record.
/// </summary>
public sealed record ToolCallSummary(
    [property: JsonPropertyName("type")] string Type,
    [property: JsonPropertyName("id")] string? Id,
    [property: JsonPropertyName("name")] string? Name,
    [property: JsonPropertyName("server")] string? Server,
    [property: JsonPropertyName("status")] string? Status,
    [property: JsonPropertyName("toolCount")] int? ToolCount);

/// <summary>
/// Represents source and semantic-measure metadata reported by Foundry or Fabric IQ.
/// </summary>
public sealed record SourceSummary(
    [property: JsonPropertyName("name")] string? Name,
    [property: JsonPropertyName("measures")] IReadOnlyList<string> Measures);

/// <summary>
/// Represents token usage reported by the Foundry Responses API.
/// </summary>
public sealed record UsageSummary(
    [property: JsonPropertyName("inputTokens")] int? InputTokens,
    [property: JsonPropertyName("outputTokens")] int? OutputTokens,
    [property: JsonPropertyName("totalTokens")] int? TotalTokens);
