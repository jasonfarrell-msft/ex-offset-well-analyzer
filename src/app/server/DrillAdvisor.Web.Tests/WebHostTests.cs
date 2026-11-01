using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using DrillAdvisor.Api.Models;
using DrillAdvisor.Api.Offset;

namespace DrillAdvisor.Web.Tests;

public sealed class WebHostTests
{
    private static readonly string[] SelectedWell0019 = ["SYN-WELL-0019"];
    private static readonly string[] SelectedWell0100 = ["SYN-WELL-0100"];
    private static readonly string[] InvalidSelectedWellId = ["INVALID"];

    [Fact]
    public async Task Chat_AnonymousRequest_PreservesTypedResponseAndConversation()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/chat",
            new
            {
                message = "Compare runs",
                conversationId = "conv_existing",
            });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = await response.Content.ReadFromJsonAsync<ChatResponse>();
        Assert.NotNull(body);
        Assert.Equal("conv_existing", body.ConversationId);
        Assert.Equal("assistant", body.Message.Role);
        Assert.StartsWith(
            "SYNTHETIC DATA • DEVELOPMENT / HISTORICAL SUMMARY ONLY",
            body.Message.Markdown,
            StringComparison.Ordinal);
        Assert.Equal("bar", body.Visuals[0].GetProperty("type").GetString());
        Assert.Equal("mcp_call", Assert.Single(body.ToolCalls).Type);
        Assert.Equal("drill_runs", Assert.Single(body.Sources).Name);
        Assert.Equal(30, body.Usage?.TotalTokens);
        Assert.Equal("Compare runs", factory.FoundryClient.LastMessage);
        Assert.NotNull(factory.FoundryClient.LastAdditionalInstructions);
        Assert.Contains(
            "SYNTHETIC DATA • DEVELOPMENT / HISTORICAL SUMMARY ONLY",
            factory.FoundryClient.LastAdditionalInstructions,
            StringComparison.Ordinal);
        Assert.Equal(
            "conv_existing",
            factory.FoundryClient.LastConversationId);
    }

    [Fact]
    public async Task Chat_WithEnvelopeOffsetContext_InjectsServerComputedNarrative()
    {
        var offsetAnalysisSpy = new SpyOffsetAnalysisService();
        await using var factory = new DrillAdvisorWebApplicationFactory(
            offsetAnalysisServiceOverride: offsetAnalysisSpy);
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/chat",
            new
            {
                message = "Explain the selected historical summary quantities.",
                offsetContext = new
                {
                    contractVersion = "offset-well-analysis-v1",
                    releaseId = "v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
                    context = new
                    {
                        targetId = "SYN-TARGET-0001",
                        criteria = new
                        {
                            radiusFt = "10000",
                            formationMatch = true,
                            holeSizeMatch = true,
                            mdOverlap = false,
                        },
                        selectedWellIds = SelectedWell0019,
                        contextRevision = 1,
                    },
                },
            });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.NotNull(factory.FoundryClient.LastMessage);
        Assert.Contains(
            "Trusted offset context (server-computed)",
            factory.FoundryClient.LastMessage,
            StringComparison.Ordinal);
        Assert.Contains(
            "SYN-WELL-0019",
            factory.FoundryClient.LastMessage,
            StringComparison.Ordinal);
        Assert.Equal(1, offsetAnalysisSpy.ContractOverloadCallCount);
        Assert.Equal(0, offsetAnalysisSpy.LegacyOverloadCallCount);
        Assert.Equal(
            OffsetContractVersions.V1.ContractVersion,
            Assert.Single(offsetAnalysisSpy.Contracts).ContractVersion);
        Assert.NotNull(factory.FoundryClient.LastAdditionalInstructions);
        Assert.Contains(
            OffsetContractVersions.V1.Disclosure,
            factory.FoundryClient.LastAdditionalInstructions,
            StringComparison.Ordinal);
    }

    [Fact]
    public async Task Chat_WithLegacyOffsetContext_InjectsServerComputedNarrative()
    {
        var offsetAnalysisSpy = new SpyOffsetAnalysisService();
        await using var factory = new DrillAdvisorWebApplicationFactory(
            offsetAnalysisServiceOverride: offsetAnalysisSpy);
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/chat",
            new
            {
                message = "Explain the selected historical summary quantities.",
                offsetContext = new
                {
                    targetId = "SYN-TARGET-0001",
                    criteria = new
                    {
                        radiusFt = "10000",
                        formationMatch = true,
                        holeSizeMatch = true,
                        mdOverlap = false,
                    },
                    selectedWellIds = SelectedWell0019,
                    contextRevision = 1,
                },
            });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.NotNull(factory.FoundryClient.LastMessage);
        Assert.Contains(
            "Trusted offset context (server-computed)",
            factory.FoundryClient.LastMessage,
            StringComparison.Ordinal);
        Assert.Contains(
            "SYN-WELL-0019",
            factory.FoundryClient.LastMessage,
            StringComparison.Ordinal);
        Assert.Equal(1, offsetAnalysisSpy.ContractOverloadCallCount);
        Assert.Equal(0, offsetAnalysisSpy.LegacyOverloadCallCount);
        Assert.Equal(
            OffsetContractVersions.V1.ContractVersion,
            Assert.Single(offsetAnalysisSpy.Contracts).ContractVersion);
        Assert.NotNull(factory.FoundryClient.LastAdditionalInstructions);
        Assert.Contains(
            OffsetContractVersions.V1.Disclosure,
            factory.FoundryClient.LastAdditionalInstructions,
            StringComparison.Ordinal);
    }

    [Fact]
    public async Task Chat_WithIneligibleOffsetSelection_ReturnsConflictWithoutFoundryCall()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/chat",
            new
            {
                message = "Explain the selected historical summary quantities.",
                offsetContext = new
                {
                    targetId = "SYN-TARGET-0001",
                    criteria = new
                    {
                        radiusFt = "10000",
                        formationMatch = true,
                        holeSizeMatch = true,
                        mdOverlap = false,
                    },
                    selectedWellIds = SelectedWell0100,
                    contextRevision = 3,
                },
            });

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal(0, factory.FoundryClient.CallCount);
        var body = await response.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal("offset_context_stale", body.GetProperty("code").GetString());
    }

    [Fact]
    public async Task Chat_WithLegacyOffsetContextWithoutSelection_ReturnsBadRequestWithoutFoundryCall()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/chat",
            new
            {
                message = "Explain the selected historical summary quantities.",
                offsetContext = new
                {
                    targetId = "SYN-TARGET-0001",
                    criteria = new
                    {
                        radiusFt = "10000",
                        formationMatch = true,
                        holeSizeMatch = true,
                        mdOverlap = false,
                    },
                    selectedWellIds = Array.Empty<string>(),
                    contextRevision = 3,
                },
            });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, factory.FoundryClient.CallCount);
        var body = await response.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal("invalid_request", body.GetProperty("code").GetString());
    }

    [Fact]
    public async Task Chat_WithTypedOperationContract_IsAccepted()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/chat",
            new
            {
                operation = "chat",
                contractVersion = "offset-well-analysis-v1",
                releaseId = "v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
                context = new
                {
                    targetId = "SYN-TARGET-0001",
                    criteria = new
                    {
                        radiusFt = "10000",
                        formationMatch = true,
                        holeSizeMatch = true,
                        mdOverlap = false,
                    },
                    selectedWellIds = SelectedWell0019,
                    contextRevision = 1,
                },
                message = "Summarize selected offsets",
                conversationId = "typed-chat-1",
            });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("typed-chat-1", factory.FoundryClient.LastConversationId);
        Assert.NotNull(factory.FoundryClient.LastMessage);
        Assert.Contains(
            "User message:",
            factory.FoundryClient.LastMessage,
            StringComparison.Ordinal);
    }

    [Fact]
    public async Task Chat_WithTypedV2OperationContract_UsesV2OffsetDisclosureInPrompt()
    {
        var offsetAnalysisSpy = new SpyOffsetAnalysisService();
        await using var factory = new DrillAdvisorWebApplicationFactory(
            offsetAnalysisServiceOverride: offsetAnalysisSpy);
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/chat",
            new
            {
                operation = "chat",
                contractVersion = "offset-well-analysis-v2",
                releaseId = "v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0",
                context = new
                {
                    targetId = "SYN-TARGET-0001",
                    criteria = new
                    {
                        radiusFt = "10000",
                        formationMatch = true,
                        holeSizeMatch = true,
                        mdOverlap = false,
                    },
                    selectedWellIds = SelectedWell0019,
                    contextRevision = 1,
                },
                message = "Summarize selected offsets",
                conversationId = "typed-chat-v2-1",
            });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.NotNull(factory.FoundryClient.LastMessage);
        Assert.StartsWith(
            "SYNTHETIC DATA • v1.2.0 • DEVELOPMENT / OFFSET COMPARISON ONLY",
            factory.FoundryClient.LastMessage,
            StringComparison.Ordinal);
        Assert.Equal(1, offsetAnalysisSpy.ContractOverloadCallCount);
        Assert.Equal(0, offsetAnalysisSpy.LegacyOverloadCallCount);
        Assert.Equal(
            OffsetContractVersions.V2.ContractVersion,
            Assert.Single(offsetAnalysisSpy.Contracts).ContractVersion);
        Assert.NotNull(factory.FoundryClient.LastAdditionalInstructions);
        Assert.Contains(
            OffsetContractVersions.V2.Disclosure,
            factory.FoundryClient.LastAdditionalInstructions,
            StringComparison.Ordinal);
    }

    [Fact]
    public async Task Chat_WithV2EnvelopeOffsetContext_UsesV2ContractForChatContext()
    {
        var offsetAnalysisSpy = new SpyOffsetAnalysisService();
        await using var factory = new DrillAdvisorWebApplicationFactory(
            offsetAnalysisServiceOverride: offsetAnalysisSpy);
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/chat",
            new
            {
                message = "Explain selected offsets.",
                offsetContext = new
                {
                    contractVersion = "offset-well-analysis-v2",
                    releaseId = "v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0",
                    context = new
                    {
                        targetId = "SYN-TARGET-0001",
                        criteria = new
                        {
                            radiusFt = "10000",
                            formationMatch = true,
                            holeSizeMatch = true,
                            mdOverlap = false,
                        },
                        selectedWellIds = SelectedWell0019,
                        contextRevision = 1,
                    },
                },
            });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(1, offsetAnalysisSpy.ContractOverloadCallCount);
        Assert.Equal(0, offsetAnalysisSpy.LegacyOverloadCallCount);
        Assert.Equal(
            OffsetContractVersions.V2.ContractVersion,
            Assert.Single(offsetAnalysisSpy.Contracts).ContractVersion);
        Assert.NotNull(factory.FoundryClient.LastMessage);
        Assert.StartsWith(
            OffsetContractVersions.V2.Disclosure,
            factory.FoundryClient.LastMessage,
            StringComparison.Ordinal);
        Assert.NotNull(factory.FoundryClient.LastAdditionalInstructions);
        Assert.Contains(
            OffsetContractVersions.V2.Disclosure,
            factory.FoundryClient.LastAdditionalInstructions,
            StringComparison.Ordinal);
    }

    [Fact]
    public async Task Chat_WithInvalidEnvelopeOffsetContract_ReturnsBadRequestWithoutFallback()
    {
        var offsetAnalysisSpy = new SpyOffsetAnalysisService();
        await using var factory = new DrillAdvisorWebApplicationFactory(
            offsetAnalysisServiceOverride: offsetAnalysisSpy);
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/chat",
            new
            {
                message = "Explain selected offsets.",
                offsetContext = new
                {
                    contractVersion = "offset-well-analysis-v2",
                    releaseId = "v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
                    context = new
                    {
                        targetId = "SYN-TARGET-0001",
                        criteria = new
                        {
                            radiusFt = "10000",
                            formationMatch = true,
                            holeSizeMatch = true,
                            mdOverlap = false,
                        },
                        selectedWellIds = SelectedWell0019,
                        contextRevision = 1,
                    },
                },
            });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, factory.FoundryClient.CallCount);
        Assert.Equal(0, offsetAnalysisSpy.ContractOverloadCallCount);
        Assert.Equal(0, offsetAnalysisSpy.LegacyOverloadCallCount);
    }

    [Fact]
    public async Task Chat_WithInvalidTypedContext_ReturnsBadRequestWithoutFoundryCall()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/chat",
            new
            {
                operation = "chat",
                contractVersion = "offset-well-analysis-v1",
                releaseId = "v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
                context = new
                {
                    targetId = "SYN-TARGET-0001",
                    criteria = new
                    {
                        radiusFt = "10000",
                        formationMatch = true,
                        holeSizeMatch = true,
                        mdOverlap = false,
                    },
                    selectedWellIds = InvalidSelectedWellId,
                    contextRevision = 1,
                },
                message = "Summarize selected offsets",
                conversationId = "typed-chat-invalid",
            });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, factory.FoundryClient.CallCount);
    }

    [Fact]
    public async Task Chat_KillSwitchDisabled_ReturnsSafeServiceUnavailable()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory(
            new Dictionary<string, string?>
            {
                ["PUBLIC_CHAT_ENABLED"] = "false",
            });
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/chat",
            new { message = "hello" });

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal(TimeSpan.FromSeconds(60), response.Headers.RetryAfter?.Delta);
        Assert.Equal(0, factory.FoundryClient.CallCount);
        var body = await response.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal(
            "public_chat_disabled",
            body.GetProperty("code").GetString());
    }

    [Fact]
    public async Task Chat_MessageOverLimit_IsRejectedBeforeFoundry()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/chat",
            new { message = new string('x', 2_001) });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, factory.FoundryClient.CallCount);
    }

    [Fact]
    public async Task Chat_NonObjectJson_IsRejectedBeforeFoundry()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();
        using var request = new StringContent("[]", Encoding.UTF8, "application/json");

        using var response = await client.PostAsync("/api/chat", request);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, factory.FoundryClient.CallCount);
    }

    [Fact]
    public async Task Chat_FourthRequestFromSameIp_IsRateLimited()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Add("X-Forwarded-For", "192.0.2.10");

        for (var index = 0; index < 3; index++)
        {
            using var admitted = await client.PostAsJsonAsync(
                "/api/chat",
                new { message = $"question {index}" });
            Assert.Equal(HttpStatusCode.OK, admitted.StatusCode);
        }

        using var rejected = await client.PostAsJsonAsync(
            "/api/chat",
            new { message = "question 4" });

        Assert.Equal(HttpStatusCode.TooManyRequests, rejected.StatusCode);
        Assert.NotNull(rejected.Headers.RetryAfter);
        Assert.Equal(3, factory.FoundryClient.CallCount);
    }

    [Fact]
    public async Task OffsetAnalysis_CompareAndCandidates_DoNotConsumeChatQuota()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Add("X-Forwarded-For", "192.0.2.10");

        using var targets = await client.PostAsJsonAsync(
            "/api/offset-analysis",
            new
            {
                operation = "targets",
                contractVersion = "offset-well-analysis-v1",
                releaseId = "v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
            });

        Assert.Equal(HttpStatusCode.OK, targets.StatusCode);

        for (var index = 0; index < 2; index++)
        {
            using var candidates = await client.PostAsJsonAsync(
                "/api/offset-analysis",
                new
                {
                    operation = "candidates",
                    contractVersion = "offset-well-analysis-v1",
                    releaseId = "v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
                    context = new
                    {
                        targetId = "SYN-TARGET-0001",
                        criteria = new
                        {
                            radiusFt = "10000",
                            formationMatch = true,
                            holeSizeMatch = true,
                            mdOverlap = false,
                        },
                        selectedWellIds = Array.Empty<string>(),
                        contextRevision = index,
                    },
                });
            Assert.Equal(HttpStatusCode.OK, candidates.StatusCode);
        }

        using var firstChat = await client.PostAsJsonAsync(
            "/api/chat",
            new { message = "question 1" });
        using var secondChat = await client.PostAsJsonAsync(
            "/api/chat",
            new { message = "question 2" });
        using var thirdChat = await client.PostAsJsonAsync(
            "/api/chat",
            new { message = "question 3" });

        Assert.Equal(HttpStatusCode.OK, firstChat.StatusCode);
        Assert.Equal(HttpStatusCode.OK, secondChat.StatusCode);
        Assert.Equal(HttpStatusCode.OK, thirdChat.StatusCode);
        Assert.Equal(3, factory.FoundryClient.CallCount);
    }

    [Fact]
    public async Task OffsetAnalysis_Candidates_ReturnsContractEnvelope()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/offset-analysis",
            new
            {
                operation = "candidates",
                contractVersion = "offset-well-analysis-v1",
                releaseId = "v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
                context = new
                {
                    targetId = "SYN-TARGET-0001",
                    criteria = new
                    {
                        radiusFt = "10000",
                        formationMatch = true,
                        holeSizeMatch = true,
                        mdOverlap = false,
                    },
                    selectedWellIds = Array.Empty<string>(),
                    contextRevision = 0,
                },
            });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal("candidates", json.GetProperty("operation").GetString());
        Assert.Equal("offset-well-analysis-v1", json.GetProperty("contractVersion").GetString());
        Assert.Equal(2, json.GetProperty("totalCount").GetInt32());
        Assert.Equal("SYN-WELL-0019", json.GetProperty("rows")[0].GetProperty("wellId").GetString());
        Assert.Equal("30.834613", json.GetProperty("rows")[0]
            .GetProperty("metrics")
            .GetProperty("summaryPenetrationRateFtPerHour")
            .GetString());
    }

    [Fact]
    public async Task OffsetAnalysis_DuplicateKeys_IsRejected()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();
        using var request = new StringContent(
            """{"operation":"targets","operation":"targets","contractVersion":"offset-well-analysis-v1","releaseId":"v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d"}""",
            Encoding.UTF8,
            "application/json");

        using var response = await client.PostAsync(
            "/api/offset-analysis",
            request);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal("INVALID_REQUEST", json.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task OffsetAnalysis_CompareWithStaleSelection_ReturnsContextMismatch()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync(
            "/api/offset-analysis",
            new
            {
                operation = "compare",
                contractVersion = "offset-well-analysis-v1",
                releaseId = "v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
                context = new
                {
                    targetId = "SYN-TARGET-0001",
                    criteria = new
                    {
                        radiusFt = "1",
                        formationMatch = true,
                        holeSizeMatch = true,
                        mdOverlap = false,
                    },
                    selectedWellIds = SelectedWell0019,
                    contextRevision = 5,
                },
            });

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal("stale", json.GetProperty("status").GetString());
        Assert.Equal(
            "CONTEXT_MISMATCH",
            json.GetProperty("error").GetProperty("code").GetString());
    }

    [Theory]
    [InlineData("/healthz", "healthy")]
    [InlineData("/readyz", "ready")]
    public async Task Probe_ReturnsOnlySafeStatus(string path, string expected)
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync(path);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = await response.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal(expected, body.GetProperty("status").GetString());
        Assert.Single(body.EnumerateObject());
    }

    [Theory]
    [InlineData("/")]
    [InlineData("/conversation/existing")]
    public async Task SpaRoute_ReturnsIndex(string path)
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync(path);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("text/html", response.Content.Headers.ContentType?.MediaType);
        Assert.Contains(
            "Drill Advisor test SPA",
            await response.Content.ReadAsStringAsync(),
            StringComparison.Ordinal);
    }

    [Fact]
    public async Task StaticAsset_IsServedWithoutSpaFallback()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/assets/app.js");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(
            "text/javascript",
            response.Content.Headers.ContentType?.MediaType);
    }

    [Fact]
    public async Task Mcp_AnonymousCaller_IsRejected()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.PostAsync(
            "/api/mcp/fabric-dataagent",
            JsonContent.Create(new { jsonrpc = "2.0", method = "initialize", id = 1 }));

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.Equal(0, factory.RelayClient.CallCount);
    }

    [Theory]
    [InlineData("bad-audience", "Mcp.Invoke", DrillAdvisorWebApplicationFactory.PrincipalId, DrillAdvisorWebApplicationFactory.ClientId, HttpStatusCode.Unauthorized)]
    [InlineData(DrillAdvisorWebApplicationFactory.Audience, "Wrong.Role", DrillAdvisorWebApplicationFactory.PrincipalId, DrillAdvisorWebApplicationFactory.ClientId, HttpStatusCode.Forbidden)]
    [InlineData(DrillAdvisorWebApplicationFactory.Audience, "Mcp.Invoke", "55555555-5555-5555-5555-555555555555", DrillAdvisorWebApplicationFactory.ClientId, HttpStatusCode.Forbidden)]
    [InlineData(DrillAdvisorWebApplicationFactory.Audience, "Mcp.Invoke", DrillAdvisorWebApplicationFactory.PrincipalId, "66666666-6666-6666-6666-666666666666", HttpStatusCode.Forbidden)]
    public async Task Mcp_InvalidJwtClaims_AreRejected(
        string audience,
        string role,
        string principalId,
        string clientId,
        HttpStatusCode expectedStatus)
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            DrillAdvisorWebApplicationFactory.CreateAccessToken(
                audience,
                role,
                principalId,
                clientId));

        using var response = await client.GetAsync("/api/mcp/fabric-dataagent");

        Assert.Equal(expectedStatus, response.StatusCode);
        Assert.Equal(0, factory.RelayClient.CallCount);
    }

    [Fact]
    public async Task Mcp_ExpiredJwt_IsRejected()
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            DrillAdvisorWebApplicationFactory.CreateAccessToken(
                expires: DateTime.UtcNow.AddMinutes(-5)));

        using var response = await client.GetAsync("/api/mcp/fabric-dataagent");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.Equal(0, factory.RelayClient.CallCount);
    }

    [Theory]
    [InlineData("GET")]
    [InlineData("POST")]
    [InlineData("DELETE")]
    public async Task Mcp_ValidFoundryJwt_AllowsStreamableHttpMethods(string method)
    {
        await using var factory = new DrillAdvisorWebApplicationFactory();
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            DrillAdvisorWebApplicationFactory.CreateAccessToken());
        using var request = new HttpRequestMessage(
            new HttpMethod(method),
            "/api/mcp/fabric-dataagent");
        if (method == "POST")
        {
            request.Content = JsonContent.Create(
                new { jsonrpc = "2.0", method = "initialize", id = 1 });
        }

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(method, Assert.Single(factory.RelayClient.Methods));
    }
}
