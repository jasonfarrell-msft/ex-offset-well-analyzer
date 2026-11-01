using DrillAdvisor.Api.Fabric;
using DrillAdvisor.Api.Identity;

namespace DrillAdvisor.Web.Endpoints;

/// <summary>
/// Implements the authenticated fixed-target Fabric streamable HTTP MCP relay.
/// </summary>
public static partial class FabricMcpEndpoint
{
    private static readonly string[] ResponseHeaders =
    [
        "MCP-Protocol-Version",
        "MCP-Session-Id",
        "Retry-After",
        "Cache-Control",
    ];

    /// <summary>
    /// Relays one authorized MCP request.
    /// </summary>
    public static async Task<IResult> HandleAsync(
        HttpRequest request,
        IFabricMcpRelayClient relayClient,
        ILoggerFactory loggerFactory,
        CancellationToken cancellationToken)
    {
        var logger = loggerFactory.CreateLogger("DrillAdvisor.FabricMcp");
        try
        {
            using var upstream = await relayClient
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
            return Results.Empty;
        }
        catch (ServiceTokenException exception)
        {
            LogFabricAuthenticationUnavailable(logger, exception);
            request.HttpContext.Response.Headers.RetryAfter = "30";
            return Results.Problem(
                detail: "The Fabric relay is temporarily unavailable.",
                type: "https://drill-advisor.example/problems/fabric_authentication_unavailable",
                statusCode: StatusCodes.Status503ServiceUnavailable,
                title: "Fabric authentication unavailable",
                extensions: new Dictionary<string, object?>
                {
                    ["code"] = "fabric_authentication_unavailable",
                });
        }
        catch (HttpRequestException exception)
        {
            LogFabricRelayUnavailable(logger, exception);
            request.HttpContext.Response.Headers.RetryAfter = "5";
            return Results.Problem(
                detail: "The configured Fabric MCP endpoint could not be reached.",
                type: "https://drill-advisor.example/problems/fabric_relay_unavailable",
                statusCode: StatusCodes.Status502BadGateway,
                title: "Fabric relay unavailable",
                extensions: new Dictionary<string, object?>
                {
                    ["code"] = "fabric_relay_unavailable",
                });
        }
    }

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
