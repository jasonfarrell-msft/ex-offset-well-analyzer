using System.Net;
using System.Net.Http.Headers;
using System.Text.Json;
using DrillAdvisor.Api.Configuration;
using DrillAdvisor.Api.Identity;
using DrillAdvisor.Api.Models;
using DrillAdvisor.Api.Serialization;
using Microsoft.Extensions.Options;

namespace DrillAdvisor.Api.Foundry;

/// <summary>
/// Calls the Foundry conversation and Responses APIs with application authorization.
/// </summary>
public sealed class FoundryClient : IFoundryClient
{
    private static readonly HashSet<HttpStatusCode> RetryableStatusCodes =
    [
        HttpStatusCode.TooManyRequests,
        HttpStatusCode.BadGateway,
        HttpStatusCode.ServiceUnavailable,
        HttpStatusCode.GatewayTimeout,
    ];

    private readonly HttpClient _httpClient;
    private readonly FoundryOptions _options;
    private readonly IFoundryTokenSource _tokenSource;
    private readonly TimeProvider _timeProvider;
    private readonly Uri _responsesEndpoint;
    private const int MaxErrorBodyLength = 4_096;

    /// <summary>
    /// Initializes a Foundry API client.
    /// </summary>
    /// <param name="httpClient">The HTTP client supplied by <see cref="IHttpClientFactory"/>.</param>
    /// <param name="options">The validated Foundry settings.</param>
    /// <param name="timeProvider">The clock used for response timestamps and retry delays.</param>
    public FoundryClient(
        HttpClient httpClient,
        IOptions<FoundryOptions> options,
        TimeProvider timeProvider,
        IFoundryTokenSource tokenSource)
    {
        ArgumentNullException.ThrowIfNull(httpClient);
        ArgumentNullException.ThrowIfNull(options);
        ArgumentNullException.ThrowIfNull(timeProvider);
        ArgumentNullException.ThrowIfNull(tokenSource);

        _httpClient = httpClient;
        _options = options.Value;
        _timeProvider = timeProvider;
        _tokenSource = tokenSource;

        var projectEndpoint = _options.ProjectEndpoint.TrimEnd('/');
        var agentName = Uri.EscapeDataString(_options.AgentName);
        _responsesEndpoint = new Uri(
            $"{projectEndpoint}/agents/{agentName}/endpoint/protocols/openai/responses?api-version=v1",
            UriKind.Absolute);
    }

    /// <inheritdoc />
    public async Task<FoundryReply> SendAsync(
        string message,
        string? conversationId,
        string? additionalInstructions,
        CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(message);

        using var timeoutCancellation =
            CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeoutCancellation.CancelAfter(_options.Timeout);

        try
        {
            var accessToken = await _tokenSource
                .GetTokenAsync(timeoutCancellation.Token)
                .ConfigureAwait(false);
            return await SendRequestAsync(
                    string.IsNullOrWhiteSpace(additionalInstructions)
                        ? message
                        : BuildInlineInstructionInput(message, additionalInstructions),
                    conversationId,
                    accessToken,
                    timeoutCancellation.Token)
                .ConfigureAwait(false);
        }
        catch (OperationCanceledException exception)
            when (!cancellationToken.IsCancellationRequested)
        {
            throw new FoundryTimeoutException(
                "The Foundry request exceeded the configured timeout.",
                exception);
        }
        catch (HttpRequestException exception)
        {
            throw new FoundryResponseException(
                "The Foundry API could not be reached.",
                exception);
        }
    }

    private async Task<FoundryReply> SendRequestAsync(
        string message,
        string? conversationId,
        string accessToken,
        CancellationToken cancellationToken)
    {
        var payload = JsonSerializer.SerializeToUtf8Bytes(
            new CreateResponseRequest(message, conversationId),
            ApiJsonContext.Default.CreateResponseRequest);
        using var response = await SendWithRetryAsync(
                _responsesEndpoint,
                payload,
                accessToken,
                cancellationToken)
            .ConfigureAwait(false);
        await using var responseStream = await response.Content
            .ReadAsStreamAsync(cancellationToken)
            .ConfigureAwait(false);

        return FoundryResponseParser.Parse(
            responseStream,
            _timeProvider);
    }

    private static string BuildInlineInstructionInput(
        string message,
        string additionalInstructions) =>
        """
        Request context for this synthetic-data POC response:
        """
        + Environment.NewLine
        + additionalInstructions
        + Environment.NewLine
        + Environment.NewLine
        + "User message:"
        + Environment.NewLine
        + message;

    private async Task<HttpResponseMessage> SendWithRetryAsync(
        Uri endpoint,
        byte[] payload,
        string accessToken,
        CancellationToken cancellationToken)
    {
        var idempotencyKey = Guid.NewGuid().ToString("N");

        for (var attempt = 0; ; attempt++)
        {
            using var request = CreateRequest(
                endpoint,
                payload,
                accessToken,
                idempotencyKey);
            var response = await _httpClient
                .SendAsync(
                    request,
                    HttpCompletionOption.ResponseHeadersRead,
                    cancellationToken)
                .ConfigureAwait(false);

            if (response.IsSuccessStatusCode)
            {
                return response;
            }

            if (!RetryableStatusCodes.Contains(response.StatusCode)
                || attempt >= _options.MaximumRetryCount)
            {
                var statusCode = response.StatusCode;
                var retryAfterSeconds = GetRetryAfterSeconds(response);
                var responseBody = await ReadSafeErrorBodyAsync(
                        response,
                        cancellationToken)
                    .ConfigureAwait(false);
                response.Dispose();
                throw new FoundryApiException(
                    statusCode,
                    retryAfterSeconds,
                    responseBody);
            }

            var retryDelay = GetRetryDelay(response, attempt);
            response.Dispose();
            await Task
                .Delay(retryDelay, _timeProvider, cancellationToken)
                .ConfigureAwait(false);
        }
    }

    private static async Task<string?> ReadSafeErrorBodyAsync(
        HttpResponseMessage response,
        CancellationToken cancellationToken)
    {
        var body = await response.Content
            .ReadAsStringAsync(cancellationToken)
            .ConfigureAwait(false);
        if (string.IsNullOrWhiteSpace(body))
        {
            return null;
        }

        return body.Length <= MaxErrorBodyLength
            ? body
            : body[..MaxErrorBodyLength];
    }

    private int? GetRetryAfterSeconds(HttpResponseMessage response)
    {
        var delay = response.Headers.RetryAfter?.Delta;
        if (delay is null && response.Headers.RetryAfter?.Date is { } date)
        {
            delay = date - _timeProvider.GetUtcNow();
        }

        return delay is null
            ? null
            : Math.Max(0, Convert.ToInt32(Math.Ceiling(delay.Value.TotalSeconds)));
    }

    private static HttpRequestMessage CreateRequest(
        Uri endpoint,
        byte[] payload,
        string accessToken,
        string idempotencyKey)
    {
        var request = new HttpRequestMessage(HttpMethod.Post, endpoint)
        {
            Content = new ByteArrayContent(payload),
        };
        request.Headers.Authorization =
            new AuthenticationHeaderValue("Bearer", accessToken);
        request.Headers.TryAddWithoutValidation(
            "Idempotency-Key",
            idempotencyKey);
        request.Content.Headers.ContentType =
            new MediaTypeHeaderValue("application/json");
        return request;
    }

    private TimeSpan GetRetryDelay(
        HttpResponseMessage response,
        int attempt)
    {
        if (response.Headers.RetryAfter?.Delta is { } delta)
        {
            return delta < TimeSpan.Zero ? TimeSpan.Zero : delta;
        }

        if (response.Headers.RetryAfter?.Date is { } date)
        {
            var delay = date - _timeProvider.GetUtcNow();
            return delay < TimeSpan.Zero ? TimeSpan.Zero : delay;
        }

        return TimeSpan.FromMilliseconds(250 * Math.Pow(2, attempt));
    }
}
