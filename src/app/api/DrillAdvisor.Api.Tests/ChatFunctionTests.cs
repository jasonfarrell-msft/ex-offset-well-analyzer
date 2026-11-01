using System.Text;
using System.Text.Json;
using DrillAdvisor.Api.Auth;
using DrillAdvisor.Api.Functions;
using DrillAdvisor.Api.Limits;
using DrillAdvisor.Api.Models;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;

namespace DrillAdvisor.Api.Tests;

public sealed class ChatFunctionTests
{
    private static readonly FoundryReply DefaultReply = new(
        "conv_test",
        "msg_test",
        "SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY\nAnswer",
        new DateTimeOffset(2026, 10, 26, 18, 0, 0, TimeSpan.Zero),
        [],
        [],
        [],
        new UsageSummary(10, 5, 15));

    [Fact]
    public async Task RunAsync_UntrustedRoute_ReturnsForbidden()
    {
        var authorizer = new StubPlatformAuthorizer
        {
            ChatResult = new PlatformAuthorizationResult(
                false,
                "trusted_swa_principal_required"),
        };
        var function = CreateFunction(authorizer: authorizer);

        var result = await function.RunAsync(
            CreateRequest("""{"message":"hello"}"""),
            CancellationToken.None);

        Assert.Equal(
            StatusCodes.Status403Forbidden,
            Assert.IsType<JsonResult>(result).StatusCode);
    }

    [Theory]
    [InlineData("""{"message":""}""")]
    [InlineData("""{"message":"   "}""")]
    [InlineData("""{"message":"hello","conversationId":"bad id"}""")]
    public async Task RunAsync_InvalidRequest_ReturnsBadRequest(string body)
    {
        var function = CreateFunction();

        var result = await function.RunAsync(
            CreateRequest(body),
            CancellationToken.None);

        Assert.Equal(
            StatusCodes.Status400BadRequest,
            Assert.IsType<JsonResult>(result).StatusCode);
    }

    [Fact]
    public async Task RunAsync_MessageExceedsPublicLimit_ReturnsBadRequest()
    {
        var function = CreateFunction();
        var body = JsonSerializer.Serialize(new { message = new string('a', 2_001) });

        var result = await function.RunAsync(
            CreateRequest(body),
            CancellationToken.None);

        Assert.Equal(
            StatusCodes.Status400BadRequest,
            Assert.IsType<JsonResult>(result).StatusCode);
    }

    [Fact]
    public async Task RunAsync_OversizedBody_ReturnsPayloadTooLarge()
    {
        var function = CreateFunction();
        var request = CreateRequest(new string('x', 8_193));
        request.ContentLength = null;

        var result = await function.RunAsync(request, CancellationToken.None);

        Assert.Equal(
            StatusCodes.Status413PayloadTooLarge,
            Assert.IsType<JsonResult>(result).StatusCode);
    }

    [Fact]
    public async Task RunAsync_KillSwitchRejection_ReturnsSafeServiceUnavailable()
    {
        var gate = new StubChatGate
        {
            Admission = new ChatAdmission(
                false,
                StatusCodes.Status503ServiceUnavailable,
                "public_chat_disabled",
                60,
                null),
        };
        var request = CreateRequest("""{"message":"hello"}""");
        var function = CreateFunction(chatGate: gate);

        var result = await function.RunAsync(request, CancellationToken.None);

        Assert.Equal(
            StatusCodes.Status503ServiceUnavailable,
            Assert.IsType<JsonResult>(result).StatusCode);
        Assert.Equal("60", request.HttpContext.Response.Headers.RetryAfter);
    }

    [Fact]
    public async Task RunAsync_ValidAnonymousReply_HasStableTopLevelContract()
    {
        var foundryClient = new StubFoundryClient(DefaultReply);
        var function = CreateFunction(foundryClient: foundryClient);

        var result = await function.RunAsync(
            CreateRequest("""{"message":"hello"}"""),
            CancellationToken.None);

        var jsonResult = Assert.IsType<JsonResult>(result);
        var response = Assert.IsType<ChatResponse>(jsonResult.Value);
        var options = Assert.IsType<JsonSerializerOptions>(
            jsonResult.SerializerSettings);
        var json = JsonSerializer.SerializeToElement(response, options);
        var propertyNames = json.EnumerateObject()
            .Select(property => property.Name)
            .Order(StringComparer.Ordinal)
            .ToArray();
        Assert.Equal(
            [
                "conversationId",
                "latencyMs",
                "message",
                "sources",
                "toolCalls",
                "usage",
                "visuals",
            ],
            propertyNames);
        Assert.Equal(1, foundryClient.CallCount);
        Assert.NotNull(foundryClient.LastAdditionalInstructions);
        Assert.Contains(
            "COUNT(DISTINCT run_id)",
            foundryClient.LastAdditionalInstructions,
            StringComparison.Ordinal);
        Assert.Contains(
            "accepted-only runs from curated source rows",
            foundryClient.LastAdditionalInstructions,
            StringComparison.Ordinal);
        Assert.Contains(
            "cross-target joins",
            foundryClient.LastAdditionalInstructions,
            StringComparison.Ordinal);
        Assert.Contains(
            "return null/unknown",
            foundryClient.LastAdditionalInstructions,
            StringComparison.Ordinal);
    }

    private static ChatFunction CreateFunction(
        StubPlatformAuthorizer? authorizer = null,
        StubChatGate? chatGate = null,
        StubFoundryClient? foundryClient = null) =>
        new(
            authorizer ?? new StubPlatformAuthorizer(),
            new StubSourceIdentifier(),
            chatGate ?? new StubChatGate(),
            foundryClient ?? new StubFoundryClient(DefaultReply),
            NullLogger<ChatFunction>.Instance);

    private static HttpRequest CreateRequest(string body)
    {
        var context = new DefaultHttpContext();
        context.Request.Method = HttpMethods.Post;
        context.Request.ContentType = "application/json";
        var bytes = Encoding.UTF8.GetBytes(body);
        context.Request.ContentLength = bytes.Length;
        context.Request.Body = new MemoryStream(bytes);
        return context.Request;
    }
}
