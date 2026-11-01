namespace DrillAdvisor.Api.Foundry;

/// <summary>
/// Represents an unsuccessful Foundry API response.
/// </summary>
public sealed class FoundryApiException : Exception
{
    /// <summary>
    /// Initializes a new Foundry API exception.
    /// </summary>
    /// <param name="statusCode">The upstream HTTP status code.</param>
    /// <param name="retryAfterSeconds">The safe upstream retry delay, when present.</param>
    public FoundryApiException(
        System.Net.HttpStatusCode statusCode,
        int? retryAfterSeconds = null,
        string? responseBody = null)
        : base("The Foundry API returned an unsuccessful response.")
    {
        StatusCode = statusCode;
        RetryAfterSeconds = retryAfterSeconds;
        ResponseBody = responseBody;
    }

    /// <summary>
    /// Gets the upstream HTTP status code.
    /// </summary>
    public System.Net.HttpStatusCode StatusCode { get; }

    /// <summary>
    /// Gets the upstream retry delay in seconds.
    /// </summary>
    public int? RetryAfterSeconds { get; }

    /// <summary>
    /// Gets the safe upstream response body (truncated), when captured.
    /// </summary>
    public string? ResponseBody { get; }
}

/// <summary>
/// Represents an invalid or incomplete Foundry response payload.
/// </summary>
public sealed class FoundryResponseException : Exception
{
    /// <summary>
    /// Initializes a new Foundry response exception.
    /// </summary>
    /// <param name="message">A safe description of the payload problem.</param>
    public FoundryResponseException(string message)
        : base(message)
    {
    }

    /// <summary>
    /// Initializes a new Foundry response exception.
    /// </summary>
    /// <param name="message">A safe description of the payload problem.</param>
    /// <param name="innerException">The underlying JSON exception.</param>
    public FoundryResponseException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}

/// <summary>
/// Represents a Foundry request that exceeded the API timeout.
/// </summary>
public sealed class FoundryTimeoutException : Exception
{
    /// <summary>
    /// Initializes a new Foundry timeout exception.
    /// </summary>
    /// <param name="message">A safe description of the timeout.</param>
    /// <param name="innerException">The underlying cancellation exception.</param>
    public FoundryTimeoutException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}
