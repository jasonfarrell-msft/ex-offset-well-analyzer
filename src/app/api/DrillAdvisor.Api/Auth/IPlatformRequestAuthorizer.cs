using Microsoft.AspNetCore.Http;

namespace DrillAdvisor.Api.Auth;

/// <summary>
/// Authorizes requests using only platform-injected authentication context.
/// </summary>
public interface IPlatformRequestAuthorizer
{
    /// <summary>
    /// Verifies an anonymous browser call arrived through the linked Static Web App.
    /// </summary>
    PlatformAuthorizationResult AuthorizeChat(HttpRequest request);

    /// <summary>
    /// Verifies an MCP call represents the configured Foundry project identity.
    /// </summary>
    PlatformAuthorizationResult AuthorizeMcp(HttpRequest request);
}

/// <summary>
/// Represents a platform request-authorization decision.
/// </summary>
public sealed record PlatformAuthorizationResult(bool IsAuthorized, string FailureCode)
{
    /// <summary>
    /// Gets a successful decision.
    /// </summary>
    public static PlatformAuthorizationResult Allowed { get; } = new(true, string.Empty);
}
