using System.Net;
using System.Text;
using DrillAdvisor.Api.Configuration;
using DrillAdvisor.Api.Fabric;
using DrillAdvisor.Api.Identity;
using Microsoft.Extensions.Options;

namespace DrillAdvisor.Web.Tests;

public sealed class FabricMcpRelayClientTests
{
    [Fact]
    public async Task ForwardAsync_IgnoresCallerTargetAndUsesConfiguredEndpoint()
    {
        var handler = new CapturingHttpMessageHandler();
        var endpoint =
            "https://api.fabric.microsoft.com/v1/mcp/workspaces/fixed/dataagents/fixed/agent";
        var client = new FabricMcpRelayClient(
            new HttpClient(handler),
            Options.Create(new FabricRelayOptions { Endpoint = endpoint }),
            new StubFabricTokenSource());
        var context = new DefaultHttpContext();
        context.Request.Method = HttpMethods.Post;
        context.Request.QueryString =
            new QueryString("?target=https://attacker.example");
        context.Request.Headers["X-Target-Url"] = "https://attacker.example";
        context.Request.Body = new MemoryStream(
            Encoding.UTF8.GetBytes("""{"jsonrpc":"2.0"}"""));

        using var response = await client.ForwardAsync(
            context.Request,
            CancellationToken.None);

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
        Assert.Equal(endpoint, handler.RequestUri?.AbsoluteUri);
        Assert.Equal("fabric-token", handler.AuthorizationParameter);
    }

    private sealed class StubFabricTokenSource : IFabricTokenSource
    {
        public ValueTask<string> GetTokenAsync(
            CancellationToken cancellationToken) =>
            ValueTask.FromResult("fabric-token");
    }
}
