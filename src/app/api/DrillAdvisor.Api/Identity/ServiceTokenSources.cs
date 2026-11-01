using Azure.Core;
using Azure.Identity;

namespace DrillAdvisor.Api.Identity;

/// <summary>
/// Supplies Azure AI access tokens for Foundry calls.
/// </summary>
public interface IFoundryTokenSource
{
    /// <summary>
    /// Gets an Azure AI application token.
    /// </summary>
    ValueTask<string> GetTokenAsync(CancellationToken cancellationToken);
}

/// <summary>
/// Supplies Microsoft Fabric application tokens for MCP calls.
/// </summary>
public interface IFabricTokenSource
{
    /// <summary>
    /// Gets a Microsoft Fabric application token.
    /// </summary>
    ValueTask<string> GetTokenAsync(CancellationToken cancellationToken);
}

/// <summary>
/// Acquires Azure AI tokens through the process-wide Azure credential.
/// </summary>
public sealed class FoundryTokenSource(TokenCredential credential) : IFoundryTokenSource
{
    internal static readonly string[] Scopes = ["https://ai.azure.com/.default"];

    private readonly TokenCredential _credential =
        credential ?? throw new ArgumentNullException(nameof(credential));

    /// <inheritdoc />
    public async ValueTask<string> GetTokenAsync(CancellationToken cancellationToken)
    {
        try
        {
            var token = await _credential
                .GetTokenAsync(new TokenRequestContext(Scopes), cancellationToken)
                .ConfigureAwait(false);
            return token.Token;
        }
        catch (CredentialUnavailableException exception)
        {
            throw new ServiceTokenException(
                "Azure AI service authentication is unavailable.",
                exception);
        }
        catch (AuthenticationFailedException exception)
        {
            throw new ServiceTokenException(
                "Azure AI service authentication failed.",
                exception);
        }
    }
}

/// <summary>
/// Acquires Fabric tokens through a federated application credential.
/// </summary>
public sealed class FabricTokenSource : IFabricTokenSource
{
    internal static readonly string[] AssertionScopes =
        ["api://AzureADTokenExchange/.default"];
    internal const string FabricApiScope =
        "https://api.fabric.microsoft.com/.default";
    internal const string PowerBiScope =
        "https://analysis.windows.net/powerbi/api/.default";

    private readonly ClientAssertionCredential _credential;
    private readonly string[] _fabricScopes;

    internal IReadOnlyList<string> Scopes => _fabricScopes;

    /// <summary>
    /// Initializes a secretless Fabric token source.
    /// </summary>
    public FabricTokenSource(
        TokenCredential assertionCredential,
        string tenantId,
        string fabricAppClientId,
        string fabricTokenScope)
    {
        ArgumentNullException.ThrowIfNull(assertionCredential);
        ArgumentException.ThrowIfNullOrWhiteSpace(tenantId);
        ArgumentException.ThrowIfNullOrWhiteSpace(fabricAppClientId);
        ArgumentException.ThrowIfNullOrWhiteSpace(fabricTokenScope);

        if (!IsSupportedScope(fabricTokenScope))
        {
            throw new ArgumentOutOfRangeException(
                nameof(fabricTokenScope),
                "The Fabric token scope is not supported.");
        }

        _credential = new ClientAssertionCredential(
            tenantId,
            fabricAppClientId,
            async cancellationToken =>
            {
                var assertion = await assertionCredential
                    .GetTokenAsync(
                        new TokenRequestContext(AssertionScopes),
                        cancellationToken)
                    .ConfigureAwait(false);
                return assertion.Token;
            });
        _fabricScopes = [fabricTokenScope];
    }

    internal static bool IsSupportedScope(string? scope) =>
        string.Equals(scope, FabricApiScope, StringComparison.Ordinal)
        || string.Equals(scope, PowerBiScope, StringComparison.Ordinal);

    /// <inheritdoc />
    public async ValueTask<string> GetTokenAsync(CancellationToken cancellationToken)
    {
        try
        {
            var token = await _credential
                .GetTokenAsync(new TokenRequestContext(_fabricScopes), cancellationToken)
                .ConfigureAwait(false);
            return token.Token;
        }
        catch (CredentialUnavailableException exception)
        {
            throw new ServiceTokenException(
                "Microsoft Fabric service authentication is unavailable.",
                exception);
        }
        catch (AuthenticationFailedException exception)
        {
            throw new ServiceTokenException(
                "Microsoft Fabric service authentication failed.",
                exception);
        }
    }
}

/// <summary>
/// Represents a safe service-token acquisition failure.
/// </summary>
public sealed class ServiceTokenException(string message, Exception innerException)
    : Exception(message, innerException);
