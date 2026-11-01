using System.Net;
using System.Text;
using DrillAdvisor.Api.Configuration;
using DrillAdvisor.Api.Fabric;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Options;

namespace DrillAdvisor.Api.Tests;

public sealed class FabricMcpRelayClientTests
{
    [Fact]
    public async Task ForwardAsync_UsesFixedTargetAndSafeProtocolHeaders()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => new HttpResponseMessage(HttpStatusCode.Accepted)
            {
                Content = new StringContent("accepted"),
            });
        var tokenSource = new StubFabricTokenSource("fabric-application-token");
        var client = new FabricMcpRelayClient(
            new HttpClient(handler),
            Options.Create(
                new FabricRelayOptions
                {
                    Endpoint =
                        "https://api.fabric.microsoft.com/v1/mcp/workspaces/fixed/dataagents/fixed/agent",
                }),
            tokenSource);
        var context = new DefaultHttpContext();
        context.Request.Method = HttpMethods.Post;
        context.Request.QueryString =
            new QueryString("?target=https://attacker.example&workspace=wrong");
        context.Request.ContentType = "application/json";
        context.Request.Body = new MemoryStream(
            Encoding.UTF8.GetBytes("""{"jsonrpc":"2.0","method":"initialize","id":1}"""));
        context.Request.Headers.Authorization = "Bearer inbound-caller-token";
        context.Request.Headers.Accept = "application/json, text/event-stream";
        context.Request.Headers["MCP-Protocol-Version"] = "2025-06-18";
        context.Request.Headers["MCP-Session-Id"] = "session-123";
        context.Request.Headers["X-Target-Url"] = "https://attacker.example";

        using var response = await client.ForwardAsync(
            context.Request,
            CancellationToken.None);

        var captured = Assert.Single(handler.Requests);
        Assert.Equal(
            "https://api.fabric.microsoft.com/v1/mcp/workspaces/fixed/dataagents/fixed/agent",
            captured.Uri.AbsoluteUri);
        Assert.Equal(HttpMethod.Post, captured.Method);
        Assert.Equal("Bearer", captured.AuthorizationScheme);
        Assert.Equal("fabric-application-token", captured.AuthorizationParameter);
        Assert.Equal("2025-06-18", Assert.Single(captured.Headers["MCP-Protocol-Version"]));
        Assert.Equal("session-123", Assert.Single(captured.Headers["MCP-Session-Id"]));
        Assert.False(captured.Headers.ContainsKey("X-Target-Url"));
        Assert.DoesNotContain("inbound-caller-token", captured.Headers.Values.SelectMany(value => value));
        Assert.Equal(1, tokenSource.CallCount);
    }
}
