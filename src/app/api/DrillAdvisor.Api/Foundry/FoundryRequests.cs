using System.Text.Json.Serialization;

namespace DrillAdvisor.Api.Foundry;

internal sealed record CreateResponseRequest(
    [property: JsonPropertyName("input")] string Input,
    [property:
        JsonPropertyName("previous_response_id"),
        JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    string? PreviousResponseId,
    [property: JsonPropertyName("stream")] bool Stream = false);
