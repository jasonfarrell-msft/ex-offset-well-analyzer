namespace DrillAdvisor.Api.Configuration;

/// <summary>
/// Configures trusted platform-authentication boundaries for public chat and MCP.
/// </summary>
public sealed class PlatformAuthOptions
{
    /// <summary>
    /// Gets or sets whether the operator confirmed the linked platform boundary.
    /// </summary>
    public bool TrustedPlatformAuthEnabled { get; set; }

    /// <summary>
    /// Gets or sets whether local chat calls may bypass platform headers.
    /// </summary>
    public bool AllowLocalAnonymous { get; set; }

    /// <summary>
    /// Gets or sets the Static Web Apps identity provider value for anonymous users.
    /// </summary>
    public string StaticWebAppsAnonymousProvider { get; set; } = "anonymous";

    /// <summary>
    /// Gets or sets the Easy Auth provider header expected from the linked backend.
    /// </summary>
    public string StaticWebAppsBackendProvider { get; set; } = "anonymous";

    /// <summary>
    /// Gets or sets the App Service authentication provider expected for Foundry.
    /// </summary>
    public string FoundryIdentityProvider { get; set; } = "aad";

    /// <summary>
    /// Gets or sets the object ID of the Foundry project managed identity.
    /// </summary>
    public string FoundryProjectPrincipalId { get; set; } = string.Empty;
}
