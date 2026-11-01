"""Build/check the dev-only summary snapshot; never regenerate release data.

Uses only stdlib and immutable CSV bytes. Run from any directory with
python3 src/app/client/scripts/offset_snapshot.py [--check].
"""

import argparse
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

CLIENT = Path(__file__).resolve().parents[1]
ROOT = CLIENT.parents[2]
RELEASE = ROOT / "data/releases/v1.1.0"
OUTPUT = CLIENT / "src/offset-preview/snapshot.json"
MANIFEST_SHA = "904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d"


def build():
    manifest_bytes = (RELEASE / "release_manifest.json").read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == MANIFEST_SHA
    manifest = json.loads(manifest_bytes)
    for filename, expected in manifest["sha256"].items():
        assert hashlib.sha256((RELEASE / filename).read_bytes()).hexdigest() == expected, filename

    def rows(name):
        with (RELEASE / f"{name}.csv").open(newline="", encoding="utf-8") as stream:
            result = list(csv.DictReader(stream))
        assert len(result) == manifest["row_counts"][f"{name}.csv"]
        assert all(r["dataset_version"] == "v1.1.0" and r["is_synthetic"] == "true" for r in result)
        return result

    def pick(row, fields):
        return {key: row[key] or None for key in fields.split()}

    targets = [pick(row, "target_id record_kind basin_name field_name expected_formation_name "
                    "planned_trajectory_profile planned_hole_size_in planned_md_min_ft planned_md_max_ft "
                    "surface_x_ft surface_y_ft coordinate_frame_id location_semantics "
                    "reference_dataset_version reference_manifest_sha256")
               for row in rows("planned_targets")]
    wells = [pick(row, "well_id well_name basin_name field_name surface_x_ft surface_y_ft "
                  "coordinate_frame_id location_semantics") for row in rows("wells")]
    sections, runs, issues = rows("sections"), rows("drilling_runs"), rows("quality_issues")
    assert len({r["run_id"] for r in runs}) == len(runs)
    assert len({r["quality_issue_id"] for r in issues}) == len(issues)
    assert len({r["section_id"] for r in sections}) == len(sections)
    assert len({r["well_id"] for r in wells}) == len(wells) == 100
    assert len({r["target_id"] for r in targets}) == len(targets) == 12
    section_index = {r["section_id"]: r for r in sections}
    for run in runs:
        assert section_index[run["section_id"]]["well_id"] == run["well_id"]
        assert run["quality_status"] in {"PASS", "WARNING", "ERROR"}
    for issue in issues:
        assert section_index[issue["section_id"]]["well_id"] == issue["well_id"]
    summaries = []
    for section in sections:
        scoped = [r for r in runs if r["section_id"] == section["section_id"]]
        accepted = [r for r in scoped if r["quality_status"] in {"PASS", "WARNING"}]
        assert all(Decimal(r["footage_ft"]) >= 0 and Decimal(r["duration_hours"]) > 0 for r in accepted)

        def total(field):
            return str(sum((Decimal(r[field]) for r in accepted), Decimal(0))) if accepted else None

        summaries.append({
            **pick(section, "section_id well_id formation_name hole_size_in start_md_ft end_md_ft trajectory_profile"),
            "acceptedRunCount": len(accepted),
            "acceptedFootageFt": total("footage_ft"),
            "acceptedDurationHours": total("duration_hours"),
            "quarantinedRunCount": len(scoped) - len(accepted),
            "warningRunCount": sum(r["quality_status"] == "WARNING" for r in accepted),
            "warningSectionCount": int(section["quality_status"] == "WARNING"),
            "warningIssueCount": sum(i["severity"] == "WARNING" and i["section_id"] == section["section_id"]
                                     for i in issues),
        })
    return {
        "provenance": {
            "datasetVersion": "v1.1.0",
            "manifestSha256": MANIFEST_SHA,
            "releaseId": f"v1.1.0:{MANIFEST_SHA}",
            "sourceFingerprintSha256": manifest["source_fingerprint"]["value"],
            "sourceFingerprintStatus": "Recorded release fingerprint only; current generator mismatch remains unresolved.",
            "sourceFilesSha256": manifest["sha256"],
            "snapshotFormat": "offline-section-summaries-v1",
        },
        "targets": targets, "wells": wells, "sections": summaries,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build(), ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    if args.check:
        assert OUTPUT.read_text(encoding="utf-8") == content, "Snapshot differs from verified release"
        print("PASS: snapshot exactly matches hash-verified immutable v1.1.0 section summaries")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(content, encoding="utf-8")
        print(f"Wrote {OUTPUT.relative_to(ROOT)}")
