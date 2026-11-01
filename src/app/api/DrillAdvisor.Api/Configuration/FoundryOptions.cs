namespace DrillAdvisor.Api.Configuration;

/// <summary>
/// Configures the Microsoft Foundry project client.
/// </summary>
public sealed class FoundryOptions
{
    /// <summary>
    /// Gets or sets the absolute Foundry project endpoint.
    /// </summary>
    public string ProjectEndpoint { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets the Foundry agent reference name.
    /// </summary>
    public string AgentName { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets the total timeout for a chat operation.
    /// </summary>
    public TimeSpan Timeout { get; set; } = TimeSpan.FromSeconds(120);

    /// <summary>
    /// Gets or sets the maximum retries after the initial request.
    /// </summary>
    public int MaximumRetryCount { get; set; } = 2;
}
