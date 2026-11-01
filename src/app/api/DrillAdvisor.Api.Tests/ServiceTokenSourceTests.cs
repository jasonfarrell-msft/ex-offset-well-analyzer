using DrillAdvisor.Api.Identity;

namespace DrillAdvisor.Api.Tests;

public sealed class ServiceTokenSourceTests
{
    [Fact]
    public async Task FoundryTokenSource_RequestsAzureAiDefaultScope()
    {
        var credential = new StubTokenCredential("foundry-service-token");
        var source = new FoundryTokenSource(credential);

        var token = await source.GetTokenAsync(CancellationToken.None);

        Assert.Equal("foundry-service-token", token);
        Assert.Equal(
            ["https://ai.azure.com/.default"],
            credential.LastScopes);
    }

    [Fact]
    public void FabricTokenSource_AllowsOnlyDocumentedFixedResourceScopes()
    {
        Assert.True(
            FabricTokenSource.IsSupportedScope(
                "https://api.fabric.microsoft.com/.default"));
        Assert.True(
            FabricTokenSource.IsSupportedScope(
                "https://analysis.windows.net/powerbi/api/.default"));
        Assert.False(
            FabricTokenSource.IsSupportedScope(
                "https://caller.example/.default"));
        Assert.False(FabricTokenSource.IsSupportedScope(null));
    }

    [Theory]
    [InlineData("https://api.fabric.microsoft.com/.default")]
    [InlineData("https://analysis.windows.net/powerbi/api/.default")]
    public void FabricTokenSource_UsesConfiguredFixedScope(string scope)
    {
        var source = new FabricTokenSource(
            new StubTokenCredential("assertion-token"),
            Guid.NewGuid().ToString(),
            Guid.NewGuid().ToString(),
            scope);

        Assert.Equal([scope], source.Scopes);
    }

    [Fact]
    public void FabricTokenSource_RejectsUnsupportedScope()
    {
        var exception = Assert.Throws<ArgumentOutOfRangeException>(
            () => new FabricTokenSource(
                new StubTokenCredential("assertion-token"),
                Guid.NewGuid().ToString(),
                Guid.NewGuid().ToString(),
                "https://caller.example/.default"));

        Assert.Equal("fabricTokenScope", exception.ParamName);
    }
}
