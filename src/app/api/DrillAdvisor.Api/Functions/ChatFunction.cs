using System.Diagnostics;
using System.Net;
using System.Text.Json;
using DrillAdvisor.Api.Auth;
using DrillAdvisor.Api.Foundry;
using DrillAdvisor.Api.Identity;
using DrillAdvisor.Api.Limits;
using DrillAdvisor.Api.Models;
using DrillAdvisor.Api.Serialization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;

namespace DrillAdvisor.Api.Functions;

/// <summary>
/// Handles public Drill Advisor chat requests admitted through the linked Static Web App.
/// </summary>
public sealed partial class ChatFunction(
    IPlatformRequestAuthorizer authorizer,
    IClientSourceIdentifier sourceIdentifier,
    IAnonymousChatGate chatGate,
    IFoundryClient foundryClient,
    ILogger<ChatFunction> logger)
{
    private const int MaximumMessageLength = 2_000;
    private const int MaximumConversationIdLength = 256;
    private const int MaximumRequestBodyBytes = 8_192;

    private readonly IPlatformRequestAuthorizer _authorizer =
        authorizer ?? throw new ArgumentNullException(nameof(authorizer));
    private readonly IClientSourceIdentifier _sourceIdentifier =
        sourceIdentifier ?? throw new ArgumentNullException(nameof(sourceIdentifier));
    private readonly IAnonymousChatGate _chatGate =
        chatGate ?? throw new ArgumentNullException(nameof(chatGate));
    private readonly IFoundryClient _foundryClient =
        foundryClient ?? throw new ArgumentNullException(nameof(foundryClient));
    private readonly ILogger<ChatFunction> _logger =
        logger ?? throw new ArgumentNullException(nameof(logger));

    /// <summary>
    /// Processes a chat request and returns the final assistant response.
    /// </summary>
    [Function("Chat")]
    public async Task<IActionResult> RunAsync(
        [HttpTrigger(
            AuthorizationLevel.Anonymous,
            "post",
            Route = "chat")]
        HttpRequest request,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);
        var startedTimestamp = Stopwatch.GetTimestamp();

        var authorization = _authorizer.AuthorizeChat(request);
        if (!authorization.IsAuthorized)
        {
            return Problem(
                StatusCodes.Status403Forbidden,
                "Public route rejected",
                "Use the public Drill Advisor site to access this endpoint.",
                authorization.FailureCode);
        }

        if (request.ContentLength > MaximumRequestBodyBytes)
        {
            return Problem(
                StatusCodes.Status413PayloadTooLarge,
                "Request too large",
                "The request body is too large.",
                "request_body_too_large");
        }

        ChatRequest? chatRequest;
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

            chatRequest = JsonSerializer.Deserialize(
                requestBody,
                ApiJsonContext.Default.ChatRequest);
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

        var sourceKey = _sourceIdentifier.GetSourceKey(request);
        var admission = _chatGate.TryAcquire(sourceKey);
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
            var reply = await _foundryClient
                .SendAsync(
                    chatRequest.Message!,
                    chatRequest.ConversationId,
                    ChatRequestInstructions.HistoricalSummary(),
                    cancellationToken)
                .ConfigureAwait(false);
            var latency = Stopwatch.GetElapsedTime(startedTimestamp);
            var response = new ChatResponse(
                reply.ConversationId,
                new AssistantMessage(
                    reply.MessageId,
                    "assistant",
                    reply.Markdown,
                    reply.CreatedAtUtc),
                reply.Visuals,
                reply.ToolCalls,
                reply.Sources,
                reply.Usage,
                Convert.ToInt64(Math.Round(latency.TotalMilliseconds)));

            return new JsonResult(
                response,
                ApiJsonContext.Default.Options)
            {
                StatusCode = StatusCodes.Status200OK,
            };
        }
        catch (FoundryTimeoutException exception)
        {
            LogFoundryTimeout(_logger, exception);
            return Problem(
                StatusCodes.Status504GatewayTimeout,
                "Foundry timeout",
                "Drill Advisor did not receive a response from Foundry in time.",
                "foundry_timeout");
        }
        catch (FoundryApiException exception)
        {
            LogFoundryStatus(_logger, (int)exception.StatusCode);
            return MapFoundryFailure(request, exception);
        }
        catch (FoundryResponseException exception)
        {
            LogInvalidFoundryResponse(_logger, exception);
            return Problem(
                StatusCodes.Status502BadGateway,
                "Invalid Foundry response",
                "Drill Advisor received an invalid response from Foundry.",
                "invalid_foundry_response");
        }
        catch (ServiceTokenException exception)
        {
            LogServiceAuthenticationUnavailable(_logger, exception);
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

    private static JsonResult? ValidateRequest(ChatRequest request)
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

    private static JsonResult MapFoundryFailure(
        HttpRequest request,
        FoundryApiException exception)
    {
        var statusCode = exception.StatusCode;
        if (statusCode == HttpStatusCode.Forbidden)
        {
            return Problem(
                StatusCodes.Status403Forbidden,
                "Foundry access denied",
                "The Drill Advisor service identity cannot use the configured Foundry project or MCP relay.",
                "foundry_access_denied",
                statusCode);
        }

        if (statusCode == HttpStatusCode.TooManyRequests)
        {
            request.HttpContext.Response.Headers.RetryAfter =
                (exception.RetryAfterSeconds ?? 5).ToString(
                    System.Globalization.CultureInfo.InvariantCulture);
            return Problem(
                StatusCodes.Status503ServiceUnavailable,
                "Foundry rate limited",
                "Foundry is temporarily rate limited. Try again later.",
                "foundry_rate_limited",
                statusCode);
        }

        return Problem(
            StatusCodes.Status502BadGateway,
            "Foundry request failed",
            "Drill Advisor could not complete the upstream Foundry request.",
            "foundry_request_failed",
            statusCode);
    }

    private static JsonResult Problem(
        int status,
        string title,
        string detail,
        string code,
        HttpStatusCode? upstreamStatus = null)
    {
        var problem = new ProblemDetails
        {
            Status = status,
            Title = title,
            Detail = detail,
            Type = $"https://drill-advisor.example/problems/{code}",
        };
        problem.Extensions["code"] = code;
        if (upstreamStatus is not null)
        {
            problem.Extensions["upstreamStatus"] = (int)upstreamStatus.Value;
        }

        return new JsonResult(
            problem,
            ApiJsonContext.Default.Options)
        {
            ContentType = "application/problem+json",
            StatusCode = status,
        };
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
        Message = "Foundry returned status code {StatusCode}.")]
    private static partial void LogFoundryStatus(
        ILogger logger,
        int statusCode);

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
}
