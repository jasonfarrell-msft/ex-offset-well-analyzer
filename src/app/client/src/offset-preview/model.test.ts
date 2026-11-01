/// <reference types="node" />
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { DEFAULT_CRITERIA, distanceLabel, findCandidates, snapshot, summarize, validRadius } from "./model";
import type { Criteria } from "./model";

const client = process.cwd();

describe("immutable preview snapshot", () => {
  it("recreates exactly from manifest-verified release bytes without regenerating the release", () => {
    expect(execFileSync("python3", ["scripts/offset_snapshot.py", "--check"], { cwd: client, encoding: "utf8" }))
      .toContain("PASS: snapshot exactly matches");
    const manifest = readFileSync(resolve(client, "../../../data/releases/v1.1.0/release_manifest.json"));
    expect(createHash("sha256").update(manifest).digest("hex")).toBe(snapshot.provenance.manifestSha256);
    expect(snapshot.targets).toHaveLength(12);
    expect(snapshot.wells).toHaveLength(100);
    expect(snapshot.sections).toHaveLength(274);
    expect(JSON.stringify(snapshot)).not.toContain("SYN-RUN-");
    for (const target of snapshot.targets) {
      expect(target.record_kind).toBe("PLANNED_TARGET");
      expect(target).not.toHaveProperty("acceptedFootageFt");
      expect(target).not.toHaveProperty("run_count");
    }
  });

  it("matches the independent Decimal oracle for all 12 targets, all 8 section profiles, zero and maximum radii", () => {
    interface OracleRow {
      wellId: string; distanceSquaredFt2: string; distanceFt: string;
      metrics: Record<string, unknown>;
      matchingSections: { sectionId: string }[];
    }
    const cases = JSON.parse(execFileSync("python3", ["scripts/offset_oracle_cases.py"], {
      cwd: client, encoding: "utf8", maxBuffer: 8 * 1024 * 1024,
    })) as { targetId: string; criteria: Criteria; rows: OracleRow[]; excludedCount: number }[];
    expect(cases).toHaveLength(120);
    for (const testCase of cases) {
      const target = snapshot.targets.find((row) => row.target_id === testCase.targetId)!;
      const { candidates, exclusions } = findCandidates(target, testCase.criteria);
      expect(candidates.map((row) => row.well_id)).toEqual(testCase.rows.map((row) => row.wellId));
      expect(Object.values(exclusions).reduce((a, b) => a + b, 0)).toBe(testCase.excludedCount);
      expect(candidates.length + testCase.excludedCount).toBe(100);
      for (const [index, actual] of candidates.entries()) {
        const expected = testCase.rows[index]!;
        expect(actual.distanceSquared.toString()).toBe(expected.distanceSquaredFt2);
        expect(distanceLabel(actual).replaceAll(",", "")).toBe(expected.distanceFt);
        expect(actual.sections.map((row) => row.section_id)).toEqual(expected.matchingSections.map((row) => row.sectionId));
        const { scope, unavailableReasons, ...metrics } = expected.metrics;
        expect(scope).toBe("MATCHING_WHOLE_SECTIONS");
        expect(unavailableReasons).toEqual([]);
        expect(actual.metrics).toEqual(metrics);
      }
    }
  }, 60000);

  it("uses unrounded radius eligibility, never the displayed distance", () => {
    const target = snapshot.targets[0]!;
    const profile = { ...DEFAULT_CRITERIA, formationMatch: false, holeSizeMatch: false };
    const all = findCandidates(target, profile).candidates;
    expect(all[0]!.well_id).toBe("SYN-WELL-0019");
    expect(distanceLabel(all[0]!)).toBe("119.2");
    expect(findCandidates(target, { ...profile, radiusFt: "119.2" }).candidates).toHaveLength(0);
    expect(findCandidates(target, { ...profile, radiusFt: "119.21" }).candidates[0]!.well_id).toBe("SYN-WELL-0019");
  });

  it("keeps warning/quarantine coverage and computes ratios from accepted sums", () => {
    const metrics = summarize(snapshot.sections);
    expect(metrics.acceptedRunCount).toBe(932);
    expect(metrics.quarantinedRunCount).toBe(5);
    expect(metrics.warningRunCount).toBe(20);
    expect(metrics.warningSectionCount).toBe(10);
    expect(metrics.warningIssueCount).toBe(15);
    const empty = summarize([]);
    expect(empty.acceptedFootageFt).toBeNull();
    expect(empty.acceptedDurationHours).toBeNull();
    expect(empty.averageFootagePerRunFt).toBeNull();
    expect(empty.summaryPenetrationRateFtPerHour).toBeNull();
  });

  it.each(["", "-1", "3000000.000001", "Infinity", "NaN", "1e4", "0.0000001"])("rejects unsupported radius %s", (value) => {
    expect(validRadius(value)).toBe(false);
    expect(findCandidates(snapshot.targets[0]!, { ...DEFAULT_CRITERIA, radiusFt: value }).candidates).toEqual([]);
  });
});
