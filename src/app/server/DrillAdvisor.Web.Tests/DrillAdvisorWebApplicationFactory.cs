using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using DrillAdvisor.Api.Fabric;
using DrillAdvisor.Api.Foundry;
using DrillAdvisor.Api.Offset;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Protocols;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;
using Microsoft.IdentityModel.Tokens;

namespace DrillAdvisor.Web.Tests;

internal sealed class DrillAdvisorWebApplicationFactory : WebApplicationFactory<Program>
{
    public const string TenantId = "11111111-1111-1111-1111-111111111111";
    public const string Audience = "api://0e956ed5-6da6-477a-b508-3c6cdf5b2861";
    public const string PrincipalId = "f9b86896-cc12-4a2f-92ff-edf9d5e570ef";
    public const string ClientId = "22222222-2222-2222-2222-222222222222";
    private const string SigningSecret =
        "DrillAdvisorTestsOnly-SymmetricSigningKey-2026!";

    private readonly IReadOnlyDictionary<string, string?> _overrides;
    private readonly IOffsetAnalysisService? _offsetAnalysisServiceOverride;

    public DrillAdvisorWebApplicationFactory(
        IReadOnlyDictionary<string, string?>? overrides = null,
        IOffsetAnalysisService? offsetAnalysisServiceOverride = null)
    {
        _overrides = overrides ?? new Dictionary<string, string?>();
        _offsetAnalysisServiceOverride = offsetAnalysisServiceOverride;
    }

    public StubFoundryClient FoundryClient { get; } = new();

    public StubFabricMcpRelayClient RelayClient { get; } = new();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        builder.UseWebRoot(Path.Combine(AppContext.BaseDirectory, "TestWebRoot"));
        builder.ConfigureAppConfiguration((_, configuration) =>
        {
            var settings = new Dictionary<string, string?>
            {
                ["ENTRA_TENANT_ID"] = TenantId,
                ["MANAGED_IDENTITY_CLIENT_ID"] =
                    "33333333-3333-3333-3333-333333333333",
                ["FABRIC_APP_CLIENT_ID"] =
                    "44444444-4444-4444-4444-444444444444",
                ["FABRIC_TOKEN_SCOPE"] =
                    "https://api.fabric.microsoft.com/.default",
                ["FOUNDRY_PROJECT_PRINCIPAL_ID"] = PrincipalId,
                ["FOUNDRY_PROJECT_CLIENT_ID"] = ClientId,
                ["FOUNDRY_PROJECT_ENDPOINT"] =
                    "https://example.services.ai.azure.com/api/projects/test",
                ["FOUNDRY_AGENT_NAME"] = "test-agent",
                ["FABRIC_DATA_AGENT_MCP_ENDPOINT"] =
                    "https://api.fabric.microsoft.com/v1/mcp/workspaces/fixed/dataagents/fixed/agent",
                ["MCP_AUDIENCE"] = Audience,
                ["MCP_REQUIRED_ROLE"] = "Mcp.Invoke",
                ["PUBLIC_CHAT_ENABLED"] = "true",
            };
            foreach (var setting in _overrides)
            {
                settings[setting.Key] = setting.Value;
            }

            configuration.AddInMemoryCollection(settings);
        });
        builder.ConfigureServices(services =>
        {
            services.RemoveAll<IFoundryClient>();
            services.RemoveAll<IFabricMcpRelayClient>();
            services.RemoveAll<IOffsetAnalysisDataSource>();
            services.RemoveAll<IOffsetAnalysisService>();
            services.AddSingleton<IFoundryClient>(FoundryClient);
            services.AddSingleton<IFabricMcpRelayClient>(RelayClient);
            if (_offsetAnalysisServiceOverride is null)
            {
                services.AddSingleton<IOffsetAnalysisDataSource, StubOffsetAnalysisDataSource>();
                services.AddSingleton<IOffsetAnalysisService, OffsetAnalysisService>();
            }
            else
            {
                services.AddSingleton(_offsetAnalysisServiceOverride);
            }
            services.AddSingleton<IPostConfigureOptions<JwtBearerOptions>>(
                new ConfigureTestJwtBearerOptions());
        });
    }

    public static string CreateAccessToken(
        string audience = Audience,
        string role = "Mcp.Invoke",
        string principalId = PrincipalId,
        string clientId = ClientId,
        DateTime? expires = null)
    {
        var credentials = new SigningCredentials(
            CreateSigningKey(),
            SecurityAlgorithms.HmacSha256);
        var expiresAt = expires ?? DateTime.UtcNow.AddMinutes(5);
        var descriptor = new SecurityTokenDescriptor
        {
            Issuer = $"https://login.microsoftonline.com/{TenantId}/v2.0",
            Audience = audience,
            Subject = new ClaimsIdentity(
            [
                new Claim("roles", role),
                new Claim("oid", principalId),
                new Claim("azp", clientId),
            ]),
            NotBefore = expiresAt.AddMinutes(-5),
            Expires = expiresAt,
            SigningCredentials = credentials,
        };
        return new JwtSecurityTokenHandler().CreateEncodedJwt(descriptor);
    }

    private static SymmetricSecurityKey CreateSigningKey() =>
        new(Encoding.UTF8.GetBytes(SigningSecret));

    private sealed class ConfigureTestJwtBearerOptions
        : IPostConfigureOptions<JwtBearerOptions>
    {
        public void PostConfigure(string? name, JwtBearerOptions options)
        {
            if (!string.Equals(
                    name,
                    JwtBearerDefaults.AuthenticationScheme,
                    StringComparison.Ordinal))
            {
                return;
            }

            var configuration = new OpenIdConnectConfiguration
            {
                Issuer =
                    $"https://login.microsoftonline.com/{TenantId}/v2.0",
            };
            configuration.SigningKeys.Add(CreateSigningKey());
            options.ConfigurationManager =
                new StaticConfigurationManager<OpenIdConnectConfiguration>(
                    configuration);
            options.TokenValidationParameters.ValidAudience = Audience;
            options.TokenValidationParameters.ValidIssuers =
            [
                $"https://login.microsoftonline.com/{TenantId}/v2.0",
                $"https://sts.windows.net/{TenantId}/",
            ];
        }
    }
}
