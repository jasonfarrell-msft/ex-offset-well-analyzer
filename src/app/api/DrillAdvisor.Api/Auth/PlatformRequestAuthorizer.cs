using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using DrillAdvisor.Api.Configuration;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Options;

namespace DrillAdvisor.Api.Auth;

/// <summary>
/// Enforces route separation using trusted Easy Auth and Static Web Apps headers.
/// </summary>
public sealed class PlatformRequestAuthorizer(
    IOptions<PlatformAuthOptions> options,
    IPlatformEnvironment environment) : IPlatformRequestAuthorizer
{
    private const string ClientPrincipalHeader = "X-MS-CLIENT-PRINCIPAL";
    private const string ClientPrincipalIdHeader = "X-MS-CLIENT-PRINCIPAL-ID";
    private const string ClientPrincipalProviderHeader = "X-MS-CLIENT-PRINCIPAL-IDP";

    private readonly PlatformAuthOptions _options =
        options?.Value ?? throw new ArgumentNullException(nameof(options));
    private readonly IPlatformEnvironment _environment =
        environment ?? throw new ArgumentNullException(nameof(environment));

    /// <inheritdoc />
    public PlatformAuthorizationResult AuthorizeChat(HttpRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);

        if (!_environment.IsAzure && _options.AllowLocalAnonymous)
        {
            return PlatformAuthorizationResult.Allowed;
        }

        if (!_options.TrustedPlatformAuthEnabled)
        {
            return new(false, "trusted_platform_auth_not_enabled");
        }

        var headerProvider = request.Headers[ClientPrincipalProviderHeader].ToString();
        if (string.IsNullOrWhiteSpace(headerProvider)
            || !MatchesProvider(headerProvider, _options.StaticWebAppsBackendProvider))
        {
            return new(false, "swa_backend_provider_required");
        }

        var encodedPrincipal = request.Headers[ClientPrincipalHeader].ToString();
        if (!string.IsNullOrWhiteSpace(encodedPrincipal)
            && (!TryReadPrincipal(request, out var principal)
                || !MatchesProvider(
                    principal.IdentityProvider,
                    _options.StaticWebAppsAnonymousProvider)
                || !string.IsNullOrWhiteSpace(principal.UserId)
                || principal.UserRoles?.Contains(
                    "anonymous",
                    StringComparer.OrdinalIgnoreCase) != true))
        {
            return new(false, "swa_anonymous_principal_invalid");
        }

        return PlatformAuthorizationResult.Allowed;
    }

    /// <inheritdoc />
    public PlatformAuthorizationResult AuthorizeMcp(HttpRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);

        var headerProvider = request.Headers[ClientPrincipalProviderHeader].ToString();
        if (string.IsNullOrWhiteSpace(headerProvider)
            || !MatchesProvider(headerProvider, _options.FoundryIdentityProvider))
        {
            return new(false, "foundry_identity_provider_required");
        }

        var expectedPrincipalId = _options.FoundryProjectPrincipalId;
        var headerPrincipalId = request.Headers[ClientPrincipalIdHeader].ToString();
        if (string.IsNullOrWhiteSpace(expectedPrincipalId)
            || string.IsNullOrWhiteSpace(headerPrincipalId)
            || !MatchesPrincipal(headerPrincipalId, expectedPrincipalId))
        {
            return new(false, "foundry_principal_not_allowed");
        }

        if (TryReadPrincipal(request, out var principal))
        {
            var claimPrincipalId = principal.GetObjectId();
            if (!MatchesProvider(principal.IdentityProvider, _options.FoundryIdentityProvider)
                || (!string.IsNullOrWhiteSpace(claimPrincipalId)
                    && !MatchesPrincipal(claimPrincipalId, expectedPrincipalId)))
            {
                return new(false, "foundry_principal_not_allowed");
            }
        }

        return PlatformAuthorizationResult.Allowed;
    }

    private static bool TryReadPrincipal(
        HttpRequest request,
        out StaticWebAppsPrincipal principal)
    {
        principal = StaticWebAppsPrincipal.Empty;
        var encoded = request.Headers[ClientPrincipalHeader].ToString();
        if (string.IsNullOrWhiteSpace(encoded))
        {
            return false;
        }

        try
        {
            var padded = encoded.PadRight(encoded.Length + ((4 - (encoded.Length % 4)) % 4), '=');
            var json = Encoding.UTF8.GetString(Convert.FromBase64String(padded));
            principal = JsonSerializer.Deserialize<StaticWebAppsPrincipal>(
                    json,
                    PrincipalJsonOptions)
                ?? StaticWebAppsPrincipal.Empty;
            return !string.IsNullOrWhiteSpace(principal.IdentityProvider);
        }
        catch (FormatException)
        {
            return false;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    private static bool MatchesProvider(string? actual, string expected) =>
        string.Equals(actual, expected, StringComparison.OrdinalIgnoreCase);

    private static bool MatchesPrincipal(string actual, string expected) =>
        string.Equals(actual, expected, StringComparison.OrdinalIgnoreCase);

    private static JsonSerializerOptions PrincipalJsonOptions { get; } =
        new(JsonSerializerDefaults.Web);

    private sealed record StaticWebAppsPrincipal(
        string? IdentityProvider,
        string? UserId,
        IReadOnlyList<string>? UserRoles,
        IReadOnlyList<StaticWebAppsClaim>? Claims)
    {
        public static StaticWebAppsPrincipal Empty { get; } =
            new(null, null, [], []);

        public string? GetObjectId() =>
            Claims?.FirstOrDefault(
                claim =>
                    string.Equals(claim.Type, "oid", StringComparison.OrdinalIgnoreCase)
                    || string.Equals(
                        claim.Type,
                        "http://schemas.microsoft.com/identity/claims/objectidentifier",
                        StringComparison.OrdinalIgnoreCase))?.Value;
    }

    private sealed record StaticWebAppsClaim(
        [property: JsonPropertyName("typ")] string? Type,
        [property: JsonPropertyName("val")] string? Value);
}
