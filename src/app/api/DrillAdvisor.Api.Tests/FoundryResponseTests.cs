using System.Net;
using System.Text.Json;
using DrillAdvisor.Api.Configuration;
using DrillAdvisor.Api.Foundry;
using Microsoft.Extensions.Options;

namespace DrillAdvisor.Api.Tests;

public sealed class FoundryResponseTests
{
    private const string Disclosure =
        "SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY";

    [Fact]
    public async Task SendAsync_ResponseWithVisual_ExtractsVisualAndPreservesDisclosure()
    {
        var markdown =
            $$"""
            {{Disclosure}}
            Summary.

            ```drill-advisor-visual
            {"type":"kpi-grid","items":[{"label":"Runs","value":12}]}
            ```
            """;
        var client = CreateClient(ResponseWith(markdown));

        var result = await client.SendAsync(
            "hello",
            "conv_1",
            null,
            CancellationToken.None);

        Assert.Equal(Disclosure, result.Markdown.Split('\n')[0]);
    }

    [Fact]
    public async Task SendAsync_ResponseWithValidVisual_RemovesBlockFromMarkdown()
    {
        var markdown =
            """
            SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY
            Summary.

            ```drill-advisor-visual
            {"type":"bar-chart","data":[{"label":"A","value":42.5,"unit":"ft/hr"}]}
            ```
            """;
        var client = CreateClient(ResponseWith(markdown));

        var result = await client.SendAsync(
            "hello",
            "conv_1",
            null,
            CancellationToken.None);

        Assert.DoesNotContain("drill-advisor-visual", result.Markdown);
    }

    [Fact]
    public async Task SendAsync_ResponseWithInvalidVisual_KeepsBlockInMarkdown()
    {
        var markdown =
            """
            SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY
            ```drill-advisor-visual
            {"type":"bar-chart","series":"invalid"}
            ```
            """;
        var client = CreateClient(ResponseWith(markdown));

        var result = await client.SendAsync(
            "hello",
            "conv_1",
            null,
            CancellationToken.None);

        Assert.Contains("drill-advisor-visual", result.Markdown);
    }

    [Fact]
    public async Task SendAsync_DataTableWithUnsupportedShapes_KeepsBlockInMarkdown()
    {
        var markdown =
            $$"""
            {{Disclosure}}
            ```drill-advisor-visual
            {"type":"data-table","columns":["Well"],"rows":[["Synthetic Aster"]]}
            ```
            """;
        var client = CreateClient(ResponseWith(markdown));

        var result = await client.SendAsync(
            "hello",
            "conv_1",
            null,
            CancellationToken.None);

        Assert.Contains("drill-advisor-visual", result.Markdown);
        Assert.Empty(result.Visuals);
    }

    [Theory]
    [InlineData("""{"type":"kpi-grid","items":[{"label":"Runs","value":12}]}""")]
    [InlineData("""{"type":"bar-chart","data":[{"label":"A","value":42.5,"unit":"ft/hr"}]}""")]
    [InlineData("""{"type":"data-table","columns":[{"key":"well","label":"Well"}],"rows":[{"well":"Synthetic Aster"}]}""")]
    public async Task SendAsync_SupportedVisualType_ReturnsVisual(string visualJson)
    {
        var markdown =
            $"{Disclosure}\n```drill-advisor-visual\n{visualJson}\n```";
        var client = CreateClient(ResponseWith(markdown));

        var result = await client.SendAsync(
            "hello",
            "conv_1",
            null,
            CancellationToken.None);

        Assert.Single(result.Visuals);
    }

    [Fact]
    public async Task SendAsync_ResponseWithReasoning_DoesNotLeakHiddenContent()
    {
        var response =
            $$"""
            {
              "id": "resp_1",
              "output": [
                {
                  "type": "reasoning",
                  "summary": [{"text":"hidden-reasoning-marker"}],
                  "encrypted_content": "encrypted-marker"
                },
                {
                  "type": "message",
                  "id": "msg_1",
                  "role": "assistant",
                  "content": [{"type":"output_text","text":{{JsonSerializer.Serialize(Disclosure + "\nSafe answer.")}}}]
                }
              ]
            }
            """;
        var client = CreateClient(response);

        var result = await client.SendAsync(
            "hello",
            "conv_1",
            null,
            CancellationToken.None);

        var serialized = JsonSerializer.Serialize(result);
        Assert.DoesNotContain("marker", serialized, StringComparison.Ordinal);
    }

    [Fact]
    public async Task SendAsync_McpRecords_ReturnsOnlySafeSummaries()
    {
        var response =
            $$"""
            {
              "id": "resp_1",
              "output": [
                {
                  "type": "mcp_list_tools",
                  "id": "list_1",
                  "server_label": "fabric-iq",
                  "tools": [{"name":"query"},{"name":"describe"}]
                },
                {
                  "type": "mcp_call",
                  "id": "call_1",
                  "server_label": "fabric-iq",
                  "name": "query",
                  "status": "completed",
                  "arguments": "must-not-return",
                  "output": {
                    "source_name": "Drill Run Semantic Model",
                    "measures": ["Average ROP", "Run Count"],
                    "rows": [{"value":123.45}]
                  }
                },
                {
                  "type": "message",
                  "id": "msg_1",
                  "role": "assistant",
                  "content": [{"type":"output_text","text":{{JsonSerializer.Serialize(Disclosure + "\nSafe answer.")}}}]
                }
              ]
            }
            """;
        var client = CreateClient(response);

        var result = await client.SendAsync(
            "hello",
            "conv_1",
            null,
            CancellationToken.None);

        Assert.Equal(2, result.ToolCalls.Count);
    }

    [Fact]
    public async Task SendAsync_McpOutputWithSourceMetadata_ExtractsSourceAndMeasures()
    {
        var response =
            $$"""
            {
              "id": "resp_1",
              "output": [
                {
                  "type": "mcp_call",
                  "id": "call_1",
                  "name": "query",
                  "output": {
                    "source_name": "Drill Run Semantic Model",
                    "measures": ["Average ROP", "Run Count"]
                  }
                },
                {
                  "type": "message",
                  "id": "msg_1",
                  "role": "assistant",
                  "content": [{"type":"output_text","text":{{JsonSerializer.Serialize(Disclosure + "\nSafe answer.")}}}]
                }
              ]
            }
            """;
        var client = CreateClient(response);

        var result = await client.SendAsync(
            "hello",
            "conv_1",
            null,
            CancellationToken.None);

        Assert.Equal(
            ["Average ROP", "Run Count"],
            Assert.Single(result.Sources).Measures);
    }

    private static FoundryClient CreateClient(string response)
    {
        var handler = new SequenceHttpMessageHandler(
            _ => HttpResponses.Json(HttpStatusCode.OK, response));
        return new FoundryClient(
            new HttpClient(handler),
            Options.Create(
                new FoundryOptions
                {
                    ProjectEndpoint =
                        "https://foundry.example/api/projects/drill-project",
                    AgentName = "welladvisor-fabric-orchestrator",
                }),
            TimeProvider.System,
            new StubFoundryTokenSource("service-token"));
    }

    private static string ResponseWith(string markdown) =>
        $$"""
        {
          "id": "resp_1",
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
