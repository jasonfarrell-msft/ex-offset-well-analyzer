using Azure.Core;
using Azure.Identity;
using DrillAdvisor.Api.Configuration;
using DrillAdvisor.Api.Fabric;
using DrillAdvisor.Api.Foundry;
using DrillAdvisor.Api.Identity;
using DrillAdvisor.Api.Limits;
using DrillAdvisor.Api.Offset;
using DrillAdvisor.Web.Auth;
using DrillAdvisor.Web.Configuration;
using DrillAdvisor.Web.Endpoints;
using DrillAdvisor.Web.Limits;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);
var configuration = builder.Configuration;

builder.Services
    .AddOptions<FoundryOptions>()
    .Configure(options =>
    {
        options.ProjectEndpoint = configuration["FOUNDRY_PROJECT_ENDPOINT"] ?? string.Empty;
        options.AgentName = configuration["FOUNDRY_AGENT_NAME"] ?? string.Empty;
        options.Timeout = TimeSpan.FromSeconds(210);
    })
    .Validate(
        options => Uri.TryCreate(options.ProjectEndpoint, UriKind.Absolute, out var endpoint)
            && endpoint.Scheme == Uri.UriSchemeHttps,
        "FOUNDRY_PROJECT_ENDPOINT must be an absolute HTTPS URI.")
    .Validate(
        options => !string.IsNullOrWhiteSpace(options.AgentName),
        "FOUNDRY_AGENT_NAME is required.")
    .ValidateOnStart();

builder.Services
    .AddOptions<FabricRelayOptions>()
    .Configure(options =>
    {
        options.Endpoint = configuration["FABRIC_DATA_AGENT_MCP_ENDPOINT"] ?? string.Empty;
    })
    .Validate(
        options => Uri.TryCreate(options.Endpoint, UriKind.Absolute, out var endpoint)
            && endpoint.Scheme == Uri.UriSchemeHttps,
        "FABRIC_DATA_AGENT_MCP_ENDPOINT must be an absolute HTTPS URI.")
    .ValidateOnStart();

builder.Services
    .AddOptions<ServiceIdentityOptions>()
    .Configure(options =>
    {
        options.ManagedIdentityClientId =
            configuration["MANAGED_IDENTITY_CLIENT_ID"] ?? string.Empty;
        options.TenantId = configuration["ENTRA_TENANT_ID"] ?? string.Empty;
        options.FabricAppClientId =
            configuration["FABRIC_APP_CLIENT_ID"] ?? string.Empty;
        options.FabricTokenScope =
            configuration["FABRIC_TOKEN_SCOPE"]
            ?? FabricTokenSource.PowerBiScope;
    })
    .Validate(
        options => Guid.TryParse(options.ManagedIdentityClientId, out _),
        "MANAGED_IDENTITY_CLIENT_ID must be a GUID.")
    .Validate(
        options => Guid.TryParse(options.TenantId, out _),
        "ENTRA_TENANT_ID must be a GUID.")
    .Validate(
        options => Guid.TryParse(options.FabricAppClientId, out _),
        "FABRIC_APP_CLIENT_ID must be a GUID.")
    .Validate(
        options => FabricTokenSource.IsSupportedScope(options.FabricTokenScope),
        "FABRIC_TOKEN_SCOPE must be one of the two supported Fabric resource scopes.")
    .ValidateOnStart();

builder.Services
    .AddOptions<OffsetAnalysisSqlOptions>()
    .Configure(options =>
    {
        options.Server = configuration["OFFSET_SQL_SERVER"] ?? string.Empty;
        options.Database = configuration["OFFSET_SQL_DATABASE"] ?? string.Empty;
        if (int.TryParse(
                configuration["OFFSET_SQL_COMMAND_TIMEOUT_SECONDS"],
                out var timeoutSeconds)
            && timeoutSeconds >= 5
            && timeoutSeconds <= 300)
        {
            options.CommandTimeoutSeconds = timeoutSeconds;
        }
    });

builder.Services
    .AddOptions<McpAuthorizationOptions>()
    .Configure(options =>
    {
        options.TenantId = configuration["ENTRA_TENANT_ID"] ?? string.Empty;
        options.Audience = configuration["MCP_AUDIENCE"] ?? string.Empty;
        options.RequiredRole =
            configuration["MCP_REQUIRED_ROLE"] ?? "Mcp.Invoke";
        options.ExpectedPrincipalId =
            configuration["FOUNDRY_PROJECT_PRINCIPAL_ID"] ?? string.Empty;
        options.ExpectedClientId =
            configuration["FOUNDRY_PROJECT_CLIENT_ID"];
    })
    .Validate(
        options => Guid.TryParse(options.TenantId, out _),
        "ENTRA_TENANT_ID must be a GUID.")
    .Validate(
        options => Uri.TryCreate(options.Audience, UriKind.Absolute, out var audience)
            && string.Equals(audience.Scheme, "api", StringComparison.Ordinal),
        "MCP_AUDIENCE must be an api:// application ID URI.")
    .Validate(
        options => string.Equals(options.RequiredRole, "Mcp.Invoke", StringComparison.Ordinal),
        "MCP_REQUIRED_ROLE must be Mcp.Invoke.")
    .Validate(
        options => Guid.TryParse(options.ExpectedPrincipalId, out _),
        "FOUNDRY_PROJECT_PRINCIPAL_ID must be a GUID.")
    .Validate(
        options => string.IsNullOrWhiteSpace(options.ExpectedClientId)
            || Guid.TryParse(options.ExpectedClientId, out _),
        "FOUNDRY_PROJECT_CLIENT_ID must be a GUID when provided.")
    .ValidateOnStart();

builder.Services
    .AddOptions<PublicChatOptions>()
    .Configure(options =>
    {
        options.Enabled =
            bool.TryParse(configuration["PUBLIC_CHAT_ENABLED"], out var enabled)
            && enabled;
    })
    .Validate(
        options =>
            options.PerSourcePerMinute == 3
            && options.PerSourceConcurrency == 1
            && options.GlobalPerMinute == 60
            && options.GlobalConcurrency == 10
            && options.DailyFoundryCalls == 500,
        "Public chat limits must match the approved single-replica POC limits.")
    .ValidateOnStart();

builder.Services
    .AddOptions<PublicOffsetAnalysisOptions>()
    .Configure(options =>
    {
        options.Enabled =
            bool.TryParse(configuration["PUBLIC_CHAT_ENABLED"], out var enabled)
            && enabled;
    })
    .Validate(
        options =>
            options.PerSourcePerMinute == 6
            && options.PerSourceConcurrency == 1
            && options.GlobalPerMinute == 90
            && options.GlobalConcurrency == 10,
        "Offset-analysis limits must match the approved single-replica POC limits.")
    .ValidateOnStart();

var tenantId = configuration["ENTRA_TENANT_ID"] ?? string.Empty;
var audience = configuration["MCP_AUDIENCE"] ?? string.Empty;
var authority = $"https://login.microsoftonline.com/{tenantId}/v2.0";
builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = authority;
        options.Audience = audience;
        options.MapInboundClaims = false;
        options.RequireHttpsMetadata = true;
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidIssuers =
            [
                $"https://login.microsoftonline.com/{tenantId}/v2.0",
                $"https://sts.windows.net/{tenantId}/",
            ],
            ValidateAudience = true,
            ValidAudience = audience,
            ValidateIssuerSigningKey = true,
            ValidateLifetime = true,
            RequireExpirationTime = true,
            RequireSignedTokens = true,
            ClockSkew = TimeSpan.FromMinutes(2),
        };
    });
builder.Services
    .AddAuthorizationBuilder()
    .AddPolicy(
        "FoundryMcp",
        policy =>
        {
            policy.RequireAuthenticatedUser();
            policy.AddRequirements(new McpCallerRequirement());
        });
builder.Services.AddSingleton<Microsoft.AspNetCore.Authorization.IAuthorizationHandler, McpCallerAuthorizationHandler>();

builder.Services.Configure<ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
    options.ForwardLimit = 1;
    options.KnownIPNetworks.Clear();
    options.KnownProxies.Clear();
});

builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton<IClientSourceIdentifier, RemoteIpSourceIdentifier>();
builder.Services.AddSingleton<IAnonymousChatGate, AnonymousChatGate>();
builder.Services.AddSingleton<IAnonymousOffsetAnalysisGate, AnonymousOffsetAnalysisGate>();
builder.Services.AddSingleton<TokenCredential>(services =>
{
    var identity = services.GetRequiredService<IOptions<ServiceIdentityOptions>>().Value;
    return string.IsNullOrWhiteSpace(configuration["IDENTITY_ENDPOINT"])
        ? new AzureCliCredential(
            new AzureCliCredentialOptions
            {
                TenantId = identity.TenantId,
            })
        : new ManagedIdentityCredential(identity.ManagedIdentityClientId);
});
builder.Services.AddSingleton<IFoundryTokenSource, FoundryTokenSource>();
builder.Services.AddSingleton<IOffsetAnalysisDataSource, SqlOffsetAnalysisDataSource>();
builder.Services.AddSingleton<IOffsetAnalysisService, OffsetAnalysisService>();
builder.Services.AddSingleton<IFabricTokenSource>(services =>
{
    var identity = services.GetRequiredService<IOptions<ServiceIdentityOptions>>().Value;
    return new FabricTokenSource(
        services.GetRequiredService<TokenCredential>(),
        identity.TenantId,
        identity.FabricAppClientId,
        identity.FabricTokenScope);
});
builder.Services
    .AddHttpClient<IFoundryClient, FoundryClient>(
        client => client.Timeout = Timeout.InfiniteTimeSpan);
builder.Services
    .AddHttpClient<IFabricMcpRelayClient, FabricMcpRelayClient>(
        client => client.Timeout = Timeout.InfiniteTimeSpan);

var app = builder.Build();

app.UseForwardedHeaders();
app.Use(async (context, next) =>
{
    context.Response.Headers.XContentTypeOptions = "nosniff";
    context.Response.Headers.XFrameOptions = "DENY";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    await next(context).ConfigureAwait(false);
});
app.UseDefaultFiles();
app.UseStaticFiles();
app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/healthz", () => Results.Ok(new { status = "healthy" }));
app.MapGet("/readyz", () => Results.Ok(new { status = "ready" }));
app.MapPost("/api/chat", ChatEndpoint.HandleAsync)
    .AllowAnonymous()
    .DisableAntiforgery();
app.MapPost("/api/offset-analysis", OffsetAnalysisEndpoint.HandleAsync)
    .AllowAnonymous()
    .DisableAntiforgery();
app.MapMethods(
        "/api/mcp/fabric-dataagent",
        [HttpMethods.Get, HttpMethods.Post, HttpMethods.Delete],
        FabricMcpEndpoint.HandleAsync)
    .RequireAuthorization("FoundryMcp")
    .DisableAntiforgery();
app.Map("/api/{**path}", () => Results.NotFound());
app.MapFallbackToFile("index.html");

await app.RunAsync().ConfigureAwait(false);

/// <summary>
/// Exposes the entry point to integration tests.
/// </summary>
public partial class Program;
