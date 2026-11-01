import { useId, useState } from "react";
import {
  DEFAULT_CRITERIA, distanceLabel, findCandidates, snapshot, validRadius,
} from "./model";
import type { Candidate, Criteria } from "./model";

const PAGE_SIZE = 25;
const number = (value: string | number | null) => value === null
  ? "Unavailable"
  : Number(value).toLocaleString("en-US", { maximumFractionDigits: 6 });

export default function OffsetPreview() {
  const [targetId, setTargetId] = useState(snapshot.targets[0]!.target_id);
  const [criteria, setCriteria] = useState<Criteria>({ ...DEFAULT_CRITERIA });
  const [selected, setSelected] = useState<string[]>([]);
  const [compared, setCompared] = useState<string[]>([]);
  const [page, setPage] = useState(0);
  const id = useId();
  const target = snapshot.targets.find((row) => row.target_id === targetId)!;
  const radiusValid = validRadius(criteria.radiusFt);
  const { candidates, exclusions } = findCandidates(target, criteria);
  const comparison = compared.map((wellId) => candidates.find((candidate) => candidate.well_id === wellId)!);
  const visible = candidates.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const pages = Math.ceil(candidates.length / PAGE_SIZE);

  function invalidate() {
    setSelected([]);
    setCompared([]);
    setPage(0);
  }
  function updateCriteria(patch: Partial<Criteria>) {
    setCriteria((current) => ({ ...current, ...patch }));
    invalidate();
  }
  function toggle(wellId: string) {
    setSelected((current) => current.includes(wellId)
      ? current.filter((value) => value !== wellId)
      : current.length < 5 ? [...current, wellId] : current);
    setCompared([]);
  }

  return (
    <main className="offset-preview">
      <aside className="offset-disclosure" aria-label="Preview limitations">
        <strong>OFFLINE SYNTHETIC PREVIEW</strong>
        <span>Dataset v1.1.0 · not connected to Fabric</span>
        <p>Fictional surface proximity is not subsurface/geologic equivalence or operational advice.
          Planned targets have no realized outcomes. No predictions or live offset chat.</p>
        <small>SYNTHETIC DATA • v1.1.0 • PREVIEW / OFFSET COMPARISON ONLY</small>
      </aside>
      <header className="offset-intro">
        <div><p className="offset-eyebrow">EXPLORATION WORKSPACE / OFFLINE PREVIEW</p>
          <h1>Offset well analysis</h1>
          <p>Explore nearby synthetic history. Choose a planned target, narrow the scope, then compare the wells you select.</p>
        </div>
        <span className="offset-version">12 planned targets<br />100 historical wells</span>
      </header>
      <ol className="offset-steps" aria-label="Analysis workflow">
        <li><b>1</b> Pick a target</li><li><b>2</b> Filter sections</li><li><b>3</b> Select up to five</li><li><b>4</b> Compare history</li>
      </ol>
      <div className="offset-grid">
        <section className="offset-card offset-controls" aria-labelledby={`${id}-scope`}>
          <h2 id={`${id}-scope`}>1–2 / Define your scope</h2>
          <label htmlFor={`${id}-target`}>Planned target</label>
          <select id={`${id}-target`} value={targetId} onChange={(event) => { setTargetId(event.target.value); invalidate(); }}>
            {snapshot.targets.map((row) => <option key={row.target_id} value={row.target_id}>{row.target_id} · {row.field_name}</option>)}
          </select>
          <div className="offset-target">
            <span className="offset-pill">PLANNED · NOT HISTORICAL</span>
            <h3>{target.expected_formation_name}</h3>
            <dl>
              <dt>Basin / field</dt><dd>{target.basin_name} / {target.field_name}</dd>
              <dt>Planned hole size</dt><dd>{target.planned_hole_size_in} in</dd>
              <dt>Planned MD interval</dt><dd>{number(target.planned_md_min_ft)}–{number(target.planned_md_max_ft)} ft</dd>
              <dt>Planned trajectory</dt><dd>{target.planned_trajectory_profile.replaceAll("_", " ")}</dd>
              <dt>Fictional surface X / Y</dt><dd>{number(target.surface_x_ft)} / {number(target.surface_y_ft)} ft</dd>
            </dl>
          </div>
          <label htmlFor={`${id}-radius`}>Surface radius (ft)</label>
          <input id={`${id}-radius`} type="number" min="0" max="3000000" step="any"
            value={criteria.radiusFt} aria-invalid={!radiusValid}
            aria-describedby={`${id}-radius-help`}
            onChange={(event) => updateCriteria({ radiusFt: event.target.value })} />
          <p id={`${id}-radius-help`} className={radiusValid ? "offset-help" : "offset-invalid"}>
            {radiusValid ? "0–3,000,000 ft; up to 6 decimal places. Eligibility uses unrounded distance." : "Enter a radius from 0 to 3,000,000 ft, with up to 6 decimal places."}
          </p>
          <fieldset>
            <legend>Apply to the same historical section</legend>
            <label className="offset-check"><input type="checkbox" checked={criteria.formationMatch}
              onChange={(event) => updateCriteria({ formationMatch: event.target.checked })} />Same canonical formation</label>
            <label className="offset-check"><input type="checkbox" checked={criteria.holeSizeMatch}
              onChange={(event) => updateCriteria({ holeSizeMatch: event.target.checked })} />Same hole size</label>
            <label className="offset-check"><input type="checkbox" checked={criteria.mdOverlap}
              onChange={(event) => updateCriteria({ mdOverlap: event.target.checked })} />Strict planned MD overlap (optional)</label>
          </fieldset>
          <p className="offset-help">All enabled criteria must match one section. Missing formation cannot satisfy a formation match.
            MD overlap excludes touching endpoints; matching sections contribute in full, without prorating.
            Basin, field and trajectory are descriptive, not hidden filters.</p>
          <button type="button" className="offset-secondary" onClick={() => updateCriteria({ ...DEFAULT_CRITERIA })}>Reset filters</button>
        </section>
        <section className="offset-card offset-candidates" aria-labelledby={`${id}-candidates`}>
          <div className="offset-section-heading">
            <div><h2 id={`${id}-candidates`}>3 / Select historical wells</h2>
              <p>Nearest first · distance then well ID · not a similarity ranking</p></div>
            <span className="offset-count">{candidates.length} eligible</span>
          </div>
          <div className="offset-selection" role="status" aria-live="polite">
            <span><strong>{selected.length} of 5 selected</strong> · {selected.length === 5 ? "Limit reached. Deselect a well to choose another." : "Select manually; nothing is selected for you."}</span>
            <button type="button" className="offset-primary" disabled={selected.length === 0 || !radiusValid}
              onClick={() => setCompared([...selected].sort())}>Compare selected ({selected.length})</button>
          </div>
          {selected.length > 0 && <div className="offset-selected-list" aria-label="Selected wells">
            {selected.map((wellId) => <button type="button" key={wellId} onClick={() => toggle(wellId)}
              aria-label={`Remove ${wellId}`}>{wellId} <span aria-hidden="true">×</span></button>)}
            <button type="button" onClick={() => { setSelected([]); setCompared([]); }}>Clear selection</button>
          </div>}
          {!radiusValid ? <div className="offset-empty"><h3>Set a valid radius to explore</h3><p>No candidates or comparisons are available until the radius is valid.</p></div>
            : !candidates.length ? <div className="offset-empty"><h3>No matching historical wells</h3>
              <p>No accepted history matches this target and filter scope. Try a larger radius or disable a section criterion explicitly. Filters are never widened automatically.</p></div>
              : <ul className="offset-candidate-list">
                {visible.map((candidate) => <li key={candidate.well_id}>
                  <label className={`offset-candidate ${selected.includes(candidate.well_id) ? "is-selected" : ""}`}>
                    <input type="checkbox" checked={selected.includes(candidate.well_id)}
                      disabled={selected.length >= 5 && !selected.includes(candidate.well_id)}
                      aria-label={`Select ${candidate.well_id}`}
                      onChange={() => toggle(candidate.well_id)} />
                    <span className="offset-candidate-body">
                      <strong>{candidate.well_name}</strong>
                      <span className="offset-well-id">{candidate.well_id} · {candidate.field_name}</span>
                      <span>{candidate.metrics.matchingSectionCount} matching sections · {candidate.metrics.acceptedRunCount} accepted runs</span>
                      <span className="offset-quality">{candidate.metrics.warningRunCount} warning runs · {candidate.metrics.warningSectionCount} warning sections · {candidate.metrics.warningIssueCount} warning issues · {candidate.metrics.quarantinedRunCount} quarantined runs</span>
                    </span>
                    <span className="offset-distance"><strong>{distanceLabel(candidate)} ft</strong><small>surface distance</small></span>
                  </label>
                </li>)}
              </ul>}
          {pages > 1 && <nav className="offset-pagination" aria-label="Candidate pages">
            <button type="button" disabled={page === 0} onClick={() => setPage((value) => value - 1)}>Previous</button>
            <span>Page {page + 1} of {pages} · {PAGE_SIZE} per page</span>
            <button type="button" disabled={page + 1 >= pages} onClick={() => setPage((value) => value + 1)}>Next</button>
          </nav>}
          {radiusValid && <details className="offset-coverage"><summary>Coverage: {candidates.length} eligible / {snapshot.wells.length} historical wells</summary>
            <p>{exclusions.outsideRadius} outside radius · {exclusions.noMatchingSection} without matching sections · {exclusions.noAcceptedRuns} with no accepted runs · {exclusions.incompatibleCoordinates} incompatible coordinates.
              Counts use the first exclusion reason in that order. Planned targets are not historical wells.</p>
          </details>}
        </section>
      </div>
      <section className="offset-card offset-comparison" aria-labelledby={`${id}-compare`}>
        <div className="offset-section-heading"><div><h2 id={`${id}-compare`}>4 / Compare accepted historical summaries</h2>
          <p>Same matching whole-section scope as selection · observed synthetic history only</p></div></div>
        {!comparison.length ? <div className="offset-empty"><h3>Your comparison starts here</h3>
          <p>Select 1–5 eligible wells, then choose Compare selected. Changing the target, filters or selection clears the previous comparison.</p></div>
          : <Comparison candidates={comparison} />}
        <div className="offset-metric-notes">
          <strong>How to read these numbers</strong>
          <p>Accepted = PASS + WARNING runs; ERROR runs are quarantined and excluded from footage, duration and ratios.
            Footage/run = sum accepted footage ÷ accepted run count. Historical summary ft/hour = sum accepted footage ÷ sum accepted duration,
            not instantaneous ROP. Ratios are calculated from sums, not averaged section rates; unavailable values are never shown as zero.
            Warning issues are distinct issue counts, not run counts. No target is included in these historical totals.</p>
        </div>
      </section>
      <section className="offset-footer" aria-label="Integration and snapshot provenance">
        <div><h2>Live offset chat is unavailable</h2>
          <p>This preview has no API, Fabric or Foundry integration and never falls back from a live request.
            Historical chat is a separate workspace; its conversations are not used here.</p></div>
        <details><summary>Inspect snapshot provenance & limitations</summary>
          <dl><dt>Source / format</dt><dd>Immutable data/releases/v1.1.0 · {snapshot.provenance.snapshotFormat}</dd>
            <dt>Release ID</dt><dd><code>{snapshot.provenance.releaseId}</code></dd>
            <dt>Release manifest SHA-256</dt><dd><code>{snapshot.provenance.manifestSha256}</code></dd>
            <dt>Recorded generator fingerprint SHA-256</dt><dd><code>{snapshot.provenance.sourceFingerprintSha256}</code></dd></dl>
          <p>{snapshot.provenance.sourceFingerprintStatus} Snapshot verification is not generator reproducibility, live integration or feature acceptance.</p>
          <p>Frame SYN-LOCAL-FT-V1 · abstract X/Y axes in ft · synthetic surface wellheads only. No geographic CRS or geologic inference.</p>
          <p>Snapshot derived offline from verified source bytes into 12 targets, 100 wells and 274 section summaries; no individual run rows.
            Generation/check: <code>python3 src/app/client/scripts/offset_snapshot.py --check</code> (repository root).</p>
          <h3>Manifest-pinned source SHA-256</h3>
          <ul>{Object.entries(snapshot.provenance.sourceFilesSha256).map(([file, hash]) => <li key={file}>{file}: <code>{hash}</code></li>)}</ul>
        </details>
      </section>
    </main>
  );
}

function Comparison({ candidates }: { candidates: Candidate[] }) {
  const metrics: [string, (candidate: Candidate) => string][] = [
    ["Surface distance (ft)", (c) => distanceLabel(c)],
    ["Matching sections", (c) => number(c.metrics.matchingSectionCount)],
    ["Accepted runs", (c) => number(c.metrics.acceptedRunCount)],
    ["Accepted footage (ft)", (c) => number(c.metrics.acceptedFootageFt)],
    ["Accepted duration (hours)", (c) => number(c.metrics.acceptedDurationHours)],
    ["Average footage/run (ft/run)", (c) => number(c.metrics.averageFootagePerRunFt)],
    ["Historical summary (ft/hour)", (c) => number(c.metrics.summaryPenetrationRateFtPerHour)],
    ["Warning runs (accepted)", (c) => number(c.metrics.warningRunCount)],
    ["Warning sections", (c) => number(c.metrics.warningSectionCount)],
    ["Warning issues", (c) => number(c.metrics.warningIssueCount)],
    ["Quarantined runs (excluded)", (c) => number(c.metrics.quarantinedRunCount)],
  ];
  return <>
    <div className="offset-table-scroll" role="region" aria-label="Selected historical well comparison" tabIndex={0}>
      <table><caption>Accepted synthetic history · dataset v1.1.0 · not connected to Fabric</caption>
        <thead><tr><th scope="col">Historical metric</th>{candidates.map((c) => <th scope="col" key={c.well_id}>{c.well_id}<small>{c.well_name}</small></th>)}</tr></thead>
        <tbody>{metrics.map(([label, render]) => <tr key={label}><th scope="row">{label}</th>
          {candidates.map((c) => <td key={c.well_id}>{render(c)}</td>)}</tr>)}</tbody>
      </table>
    </div>
    <div className="offset-section-evidence">{candidates.map((candidate) => <details key={candidate.well_id}>
      <summary>{candidate.well_id} · inspect {candidate.sections.length} matching sections</summary>
      <p>{candidate.basin_name} / {candidate.field_name}. Observed trajectories are descriptive, not planned-target outcomes.</p>
      <ul>{candidate.sections.map((section) => <li key={section.section_id}>
        <strong>{section.section_id}</strong> · {section.formation_name ?? "Unknown formation"} · {section.hole_size_in} in · MD {number(section.start_md_ft)}–{number(section.end_md_ft)} ft · observed {section.trajectory_profile.replaceAll("_", " ")}
      </li>)}</ul>
    </details>)}</div>
  </>;
}
