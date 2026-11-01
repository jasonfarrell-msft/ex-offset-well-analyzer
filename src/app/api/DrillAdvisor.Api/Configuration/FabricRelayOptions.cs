namespace DrillAdvisor.Api.Configuration;

/// <summary>
/// Configures the fixed Microsoft Fabric Data Agent MCP target.
/// </summary>
public sealed class FabricRelayOptions
{
    /// <summary>
    /// Gets or sets the immutable HTTPS target configured by the operator.
    /// </summary>
    public string Endpoint { get; set; } = string.Empty;
}
