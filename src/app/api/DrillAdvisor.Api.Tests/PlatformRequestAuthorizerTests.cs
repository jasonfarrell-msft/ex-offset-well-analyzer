using System.Text;
using System.Text.Json;
using DrillAdvisor.Api.Auth;
using DrillAdvisor.Api.Configuration;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Options;

namespace DrillAdvisor.Api.Tests;

public sealed class PlatformRequestAuthorizerTests
{
    private const string FoundryPrincipalId =
        "11111111-1111-1111-1111-111111111111";

    [Fact]
    public void AuthorizeChat_LocalBypassRequiresExplicitSetting()
    {
        var request = new DefaultHttpContext().Request;

        var denied = CreateAuthorizer(allowLocal: false, isAzure: false)
            .AuthorizeChat(request);
        var allowed = CreateAuthorizer(allowLocal: true, isAzure: false)
            .AuthorizeChat(request);

        Assert.False(denied.IsAuthorized);
        Assert.True(allowed.IsAuthorized);
    }

    [Fact]
    public void AuthorizeChat_AzureAcceptsOnlyAnonymousSwaPrincipal()
    {
        var anonymous = CreateRequest(
            provider: "anonymous",
            userId: string.Empty,
            roles: ["anonymous"],
            headerProvider: "azureStaticWebApps");
        var directEntra = CreateRequest(
            provider: "aad",
            userId: FoundryPrincipalId,
            roles: ["authenticated"]);

        var authorizer = CreateAuthorizer(allowLocal: true, isAzure: true);

        Assert.True(authorizer.AuthorizeChat(anonymous).IsAuthorized);
        Assert.False(authorizer.AuthorizeChat(directEntra).IsAuthorized);
    }

    [Fact]
    public void AuthorizeChat_AzureAcceptsLinkedBackendWithoutAnonymousPrincipal()
    {
        var context = new DefaultHttpContext();
        context.Request.Headers["X-MS-CLIENT-PRINCIPAL-IDP"] =
            "azureStaticWebApps";
        var authorizer = CreateAuthorizer(allowLocal: false, isAzure: true);

        var result = authorizer.AuthorizeChat(context.Request);

        Assert.True(result.IsAuthorized);
    }

    [Fact]
    public void AuthorizeChat_AzureRejectsMalformedOptionalPrincipal()
    {
        var context = new DefaultHttpContext();
        context.Request.Headers["X-MS-CLIENT-PRINCIPAL-IDP"] =
            "azureStaticWebApps";
        context.Request.Headers["X-MS-CLIENT-PRINCIPAL"] = "not-base64";
        var authorizer = CreateAuthorizer(allowLocal: false, isAzure: true);

        var result = authorizer.AuthorizeChat(context.Request);

        Assert.False(result.IsAuthorized);
        Assert.Equal("swa_anonymous_principal_invalid", result.FailureCode);
    }

    [Fact]
    public void AuthorizeChat_AzureAcceptsLinkedBackendPrincipalId()
    {
        var context = new DefaultHttpContext();
        context.Request.Headers["X-MS-CLIENT-PRINCIPAL-IDP"] =
            "azureStaticWebApps";
        context.Request.Headers["X-MS-CLIENT-PRINCIPAL-ID"] =
            FoundryPrincipalId;
        var authorizer = CreateAuthorizer(allowLocal: false, isAzure: true);
        var result = authorizer.AuthorizeChat(context.Request);

        Assert.True(result.IsAuthorized);
    }

    [Fact]
    public void AuthorizeChat_AzureFailsClosedUntilPlatformBoundaryIsConfirmed()
    {
        var request = CreateRequest(
            provider: "anonymous",
            userId: string.Empty,
            roles: ["anonymous"]);
        var authorizer = CreateAuthorizer(
            allowLocal: false,
            isAzure: true,
            trustedPlatformAuthEnabled: false);

        var result = authorizer.AuthorizeChat(request);

        Assert.False(result.IsAuthorized);
        Assert.Equal("trusted_platform_auth_not_enabled", result.FailureCode);
    }

    [Fact]
    public void AuthorizeMcp_RequiresConfiguredProviderAndPrincipal()
    {
        var allowed = CreateRequest(
            provider: "aad",
            userId: FoundryPrincipalId,
            roles: ["authenticated"],
            principalId: FoundryPrincipalId);
        var wrongPrincipal = CreateRequest(
            provider: "aad",
            userId: "22222222-2222-2222-2222-222222222222",
            roles: ["authenticated"],
            principalId: "22222222-2222-2222-2222-222222222222");
        var anonymous = CreateRequest(
            provider: "anonymous",
            userId: string.Empty,
            roles: ["anonymous"]);

        var authorizer = CreateAuthorizer(allowLocal: false, isAzure: true);

        Assert.True(authorizer.AuthorizeMcp(allowed).IsAuthorized);
        Assert.False(authorizer.AuthorizeMcp(wrongPrincipal).IsAuthorized);
        Assert.False(authorizer.AuthorizeMcp(anonymous).IsAuthorized);
    }

    [Fact]
    public void AuthorizeMcp_RemainsAvailableBeforePublicChatCutover()
    {
        var request = CreateRequest(
            provider: "aad",
            userId: FoundryPrincipalId,
            roles: ["authenticated"],
            principalId: FoundryPrincipalId);
        var authorizer = CreateAuthorizer(
            allowLocal: false,
            isAzure: true,
            trustedPlatformAuthEnabled: false);

        var result = authorizer.AuthorizeMcp(request);

        Assert.True(result.IsAuthorized);
    }

    [Fact]
    public void AuthorizeMcp_AcceptsEasyAuthProviderAndPrincipalHeaders()
    {
        var context = new DefaultHttpContext();
        context.Request.Headers["X-MS-CLIENT-PRINCIPAL-IDP"] = "aad";
        context.Request.Headers["X-MS-CLIENT-PRINCIPAL-ID"] = FoundryPrincipalId;
        var authorizer = CreateAuthorizer(allowLocal: false, isAzure: true);

        var result = authorizer.AuthorizeMcp(context.Request);

        Assert.True(result.IsAuthorized);
    }

    private static PlatformRequestAuthorizer CreateAuthorizer(
        bool allowLocal,
        bool isAzure,
        bool trustedPlatformAuthEnabled = true) =>
        new(
            Options.Create(
                new PlatformAuthOptions
                {
                    TrustedPlatformAuthEnabled = trustedPlatformAuthEnabled,
                    AllowLocalAnonymous = allowLocal,
                    StaticWebAppsAnonymousProvider = "anonymous",
                    StaticWebAppsBackendProvider = "azureStaticWebApps",
                    FoundryIdentityProvider = "aad",
                    FoundryProjectPrincipalId = FoundryPrincipalId,
                }),
            new StubPlatformEnvironment(isAzure));

    private static HttpRequest CreateRequest(
        string provider,
        string userId,
        IReadOnlyList<string> roles,
        string? principalId = null,
        string? headerProvider = null)
    {
        var context = new DefaultHttpContext();
        var principal = JsonSerializer.Serialize(
            new
            {
                identityProvider = provider,
                userId,
                userRoles = roles,
                claims = Array.Empty<object>(),
            });
        context.Request.Headers["X-MS-CLIENT-PRINCIPAL"] =
            Convert.ToBase64String(Encoding.UTF8.GetBytes(principal));
        context.Request.Headers["X-MS-CLIENT-PRINCIPAL-IDP"] =
            headerProvider ?? provider;
        if (principalId is not null)
        {
            context.Request.Headers["X-MS-CLIENT-PRINCIPAL-ID"] = principalId;
        }

        return context.Request;
    }
}
