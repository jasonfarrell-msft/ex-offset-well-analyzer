namespace DrillAdvisor.Api.Configuration;

/// <summary>
/// Configures SQL access for offset-well analysis operations.
/// </summary>
public sealed class OffsetAnalysisSqlOptions
{
    /// <summary>
    /// Gets or sets the SQL server host name.
    /// </summary>
    public string Server { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets the SQL database name.
    /// </summary>
    public string Database { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets the per-command timeout in seconds.
    /// </summary>
    public int CommandTimeoutSeconds { get; set; } = 30;
}
