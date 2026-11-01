using System.Text.Json;
using DrillAdvisor.Api.Offset;

namespace DrillAdvisor.Api.Tests;

public sealed class OffsetRequestParserTests
{
    [Fact]
    public void TryParseOperationRequest_V1RejectsUnknownProperties()
    {
        var document = JsonDocument.Parse(
            """
            {
              "operation":"targets",
              "contractVersion":"offset-well-analysis-v1",
              "releaseId":"v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
              "unexpected":"value"
            }
            """);

        var parsed = OffsetRequestParser.TryParseOperationRequest(
            document.RootElement,
            allowChatOperation: false,
            out _,
            out _,
            out _);

        Assert.False(parsed);
    }

    [Fact]
    public void TryParseOperationRequest_V2AcceptsReleasePin()
    {
        var document = JsonDocument.Parse(
            """
            {
              "operation":"targets",
              "contractVersion":"offset-well-analysis-v2",
              "releaseId":"v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0"
            }
            """);

        var parsed = OffsetRequestParser.TryParseOperationRequest(
            document.RootElement,
            allowChatOperation: false,
            out var request,
            out _,
            out _);

        Assert.True(parsed);
        Assert.NotNull(request);
        Assert.Equal(OffsetContractVersions.V2.ContractVersion, request.ContractVersion);
        Assert.Equal(OffsetContractVersions.V2.ReleaseId, request.ReleaseId);
    }

    [Fact]
    public void TryParseChatOffsetContext_AcceptsV2Envelope()
    {
        var document = JsonDocument.Parse(
            """
            {
              "offsetContext": {
                "contractVersion":"offset-well-analysis-v2",
                "releaseId":"v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0",
                "context": {
                  "targetId":"SYN-TARGET-0001",
                  "criteria": {
                    "radiusFt":"10000",
                    "formationMatch": true,
                    "holeSizeMatch": true,
                    "mdOverlap": false
                  },
                  "selectedWellIds":["SYN-WELL-0019"],
                  "contextRevision":0
                }
              }
            }
            """);

        var parsed = OffsetRequestParser.TryParseChatOffsetContext(
            document.RootElement,
            out var context,
            out var contract);

        Assert.True(parsed);
        Assert.NotNull(context);
        Assert.Equal("SYN-TARGET-0001", context.TargetId);
        Assert.Equal(OffsetContractVersions.V2.ContractVersion, contract.ContractVersion);
    }
}
