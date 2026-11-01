using System.Globalization;
using System.Text.Json;
using DrillAdvisor.Api.Models;

namespace DrillAdvisor.Api.Foundry;

internal static class FoundryResponseParser
{
    private static readonly string[] SourcePropertyNames =
    [
        "source",
        "source_name",
        "sourceName",
        "dataset",
        "table",
    ];

    private static readonly string[] MeasurePropertyNames =
    [
        "measure",
        "measure_name",
        "measureName",
        "measures",
    ];

    public static FoundryReply Parse(
        Stream responseStream,
        TimeProvider timeProvider)
    {
        ArgumentNullException.ThrowIfNull(responseStream);
        ArgumentNullException.ThrowIfNull(timeProvider);

        try
        {
            using var document = JsonDocument.Parse(responseStream);
            var root = document.RootElement;
            var finalMessage = FindFinalAssistantMessage(root);
            var markdown = ExtractOutputText(root, finalMessage);
            if (string.IsNullOrEmpty(markdown))
            {
                throw new FoundryResponseException(
                    "The Foundry response did not contain assistant output text.");
            }

            var resolvedConversationId = TryGetString(root, "id")
                ?? throw new FoundryResponseException(
                    "The Foundry response did not contain a continuation ID.");
            var parsedVisuals = VisualBlockParser.Parse(markdown);
            return new FoundryReply(
                resolvedConversationId,
                ExtractMessageId(root, finalMessage),
                parsedVisuals.Markdown,
                ExtractCreatedAt(root, timeProvider),
                parsedVisuals.Visuals,
                ExtractToolCalls(root),
                ExtractSources(root),
                ExtractUsage(root));
        }
        catch (JsonException exception)
        {
            throw new FoundryResponseException(
                "The Foundry response was not valid JSON.",
                exception);
        }
    }

    private static JsonElement? FindFinalAssistantMessage(JsonElement root)
    {
        JsonElement? finalMessage = null;
        if (!root.TryGetProperty("output", out var output)
            || output.ValueKind != JsonValueKind.Array)
        {
            return finalMessage;
        }

        foreach (var item in output.EnumerateArray())
        {
            if (HasStringValue(item, "type", "message")
                && HasStringValue(item, "role", "assistant"))
            {
                finalMessage = item;
            }
        }

        return finalMessage;
    }

    private static string ExtractOutputText(
        JsonElement root,
        JsonElement? finalMessage)
    {
        if (finalMessage is { } message
            && message.TryGetProperty("content", out var content)
            && content.ValueKind == JsonValueKind.Array)
        {
            var textParts = content
                .EnumerateArray()
                .Where(item => HasStringValue(item, "type", "output_text"))
                .Select(item => TryGetString(item, "text"))
                .Where(text => text is not null);
            var text = string.Concat(textParts);
            if (text.Length > 0)
            {
                return text;
            }
        }

        return TryGetString(root, "output_text") ?? string.Empty;
    }

    private static string ExtractMessageId(
        JsonElement root,
        JsonElement? finalMessage) =>
        finalMessage is { } message
            ? TryGetString(message, "id")
                ?? TryGetString(root, "id")
                ?? Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture)
            : TryGetString(root, "id")
                ?? Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture);

    private static DateTimeOffset ExtractCreatedAt(
        JsonElement root,
        TimeProvider timeProvider)
    {
        if (root.TryGetProperty("created_at", out var createdAt))
        {
            if (createdAt.ValueKind == JsonValueKind.Number
                && createdAt.TryGetInt64(out var unixSeconds))
            {
                return DateTimeOffset.FromUnixTimeSeconds(unixSeconds);
            }

            if (createdAt.ValueKind == JsonValueKind.String
                && DateTimeOffset.TryParse(
                    createdAt.GetString(),
                    CultureInfo.InvariantCulture,
                    DateTimeStyles.AssumeUniversal,
                    out var timestamp))
            {
                return timestamp.ToUniversalTime();
            }
        }

        return timeProvider.GetUtcNow();
    }

    private static IReadOnlyList<ToolCallSummary> ExtractToolCalls(JsonElement root)
    {
        if (!root.TryGetProperty("output", out var output)
            || output.ValueKind != JsonValueKind.Array)
        {
            return Array.Empty<ToolCallSummary>();
        }

        var toolCalls = new List<ToolCallSummary>();
        foreach (var item in output.EnumerateArray())
        {
            var type = TryGetString(item, "type");
            if (type is not ("mcp_list_tools" or "mcp_call"))
            {
                continue;
            }

            int? toolCount = null;
            if (type == "mcp_list_tools"
                && item.TryGetProperty("tools", out var tools)
                && tools.ValueKind == JsonValueKind.Array)
            {
                toolCount = tools.GetArrayLength();
            }

            toolCalls.Add(
                new ToolCallSummary(
                    type,
                    TryGetString(item, "id"),
                    TryGetString(item, "name"),
                    TryGetString(item, "server_label")
                        ?? TryGetString(item, "server"),
                    TryGetString(item, "status"),
                    toolCount));
        }

        return toolCalls;
    }

    private static SourceSummary[] ExtractSources(JsonElement root)
    {
        var sources = new Dictionary<string, SourceAccumulator>(
            StringComparer.OrdinalIgnoreCase);

        if (root.TryGetProperty("sources", out var topLevelSources))
        {
            VisitSourceMetadata(topLevelSources, sources, null);
        }

        if (root.TryGetProperty("output", out var output)
            && output.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in output.EnumerateArray())
            {
                var type = TryGetString(item, "type");
                if (type == "message"
                    && item.TryGetProperty("content", out var content)
                    && content.ValueKind == JsonValueKind.Array)
                {
                    foreach (var contentItem in content.EnumerateArray())
                    {
                        if (contentItem.TryGetProperty("annotations", out var annotations))
                        {
                            VisitSourceMetadata(annotations, sources, null);
                        }
                    }
                }
                else if (type == "mcp_call"
                    && item.TryGetProperty("output", out var toolOutput))
                {
                    VisitToolOutput(toolOutput, sources);
                }
            }
        }

        return sources.Values
            .Select(
                source => new SourceSummary(
                    source.Name,
                    source.Measures.Order(StringComparer.Ordinal).ToArray()))
            .OrderBy(source => source.Name, StringComparer.OrdinalIgnoreCase)
            .ToArray();
    }

    private static void VisitToolOutput(
        JsonElement toolOutput,
        IDictionary<string, SourceAccumulator> sources)
    {
        if (toolOutput.ValueKind == JsonValueKind.String)
        {
            var outputText = toolOutput.GetString();
            if (string.IsNullOrWhiteSpace(outputText)
                || outputText.Length > 1_000_000)
            {
                return;
            }

            try
            {
                using var outputDocument = JsonDocument.Parse(outputText);
                VisitSourceMetadata(outputDocument.RootElement, sources, null);
            }
            catch (JsonException)
            {
                // Plain-text tool output is intentionally not returned or inspected.
            }

            return;
        }

        VisitSourceMetadata(toolOutput, sources, null);
    }

    private static void VisitSourceMetadata(
        JsonElement element,
        IDictionary<string, SourceAccumulator> sources,
        string? inheritedSource)
    {
        if (element.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in element.EnumerateArray())
            {
                VisitSourceMetadata(item, sources, inheritedSource);
            }

            return;
        }

        if (element.ValueKind != JsonValueKind.Object)
        {
            return;
        }

        var sourceName = GetFirstString(element, SourcePropertyNames)
            ?? inheritedSource;
        var measures = GetStrings(element, MeasurePropertyNames);
        if (sourceName is not null || measures.Length > 0)
        {
            var key = sourceName ?? string.Empty;
            if (!sources.TryGetValue(key, out var source))
            {
                source = new SourceAccumulator(sourceName);
                sources.Add(key, source);
            }

            foreach (var measure in measures)
            {
                source.Measures.Add(measure);
            }
        }

        foreach (var property in element.EnumerateObject())
        {
            if (property.Value.ValueKind is JsonValueKind.Object or JsonValueKind.Array)
            {
                VisitSourceMetadata(property.Value, sources, sourceName);
            }
        }
    }

    private static UsageSummary? ExtractUsage(JsonElement root)
    {
        if (!root.TryGetProperty("usage", out var usage)
            || usage.ValueKind != JsonValueKind.Object)
        {
            return null;
        }

        return new UsageSummary(
            TryGetInt32(usage, "input_tokens"),
            TryGetInt32(usage, "output_tokens"),
            TryGetInt32(usage, "total_tokens"));
    }

    private static bool HasStringValue(
        JsonElement element,
        string propertyName,
        string expected) =>
        string.Equals(
            TryGetString(element, propertyName),
            expected,
            StringComparison.Ordinal);

    private static string? TryGetString(
        JsonElement element,
        string propertyName) =>
        element.ValueKind == JsonValueKind.Object
        && element.TryGetProperty(propertyName, out var property)
        && property.ValueKind == JsonValueKind.String
            ? property.GetString()
            : null;

    private static int? TryGetInt32(
        JsonElement element,
        string propertyName) =>
        element.TryGetProperty(propertyName, out var property)
        && property.ValueKind == JsonValueKind.Number
        && property.TryGetInt32(out var value)
            ? value
            : null;

    private static string? GetFirstString(
        JsonElement element,
        IEnumerable<string> propertyNames)
    {
        foreach (var propertyName in propertyNames)
        {
            var value = TryGetString(element, propertyName);
            if (!string.IsNullOrWhiteSpace(value))
            {
                return value;
            }
        }

        return null;
    }

    private static string[] GetStrings(
        JsonElement element,
        IEnumerable<string> propertyNames)
    {
        var values = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var propertyName in propertyNames)
        {
            if (!element.TryGetProperty(propertyName, out var property))
            {
                continue;
            }

            if (property.ValueKind == JsonValueKind.String
                && !string.IsNullOrWhiteSpace(property.GetString()))
            {
                values.Add(property.GetString()!);
            }
            else if (property.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in property.EnumerateArray())
                {
                    if (item.ValueKind == JsonValueKind.String
                        && !string.IsNullOrWhiteSpace(item.GetString()))
                    {
                        values.Add(item.GetString()!);
                    }
                }
            }
        }

        return values.ToArray();
    }

    private sealed class SourceAccumulator(string? name)
    {
        public string? Name { get; } = name;

        public HashSet<string> Measures { get; } =
            new(StringComparer.OrdinalIgnoreCase);
    }
}
