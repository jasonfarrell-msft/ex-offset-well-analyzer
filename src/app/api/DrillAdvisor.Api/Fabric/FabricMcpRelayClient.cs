using System.Net.Http.Headers;
using DrillAdvisor.Api.Configuration;
using DrillAdvisor.Api.Identity;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Options;

namespace DrillAdvisor.Api.Fabric;

/// <summary>
/// Relays only protocol headers and body content to one configured Fabric endpoint.
/// </summary>
public sealed class FabricMcpRelayClient(
    HttpClient httpClient,
    IOptions<FabricRelayOptions> options,
    IFabricTokenSource tokenSource) : IFabricMcpRelayClient
{
    private static readonly string[] ForwardedHeaders =
    [
        "MCP-Protocol-Version",
        "MCP-Session-Id",
        "Last-Event-ID",
    ];

    private readonly HttpClient _httpClient =
        httpClient ?? throw new ArgumentNullException(nameof(httpClient));
    private readonly Uri _endpoint = new(
        options?.Value.Endpoint
            ?? throw new ArgumentNullException(nameof(options)),
        UriKind.Absolute);
    private readonly IFabricTokenSource _tokenSource =
        tokenSource ?? throw new ArgumentNullException(nameof(tokenSource));

    /// <inheritdoc />
    public async Task<HttpResponseMessage> ForwardAsync(
        HttpRequest request,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);

        var token = await _tokenSource
            .GetTokenAsync(cancellationToken)
            .ConfigureAwait(false);
        var method = new HttpMethod(request.Method);
        using var relayRequest = new HttpRequestMessage(method, _endpoint);
        relayRequest.Headers.Authorization =
            new AuthenticationHeaderValue("Bearer", token);

        if (request.Headers.Accept.Count > 0)
        {
            relayRequest.Headers.TryAddWithoutValidation(
                "Accept",
                request.Headers.Accept.ToArray());
        }

        foreach (var header in ForwardedHeaders)
        {
            if (request.Headers.TryGetValue(header, out var values))
            {
                relayRequest.Headers.TryAddWithoutValidation(
                    header,
                    values.ToArray());
            }
        }

        if (HttpMethods.IsPost(request.Method))
        {
            relayRequest.Content = new StreamContent(request.Body);
            if (!string.IsNullOrWhiteSpace(request.ContentType))
            {
                relayRequest.Content.Headers.ContentType =
                    MediaTypeHeaderValue.Parse(request.ContentType);
            }
        }

        return await _httpClient
            .SendAsync(
                relayRequest,
                HttpCompletionOption.ResponseHeadersRead,
                cancellationToken)
            .ConfigureAwait(false);
    }
}
