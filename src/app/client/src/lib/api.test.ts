import { createChatApi, createOffsetApi } from "./api";
import type { ChatResponse, OffsetContext } from "../types";

const responseBody: ChatResponse = {
  conversationId: "conversation-1",
  message: {
    id: "assistant-1",
    role: "assistant",
    markdown: "Answer",
    createdAtUtc: "2026-10-26T18:00:00Z",
  },
  visuals: [],
  toolCalls: [],
  sources: [],
};

describe("createChatApi", () => {
  it("sends an anonymous JSON request without an access-token header", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await createChatApi(fetcher).send({
      message: "Compare ROP",
      conversationId: "conversation-0",
    });

    expect(fetcher).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
        body: JSON.stringify({
          message: "Compare ROP",
          conversationId: "conversation-0",
        }),
      }),
    );
    const requestHeaders = fetcher.mock.calls[0]?.[1]?.headers;
    expect(requestHeaders).not.toHaveProperty("Authorization");
    expect(requestHeaders).not.toHaveProperty("X-Drill-Advisor-Access-Token");
  });
});

describe("createOffsetApi", () => {
  it("posts targets/candidates/compare to /api/offset-analysis", async () => {
    const offsetBody = {
      contractVersion: "offset-well-analysis-v2",
      queryContractVersion: "offset-well-analysis-v2",
      transformationContractVersion: "1.2.0",
      datasetVersion: "v1.2.0",
      releaseId:
        "v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0",
      manifestSha256:
        "6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0",
      operation: "targets",
      status: "success",
      context: null,
      contextHash: null,
      rows: [
        {
          targetId: "SYN-TARGET-0001",
          recordKind: "PLANNED_TARGET",
          basinName: "Synthetic North Basin",
          fieldName: "Fictional Aurora Field",
          expectedFormationName: "Synthetic Brimstone",
          plannedTrajectoryProfile: "BUILD_AND_HOLD",
          plannedHoleSizeIn: "17.5",
          plannedMdMinFt: "7250",
          plannedMdMaxFt: "13000",
          coordinateFrameId: "SYN-LOCAL-FT-V1",
          locationSemantics: "SYNTHETIC_SURFACE_WELLHEAD",
          coordinateUnits: "ft",
          surfaceXFt: "0",
          surfaceYFt: "0",
          referenceDatasetVersion: "v1.0.0",
          referenceManifestSha256:
            "f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9",
          isSynthetic: true,
        },
      ],
      totalCount: 12,
      truncated: false,
      exclusions: [],
      evidence: {
        receiptId: "receipt-id-1234567890",
        requestId: "request-id-1234567890",
        toolCallId: "tool-call-1234567890",
        resultId: "result-id-1234567890",
        sources: [
          {
            view: "serving.planned_target_summary",
            columns: ["target_id"],
            measures: [],
          },
        ],
        grain: "RELEASE_TARGET",
        units: {
          distanceSquaredFt2: "ft^2",
          distanceFt: "ft",
          acceptedFootageFt: "ft",
          acceptedDurationHours: "hours",
          averageFootagePerRunFt: "ft/run",
          summaryPenetrationRateFtPerHour: "ft/hour",
          counts: "entities_at_named_grain",
        },
        denominators: {
          averageFootagePerRunFt: "acceptedRunCount",
          summaryPenetrationRateFtPerHour: "acceptedDurationHours",
        },
        qualityCaveats: ["Synthetic data"],
        completion: "VALIDATED_AUTHENTICATED_RESULT",
      },
    };

    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify(offsetBody),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ ...offsetBody, operation: "candidates", context: contextForMock() }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            ...offsetBody,
            operation: "compare",
            context: { ...contextForMock(), selectedWellIds: ["SYN-WELL-0019"] },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    const api = createOffsetApi(fetcher);
    await api.targets();

    const context = contextForMock();
    await api.candidates(context);
    await api.compare({ ...context, selectedWellIds: ["SYN-WELL-0019"] });

    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "/api/offset-analysis",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          operation: "targets",
          contractVersion: "offset-well-analysis-v2",
          releaseId:
            "v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0",
        }),
      }),
    );
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "/api/offset-analysis",
      expect.objectContaining({
        body: JSON.stringify({
          operation: "candidates",
          contractVersion: "offset-well-analysis-v2",
          releaseId:
            "v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0",
          context,
        }),
      }),
    );
    expect(fetcher).toHaveBeenNthCalledWith(
      3,
      "/api/offset-analysis",
      expect.objectContaining({
        body: JSON.stringify({
          operation: "compare",
          contractVersion: "offset-well-analysis-v2",
          releaseId:
            "v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0",
          context: { ...context, selectedWellIds: ["SYN-WELL-0019"] },
        }),
      }),
    );
  });
});

function contextForMock(): OffsetContext {
  return {
    targetId: "SYN-TARGET-0001",
    criteria: {
      radiusFt: "10000",
      formationMatch: true,
      holeSizeMatch: true,
      mdOverlap: false,
    },
    selectedWellIds: [],
    contextRevision: 0,
  };
}
