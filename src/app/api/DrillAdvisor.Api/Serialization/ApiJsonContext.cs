using System.Text.Json.Serialization;
using DrillAdvisor.Api.Foundry;
using DrillAdvisor.Api.Models;
using Microsoft.AspNetCore.Mvc;

namespace DrillAdvisor.Api.Serialization;

[JsonSourceGenerationOptions(
    PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase,
    PropertyNameCaseInsensitive = true)]
[JsonSerializable(typeof(ChatRequest))]
[JsonSerializable(typeof(ChatResponse))]
[JsonSerializable(typeof(ProblemDetails))]
[JsonSerializable(typeof(CreateResponseRequest))]
internal sealed partial class ApiJsonContext : JsonSerializerContext;
