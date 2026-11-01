using System.Net;
using Azure.Core;
using DrillAdvisor.Api.Auth;
using DrillAdvisor.Api.Foundry;
using DrillAdvisor.Api.Identity;
using DrillAdvisor.Api.Limits;
using DrillAdvisor.Api.Models;
using Microsoft.AspNetCore.Http;

namespace DrillAdvisor.Api.Tests;

internal sealed class StubPlatformAuthorizer : IPlatformRequestAuthorizer
{
    public PlatformAuthorizationResult ChatResult { get; set; } =
        PlatformAuthorizationResult.Allowed;

    public PlatformAuthorizationResult McpResult { get; set; } =
        PlatformAuthorizationResult.Allowed;

    public PlatformAuthorizationResult AuthorizeChat(HttpRequest request) =>
        ChatResult;

    public PlatformAuthorizationResult AuthorizeMcp(HttpRequest request) =>
        McpResult;
}

internal sealed class StubPlatformEnvironment(bool isAzure) : IPlatformEnvironment
{
    public bool IsAzure { get; } = isAzure;
}

internal sealed class StubSourceIdentifier(string sourceKey = "source")
    : IClientSourceIdentifier
{
    public string GetSourceKey(HttpRequest request) => sourceKey;
}

internal sealed class StubChatGate : IAnonymousChatGate
{
    public ChatAdmission Admission { get; set; } =
        ChatAdmission.Allowed(new StubLease());

    public ChatAdmission TryAcquire(string sourceKey) => Admission;

    private sealed class StubLease : IDisposable
    {
        public void Dispose()
        {
        }
    }
}

internal sealed class StubFoundryClient(FoundryReply reply) : IFoundryClient
{
    public int CallCount { get; private set; }

    public string? LastAdditionalInstructions { get; private set; }

    public Exception? ExceptionToThrow { get; set; }

    public Task<FoundryReply> SendAsync(
        string message,
        string? conversationId,
        string? additionalInstructions,
        CancellationToken cancellationToken)
    {
        CallCount++;
        LastAdditionalInstructions = additionalInstructions;
        if (ExceptionToThrow is not null)
        {
            throw ExceptionToThrow;
        }

        return Task.FromResult(reply);
    }
}

internal sealed class StubFoundryTokenSource(string token) : IFoundryTokenSource
{
    public int CallCount { get; private set; }

    public ValueTask<string> GetTokenAsync(CancellationToken cancellationToken)
    {
        CallCount++;
        return ValueTask.FromResult(token);
    }
}

internal sealed class StubFabricTokenSource(string token) : IFabricTokenSource
{
    public int CallCount { get; private set; }

    public ValueTask<string> GetTokenAsync(CancellationToken cancellationToken)
    {
        CallCount++;
        return ValueTask.FromResult(token);
    }
}

internal sealed class StubTokenCredential(string token) : TokenCredential
{
    public IReadOnlyList<string>? LastScopes { get; private set; }

    public override AccessToken GetToken(
        TokenRequestContext requestContext,
        CancellationToken cancellationToken)
    {
        LastScopes = requestContext.Scopes;
        return new AccessToken(token, DateTimeOffset.UtcNow.AddMinutes(30));
    }

    public override ValueTask<AccessToken> GetTokenAsync(
        TokenRequestContext requestContext,
        CancellationToken cancellationToken) =>
        ValueTask.FromResult(GetToken(requestContext, cancellationToken));
}

internal sealed class AdjustableTimeProvider(DateTimeOffset utcNow) : TimeProvider
{
    private DateTimeOffset _utcNow = utcNow;

    public override DateTimeOffset GetUtcNow() => _utcNow;

    public void Advance(TimeSpan duration) => _utcNow += duration;
}

internal sealed class SequenceHttpMessageHandler(
    params Func<HttpRequestMessage, HttpResponseMessage>[] responses)
    : HttpMessageHandler
{
    private int _index;

    public List<CapturedRequest> Requests { get; } = [];

    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        var body = request.Content is null
            ? null
            : await request.Content
                .ReadAsStringAsync(cancellationToken)
                .ConfigureAwait(false);
        Requests.Add(
            new CapturedRequest(
                request.RequestUri!,
                request.Method,
                request.Headers.Authorization?.Scheme,
                request.Headers.Authorization?.Parameter,
                request.Headers.TryGetValues("Idempotency-Key", out var values)
                    ? values.Single()
                    : null,
                request.Headers.ToDictionary(
                    header => header.Key,
                    header => header.Value.ToArray(),
                    StringComparer.OrdinalIgnoreCase),
                request.Content?.Headers.ContentType?.ToString(),
                body));

        var responseFactory = responses[Math.Min(_index, responses.Length - 1)];
        _index++;
        var response = responseFactory(request);
        response.RequestMessage = request;
        return response;
    }
}

internal sealed record CapturedRequest(
    Uri Uri,
    HttpMethod Method,
    string? AuthorizationScheme,
    string? AuthorizationParameter,
    string? IdempotencyKey,
    IReadOnlyDictionary<string, string[]> Headers,
    string? ContentType,
    string? Body);

internal static class HttpResponses
{
    public static HttpResponseMessage Json(
        HttpStatusCode statusCode,
        string json)
    {
        var response = new HttpResponseMessage(statusCode)
        {
            Content = new StringContent(
                json,
                System.Text.Encoding.UTF8,
                "application/json"),
        };
        return response;
    }
}
