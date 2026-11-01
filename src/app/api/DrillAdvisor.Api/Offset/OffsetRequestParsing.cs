using System.Collections;
using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace DrillAdvisor.Api.Offset;

public static partial class StrictJson
{
    public static JsonDocument Parse(ReadOnlySpan<byte> utf8Json)
    {
        EnsureNoDuplicateProperties(utf8Json);
        return JsonDocument.Parse(utf8Json.ToArray());
    }

    private static void EnsureNoDuplicateProperties(ReadOnlySpan<byte> utf8Json)
    {
        var reader = new Utf8JsonReader(
            utf8Json,
            new JsonReaderOptions
            {
                AllowTrailingCommas = false,
                CommentHandling = JsonCommentHandling.Disallow,
            });

        var objectPropertyNames = new Stack<HashSet<string>>();
        while (reader.Read())
        {
            if (reader.TokenType == JsonTokenType.StartObject)
            {
                objectPropertyNames.Push(new HashSet<string>(StringComparer.Ordinal));
                continue;
            }

            if (reader.TokenType == JsonTokenType.EndObject)
            {
                _ = objectPropertyNames.Pop();
                continue;
            }

            if (reader.TokenType != JsonTokenType.PropertyName)
            {
                continue;
            }

            var name = reader.GetString() ?? string.Empty;
            var names = objectPropertyNames.Peek();
            if (!names.Add(name))
            {
                throw new JsonException($"Duplicate JSON member '{name}' is not allowed.");
            }
        }
    }
}

public static partial class OffsetRequestParser
{
    public static bool TryParseOperationRequest(
        JsonElement root,
        bool allowChatOperation,
        out OffsetOperationRequest? request,
        out string errorCode,
        out string errorDetail)
    {
        request = null;
        errorCode = "INVALID_REQUEST";
        errorDetail = "The request does not match the required offset contract.";
        if (root.ValueKind != JsonValueKind.Object)
        {
            return false;
        }

        if (!TryReadRequiredString(root, "operation", out var operation)
            || !TryReadRequiredString(root, "contractVersion", out var contractVersion)
            || !TryReadRequiredString(root, "releaseId", out var releaseId))
        {
            return false;
        }

        if (!OffsetContractVersions.TryResolve(
                contractVersion,
                releaseId,
                out var contract))
        {
            return false;
        }

        var allowed = allowChatOperation
            ? operation is "targets" or "candidates" or "compare" or "chat"
            : operation is "targets" or "candidates" or "compare";
        if (!allowed)
        {
            return false;
        }

        OffsetContext? context = null;
        string? message = null;
        string? conversationId = null;

        if (operation != "targets")
        {
            if (!root.TryGetProperty("context", out var contextElement)
                || !TryParseContext(contextElement, out context, out errorDetail))
            {
                return false;
            }
        }

        if (operation == "chat")
        {
            if (!TryReadRequiredString(root, "message", out message))
            {
                return false;
            }

            if (string.IsNullOrWhiteSpace(message) || message.Length > OffsetContract.MaximumMessageLength)
            {
                return false;
            }

            if (root.TryGetProperty("conversationId", out var conversationElement))
            {
                if (conversationElement.ValueKind != JsonValueKind.String)
                {
                    return false;
                }

                conversationId = conversationElement.GetString();
                if (string.IsNullOrWhiteSpace(conversationId))
                {
                    return false;
                }
            }
        }

        if (!ValidateShape(root, operation))
        {
            return false;
        }

        if (context is not null && !ValidateContextByOperation(context, operation, out errorCode, out errorDetail))
        {
            return false;
        }

        request = new OffsetOperationRequest(
            operation,
            contractVersion,
            releaseId,
            contract,
            context,
            message,
            conversationId);
        return true;
    }

    public static bool TryParseChatOffsetContext(
        JsonElement root,
        out OffsetContext? context)
    {
        return TryParseChatOffsetContext(root, out context, out _);
    }

    public static bool TryParseChatOffsetContext(
        JsonElement root,
        out OffsetContext? context,
        out OffsetContractSpec contract)
    {
        context = null;
        contract = OffsetContractVersions.V1;
        if (!root.TryGetProperty("offsetContext", out var contextElement))
        {
            return true;
        }

        if (contextElement.ValueKind != JsonValueKind.Object)
        {
            return false;
        }

        if (contextElement.TryGetProperty("context", out var envelopeContextElement))
        {
            if (!TryReadRequiredString(contextElement, "contractVersion", out var contractVersion)
                || !TryReadRequiredString(contextElement, "releaseId", out var releaseId))
            {
                return false;
            }

            if (!OffsetContractVersions.TryResolve(
                    contractVersion,
                    releaseId,
                    out contract))
            {
                return false;
            }

            if (!ValidateOffsetContextEnvelopeShape(contextElement))
            {
                return false;
            }

            return TryParseContext(envelopeContextElement, out context, out _);
        }

        contract = OffsetContractVersions.V1;
        return TryParseContext(contextElement, out context, out _);
    }

    private static bool TryParseContext(
        JsonElement contextElement,
        out OffsetContext? context,
        out string errorDetail)
    {
        context = null;
        errorDetail = "Invalid offset context.";
        if (contextElement.ValueKind != JsonValueKind.Object)
        {
            return false;
        }

        if (!TryReadRequiredString(contextElement, "targetId", out var targetId)
            || !contextElement.TryGetProperty("criteria", out var criteriaElement)
            || !TryParseCriteria(criteriaElement, out var criteria))
        {
            return false;
        }

        if (!TargetIdPattern().IsMatch(targetId))
        {
            return false;
        }

        if (!contextElement.TryGetProperty("selectedWellIds", out var selectedElement)
            || selectedElement.ValueKind != JsonValueKind.Array)
        {
            return false;
        }

        var selected = new List<string>();
        foreach (var item in selectedElement.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.String)
            {
                return false;
            }

            var wellId = item.GetString() ?? string.Empty;
            if (!WellIdPattern().IsMatch(wellId))
            {
                return false;
            }

            selected.Add(wellId);
        }

        if (selected.Count > 5
            || selected.Distinct(StringComparer.Ordinal).Count() != selected.Count
            || !selected.SequenceEqual(selected.Order(StringComparer.Ordinal), StringComparer.Ordinal))
        {
            return false;
        }

        if (!contextElement.TryGetProperty("contextRevision", out var revisionElement)
            || revisionElement.ValueKind != JsonValueKind.Number
            || !revisionElement.TryGetInt64(out var contextRevision)
            || contextRevision < 0)
        {
            return false;
        }

        if (!ValidateContextShape(contextElement))
        {
            return false;
        }

        context = new OffsetContext(targetId, criteria, selected, contextRevision);
        return true;
    }

    private static bool TryParseCriteria(
        JsonElement criteriaElement,
        out OffsetCriteria criteria)
    {
        criteria = null!;
        if (criteriaElement.ValueKind != JsonValueKind.Object
            || !TryReadRequiredString(criteriaElement, "radiusFt", out var radius)
            || !TryReadRequiredBoolean(criteriaElement, "formationMatch", out var formationMatch)
            || !TryReadRequiredBoolean(criteriaElement, "holeSizeMatch", out var holeSizeMatch)
            || !TryReadRequiredBoolean(criteriaElement, "mdOverlap", out var mdOverlap))
        {
            return false;
        }

        if (!RadiusPattern().IsMatch(radius))
        {
            return false;
        }

        if (!decimal.TryParse(radius, NumberStyles.Number, CultureInfo.InvariantCulture, out var radiusValue)
            || radiusValue < 0
            || radiusValue > 3_000_000)
        {
            return false;
        }

        if (!ValidateCriteriaShape(criteriaElement))
        {
            return false;
        }

        criteria = new OffsetCriteria(radius, formationMatch, holeSizeMatch, mdOverlap);
        return true;
    }

    private static bool ValidateShape(JsonElement root, string operation)
    {
        var allowed = operation switch
        {
            "targets" => new HashSet<string>(["operation", "contractVersion", "releaseId"], StringComparer.Ordinal),
            "candidates" or "compare" => new HashSet<string>(["operation", "contractVersion", "releaseId", "context"], StringComparer.Ordinal),
            "chat" => new HashSet<string>(["operation", "contractVersion", "releaseId", "context", "message", "conversationId"], StringComparer.Ordinal),
            _ => [],
        };
        return root.EnumerateObject().All(property => allowed.Contains(property.Name));
    }

    private static bool ValidateContextShape(JsonElement contextElement)
    {
        var allowed = new HashSet<string>(
            ["targetId", "criteria", "selectedWellIds", "contextRevision"],
            StringComparer.Ordinal);
        return contextElement.EnumerateObject().All(property => allowed.Contains(property.Name));
    }

    private static bool ValidateOffsetContextEnvelopeShape(JsonElement contextElement)
    {
        var allowed = new HashSet<string>(
            ["contractVersion", "releaseId", "context"],
            StringComparer.Ordinal);
        return contextElement.EnumerateObject().All(property => allowed.Contains(property.Name));
    }

    private static bool ValidateCriteriaShape(JsonElement criteriaElement)
    {
        var allowed = new HashSet<string>(
            ["radiusFt", "formationMatch", "holeSizeMatch", "mdOverlap"],
            StringComparer.Ordinal);
        return criteriaElement.EnumerateObject().All(property => allowed.Contains(property.Name));
    }

    private static bool ValidateContextByOperation(
        OffsetContext context,
        string operation,
        out string errorCode,
        out string errorDetail)
    {
        errorCode = "INVALID_REQUEST";
        errorDetail = "The request context is invalid for this operation.";
        var count = context.SelectedWellIds.Count;
        if (operation == "candidates" && count != 0)
        {
            return false;
        }

        if (operation is "compare" or "chat" && (count < 1 || count > 5))
        {
            return false;
        }

        return true;
    }

    private static bool TryReadRequiredString(
        JsonElement root,
        string propertyName,
        out string value)
    {
        value = string.Empty;
        if (!root.TryGetProperty(propertyName, out var element)
            || element.ValueKind != JsonValueKind.String)
        {
            return false;
        }

        value = element.GetString() ?? string.Empty;
        return !string.IsNullOrWhiteSpace(value);
    }

    private static bool TryReadRequiredBoolean(
        JsonElement root,
        string propertyName,
        out bool value)
    {
        value = false;
        if (!root.TryGetProperty(propertyName, out var element)
            || (element.ValueKind is not JsonValueKind.True
                and not JsonValueKind.False))
        {
            return false;
        }

        value = element.GetBoolean();
        return true;
    }

    [GeneratedRegex("^SYN-TARGET-(?:000[1-9]|001[0-2])$")]
    private static partial Regex TargetIdPattern();

    [GeneratedRegex("^SYN-WELL-(?:00[0-9][0-9]|0100)$")]
    private static partial Regex WellIdPattern();

    [GeneratedRegex("^(?:0|[1-9][0-9]{0,6})(?:\\.[0-9]{1,6})?$")]
    private static partial Regex RadiusPattern();
}

public static class OffsetChatContextFormatter
{
    private const string VersionNeutralDisclosure =
        "SYNTHETIC DATA • DEVELOPMENT / OFFSET COMPARISON ONLY";

    public static string BuildPrompt(
        OffsetContractSpec? contract,
        OffsetContext context,
        IReadOnlyList<OffsetChatWellSummary> wells,
        string userMessage)
    {
        var buffer = new StringBuilder();
        _ = buffer.AppendLine(contract?.Disclosure ?? VersionNeutralDisclosure);
        _ = buffer.AppendLine("Trusted offset context (server-computed):");
        _ = buffer.Append("- targetId: ").Append(context.TargetId).AppendLine();
        _ = buffer.Append("- radiusFt: ")
            .Append(OffsetFormats.CanonicalDecimal(OffsetContextHasher.ParseDecimal(context.Criteria.RadiusFt)))
            .AppendLine();
        _ = buffer.Append("- formationMatch: ")
            .Append(context.Criteria.FormationMatch ? "true" : "false")
            .AppendLine();
        _ = buffer.Append("- holeSizeMatch: ")
            .Append(context.Criteria.HoleSizeMatch ? "true" : "false")
            .AppendLine();
        _ = buffer.Append("- mdOverlap: ")
            .Append(context.Criteria.MdOverlap ? "true" : "false")
            .AppendLine();
        _ = buffer.AppendLine("- selectedWells:");
        foreach (var well in wells)
        {
            _ = buffer.Append("  - ").Append(well.WellId)
                .Append(": distanceFt=").Append(well.DistanceFt)
                .Append(", acceptedRuns=").Append(well.AcceptedRunCount.ToString(System.Globalization.CultureInfo.InvariantCulture))
                .Append(", acceptedFootageFt=").Append(well.AcceptedFootageFt ?? "null")
                .Append(", acceptedDurationHours=").Append(well.AcceptedDurationHours ?? "null")
                .Append(", summaryPenetrationRateFtPerHour=").Append(well.SummaryPenetrationRateFtPerHour ?? "null")
                .AppendLine();
        }

        _ = buffer.AppendLine();
        _ = buffer.AppendLine("User message:");
        _ = buffer.Append(userMessage);
        return buffer.ToString();
    }
}
