using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace DrillAdvisor.Api.Foundry;

internal static partial class VisualBlockParser
{
    public static (string Markdown, IReadOnlyList<JsonElement> Visuals) Parse(
        string markdown)
    {
        var matches = VisualBlockRegex().Matches(markdown);
        if (matches.Count == 0)
        {
            return (markdown, Array.Empty<JsonElement>());
        }

        var visuals = new List<JsonElement>(matches.Count);
        var result = new StringBuilder(markdown.Length);
        var currentIndex = 0;

        foreach (Match match in matches)
        {
            result.Append(markdown, currentIndex, match.Index - currentIndex);

            if (TryParseVisual(match.Groups["json"].Value, out var visual))
            {
                visuals.Add(visual);
            }
            else
            {
                result.Append(match.Value);
            }

            currentIndex = match.Index + match.Length;
        }

        result.Append(markdown, currentIndex, markdown.Length - currentIndex);
        return (result.ToString(), visuals);
    }

    private static bool TryParseVisual(
        string json,
        out JsonElement visual)
    {
        visual = default;
        try
        {
            using var document = JsonDocument.Parse(json);
            if (document.RootElement.ValueKind != JsonValueKind.Object
                || !document.RootElement.TryGetProperty("type", out var typeElement)
                || typeElement.ValueKind != JsonValueKind.String)
            {
                return false;
            }

            var isValid = typeElement.GetString() switch
            {
                "kpi-grid" => IsValidKpiGrid(document.RootElement),
                "bar-chart" => IsValidBarChart(document.RootElement),
                "data-table" => IsValidDataTable(document.RootElement),
                _ => false,
            };

            if (!isValid)
            {
                return false;
            }

            visual = document.RootElement.Clone();
            return true;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    private static bool IsValidKpiGrid(JsonElement visual) =>
        visual.TryGetProperty("items", out var items)
        && items.ValueKind == JsonValueKind.Array
        && items.EnumerateArray().All(
            item => item.ValueKind == JsonValueKind.Object
                && HasNonEmptyString(item, "label")
                && item.TryGetProperty("value", out var value)
                && value.ValueKind is JsonValueKind.String or JsonValueKind.Number);

    private static bool IsValidBarChart(JsonElement visual) =>
        visual.TryGetProperty("data", out var data)
        && data.ValueKind == JsonValueKind.Array
        && data.EnumerateArray().All(
            item => item.ValueKind == JsonValueKind.Object
                && HasNonEmptyString(item, "label")
                && item.TryGetProperty("value", out var value)
                && value.ValueKind == JsonValueKind.Number
                && (!item.TryGetProperty("unit", out var unit)
                    || unit.ValueKind == JsonValueKind.String));

    private static bool IsValidDataTable(JsonElement visual) =>
        visual.TryGetProperty("columns", out var columns)
        && columns.ValueKind == JsonValueKind.Array
        && columns.EnumerateArray().All(IsValidColumn)
        && visual.TryGetProperty("rows", out var rows)
        && rows.ValueKind == JsonValueKind.Array
        && rows.EnumerateArray().All(
            row => row.ValueKind == JsonValueKind.Object);

    private static bool IsValidColumn(JsonElement column) =>
        column.ValueKind == JsonValueKind.Object
        && HasNonEmptyString(column, "key")
        && HasNonEmptyString(column, "label");

    private static bool HasNonEmptyString(
        JsonElement element,
        string propertyName) =>
        element.TryGetProperty(propertyName, out var property)
        && property.ValueKind == JsonValueKind.String
        && !string.IsNullOrWhiteSpace(property.GetString());

    [GeneratedRegex(
        "```drill-advisor-visual[ \\t]*\\r?\\n(?<json>.*?)\\r?\\n```",
        RegexOptions.CultureInvariant | RegexOptions.Singleline,
        matchTimeoutMilliseconds: 1000)]
    private static partial Regex VisualBlockRegex();
}
