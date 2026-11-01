namespace DrillAdvisor.Api.Configuration;

/// <summary>
/// Defines anonymous request limits for public offset-analysis reads.
/// </summary>
public sealed class PublicOffsetAnalysisOptions
{
    /// <summary>
    /// Gets or sets whether anonymous offset analysis is enabled.
    /// </summary>
    public bool Enabled { get; set; }

    /// <summary>
    /// Gets or sets the per-source rolling one-minute limit.
    /// </summary>
    public int PerSourcePerMinute { get; set; } = 6;

    /// <summary>
    /// Gets or sets the per-source concurrent request limit.
    /// </summary>
    public int PerSourceConcurrency { get; set; } = 1;

    /// <summary>
    /// Gets or sets the global rolling one-minute limit.
    /// </summary>
    public int GlobalPerMinute { get; set; } = 90;

    /// <summary>
    /// Gets or sets the global concurrent request limit.
    /// </summary>
    public int GlobalConcurrency { get; set; } = 10;
}
