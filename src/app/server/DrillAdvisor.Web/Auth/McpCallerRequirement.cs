using System.Security.Claims;
using DrillAdvisor.Web.Configuration;
using Microsoft.AspNetCore.Authorization;
using Microsoft.Extensions.Options;

namespace DrillAdvisor.Web.Auth;

/// <summary>
/// Requires the configured Foundry managed identity and application role.
/// </summary>
public sealed class McpCallerRequirement : IAuthorizationRequirement;

/// <summary>
/// Validates authorization claims that are specific to the MCP relay caller.
/// </summary>
public sealed class McpCallerAuthorizationHandler(
    IOptions<McpAuthorizationOptions> options)
    : AuthorizationHandler<McpCallerRequirement>
{
    private readonly McpAuthorizationOptions _options =
        options?.Value ?? throw new ArgumentNullException(nameof(options));

    /// <inheritdoc />
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context,
        McpCallerRequirement requirement)
    {
        var objectId = GetClaim(context.User, "oid")
            ?? GetClaim(
                context.User,
                "http://schemas.microsoft.com/identity/claims/objectidentifier");
        var hasRequiredRole = context.User
            .FindAll("roles")
            .Any(claim => string.Equals(
                claim.Value,
                _options.RequiredRole,
                StringComparison.Ordinal));

        if (!hasRequiredRole
            || !string.Equals(
                objectId,
                _options.ExpectedPrincipalId,
                StringComparison.OrdinalIgnoreCase))
        {
            return Task.CompletedTask;
        }

        var clientId = GetClaim(context.User, "azp")
            ?? GetClaim(context.User, "appid");
        if (!string.IsNullOrWhiteSpace(_options.ExpectedClientId)
            && clientId is not null
            && !string.Equals(
                clientId,
                _options.ExpectedClientId,
                StringComparison.OrdinalIgnoreCase))
        {
            return Task.CompletedTask;
        }

        context.Succeed(requirement);
        return Task.CompletedTask;
    }

    private static string? GetClaim(ClaimsPrincipal principal, string claimType) =>
        principal.FindFirst(claimType)?.Value;
}
