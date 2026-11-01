using Azure.Core;
using Azure.Identity;
using DrillAdvisor.Api.Auth;
using DrillAdvisor.Api.Configuration;
using DrillAdvisor.Api.Fabric;
using DrillAdvisor.Api.Foundry;
using DrillAdvisor.Api.Identity;
using DrillAdvisor.Api.Limits;
using Microsoft.Azure.Functions.Worker.Builder;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;

var builder = FunctionsApplication.CreateBuilder(args);

builder.ConfigureFunctionsWebApplication();

builder.Services
    .AddOptions<FoundryOptions>()
    .Configure<IConfiguration>(
        (options, configuration) =>
        {
            options.ProjectEndpoint = configuration["FOUNDRY_PROJECT_ENDPOINT"] ?? string.Empty;
            options.AgentName = configuration["FOUNDRY_AGENT_NAME"] ?? string.Empty;
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
    .Configure<IConfiguration>(
        (options, configuration) =>
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
    .Configure<IConfiguration>(
        (options, configuration) =>
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
    .AddOptions<PlatformAuthOptions>()
    .Configure<IConfiguration>(
        (options, configuration) =>
        {
            options.TrustedPlatformAuthEnabled =
                bool.TryParse(
                    configuration["TRUSTED_PLATFORM_AUTH_ENABLED"],
                    out var trustedPlatformAuthEnabled)
                && trustedPlatformAuthEnabled;
            options.AllowLocalAnonymous =
                bool.TryParse(
                    configuration["ALLOW_LOCAL_ANONYMOUS"],
                    out var allowLocalAnonymous)
                && allowLocalAnonymous;
            options.StaticWebAppsAnonymousProvider =
                configuration["SWA_ANONYMOUS_IDENTITY_PROVIDER"] ?? "anonymous";
            options.StaticWebAppsBackendProvider =
                configuration["SWA_BACKEND_IDENTITY_PROVIDER"] ?? "anonymous";
            options.FoundryIdentityProvider =
                configuration["FOUNDRY_IDENTITY_PROVIDER"] ?? "aad";
            options.FoundryProjectPrincipalId =
                configuration["FOUNDRY_PROJECT_PRINCIPAL_ID"] ?? string.Empty;
        })
    .Validate(
        options => !string.IsNullOrWhiteSpace(options.StaticWebAppsAnonymousProvider),
        "SWA_ANONYMOUS_IDENTITY_PROVIDER is required.")
    .Validate(
        options => !string.IsNullOrWhiteSpace(options.StaticWebAppsBackendProvider),
        "SWA_BACKEND_IDENTITY_PROVIDER is required.")
    .Validate(
        options => !string.IsNullOrWhiteSpace(options.FoundryIdentityProvider),
        "FOUNDRY_IDENTITY_PROVIDER is required.")
    .Validate(
        options => Guid.TryParse(options.FoundryProjectPrincipalId, out _),
        "FOUNDRY_PROJECT_PRINCIPAL_ID must be a GUID.")
    .ValidateOnStart();

builder.Services
    .AddOptions<PublicChatOptions>()
    .Configure<IConfiguration>(
        (options, configuration) =>
        {
            options.Enabled =
                bool.TryParse(configuration["PUBLIC_CHAT_ENABLED"], out var enabled)
                && enabled;
        })
    .Validate(
        options =>
            options.PerSourcePerMinute > 0
            && options.PerSourceConcurrency > 0
            && options.GlobalPerMinute > 0
            && options.GlobalConcurrency > 0
            && options.DailyFoundryCalls > 0,
        "Public chat limits must be positive.")
    .ValidateOnStart();

builder.Services.AddSingleton<TimeProvider>(TimeProvider.System);
builder.Services.AddSingleton<IPlatformEnvironment, PlatformEnvironment>();
builder.Services.AddSingleton<IPlatformRequestAuthorizer, PlatformRequestAuthorizer>();
builder.Services.AddSingleton<IClientSourceIdentifier, ClientSourceIdentifier>();
builder.Services.AddSingleton<IAnonymousChatGate, AnonymousChatGate>();

builder.Services.AddSingleton<TokenCredential>(
    services =>
    {
        var environment = services.GetRequiredService<IPlatformEnvironment>();
        var identity = services
            .GetRequiredService<IOptions<ServiceIdentityOptions>>()
            .Value;
        return environment.IsAzure
            ? new ManagedIdentityCredential(identity.ManagedIdentityClientId)
            : new AzureCliCredential(
                new AzureCliCredentialOptions
                {
                    TenantId = identity.TenantId,
                });
    });
builder.Services.AddSingleton<IFoundryTokenSource, FoundryTokenSource>();
builder.Services.AddSingleton<IFabricTokenSource>(
    services =>
    {
        var identity = services
            .GetRequiredService<IOptions<ServiceIdentityOptions>>()
            .Value;
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

await builder.Build().RunAsync().ConfigureAwait(false);
