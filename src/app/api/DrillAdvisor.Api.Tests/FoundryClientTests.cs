using System.Net;
using System.Text.Json;
using DrillAdvisor.Api.Configuration;
using DrillAdvisor.Api.Foundry;
using DrillAdvisor.Api.Identity;
using Microsoft.Extensions.Options;

namespace DrillAdvisor.Api.Tests;

public sealed class FoundryClientTests
{
    [Fact]
    public async Task SendAsync_NoConversationId_UsesResponseIdAsContinuation()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => HttpResponses.Json(
                HttpStatusCode.OK,
                AssistantResponse("done", "resp_created")));
        var client = CreateClient(handler);

        var result = await client.SendAsync(
            "hello",
            null,
            null,
            CancellationToken.None);

        Assert.Equal("resp_created", result.ConversationId);
    }

    [Fact]
    public async Task SendAsync_NoConversationId_CallsOnlyResponsesEndpoint()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => HttpResponses.Json(
                HttpStatusCode.OK,
                AssistantResponse("done", "resp_created")));
        var client = CreateClient(handler);

        await client.SendAsync(
            "hello",
            null,
            null,
            CancellationToken.None);

        Assert.Equal(
            "/api/projects/drill-project/agents/welladvisor-fabric-orchestrator/endpoint/protocols/openai/responses",
            Assert.Single(handler.Requests).Uri.AbsolutePath);
        Assert.Equal("api-version=v1", handler.Requests.Single().Uri.Query.TrimStart('?'));
        using var document = JsonDocument.Parse(handler.Requests.Single().Body!);
        Assert.False(document.RootElement.TryGetProperty("previous_response_id", out _));
        Assert.False(document.RootElement.TryGetProperty("instructions", out _));
        Assert.False(document.RootElement.TryGetProperty("additional_instructions", out _));
    }

    [Fact]
    public async Task SendAsync_ExistingConversation_CallsResponsesOnce()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => HttpResponses.Json(HttpStatusCode.OK, AssistantResponse("done")));
        var client = CreateClient(handler);

        await client.SendAsync(
            "hello",
            "conv_existing",
            null,
            CancellationToken.None);

        Assert.Single(handler.Requests);
    }

    [Fact]
    public async Task SendAsync_ExistingConversation_ForwardsExpectedRequestBody()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => HttpResponses.Json(
                HttpStatusCode.OK,
                AssistantResponse("done", "resp_next")));
        var client = CreateClient(handler);

        var result = await client.SendAsync(
            "hello",
            "conv_existing",
            null,
            CancellationToken.None);

        using var document = JsonDocument.Parse(handler.Requests.Single().Body!);
        Assert.Equal(
            "conv_existing",
            document.RootElement.GetProperty("previous_response_id").GetString());
        Assert.False(document.RootElement.GetProperty("stream").GetBoolean());
        Assert.Equal("resp_next", result.ConversationId);
    }

    [Fact]
    public async Task SendAsync_ExistingConversation_AcquiresAndForwardsServiceToken()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => HttpResponses.Json(HttpStatusCode.OK, AssistantResponse("done")));
        var tokenSource = new StubFoundryTokenSource("service-token");
        var client = CreateClient(handler, tokenSource);

        await client.SendAsync(
            "hello",
            "conv_existing",
            null,
            CancellationToken.None);

        Assert.Equal(
            "service-token",
            handler.Requests.Single().AuthorizationParameter);
        Assert.Equal(1, tokenSource.CallCount);
    }

    [Fact]
    public async Task SendAsync_WithAdditionalInstructions_InlinesGuidanceInOneRequest()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => HttpResponses.Json(HttpStatusCode.OK, AssistantResponse("done")));
        var client = CreateClient(handler);

        await client.SendAsync(
            "hello",
            "conv_existing",
            "First line must be synthetic disclosure.",
            CancellationToken.None);

        using var document = JsonDocument.Parse(handler.Requests.Single().Body!);
        var input = document.RootElement.GetProperty("input").GetString();
        Assert.Contains("First line must be synthetic disclosure.", input);
        Assert.Contains("User message:", input);
        Assert.EndsWith("hello", input);
        Assert.Equal("conv_existing", document.RootElement.GetProperty("previous_response_id").GetString());
        Assert.False(document.RootElement.TryGetProperty("instructions", out _));
        Assert.False(document.RootElement.TryGetProperty("additional_instructions", out _));
    }

    [Fact]
    public async Task SendAsync_WithGuidanceAndBadRequest_DoesNotProbeUnsupportedFields()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => HttpResponses.Json(
                HttpStatusCode.BadRequest,
                """
                {
                  "error": {
                    "message": "The field 'instructions' is unsupported for this endpoint."
                  }
                }
                """));
        var client = CreateClient(handler);

        await Assert.ThrowsAsync<FoundryApiException>(() => client.SendAsync(
            "hello",
            "conv_existing",
            "First line must be synthetic disclosure.",
            CancellationToken.None));

        Assert.Single(handler.Requests);
    }

    [Fact]
    public async Task SendAsync_WithGuidanceAndTransientFailure_RetriesSameInput()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => RetryResponse(HttpStatusCode.TooManyRequests),
            _ => HttpResponses.Json(HttpStatusCode.OK, AssistantResponse("done")));
        var client = CreateClient(handler);

        await client.SendAsync(
            "hello",
            "conv_existing",
            "First line must be synthetic disclosure.",
            CancellationToken.None);

        Assert.Equal(2, handler.Requests.Count);
        Assert.Equal(handler.Requests[0].Body, handler.Requests[1].Body);

        using var third = JsonDocument.Parse(handler.Requests[1].Body!);
        Assert.False(third.RootElement.TryGetProperty("instructions", out _));
        Assert.False(third.RootElement.TryGetProperty("additional_instructions", out _));
        var input = third.RootElement.GetProperty("input").GetString();
        Assert.NotNull(input);
        Assert.Contains("Request context for this synthetic-data POC response:", input);
        Assert.Contains("First line must be synthetic disclosure.", input);
        Assert.Contains("User message:", input);
        Assert.Contains("hello", input);
    }

    [Fact]
    public async Task SendAsync_TransientStatusWithRetryAfter_RetriesAtMostTwice()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => RetryResponse(HttpStatusCode.TooManyRequests),
            _ => RetryResponse(HttpStatusCode.ServiceUnavailable),
            _ => HttpResponses.Json(HttpStatusCode.OK, AssistantResponse("done")));
        var client = CreateClient(handler);

        await client.SendAsync(
            "hello",
            "conv_existing",
            null,
            CancellationToken.None);

        Assert.Equal(3, handler.Requests.Count);
    }

    [Fact]
    public async Task SendAsync_Retry_ReusesIdempotencyKey()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => RetryResponse(HttpStatusCode.TooManyRequests),
            _ => HttpResponses.Json(HttpStatusCode.OK, AssistantResponse("done")));
        var client = CreateClient(handler);

        await client.SendAsync(
            "hello",
            "conv_existing",
            null,
            CancellationToken.None);

        Assert.Single(
            handler.Requests
                .Select(request => request.IdempotencyKey)
                .Distinct(StringComparer.Ordinal));
    }

    [Fact]
    public async Task SendAsync_NonTransientStatus_DoesNotRetry()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => HttpResponses.Json(HttpStatusCode.InternalServerError, "{}"));
        var client = CreateClient(handler);

        await Assert.ThrowsAsync<FoundryApiException>(
            () => client.SendAsync(
                "hello",
                "conv_existing",
                null,
                CancellationToken.None));

        Assert.Single(handler.Requests);
    }

    [Fact]
    public async Task SendAsync_PersistentTransientStatus_StopsAfterRetryLimit()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => RetryResponse(HttpStatusCode.BadGateway));
        var client = CreateClient(handler);

        await Assert.ThrowsAsync<FoundryApiException>(
            () => client.SendAsync(
                "hello",
                "conv_existing",
                null,
                CancellationToken.None));

        Assert.Equal(3, handler.Requests.Count);
    }

    [Fact]
    public async Task SendAsync_FailureIncludesUpstreamResponseBody()
    {
        var handler = new SequenceHttpMessageHandler(
            _ => HttpResponses.Json(
                HttpStatusCode.BadRequest,
                """
                {
                  "error": {
                    "message": "invalid request payload"
                  }
                }
                """));
        var client = CreateClient(handler);

        var exception = await Assert.ThrowsAsync<FoundryApiException>(
            () => client.SendAsync(
                "hello",
                "conv_existing",
                null,
                CancellationToken.None));

        Assert.Contains("invalid request payload", exception.ResponseBody);
    }

    private static FoundryClient CreateClient(
        HttpMessageHandler handler,
        IFoundryTokenSource? tokenSource = null)
    {
        var options = Options.Create(
            new FoundryOptions
            {
                ProjectEndpoint =
                    "https://foundry.example/api/projects/drill-project",
                AgentName = "welladvisor-fabric-orchestrator",
                Timeout = TimeSpan.FromSeconds(120),
                MaximumRetryCount = 2,
            });
        return new FoundryClient(
            new HttpClient(handler),
            options,
            TimeProvider.System,
            tokenSource ?? new StubFoundryTokenSource("service-token"));
    }

    private static HttpResponseMessage RetryResponse(HttpStatusCode statusCode)
    {
        var response = HttpResponses.Json(statusCode, "{}");
        response.Headers.RetryAfter =
            new System.Net.Http.Headers.RetryConditionHeaderValue(
                TimeSpan.Zero);
        return response;
    }

    private static string AssistantResponse(
        string markdown,
        string responseId = "resp_1")
    {
        return
            $$"""
            {
              "id": {{JsonSerializer.Serialize(responseId)}},
              "created_at": 1793037600,
              "output": [
                {
                  "type": "message",
                  "id": "msg_1",
                  "role": "assistant",
                  "content": [
                    {
                      "type": "output_text",
                      "text": {{JsonSerializer.Serialize(markdown)}}
                    }
                  ]
                }
              ],
              "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15
              }
            }
            """;
    }
}
