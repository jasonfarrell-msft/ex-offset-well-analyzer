namespace DrillAdvisor.Web.Configuration;

/// <summary>
/// Configures direct validation of Foundry project managed-identity tokens.
/// </summary>
public sealed class McpAuthorizationOptions
{
    /// <summary>
    /// Gets or sets the Microsoft Entra tenant ID trusted by the relay.
    /// </summary>
    public string TenantId { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets the relay application ID URI expected in the audience claim.
    /// </summary>
    public string Audience { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets the app role required to invoke the relay.
    /// </summary>
    public string RequiredRole { get; set; } = "Mcp.Invoke";

    /// <summary>
    /// Gets or sets the object ID of the Foundry project managed identity.
    /// </summary>
    public string ExpectedPrincipalId { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets the optional client ID expected when the token exposes one.
    /// </summary>
    public string? ExpectedClientId { get; set; }
}
