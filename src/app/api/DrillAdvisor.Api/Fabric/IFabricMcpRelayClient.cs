using Microsoft.AspNetCore.Http;

namespace DrillAdvisor.Api.Fabric;

/// <summary>
/// Forwards streamable HTTP MCP traffic to the configured Fabric Data Agent.
/// </summary>
public interface IFabricMcpRelayClient
{
    /// <summary>
    /// Forwards an allowed MCP request without accepting a caller-selected target.
    /// </summary>
    Task<HttpResponseMessage> ForwardAsync(
        HttpRequest request,
        CancellationToken cancellationToken);
}
