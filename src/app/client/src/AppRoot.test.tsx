import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("AppRoot", () => {
  it("shows workspace navigation and opens historical chat by default", async () => {
    const { AppRoot } = await import("./AppRoot");
    render(<AppRoot />);

    expect(screen.getByRole("navigation", { name: "Drill Advisor workspace" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Historical chat" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: /Summarize all 100 synthetic wells/ })).toBeVisible();
  });

  it("navigates to live offset analysis and supports direct URL access", async () => {
    const user = userEvent.setup();
    const { AppRoot } = await import("./AppRoot");
    render(<AppRoot />);

    await user.click(screen.getByRole("button", { name: "Offset well analysis" }));
    expect(window.location.search).toBe("?view=offset");
    expect(screen.getByRole("heading", { name: "Offset well analysis" })).toBeVisible();

    cleanup();
    window.history.replaceState(null, "", "/?view=offset");
    render(<AppRoot />);

    expect(
      screen.getByRole("button", { name: "Offset well analysis", hidden: true }),
    ).toHaveAttribute("aria-current", "page");
    expect(
      screen.getByRole("heading", { name: "Offset well analysis", hidden: true }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("dialog", { name: "Loading offset workspace data" }),
    ).toBeVisible();
  });

  it("loads offset targets/candidates once without runaway refetching", async () => {
    window.history.replaceState(null, "", "/?view=offset");
    vi.resetModules();

    const versions = {
      contractVersion: "offset-well-analysis-v1",
      queryContractVersion: "offset-well-analysis-v1",
      transformationContractVersion: "1.1.0",
      datasetVersion: "v1.1.0",
      releaseId: "v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
      manifestSha256: "904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
    };
    const target = {
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
    };
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = JSON.parse((init?.body as string) ?? "{}") as { operation?: string };
      if (body.operation === "targets") {
        return new Response(JSON.stringify({
          ...versions,
          operation: "targets",
          status: "success",
          context: null,
          contextHash: null,
          rows: [target],
          totalCount: 1,
          truncated: false,
          exclusions: [],
          evidence: { receiptId: "r1", requestId: "r1", toolCallId: "r1", resultId: "r1", sources: [], grain: "RELEASE_TARGET", units: {}, denominators: {}, qualityCaveats: [], completion: "VALIDATED_AUTHENTICATED_RESULT" },
        }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (body.operation === "candidates") {
        return new Response(JSON.stringify({
          ...versions,
          operation: "candidates",
          status: "success",
          context: {
            targetId: target.targetId,
            criteria: { radiusFt: "10000", formationMatch: true, holeSizeMatch: true, mdOverlap: false },
            selectedWellIds: [],
            contextRevision: 0,
          },
          contextHash: "a".repeat(64),
          rows: [{
            wellId: "SYN-WELL-0001",
            wellName: "Well 1",
            basinName: "Synthetic North Basin",
            fieldName: "Fictional Aurora Field",
            coordinateFrameId: "SYN-LOCAL-FT-V1",
            locationSemantics: "SYNTHETIC_SURFACE_WELLHEAD",
            coordinateUnits: "ft",
            distanceSquaredFt2: "1",
            distanceFt: "1.0",
            matchingSections: [{
              sectionId: "SYN-SEC-0001-01",
              formationName: "Synthetic Brimstone",
              holeSizeIn: "17.5",
              startMdFt: "0",
              endMdFt: "100",
              trajectoryProfile: "VERTICAL",
            }],
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
          }],
          totalCount: 1,
          truncated: false,
          exclusions: [],
          evidence: { receiptId: "r2", requestId: "r2", toolCallId: "r2", resultId: "r2", sources: [], grain: "RELEASE_TARGET_WELL_MATCHING_SECTIONS", units: {}, denominators: {}, qualityCaveats: [], completion: "VALIDATED_AUTHENTICATED_RESULT" },
        }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      throw new Error(`Unexpected operation: ${String(body.operation)}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { AppRoot } = await import("./AppRoot");
    render(<AppRoot />);

    expect(await screen.findByText("1 eligible")).toBeVisible();
    expect(screen.getByText("SYN-TARGET-0001 · Fictional Aurora Field")).toBeVisible();

    const offsetCalls = () =>
      fetchMock.mock.calls.filter((call) => call[0] === "/api/offset-analysis").length;
    expect(offsetCalls()).toBe(2);

    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(offsetCalls()).toBe(2);
  });
});
