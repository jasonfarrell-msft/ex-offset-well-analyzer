using DrillAdvisor.Api.Auth;
using DrillAdvisor.Api.Fabric;
using DrillAdvisor.Api.Identity;
using DrillAdvisor.Api.Serialization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;

namespace DrillAdvisor.Api.Functions;

/// <summary>
/// Exposes the fixed-target Fabric Data Agent streamable HTTP MCP relay.
/// </summary>
public sealed partial class FabricMcpRelayFunction(
    IPlatformRequestAuthorizer authorizer,
    IFabricMcpRelayClient relayClient,
    ILogger<FabricMcpRelayFunction> logger)
{
    private static readonly string[] ResponseHeaders =
    [
        "MCP-Protocol-Version",
        "MCP-Session-Id",
        "Retry-After",
        "Cache-Control",
    ];

    private readonly IPlatformRequestAuthorizer _authorizer =
        authorizer ?? throw new ArgumentNullException(nameof(authorizer));
    private readonly IFabricMcpRelayClient _relayClient =
        relayClient ?? throw new ArgumentNullException(nameof(relayClient));
    private readonly ILogger<FabricMcpRelayFunction> _logger =
        logger ?? throw new ArgumentNullException(nameof(logger));

    /// <summary>
    /// Proxies POST, GET, and DELETE MCP traffic after Foundry identity validation.
    /// </summary>
    [Function("FabricDataAgentMcp")]
    public async Task<IActionResult> RunAsync(
        [HttpTrigger(
            AuthorizationLevel.Anonymous,
            "post",
            "get",
            "delete",
            Route = "mcp/fabric-dataagent")]
        HttpRequest request,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);

        var authorization = _authorizer.AuthorizeMcp(request);
        if (!authorization.IsAuthorized)
        {
            LogMcpCallerRejected(_logger, authorization.FailureCode);
            return Problem(
                StatusCodes.Status403Forbidden,
                "MCP caller rejected",
                "Only the configured Foundry project identity may use this relay.",
                authorization.FailureCode);
        }

        try
        {
            using var upstream = await _relayClient
                .ForwardAsync(request, cancellationToken)
                .ConfigureAwait(false);
            var response = request.HttpContext.Response;
            response.StatusCode = (int)upstream.StatusCode;
            response.ContentType = upstream.Content.Headers.ContentType?.ToString();

            foreach (var header in ResponseHeaders)
            {
                if (upstream.Headers.TryGetValues(header, out var values))
                {
                    response.Headers[header] = values.ToArray();
                }
            }

            await upstream.Content
                .CopyToAsync(response.Body, cancellationToken)
                .ConfigureAwait(false);
            return new EmptyResult();
        }
        catch (ServiceTokenException exception)
        {
            LogFabricAuthenticationUnavailable(_logger, exception);
            request.HttpContext.Response.Headers.RetryAfter = "30";
            return Problem(
                StatusCodes.Status503ServiceUnavailable,
                "Fabric authentication unavailable",
                "The Fabric relay is temporarily unavailable.",
                "fabric_authentication_unavailable");
        }
        catch (HttpRequestException exception)
        {
            LogFabricRelayUnavailable(_logger, exception);
            request.HttpContext.Response.Headers.RetryAfter = "5";
            return Problem(
                StatusCodes.Status502BadGateway,
                "Fabric relay unavailable",
                "The configured Fabric MCP endpoint could not be reached.",
                "fabric_relay_unavailable");
        }
    }

    private static JsonResult Problem(
        int status,
        string title,
        string detail,
        string code)
    {
        var problem = new ProblemDetails
        {
            Status = status,
            Title = title,
            Detail = detail,
            Type = $"https://drill-advisor.example/problems/{code}",
        };
        problem.Extensions["code"] = code;
        return new JsonResult(problem, ApiJsonContext.Default.Options)
        {
            ContentType = "application/problem+json",
            StatusCode = status,
        };
    }

    [LoggerMessage(
        EventId = 2000,
        Level = LogLevel.Warning,
        Message = "MCP caller rejected with authorization code {FailureCode}.")]
    private static partial void LogMcpCallerRejected(
        ILogger logger,
        string? failureCode);

    [LoggerMessage(
        EventId = 2001,
        Level = LogLevel.Warning,
        Message = "Microsoft Fabric application authentication is unavailable.")]
    private static partial void LogFabricAuthenticationUnavailable(
        ILogger logger,
        Exception exception);

    [LoggerMessage(
        EventId = 2002,
        Level = LogLevel.Warning,
        Message = "The configured Microsoft Fabric MCP endpoint is unavailable.")]
    private static partial void LogFabricRelayUnavailable(
        ILogger logger,
        Exception exception);
}
