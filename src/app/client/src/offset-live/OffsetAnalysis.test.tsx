import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { OffsetAnalysis } from "./OffsetAnalysis";
import type {
  ChatApi,
  ChatResponse,
  OffsetApi,
  OffsetCandidatesResponse,
  OffsetCompareResponse,
  OffsetContext,
  OffsetTarget,
  OffsetTargetsResponse,
} from "../types";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

const target: OffsetTarget = {
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
  surfaceXFt: "100",
  surfaceYFt: "200",
  referenceDatasetVersion: "v1.0.0",
  referenceManifestSha256: "f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9",
  isSynthetic: true,
  plannedBitType: "PDC",
  plannedBhaType: "ROTARY_STEERABLE",
  plannedMudType: "WBM",
};

function versions(
  overrides: Partial<{
    contractVersion: string;
    queryContractVersion: string;
    transformationContractVersion: string;
    datasetVersion: string;
    releaseId: string;
    manifestSha256: string;
  }> = {},
) {
  return {
    contractVersion: "offset-well-analysis-v1",
    queryContractVersion: "offset-well-analysis-v1",
    transformationContractVersion: "1.1.0",
    datasetVersion: "v1.1.0",
    releaseId: "v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
    manifestSha256: "904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
    ...overrides,
  };
}

function candidateResponse(contextRevision = 1): OffsetCandidatesResponse {
  return {
    ...versions(),
    operation: "candidates",
    status: "success",
    context: {
      targetId: target.targetId,
      criteria: {
        radiusFt: "10000",
        formationMatch: true,
        holeSizeMatch: true,
        mdOverlap: false,
      },
      selectedWellIds: [],
      contextRevision,
    },
    contextHash: "a".repeat(64),
    rows: Array.from({ length: 6 }, (_, index) => ({
      wellId: `SYN-WELL-00${(index + 1).toString().padStart(2, "0")}`,
      wellName: `Well ${index + 1}`,
      basinName: "Synthetic North Basin",
      fieldName: "Fictional Aurora Field",
      coordinateFrameId: "SYN-LOCAL-FT-V1",
      locationSemantics: "SYNTHETIC_SURFACE_WELLHEAD",
      coordinateUnits: "ft",
      distanceSquaredFt2: String(index + 1),
      distanceFt: `${index + 1}.0`,
      matchingSections: [
        {
          sectionId: `SYN-SEC-000${index + 1}-01`,
          formationName: "Synthetic Brimstone",
          holeSizeIn: "17.5",
          startMdFt: "0",
          endMdFt: "100",
          trajectoryProfile: "VERTICAL",
        },
      ],
      metrics: {
        matchingSectionCount: 1,
        acceptedRunCount: 2,
        acceptedFootageFt: "100",
        acceptedDurationHours: "10",
        averageFootagePerRunFt: "50.000000",
        summaryPenetrationRateFtPerHour: "10.000000",
        quarantinedRunCount: 0,
        warningRunCount: 0,
        warningSectionCount: 0,
        warningIssueCount: 0,
        scope: "MATCHING_WHOLE_SECTIONS",
        unavailableReasons: [],
      },
    })),
    totalCount: 6,
    truncated: false,
    exclusions: [],
    evidence: {
      receiptId: "receipt-id-1234567890",
      requestId: "request-id-1234567890",
      toolCallId: "tool-call-1234567890",
      resultId: "result-id-1234567890",
      sources: [
        {
          view: "serving.offset_candidate_summary",
          columns: ["target_id", "well_id"],
          measures: [],
        },
      ],
      grain: "RELEASE_TARGET_WELL_MATCHING_SECTIONS",
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
}

function compareResponse(context: OffsetContext): OffsetCompareResponse {
  return {
    ...versions(),
    operation: "compare",
    status: "success",
    context,
    contextHash: "b".repeat(64),
    rows: context.selectedWellIds.map((wellId) => ({
      wellId,
      matchingSections: [
        {
          sectionId: `SYN-SEC-${wellId.slice(-4)}-01`,
          formationName: "Synthetic Brimstone",
          holeSizeIn: "17.5",
          startMdFt: "0",
          endMdFt: "100",
          trajectoryProfile: "VERTICAL",
        },
      ],
      metrics: {
        matchingSectionCount: 1,
        acceptedRunCount: 2,
        acceptedFootageFt: "100",
        acceptedDurationHours: "10",
        averageFootagePerRunFt: "50.000000",
        summaryPenetrationRateFtPerHour: "10.000000",
        quarantinedRunCount: 0,
        warningRunCount: 0,
        warningSectionCount: 0,
        warningIssueCount: 0,
        scope: "MATCHING_WHOLE_SECTIONS",
        unavailableReasons: [],
      },
      plannedBitType: "PDC",
      plannedBhaType: "ROTARY_STEERABLE",
      plannedMudType: "WBM",
      runConfigContext: {
        runTuples: [{
          bitType: "PDC",
          bhaType: "ROTARY_STEERABLE",
          mudType: "WBM",
          mudWeightPpg: "10.2",
          mudFunnelViscositySec: "42",
          acceptedRunCount: 2,
          acceptedFootageFt: "100",
          acceptedDurationHours: "10",
        }],
      },
      eventContext: {
        totalEventCount: 3,
        totalEventDurationHours: "4.5",
        byType: [
          { eventType: "LOSSES", eventCount: 2, eventDurationHours: "3.0" },
          { eventType: "NPT", eventCount: 1, eventDurationHours: "1.5" },
        ],
        bySubtype: [
          {
            eventType: "LOSSES",
            eventSubtype: "PARTIAL",
            eventCount: 2,
            eventDurationHours: "3.0",
          },
        ],
      },
    })),
    totalCount: context.selectedWellIds.length,
    truncated: false,
    exclusions: [],
    evidence: {
      receiptId: "compare-receipt-1234",
      requestId: "compare-request-1234",
      toolCallId: "compare-tool-1234",
      resultId: "compare-result-1234",
      sources: [
        {
          view: "serving.offset_section_summary",
          columns: ["well_id", "section_id"],
          measures: [],
        },
      ],
      grain: "RELEASE_TARGET_WELL_MATCHING_SECTIONS",
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
}

function targetsResponse(): OffsetTargetsResponse {
  return {
    ...versions(),
    operation: "targets",
    status: "success",
    context: null,
    contextHash: null,
    rows: [target],
    totalCount: 12,
    truncated: false,
    exclusions: [],
    evidence: {
      receiptId: "targets-receipt-1234",
      requestId: "targets-request-1234",
      toolCallId: "targets-tool-1234",
      resultId: "targets-result-1234",
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
}

describe("OffsetAnalysis", () => {
  it("shows disclosure with API contract and release from successful responses", async () => {
    const currentVersions = versions({
      contractVersion: "offset-well-analysis-v2",
      queryContractVersion: "offset-well-analysis-v2",
      transformationContractVersion: "1.2.0",
      datasetVersion: "v1.2.0",
      releaseId:
        "v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0",
      manifestSha256: "6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0",
    });
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue({
        ...targetsResponse(),
        ...currentVersions,
      }),
      candidates: vi.fn().mockResolvedValue({
        ...candidateResponse(),
        ...currentVersions,
      }),
      compare: vi.fn().mockResolvedValue(compareResponse({
        targetId: target.targetId,
        criteria: {
          radiusFt: "10000",
          formationMatch: true,
          holeSizeMatch: true,
          mdOverlap: false,
        },
        selectedWellIds: ["SYN-WELL-0001"],
        contextRevision: 2,
      })),
    };

    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    expect(screen.getByText("offset-well-analysis-v2")).toBeVisible();
    expect(screen.getByText("v1.2.0")).toBeVisible();
    expect(
      screen.queryByText("SYNTHETIC DATA • v1.1.0 • DEVELOPMENT / OFFSET COMPARISON ONLY"),
    ).not.toBeInTheDocument();
  });

  it("shows loading and then renders candidates", async () => {
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn().mockResolvedValue(compareResponse({
        targetId: target.targetId,
        criteria: {
          radiusFt: "10000",
          formationMatch: true,
          holeSizeMatch: true,
          mdOverlap: false,
        },
        selectedWellIds: ["SYN-WELL-0001"],
        contextRevision: 2,
      })),
    };

    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);

    expect(screen.getByText("Loading targets…")).toBeVisible();
    expect(await screen.findByText("6 eligible")).toBeVisible();
    expect(screen.getByLabelText("Select SYN-WELL-0001")).toBeVisible();
  });

  it("keeps a blocking loader visible from targets through initial candidates without a gap", async () => {
    const targetsRequest = deferred<OffsetTargetsResponse>();
    const candidatesRequest = deferred<OffsetCandidatesResponse>();
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockImplementation(async () => targetsRequest.promise),
      candidates: vi.fn().mockImplementation(async () => candidatesRequest.promise),
      compare: vi.fn(),
    };

    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);

    expect(
      screen.getByRole("dialog", { name: "Loading offset workspace data" }),
    ).toBeVisible();
    expect(
      screen.getByText("Loading planned targets before candidate analysis can begin."),
    ).toBeVisible();

    targetsRequest.resolve(targetsResponse());
    await waitFor(() => expect(offsetApi.candidates).toHaveBeenCalledTimes(1));
    expect(
      screen.getByRole("dialog", { name: "Loading offset workspace data" }),
    ).toBeVisible();
    expect(
      screen.getByText("Loading candidate wells for the current target and filter criteria."),
    ).toBeVisible();

    candidatesRequest.resolve(candidateResponse());
    await waitFor(() =>
      expect(
        screen.queryByRole("dialog", { name: "Loading offset workspace data" }),
      ).not.toBeInTheDocument(),
    );
    expect(await screen.findByText("6 eligible")).toBeVisible();
  });

  it("enforces max selection and compares selected wells", async () => {
    const compare = vi.fn(async (context: OffsetContext) => compareResponse(context));
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare,
    };

    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    for (let i = 1; i <= 5; i += 1) {
      await user.click(
        screen.getByLabelText(`Select SYN-WELL-00${i.toString().padStart(2, "0")}`),
      );
    }

    expect(screen.getByLabelText("Select SYN-WELL-0006")).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Compare selected (5)" }));
    await screen.findByRole("table");

    expect(compare).toHaveBeenCalledWith(
      expect.objectContaining({
        targetId: "SYN-TARGET-0001",
        selectedWellIds: [
          "SYN-WELL-0001",
          "SYN-WELL-0002",
          "SYN-WELL-0003",
          "SYN-WELL-0004",
          "SYN-WELL-0005",
        ],
      }),
      expect.any(AbortSignal),
    );
  });

  it("resets selection and comparison when scope changes", async () => {
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi
        .fn()
        .mockResolvedValueOnce(candidateResponse(1))
        .mockResolvedValue(candidateResponse(3)),
      compare: vi.fn(async (context: OffsetContext) => compareResponse(context)),
    };

    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    expect(await screen.findByRole("table")).toBeVisible();
    expect(screen.getByRole("heading", { name: "4 / Compare accepted historical summaries" })).toBeVisible();
    expect(screen.getByText("Comparison ready for 1 selected well.")).toBeVisible();

    await user.clear(screen.getByLabelText("Surface radius (ft)"));
    await user.type(screen.getByLabelText("Surface radius (ft)"), "12000");

    await waitFor(() => expect(screen.getByText("0 of 5 selected")).toBeVisible());
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText("Comparison ready for 1 selected well.")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "4 / Compare accepted historical summaries" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "3 / Select historical wells" })).toBeVisible();
  });

  it("does not refetch candidates when only manual selection changes", async () => {
    const candidates = vi.fn().mockResolvedValue(candidateResponse());
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates,
      compare: vi.fn(async (context: OffsetContext) => compareResponse(context)),
    };

    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");
    expect(candidates).toHaveBeenCalledTimes(1);

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByLabelText("Select SYN-WELL-0002"));
    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));

    expect(candidates).toHaveBeenCalledTimes(1);
  });

  it("aborts an in-flight compare request on unmount to avoid stale updates", async () => {
    const compareRequest = deferred<OffsetCompareResponse>();
    let compareAborted = false;
    const compare = vi.fn().mockImplementation(async (_context: OffsetContext, signal?: AbortSignal) => {
      const signalReference = signal as {
        addEventListener?: (type: string, listener: () => void) => void;
      } | undefined;
      signalReference?.addEventListener?.("abort", () => {
        compareAborted = true;
      });
      return compareRequest.promise;
    });
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare,
    };

    const user = userEvent.setup();
    const { unmount } = render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));

    expect(compare).toHaveBeenCalledTimes(1);
    expect(compareAborted).toBe(false);

    unmount();

    expect(compareAborted).toBe(true);
  });

  it("shows a blocking compare loader and unlocks after compare failure", async () => {
    const compareRequest = deferred<OffsetCompareResponse>();
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn().mockImplementation(async () => compareRequest.promise),
    };
    const user = userEvent.setup();

    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));

    expect(
      screen.getByText("Building selected well comparison results."),
    ).toBeVisible();

    compareRequest.resolve({
      ...versions(),
      status: "unavailable",
      operation: "compare",
      context: {
        targetId: target.targetId,
        criteria: {
          radiusFt: "10000",
          formationMatch: true,
          holeSizeMatch: true,
          mdOverlap: false,
        },
        selectedWellIds: ["SYN-WELL-0001"],
        contextRevision: 1,
      },
      contextHash: null,
      evidence: null,
      error: {
        code: "UPSTREAM_UNAVAILABLE",
        retryable: true,
      },
    });

    await waitFor(() =>
      expect(
        screen.queryByRole("dialog", { name: "Loading offset workspace data" }),
      ).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("heading", { name: "Comparison unavailable" })).toBeVisible();
    expect(screen.getByText("The service returned UPSTREAM_UNAVAILABLE.")).toBeVisible();
  });

  it("blocks background nav controls while loading and restores interaction afterward", async () => {
    const targetsRequest = deferred<OffsetTargetsResponse>();
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockImplementation(async () => targetsRequest.promise),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn(),
    };
    const onNavigate = vi.fn();
    const user = userEvent.setup();

    render(
      <div>
        <button type="button" onClick={onNavigate}>
          Workspace navigation
        </button>
        <OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />
      </div>,
    );

    const navButton = screen.getByRole("button", { name: "Workspace navigation" });
    navButton.focus();
    await user.keyboard("{Enter}");
    await user.click(navButton);
    expect(onNavigate).not.toHaveBeenCalled();

    targetsRequest.resolve(targetsResponse());
    await screen.findByText("6 eligible");

    await user.click(navButton);
    expect(onNavigate).toHaveBeenCalledTimes(1);
  });

  it("re-shows and clears blocking loader on candidate refetch from filter updates", async () => {
    const firstCandidates = deferred<OffsetCandidatesResponse>();
    const secondCandidates = deferred<OffsetCandidatesResponse>();
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi
        .fn()
        .mockImplementationOnce(async () => firstCandidates.promise)
        .mockImplementationOnce(async () => secondCandidates.promise),
      compare: vi.fn(),
    };
    const user = userEvent.setup();

    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);

    expect(
      screen.getByRole("dialog", { name: "Loading offset workspace data" }),
    ).toBeVisible();
    firstCandidates.resolve(candidateResponse(1));
    await screen.findByText("6 eligible");

    await user.clear(screen.getByLabelText("Surface radius (ft)"));
    await user.type(screen.getByLabelText("Surface radius (ft)"), "12000");

    expect(
      screen.getByRole("dialog", { name: "Loading offset workspace data" }),
    ).toBeVisible();
    secondCandidates.resolve(candidateResponse(2));
    await waitFor(() =>
      expect(
        screen.queryByRole("dialog", { name: "Loading offset workspace data" }),
      ).not.toBeInTheDocument(),
    );
    expect(offsetApi.candidates).toHaveBeenCalledTimes(2);
  });

  it("clears candidate loading state when radius becomes invalid during an in-flight request", async () => {
    const candidatesRequest = deferred<OffsetCandidatesResponse>();
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockImplementation(async () => candidatesRequest.promise),
      compare: vi.fn(),
    };
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);

    await waitFor(() => expect(offsetApi.candidates).toHaveBeenCalledTimes(1));
    expect(
      screen.getByText("Loading candidate wells for the current target and filter criteria."),
    ).toBeVisible();

    fireEvent.change(screen.getByLabelText("Surface radius (ft)"), {
      target: { value: "3000000.000001" },
    });

    await waitFor(() =>
      expect(
        screen.queryByRole("dialog", { name: "Loading offset workspace data" }),
      ).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: "Compare selected (0)" })).toBeDisabled();
  });

  it("advances to a results pane after compare and returns to selection without losing state", async () => {
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn(async (context: OffsetContext) => compareResponse(context)),
    };
    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    await screen.findByRole("table");

    expect(screen.queryByRole("heading", { name: "3 / Select historical wells" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back to selection" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Edit selection" })).toBeVisible();
    expect(screen.getByText("Comparison ready for 1 selected well.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Back to selection" }));
    expect(screen.getByRole("heading", { name: "3 / Select historical wells" })).toBeVisible();
    expect(screen.getByRole("button", { name: "View comparison" })).toBeVisible();
    expect(screen.getByLabelText("Select SYN-WELL-0001")).toBeChecked();
    await user.click(screen.getByRole("button", { name: "View comparison" }));
    expect(await screen.findByRole("table")).toBeVisible();
  });

  it("renders planned intent, observed tuples, events, and synthetic disclosure", async () => {
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn(async (context: OffsetContext) => {
        const response = compareResponse(context);
        if (response.status === "success" && response.rows[1]) {
          response.rows[1] = {
            ...response.rows[1],
            runConfigContext: null,
            eventContext: null,
          };
        }
        return response;
      }),
    };
    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByLabelText("Select SYN-WELL-0002"));
    await user.click(screen.getByRole("button", { name: "Compare selected (2)" }));
    await screen.findByRole("table");

    expect(screen.getByText(/Synthetic comparison context only/i)).toBeVisible();
    expect(screen.getByRole("heading", { name: "Planned target intent (if provided)" })).toBeVisible();
    expect(screen.getByText("PDC")).toBeVisible();
    expect(screen.getByText(/Well-wide configuration tuples \(1\)/)).toBeVisible();
    await user.click(screen.getByText(/Well-wide configuration tuples \(1\)/));
    await user.click(screen.getByText("Observed well context events (well-wide)"));
    expect(screen.getByText(/Mud weight: 10.2 ppg/i)).toBeVisible();
    expect(screen.getByText(/Well-wide tuple totals — accepted runs: 2/i)).toBeVisible();
    expect(screen.getByText(/Well-wide event totals — count: 3/i)).toBeVisible();
    expect(screen.getAllByText(/unavailable in this response/i).length).toBeGreaterThan(0);
  });

  it("renders detailed compare provenance with sources, grain, units, denominators, and caveats", async () => {
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn(async (context: OffsetContext) => compareResponse(context)),
    };
    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    await screen.findByRole("table");

    expect(screen.getByText("Correlation IDs: toolCallId compare-tool-1234 · resultId compare-result-1234 · contextHash bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")).toBeVisible();

    await user.click(screen.getByText("Evidence sources (1)"));
    expect(screen.getByText("serving.offset_section_summary")).toBeVisible();
    expect(screen.getByText("Columns: well_id, section_id")).toBeVisible();

    await user.click(screen.getByText("Grain, units, and denominators"));
    expect(screen.getByText("Grain: RELEASE_TARGET_WELL_MATCHING_SECTIONS")).toBeVisible();
    expect(screen.getByText("acceptedFootageFt")).toBeVisible();
    expect(screen.getByText("acceptedDurationHours")).toBeVisible();
    expect(screen.getAllByText("summaryPenetrationRateFtPerHour").length).toBeGreaterThan(0);

    await user.click(screen.getByText("Quality caveats"));
    expect(screen.getByText("Synthetic data")).toBeVisible();
  });

  it("shows unavailable correlation IDs when optional compare IDs are missing", async () => {
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn(async (context: OffsetContext) => {
        const response = compareResponse(context);
        if (response.status !== "success") return response;
        return {
          ...response,
          contextHash: null,
          evidence: {
            ...response.evidence,
            toolCallId: "",
            resultId: "",
          },
        };
      }),
    };
    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    await screen.findByRole("table");

    expect(screen.getByText("Correlation IDs: Unavailable in this response.")).toBeVisible();
    expect(screen.queryByText(/toolCallId/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/resultId/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/contextHash/i)).not.toBeInTheDocument();
  });

  it("allows choosing only compared wells as reference and generates a qualitative brief", async () => {
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn(async (context: OffsetContext) => compareResponse(context)),
    };
    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    await screen.findByRole("table");

    expect(screen.getByLabelText("Use SYN-WELL-0001 as reference")).toBeVisible();
    expect(
      screen.queryByLabelText("Use SYN-WELL-0002 as reference"),
    ).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("Use SYN-WELL-0001 as reference"));
    await user.type(
      screen.getByLabelText("Optional rationale (workspace-only note)"),
      "Closest trajectory fit with available section details.",
    );
    await user.click(screen.getByRole("button", { name: "Create target expectation brief" }));

    expect(
      await screen.findByRole("region", { name: "Target expectation evidence brief" }),
    ).toBeVisible();
    expect(
      screen.getByText(/Cannot estimate expected target footage, duration, ft\/hour/i),
    ).toBeVisible();
    expect(
      screen.getByText(/Synthetic POC evidence only\. Correlation in this comparison is not causation/i),
    ).toBeVisible();
    expect(screen.getByText(/User rationale \(workspace note\):/i)).toBeVisible();
    expect(screen.getByRole("link", { name: "Download brief JSON" })).toBeVisible();
  });

  it("summarizes formation/hole fit as descriptive counts when filters are OFF", async () => {
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn(async (context: OffsetContext) => {
        const response = compareResponse(context);
        if (response.status === "success" && response.rows[0]) {
          response.rows[0] = {
            ...response.rows[0],
            matchingSections: [
              {
                sectionId: "SYN-SEC-MISMATCH-01",
                formationName: "Different Formation",
                holeSizeIn: "12.25",
                startMdFt: "0",
                endMdFt: "100",
                trajectoryProfile: "VERTICAL",
              },
            ],
          };
        }
        return response;
      }),
    };
    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Same canonical formation"));
    await user.click(screen.getByLabelText("Same hole size"));
    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    await screen.findByRole("table");
    await user.click(screen.getByLabelText("Use SYN-WELL-0001 as reference"));
    await user.click(screen.getByRole("button", { name: "Create target expectation brief" }));

    expect(
      await screen.findByText(
        "Formation/hole fit: formation filter OFF; 0/1 sections match target canonical formation. Hole-size filter OFF; 0/1 sections match target hole size. Filters that are OFF did not constrain section eligibility, so these counts are descriptive only.",
      ),
    ).toBeVisible();
  });

  it("shows unavailable formation/hole fit counts when the selected reference has zero matching sections", async () => {
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn(async (context: OffsetContext) => {
        const response = compareResponse(context);
        if (response.status === "success" && response.rows[0]) {
          response.rows[0] = {
            ...response.rows[0],
            matchingSections: [],
            metrics: {
              ...response.rows[0].metrics,
              matchingSectionCount: 0,
            },
          };
        }
        return response;
      }),
    };
    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    await screen.findByRole("table");
    await user.click(screen.getByLabelText("Use SYN-WELL-0001 as reference"));
    await user.click(screen.getByRole("button", { name: "Create target expectation brief" }));

    expect(
      await screen.findByText(
        "Formation/hole fit: no matching sections were returned, so canonical alignment counts are unavailable.",
      ),
    ).toBeVisible();
  });

  it("includes warning section/issue counts in brief UI and downloaded JSON", async () => {
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn(async (context: OffsetContext) => {
        const response = compareResponse(context);
        if (response.status === "success" && response.rows[0]) {
          response.rows[0] = {
            ...response.rows[0],
            metrics: {
              ...response.rows[0].metrics,
              warningRunCount: 3,
              warningSectionCount: 2,
              warningIssueCount: 5,
              quarantinedRunCount: 1,
            },
          };
        }
        return response;
      }),
    };
    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    await screen.findByRole("table");
    await user.click(screen.getByLabelText("Use SYN-WELL-0001 as reference"));
    await user.click(screen.getByRole("button", { name: "Create target expectation brief" }));
    await screen.findByRole("region", { name: "Target expectation evidence brief" });

    expect(
      screen.getByText(/Warning runs 3; warning sections 2; warning issues 5; quarantined runs 1\./i),
    ).toBeVisible();

    const downloadLink = screen.getByRole("link", { name: "Download brief JSON" });
    const href = downloadLink.getAttribute("href");
    expect(href).toContain("data:application/json;charset=utf-8,");
    const encodedPayload = href?.replace("data:application/json;charset=utf-8,", "") ?? "";
    const parsed = JSON.parse(decodeURIComponent(encodedPayload)) as {
      warningRunCount: number;
      warningSectionCount: number;
      warningIssueCount: number;
      quarantinedRunCount: number;
    };
    expect(parsed.warningRunCount).toBe(3);
    expect(parsed.warningSectionCount).toBe(2);
    expect(parsed.warningIssueCount).toBe(5);
    expect(parsed.quarantinedRunCount).toBe(1);
  });

  it("clears reference choice and rationale when context changes", async () => {
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi
        .fn()
        .mockResolvedValueOnce(candidateResponse(1))
        .mockResolvedValueOnce(candidateResponse(2))
        .mockResolvedValue(candidateResponse(3)),
      compare: vi.fn(async (context: OffsetContext) => compareResponse(context)),
    };
    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    await screen.findByRole("table");

    await user.click(screen.getByLabelText("Use SYN-WELL-0001 as reference"));
    await user.type(
      screen.getByLabelText("Optional rationale (workspace-only note)"),
      "Temporary rationale.",
    );
    await user.clear(screen.getByLabelText("Surface radius (ft)"));
    await user.type(screen.getByLabelText("Surface radius (ft)"), "12000");
    await screen.findByRole("heading", { name: "3 / Select historical wells" });

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    await screen.findByRole("table");

    const rationaleInput = screen.getByLabelText("Optional rationale (workspace-only note)");
    expect(rationaleInput).toHaveValue("");
    expect(screen.getByLabelText("Use SYN-WELL-0001 as reference")).not.toBeChecked();
  });

  it("supports switching reference wells before finalizing the brief", async () => {
    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn(async (context: OffsetContext) => compareResponse(context)),
    };
    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: vi.fn() }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByLabelText("Select SYN-WELL-0002"));
    await user.click(screen.getByRole("button", { name: "Compare selected (2)" }));
    await screen.findByRole("table");

    await user.click(screen.getByLabelText("Use SYN-WELL-0001 as reference"));
    await user.click(screen.getByLabelText("Use SYN-WELL-0002 as reference"));
    await user.click(screen.getByRole("button", { name: "Create target expectation brief" }));

    expect(await screen.findByText(/using reference/i)).toHaveTextContent("SYN-WELL-0002");
    await user.click(screen.getByRole("button", { name: "Change reference" }));
    expect(screen.getByLabelText("Use SYN-WELL-0002 as reference")).toBeChecked();
  });

  it("sends follow-up chat with selected offset context", async () => {
    const chatSend: ChatApi["send"] = vi.fn().mockResolvedValue({
        conversationId: "offset-chat-1",
        message: {
          id: "assistant-1",
          role: "assistant",
          markdown: "Grounded answer",
          createdAtUtc: "2026-10-29T10:00:00Z",
        },
        visuals: [],
        toolCalls: [],
        sources: [],
      } satisfies ChatResponse);

    const offsetApi: OffsetApi = {
      targets: vi.fn().mockResolvedValue(targetsResponse()),
      candidates: vi.fn().mockResolvedValue(candidateResponse()),
      compare: vi.fn(async (context: OffsetContext) => compareResponse(context)),
    };

    const user = userEvent.setup();
    render(<OffsetAnalysis offsetApi={offsetApi} chatApi={{ send: chatSend }} />);
    await screen.findByText("6 eligible");

    await user.click(screen.getByLabelText("Select SYN-WELL-0001"));
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    await screen.findByRole("table");

    await user.type(
      screen.getByLabelText("Ask follow-up about selected offset context"),
      "Why is this well included?",
    );
    await user.click(screen.getByRole("button", { name: "Ask follow-up" }));

    await screen.findByText("Grounded answer");

    expect(chatSend).toHaveBeenCalledWith(
      expect.objectContaining({
        message: "Why is this well included?",
        offsetContext: expect.objectContaining({
          contractVersion: "offset-well-analysis-v1",
          releaseId:
            "v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
          context: expect.objectContaining({
            selectedWellIds: ["SYN-WELL-0001"],
          }),
        }),
      }),
      expect.any(AbortSignal),
    );
  });
});
