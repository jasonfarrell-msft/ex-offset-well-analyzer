namespace DrillAdvisor.Api.Configuration;

/// <summary>
/// Configures keyless Azure service identities.
/// </summary>
public sealed class ServiceIdentityOptions
{
    /// <summary>
    /// Gets or sets the user-assigned managed identity client ID.
    /// </summary>
    public string ManagedIdentityClientId { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets the Microsoft Entra tenant ID.
    /// </summary>
    public string TenantId { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets the Fabric application registration client ID.
    /// </summary>
    public string FabricAppClientId { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets the fixed Microsoft Fabric token scope.
    /// </summary>
    public string FabricTokenScope { get; set; } = string.Empty;
}
