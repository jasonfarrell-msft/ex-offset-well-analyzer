using System.Diagnostics;
using System.Net;
using System.Text.Json;
using DrillAdvisor.Api.Foundry;
using DrillAdvisor.Api.Identity;
using DrillAdvisor.Api.Limits;
using DrillAdvisor.Api.Models;
using DrillAdvisor.Api.Offset;
using DrillAdvisor.Api.Serialization;
using Microsoft.AspNetCore.Mvc;
using System.Data.SqlClient;

namespace DrillAdvisor.Web.Endpoints;

/// <summary>
/// Implements the anonymous public chat endpoint without browser authentication.
/// </summary>
public static partial class ChatEndpoint
{
    private const int MaximumMessageLength = 2_000;
    private const int MaximumConversationIdLength = 256;
    private const int MaximumRequestBodyBytes = 8_192;

    /// <summary>
    /// Handles one public chat request.
    /// </summary>
    public static async Task<IResult> HandleAsync(
        HttpRequest request,
        IClientSourceIdentifier sourceIdentifier,
        IAnonymousChatGate chatGate,
        IOffsetAnalysisService offsetAnalysisService,
        IFoundryClient foundryClient,
        ILoggerFactory loggerFactory,
        CancellationToken cancellationToken)
    {
        var logger = loggerFactory.CreateLogger("DrillAdvisor.Chat");
        var startedTimestamp = Stopwatch.GetTimestamp();

        if (request.ContentLength > MaximumRequestBodyBytes)
        {
            return Problem(
                StatusCodes.Status413PayloadTooLarge,
                "Request too large",
                "The request body is too large.",
                "request_body_too_large");
        }

        ChatRequest? chatRequest;
        OffsetContext? offsetContext = null;
        OffsetContractSpec? offsetContract = null;
        try
        {
            var requestBody = await ReadRequestBodyAsync(
                    request.Body,
                    cancellationToken)
                .ConfigureAwait(false);
            if (requestBody is null)
            {
                return Problem(
                    StatusCodes.Status413PayloadTooLarge,
                    "Request too large",
                    "The request body is too large.",
                    "request_body_too_large");
            }

            using var document = StrictJson.Parse(requestBody);
            if (document.RootElement.ValueKind != JsonValueKind.Object)
            {
                return Problem(
                    StatusCodes.Status400BadRequest,
                    "Invalid request",
                    "The request body does not match the required offset context shape.",
                    "invalid_request");
            }

            var hasTypedOperationContractFields =
                document.RootElement.TryGetProperty("operation", out _)
                || document.RootElement.TryGetProperty("contractVersion", out _)
                || document.RootElement.TryGetProperty("releaseId", out _)
                || document.RootElement.TryGetProperty("context", out _);
            if (OffsetRequestParser.TryParseOperationRequest(
                    document.RootElement,
                    allowChatOperation: true,
                    out var operationRequest,
                    out _,
                    out _)
                && string.Equals(operationRequest!.Operation, "chat", StringComparison.Ordinal))
            {
                chatRequest = new ChatRequest(
                    operationRequest.Message,
                    operationRequest.ConversationId);
                offsetContext = operationRequest.Context;
                offsetContract = operationRequest.Contract;
            }
            else
            {
                if (hasTypedOperationContractFields)
                {
                    return Problem(
                        StatusCodes.Status400BadRequest,
                        "Invalid request",
                        "The request body does not match the required offset context shape.",
                        "invalid_request");
                }

                chatRequest = JsonSerializer.Deserialize(
                    requestBody,
                    ApiJsonContext.Default.ChatRequest);
                if (!OffsetRequestParser.TryParseChatOffsetContext(
                        document.RootElement,
                        out offsetContext,
                        out offsetContract))
                {
                    return Problem(
                        StatusCodes.Status400BadRequest,
                        "Invalid request",
                        "The request body does not match the required offset context shape.",
                        "invalid_request");
                }
            }
        }
        catch (JsonException)
        {
            return Problem(
                StatusCodes.Status400BadRequest,
                "Invalid request",
                "The request body must be valid JSON.",
                "invalid_json");
        }

        if (chatRequest is null)
        {
            return Problem(
                StatusCodes.Status400BadRequest,
                "Invalid request",
                "The request body is required.",
                "request_body_required");
        }

        var validationProblem = ValidateRequest(chatRequest);
        if (validationProblem is not null)
        {
            return validationProblem;
        }

        var admission = chatGate.TryAcquire(sourceIdentifier.GetSourceKey(request));
        if (!admission.IsAllowed)
        {
            request.HttpContext.Response.Headers.RetryAfter =
                admission.RetryAfterSeconds.ToString(
                    System.Globalization.CultureInfo.InvariantCulture);
            return Problem(
                admission.StatusCode,
                admission.StatusCode == StatusCodes.Status429TooManyRequests
                    ? "Request limit reached"
                    : "Public chat unavailable",
                admission.StatusCode == StatusCodes.Status429TooManyRequests
                    ? "The anonymous POC request limit was reached. Retry later."
                    : "The anonymous POC is temporarily unavailable.",
                admission.Code);
        }

        using var admissionLease = admission.Lease;
        try
        {
            var foundryInput = chatRequest.Message!;
            string? additionalInstructions;
            if (offsetContext is not null)
            {
                IReadOnlyList<OffsetChatWellSummary> summaries;
                try
                {
                    summaries = await offsetAnalysisService
                        .BuildChatContextAsync(
                            offsetContract ?? OffsetContractVersions.V1,
                            offsetContext,
                            cancellationToken)
                        .ConfigureAwait(false);
                }
                catch (OffsetChatContextException exception)
                {
                    return Problem(
                        exception.StatusCode,
                        exception.StatusCode == StatusCodes.Status409Conflict
                            ? "Offset context stale"
                            : "Invalid offset context",
                        exception.Message,
                        exception.Code);
                }
                catch (Exception exception) when (exception is InvalidOperationException
                                                  or SqlException)
                {
                    LogOffsetContextUnavailable(logger, exception);
                    request.HttpContext.Response.Headers.RetryAfter = "15";
                    return Problem(
                        StatusCodes.Status503ServiceUnavailable,
                        "Offset context unavailable",
                        "Offset analysis context is unavailable. Configure SQL access and retry.",
                        "offset_context_unavailable");
                }

                foundryInput = OffsetChatContextFormatter.BuildPrompt(
                    offsetContract,
                    offsetContext,
                    summaries,
                    chatRequest.Message!);
                additionalInstructions =
                    ChatRequestInstructions.OffsetComparison(offsetContract);
            }
            else
            {
                additionalInstructions =
                    ChatRequestInstructions.HistoricalSummary();
            }

            var reply = await foundryClient
                .SendAsync(
                    foundryInput,
                    chatRequest.ConversationId,
                    additionalInstructions,
                    cancellationToken)
                .ConfigureAwait(false);
            var disclosure = offsetContext is null
                ? ChatRequestInstructions.HistoricalDisclosure
                : (offsetContract?.Disclosure
                   ?? "SYNTHETIC DATA • DEVELOPMENT / OFFSET COMPARISON ONLY");
            var markdown = EnsureDisclosureFirstLine(reply.Markdown, disclosure);
            var response = new ChatResponse(
                reply.ConversationId,
                new AssistantMessage(
                    reply.MessageId,
                    "assistant",
                    markdown,
                    reply.CreatedAtUtc),
                reply.Visuals,
                reply.ToolCalls,
                reply.Sources,
                reply.Usage,
                Convert.ToInt64(
                    Math.Round(Stopwatch.GetElapsedTime(startedTimestamp).TotalMilliseconds)));

            return Results.Json(
                response,
                ApiJsonContext.Default.ChatResponse,
                statusCode: StatusCodes.Status200OK);
        }
        catch (FoundryTimeoutException exception)
        {
            LogFoundryTimeout(logger, exception);
            return Problem(
                StatusCodes.Status504GatewayTimeout,
                "Foundry timeout",
                "Drill Advisor did not receive a response from Foundry in time.",
                "foundry_timeout");
        }
        catch (FoundryApiException exception)
        {
            LogFoundryStatus(
                logger,
                (int)exception.StatusCode,
                exception.ResponseBody ?? "<empty>");
            return MapFoundryFailure(request, exception);
        }
        catch (FoundryResponseException exception)
        {
            LogInvalidFoundryResponse(logger, exception);
            return Problem(
                StatusCodes.Status502BadGateway,
                "Invalid Foundry response",
                "Drill Advisor received an invalid response from Foundry.",
                "invalid_foundry_response");
        }
        catch (ServiceTokenException exception)
        {
            LogServiceAuthenticationUnavailable(logger, exception);
            request.HttpContext.Response.Headers.RetryAfter = "30";
            return Problem(
                StatusCodes.Status503ServiceUnavailable,
                "Service authentication unavailable",
                "Drill Advisor cannot authenticate to Foundry right now.",
                "foundry_authentication_unavailable");
        }
    }

    private static async Task<byte[]?> ReadRequestBodyAsync(
        Stream requestBody,
        CancellationToken cancellationToken)
    {
        var buffer = new byte[MaximumRequestBodyBytes + 1];
        var totalRead = 0;
        while (totalRead < buffer.Length)
        {
            var read = await requestBody
                .ReadAsync(buffer.AsMemory(totalRead), cancellationToken)
                .ConfigureAwait(false);
            if (read == 0)
            {
                return buffer[..totalRead];
            }

            totalRead += read;
        }

        return null;
    }

    private static IResult? ValidateRequest(ChatRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Message))
        {
            return Problem(
                StatusCodes.Status400BadRequest,
                "Invalid message",
                "The message must not be empty.",
                "message_required");
        }

        if (request.Message.Length > MaximumMessageLength)
        {
            return Problem(
                StatusCodes.Status400BadRequest,
                "Invalid message",
                $"The message must not exceed {MaximumMessageLength} characters.",
                "message_too_long");
        }

        if (request.ConversationId is { } conversationId
            && (string.IsNullOrWhiteSpace(conversationId)
                || conversationId.Length > MaximumConversationIdLength
                || conversationId.Any(char.IsWhiteSpace)))
        {
            return Problem(
                StatusCodes.Status400BadRequest,
                "Invalid conversation ID",
                "The conversationId must be a nonempty ID without whitespace and must not exceed 256 characters.",
                "invalid_conversation_id");
        }

        return null;
    }

    private static IResult MapFoundryFailure(
        HttpRequest request,
        FoundryApiException exception)
    {
        if (exception.StatusCode == HttpStatusCode.Forbidden)
        {
            return Problem(
                StatusCodes.Status403Forbidden,
                "Foundry access denied",
                "The Drill Advisor service identity cannot use the configured Foundry project or MCP relay.",
                "foundry_access_denied",
                exception.StatusCode);
        }

        if (exception.StatusCode == HttpStatusCode.TooManyRequests)
        {
            request.HttpContext.Response.Headers.RetryAfter =
                (exception.RetryAfterSeconds ?? 5).ToString(
                    System.Globalization.CultureInfo.InvariantCulture);
            return Problem(
                StatusCodes.Status503ServiceUnavailable,
                "Foundry rate limited",
                "Foundry is temporarily rate limited. Try again later.",
                "foundry_rate_limited",
                exception.StatusCode);
        }

        return Problem(
            StatusCodes.Status502BadGateway,
            "Foundry request failed",
            "Drill Advisor could not complete the upstream Foundry request.",
            "foundry_request_failed",
            exception.StatusCode);
    }

    private static IResult Problem(
        int status,
        string title,
        string detail,
        string code,
        HttpStatusCode? upstreamStatus = null)
    {
        var extensions = new Dictionary<string, object?>
        {
            ["code"] = code,
        };
        if (upstreamStatus is not null)
        {
            extensions["upstreamStatus"] = (int)upstreamStatus.Value;
        }

        return Results.Problem(
            detail: detail,
            type: $"https://drill-advisor.example/problems/{code}",
            statusCode: status,
            title: title,
            extensions: extensions);
    }

    private static string EnsureDisclosureFirstLine(
        string markdown,
        string disclosure)
    {
        var trimmed = (markdown ?? string.Empty).TrimStart();
        if (string.IsNullOrWhiteSpace(trimmed))
        {
            return disclosure;
        }

        var lines = trimmed
            .Replace("\r\n", "\n", StringComparison.Ordinal)
            .Split('\n');
        lines[0] = disclosure;
        var filtered = new List<string>(lines.Length) { lines[0] };
        for (var i = 1; i < lines.Length; i++)
        {
            if (lines[i].StartsWith(
                    "SYNTHETIC DATA •",
                    StringComparison.Ordinal))
            {
                continue;
            }

            filtered.Add(lines[i]);
        }

        return string.Join("\n", filtered);
    }

    [LoggerMessage(
        EventId = 1002,
        Level = LogLevel.Warning,
        Message = "Foundry request timed out.")]
    private static partial void LogFoundryTimeout(
        ILogger logger,
        Exception exception);

    [LoggerMessage(
        EventId = 1003,
        Level = LogLevel.Warning,
        Message = "Foundry returned status code {StatusCode}. Body: {ResponseBody}")]
    private static partial void LogFoundryStatus(
        ILogger logger,
        int statusCode,
        string responseBody);

    [LoggerMessage(
        EventId = 1004,
        Level = LogLevel.Warning,
        Message = "Foundry returned an unusable response.")]
    private static partial void LogInvalidFoundryResponse(
        ILogger logger,
        Exception exception);

    [LoggerMessage(
        EventId = 1005,
        Level = LogLevel.Warning,
        Message = "Foundry application authentication is unavailable.")]
    private static partial void LogServiceAuthenticationUnavailable(
        ILogger logger,
        Exception exception);

    [LoggerMessage(
        EventId = 1006,
        Level = LogLevel.Warning,
        Message = "Offset context could not be computed from SQL data.")]
    private static partial void LogOffsetContextUnavailable(
        ILogger logger,
        Exception exception);
}
