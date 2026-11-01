import snapshot from "./snapshot.json";

export { snapshot };
export type Target = (typeof snapshot.targets)[number];
export type Section = (typeof snapshot.sections)[number];
export interface Criteria {
  radiusFt: string;
  formationMatch: boolean;
  holeSizeMatch: boolean;
  mdOverlap: boolean;
}
export const DEFAULT_CRITERIA: Criteria = {
  radiusFt: "10000", formationMatch: true, holeSizeMatch: true, mdOverlap: false,
};

const SCALE = 1_000_000n;

// Exact fixed-point arithmetic is sufficient for the immutable source precision
// and the preview's explicitly bounded (six decimal place) radius input.
function fixed(value: string) {
  if (!/^-?\d+(?:\.\d{1,6})?$/.test(value)) throw new Error("Invalid preview decimal");
  const negative = value.startsWith("-");
  const [whole = "0", fraction = ""] = value.replace("-", "").split(".");
  const result = BigInt(whole) * SCALE + BigInt(fraction.padEnd(6, "0"));
  return negative ? -result : result;
}

export function validRadius(value: string) {
  if (!/^\d+(?:\.\d{1,6})?$/.test(value)) return false;
  const radius = fixed(value);
  return radius >= 0n && radius <= 3_000_000n * SCALE;
}

function decimal(value: bigint) {
  const fraction = String(value % SCALE).padStart(6, "0").replace(/0+$/, "");
  return `${value / SCALE}${fraction ? `.${fraction}` : ""}`;
}

function ratio(numerator: bigint, denominator: bigint) {
  if (denominator <= 0n) return null;
  const scaled = (numerator * SCALE * 2n + denominator) / (denominator * 2n);
  return `${scaled / SCALE}.${String(scaled % SCALE).padStart(6, "0")}`;
}

export function summarize(sections: Section[]) {
  const sumCount = (field: "acceptedRunCount" | "quarantinedRunCount" | "warningRunCount" | "warningSectionCount" | "warningIssueCount") =>
    sections.reduce((sum, section) => sum + section[field], 0);
  const acceptedRunCount = sumCount("acceptedRunCount");
  const sum = (field: "acceptedFootageFt" | "acceptedDurationHours") => {
    const acceptedSections = sections.filter((section) => section.acceptedRunCount > 0);
    if (!acceptedRunCount || acceptedSections.some((section) => section[field] === null)) return null;
    return acceptedSections.reduce((total, section) => total + fixed(section[field]!), 0n);
  };
  const footage = sum("acceptedFootageFt");
  const duration = sum("acceptedDurationHours");
  return {
    matchingSectionCount: sections.length,
    acceptedRunCount,
    acceptedFootageFt: footage === null ? null : decimal(footage),
    acceptedDurationHours: duration === null ? null : decimal(duration),
    averageFootagePerRunFt: footage === null ? null : ratio(footage, BigInt(acceptedRunCount) * SCALE),
    summaryPenetrationRateFtPerHour: footage === null || duration === null ? null : ratio(footage, duration),
    quarantinedRunCount: sumCount("quarantinedRunCount"),
    warningRunCount: sumCount("warningRunCount"),
    warningSectionCount: sumCount("warningSectionCount"),
    warningIssueCount: sumCount("warningIssueCount"),
  };
}

function matching(section: Section, target: Target, criteria: Criteria) {
  if (criteria.formationMatch && (!section.formation_name || section.formation_name !== target.expected_formation_name)) return false;
  if (criteria.holeSizeMatch && fixed(section.hole_size_in) !== fixed(target.planned_hole_size_in)) return false;
  return !criteria.mdOverlap || (
    fixed(section.start_md_ft) < fixed(target.planned_md_max_ft) &&
    fixed(target.planned_md_min_ft) < fixed(section.end_md_ft)
  );
}

export function findCandidates(target: Target, criteria: Criteria) {
  const exclusions = { outsideRadius: 0, noMatchingSection: 0, noAcceptedRuns: 0, incompatibleCoordinates: 0 };
  if (!validRadius(criteria.radiusFt)) return { candidates: [], exclusions };
  const radius = fixed(criteria.radiusFt);
  const candidates = snapshot.wells.flatMap((well) => {
    if (well.coordinate_frame_id !== target.coordinate_frame_id ||
        well.coordinate_frame_id !== "SYN-LOCAL-FT-V1" ||
        well.location_semantics !== target.location_semantics ||
        well.location_semantics !== "SYNTHETIC_SURFACE_WELLHEAD") {
      exclusions.incompatibleCoordinates++;
      return [];
    }
    const dx = BigInt(target.surface_x_ft) - BigInt(well.surface_x_ft);
    const dy = BigInt(target.surface_y_ft) - BigInt(well.surface_y_ft);
    const distanceSquared = dx * dx + dy * dy;
    if (distanceSquared * SCALE * SCALE > radius * radius) {
      exclusions.outsideRadius++;
      return [];
    }
    const sections = snapshot.sections.filter((section) => section.well_id === well.well_id && matching(section, target, criteria))
      .sort((a, b) => a.section_id.localeCompare(b.section_id));
    if (!sections.length) {
      exclusions.noMatchingSection++;
      return [];
    }
    const metrics = summarize(sections);
    if (!metrics.acceptedRunCount) {
      exclusions.noAcceptedRuns++;
      return [];
    }
    return [{ ...well, distanceSquared: Number(distanceSquared), sections, metrics }];
  });
  candidates.sort((a, b) => a.distanceSquared - b.distanceSquared || (a.well_id < b.well_id ? -1 : a.well_id > b.well_id ? 1 : 0));
  return { candidates, exclusions };
}
export type Candidate = ReturnType<typeof findCandidates>["candidates"][number];

export function distanceLabel(candidate: Candidate) {
  return Math.sqrt(candidate.distanceSquared).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}
