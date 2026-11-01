namespace DrillAdvisor.Api.Configuration;

/// <summary>
/// Configures fixed-instance anonymous POC admission controls.
/// </summary>
public sealed class PublicChatOptions
{
    /// <summary>
    /// Gets or sets whether public chat traffic is admitted.
    /// </summary>
    public bool Enabled { get; set; }

    /// <summary>
    /// Gets or sets the per-source-IP admission limit per rolling minute.
    /// </summary>
    public int PerSourcePerMinute { get; set; } = 3;

    /// <summary>
    /// Gets or sets the maximum concurrent request count per source IP.
    /// </summary>
    public int PerSourceConcurrency { get; set; } = 1;

    /// <summary>
    /// Gets or sets the global admission limit per rolling minute.
    /// </summary>
    public int GlobalPerMinute { get; set; } = 60;

    /// <summary>
    /// Gets or sets the global concurrent request limit.
    /// </summary>
    public int GlobalConcurrency { get; set; } = 10;

    /// <summary>
    /// Gets or sets the UTC-day Foundry call limit.
    /// </summary>
    public int DailyFoundryCalls { get; set; } = 500;
}
