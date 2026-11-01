namespace DrillAdvisor.Api.Auth;

/// <summary>
/// Identifies whether the Functions process is running in Azure.
/// </summary>
public interface IPlatformEnvironment
{
    /// <summary>
    /// Gets a value indicating whether Azure Functions host markers are present.
    /// </summary>
    bool IsAzure { get; }
}

/// <summary>
/// Reads Azure Functions host markers from the process environment.
/// </summary>
public sealed class PlatformEnvironment : IPlatformEnvironment
{
    /// <inheritdoc />
    public bool IsAzure =>
        !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("WEBSITE_INSTANCE_ID"))
        || !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("WEBSITE_HOSTNAME"));
}
