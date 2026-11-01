"""Validation helpers shared by tests and release checks."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path

from .generator import (
    COORDINATE_FRAME,
    CURRENT_GENERATOR_VERSION,
    EVENT_SUBTYPES_BY_TYPE,
    EVENT_TYPES,
    HISTORICAL_REFERENCE_VERSION,
    LOCATION_SEMANTICS,
    SPATIAL_CLUSTERS,
    SOURCE_FINGERPRINT_ALGORITHM,
    SOURCE_FINGERPRINT_CANONICALIZATION,
    SOURCE_FINGERPRINT_FORMAT_VERSION,
    SOURCE_FINGERPRINT_INVENTORY_FILENAME,
    SOURCE_FINGERPRINT_INVENTORY_FORMAT_VERSION,
    _event_id,
    _surface_location,
    source_fingerprint,
    source_fingerprint_inventory,
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_release(
    release_path: Path,
    *,
    source_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    source_root = source_root or Path(__file__).resolve().parents[2]
    manifest = json.loads((release_path / "release_manifest.json").read_text(encoding="utf-8"))
    wells = read_csv(release_path / "wells.csv")
    sections = read_csv(release_path / "sections.csv")
    runs = read_csv(release_path / "drilling_runs.csv")
    run_events_path = release_path / "run_events.csv"
    run_events = read_csv(run_events_path) if run_events_path.is_file() else []
    issues = read_csv(release_path / "quality_issues.csv")
    splits = read_csv(release_path / "split_assignments.csv")
    planned_targets_path = release_path / "planned_targets.csv"
    planned_targets = read_csv(planned_targets_path) if planned_targets_path.is_file() else []

    if len(wells) != 100:
        errors.append(f"Expected exactly 100 wells; found {len(wells)}")

    for label, rows, key in [
        ("well", wells, "well_id"),
        ("section", sections, "section_id"),
        ("run", runs, "run_id"),
        ("quality issue", issues, "quality_issue_id"),
    ]:
        values = [row[key] for row in rows]
        if len(values) != len(set(values)):
            errors.append(f"Duplicate {label} business keys")

    well_ids = {row["well_id"] for row in wells}
    section_by_id = {row["section_id"]: row for row in sections}
    if any(row["well_id"] not in well_ids for row in sections):
        errors.append("Section references a missing well")
    if any(
        row["well_id"] not in well_ids
        or row["section_id"] not in section_by_id
        or section_by_id[row["section_id"]]["well_id"] != row["well_id"]
        for row in runs
    ):
        errors.append("Run references an inconsistent well or section")

    for well in wells:
        spud = datetime.fromisoformat(well["spud_date"])
        completion = datetime.fromisoformat(well["completion_date"])
        if completion < spud:
            errors.append(f"Well chronology invalid: {well['well_id']}")
        if float(well["total_footage_ft"]) <= 0 or float(well["total_duration_hours"]) <= 0:
            errors.append(f"Well aggregate range invalid: {well['well_id']}")
        if not well["well_name"].startswith("Fictional ") or not well["operator_name"].startswith(
            "Synthetic Demonstration Operator "
        ):
            errors.append(f"Well labels are not unambiguously fictional: {well['well_id']}")

    runs_by_section: dict[str, list[dict]] = defaultdict(list)
    runs_by_well: dict[str, list[dict]] = defaultdict(list)
    sections_by_well: dict[str, list[dict]] = defaultdict(list)
    for run in runs:
        runs_by_section[run["section_id"]].append(run)
        runs_by_well[run["well_id"]].append(run)
    for section in sections:
        sections_by_well[section["well_id"]].append(section)
        start = float(section["start_md_ft"])
        end = float(section["end_md_ft"])
        footage = float(section["footage_ft"])
        if start < 0 or end <= start or round(end - start, 1) != round(footage, 1):
            errors.append(f"Section depth range invalid: {section['section_id']}")
        if float(section["duration_hours"]) <= 0:
            errors.append(f"Section duration invalid: {section['section_id']}")
        if float(section["hole_size_in"]) not in {17.5, 12.25, 8.5, 6.125}:
            errors.append(f"Section unit/range invalid: {section['section_id']}")

    for run in runs:
        start = float(run["start_md_ft"])
        end = float(run["end_md_ft"])
        footage = float(run["footage_ft"])
        start_time = datetime.fromisoformat(run["start_time_utc"].replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(run["end_time_utc"].replace("Z", "+00:00"))
        codes = set(filter(None, run["quality_reason_codes"].split("|")))
        if start < 0 or end <= start or round(end - start, 1) != round(footage, 1):
            errors.append(f"Run depth range invalid: {run['run_id']}")
        if float(run["duration_hours"]) <= 0:
            if codes != {"NON_POSITIVE_DURATION"} or run["quality_status"] != "ERROR":
                errors.append(f"Uncontrolled non-positive duration: {run['run_id']}")
            if end_time != start_time:
                errors.append(f"Flagged zero duration has unequal timestamps: {run['run_id']}")
        elif end_time <= start_time:
            errors.append(f"Run chronology invalid: {run['run_id']}")
        if float(run["bit_size_in"]) != float(section_by_id[run["section_id"]]["hole_size_in"]):
            errors.append(f"Run bit size differs from canonical parent hole size: {run['run_id']}")
        if manifest.get("generator_version") == CURRENT_GENERATOR_VERSION:
            try:
                mud_weight_ppg = float(run["mud_weight_ppg"])
                mud_funnel_viscosity_sec = float(run["mud_funnel_viscosity_sec"])
            except (KeyError, ValueError):
                errors.append(f"Run mud properties are invalid: {run['run_id']}")
                mud_weight_ppg = None
                mud_funnel_viscosity_sec = None
            if mud_weight_ppg is not None and not 8.0 <= mud_weight_ppg <= 18.0:
                errors.append(f"Run mud weight out of bounds: {run['run_id']}")
            if mud_funnel_viscosity_sec is not None and not 28 <= mud_funnel_viscosity_sec <= 120:
                errors.append(f"Run mud funnel viscosity out of bounds: {run['run_id']}")

    for section_id, child_runs in runs_by_section.items():
        section = section_by_id[section_id]
        ordered_runs = sorted(child_runs, key=lambda row: int(row["run_sequence_in_section"]))
        expected_sequences = list(range(1, len(ordered_runs) + 1))
        actual_sequences = [int(row["run_sequence_in_section"]) for row in ordered_runs]
        if actual_sequences != expected_sequences:
            errors.append(f"Run sequence is not contiguous: {section_id}")
        for previous, current in zip(ordered_runs, ordered_runs[1:]):
            previous_end = datetime.fromisoformat(
                previous["end_time_utc"].replace("Z", "+00:00")
            )
            current_start = datetime.fromisoformat(
                current["start_time_utc"].replace("Z", "+00:00")
            )
            if current_start < previous_end:
                errors.append(f"Run chronology overlaps within section: {section_id}")
            if float(current["start_md_ft"]) != float(previous["end_md_ft"]):
                errors.append(f"Run depth is not contiguous within section: {section_id}")
        if int(section["run_count"]) != len(child_runs):
            errors.append(f"Section run count mismatch: {section_id}")
        if round(sum(float(row["footage_ft"]) for row in child_runs), 1) != round(
            float(section["footage_ft"]), 1
        ):
            errors.append(f"Section footage reconciliation failed: {section_id}")
        if round(sum(float(row["duration_hours"]) for row in child_runs), 2) != round(
            float(section["duration_hours"]), 2
        ):
            errors.append(f"Section duration reconciliation failed: {section_id}")

    for well in wells:
        child_runs = runs_by_well[well["well_id"]]
        child_sections = sorted(
            sections_by_well[well["well_id"]],
            key=lambda row: int(row["section_sequence"]),
        )
        expected_sequences = list(range(1, len(child_sections) + 1))
        actual_sequences = [int(row["section_sequence"]) for row in child_sections]
        if actual_sequences != expected_sequences:
            errors.append(f"Section sequence is not contiguous: {well['well_id']}")
        for previous, current in zip(child_sections, child_sections[1:]):
            if float(current["start_md_ft"]) != float(previous["end_md_ft"]):
                errors.append(f"Section depth is not contiguous: {well['well_id']}")
        if int(well["run_count"]) != len(child_runs) or int(well["section_count"]) != len(child_sections):
            errors.append(f"Well child count mismatch: {well['well_id']}")
        if round(sum(float(row["footage_ft"]) for row in child_runs), 1) != round(
            float(well["total_footage_ft"]), 1
        ):
            errors.append(f"Well footage reconciliation failed: {well['well_id']}")
        if round(sum(float(row["duration_hours"]) for row in child_runs), 2) != round(
            float(well["total_duration_hours"]), 2
        ):
            errors.append(f"Well duration reconciliation failed: {well['well_id']}")

    for filename, expected_count in manifest["row_counts"].items():
        actual_count = len(read_csv(release_path / filename))
        if actual_count != expected_count:
            errors.append(f"Manifest row count mismatch for {filename}")
    for filename, expected_hash in manifest["sha256"].items():
        if sha256(release_path / filename) != expected_hash:
            errors.append(f"SHA-256 mismatch for {filename}")

    if manifest.get("dataset_version") == HISTORICAL_REFERENCE_VERSION:
        expected_release_metadata = {
            "release_status": "pre_git_canonical",
            "source_control_status": "pre_git",
            "git_commit": None,
            "git_baseline_required_after_first_load": True,
            "post_first_load_gate": {
                "status": "blocked_pending_git_baseline",
                "required_before": [
                    "further_transformations",
                    "agent_development",
                    "ui_development",
                ],
            },
        }
        for field, expected_value in expected_release_metadata.items():
            if manifest.get(field) != expected_value:
                errors.append(f"Manifest pre-Git canonical release metadata mismatch for {field}")
    else:
        expected_release_metadata = {
            "release_status": "generated_unpublished",
            "source_control_status": "working_tree",
            "git_commit": None,
            "git_baseline_required_after_first_load": True,
        }
        for field, expected_value in expected_release_metadata.items():
            if manifest.get(field) != expected_value:
                errors.append(f"Manifest unpublished release metadata mismatch for {field}")
        if not manifest.get("generator_version"):
            errors.append("Manifest unpublished release metadata missing generator_version")

    fingerprint = manifest.get("source_fingerprint")
    if not isinstance(fingerprint, dict):
        errors.append("Manifest source fingerprint is missing")
    else:
        if fingerprint.get("algorithm") != SOURCE_FINGERPRINT_ALGORITHM:
            errors.append("Unsupported source fingerprint algorithm")
        if fingerprint.get("canonicalization") != SOURCE_FINGERPRINT_CANONICALIZATION:
            errors.append("Unsupported source fingerprint canonicalization")
        if fingerprint.get("format_version") != SOURCE_FINGERPRINT_FORMAT_VERSION:
            errors.append("Unsupported source fingerprint format version")
        if (
            manifest.get("dataset_version") != HISTORICAL_REFERENCE_VERSION
            and manifest.get("generator_version") == CURRENT_GENERATOR_VERSION
        ):
            if fingerprint != source_fingerprint(source_root):
                errors.append("Source fingerprint does not match current generator source")

    inventory_reference = manifest.get("source_fingerprint_inventory")
    inventory_path = release_path / SOURCE_FINGERPRINT_INVENTORY_FILENAME
    if inventory_reference != {
        "artifact": SOURCE_FINGERPRINT_INVENTORY_FILENAME,
        "sha256": manifest.get("sha256", {}).get(SOURCE_FINGERPRINT_INVENTORY_FILENAME),
    }:
        errors.append("Manifest source fingerprint inventory reference is invalid")
    if not inventory_path.is_file():
        errors.append("Source fingerprint inventory artifact is missing")
    else:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        if inventory.get("format_version") != SOURCE_FINGERPRINT_INVENTORY_FORMAT_VERSION:
            errors.append("Unsupported source fingerprint inventory format version")
        if inventory.get("file_hash_algorithm") != SOURCE_FINGERPRINT_ALGORITHM:
            errors.append("Unsupported source fingerprint inventory hash algorithm")
        inventory_paths = [
            entry.get("path") for entry in inventory.get("files", [])
            if isinstance(entry, dict)
        ]
        included_paths = fingerprint.get("included_paths", []) if isinstance(fingerprint, dict) else []
        if inventory_paths != sorted(included_paths):
            errors.append("Source fingerprint inventory paths do not match the manifest")
        if (
            manifest.get("dataset_version") != HISTORICAL_REFERENCE_VERSION
            and manifest.get("generator_version") == CURRENT_GENERATOR_VERSION
        ):
            if inventory != source_fingerprint_inventory(source_root):
                errors.append("Source fingerprint inventory does not match current generator source")
        if inventory.get("aggregate_source_fingerprint") != fingerprint:
            errors.append("Source fingerprint inventory aggregate does not match manifest")

    issue_counts = dict(sorted(Counter(row["reason_code"] for row in issues).items()))
    if issue_counts != manifest["intentional_issue_counts"]:
        errors.append("Intentional issue counts do not match manifest")

    if len(splits) != len(wells) or {row["well_id"] for row in splits} != well_ids:
        errors.append("Split assignments do not cover each well exactly once")

    runs_by_id = {row["run_id"]: row for row in runs}
    if manifest.get("generator_version") == CURRENT_GENERATOR_VERSION:
        if not run_events_path.is_file():
            errors.append("Run-events artifact is missing")
        event_ids = [row.get("event_id", "") for row in run_events]
        if len(event_ids) != len(set(event_ids)):
            errors.append("Duplicate run-event identities")
        event_pairs: set[tuple[str, str, str]] = set()
        for event in run_events:
            run_id = event.get("run_id", "")
            if run_id not in runs_by_id:
                errors.append(f"Run event references missing run: {event.get('event_id', '')}")
                continue
            run = runs_by_id[run_id]
            if event.get("well_id") != run["well_id"] or event.get("section_id") != run["section_id"]:
                errors.append(f"Run event parent references are inconsistent: {event.get('event_id', '')}")
            event_type = event.get("event_type", "")
            if event_type not in EVENT_TYPES:
                errors.append(f"Run event type is invalid: {event.get('event_id', '')}")
                continue
            event_subtype = event.get("event_subtype", "")
            if event_subtype not in EVENT_SUBTYPES_BY_TYPE[event_type]:
                errors.append(f"Run event subtype is invalid for type: {event.get('event_id', '')}")
            pair = (run_id, event_type, event_subtype)
            if pair in event_pairs:
                errors.append(f"Duplicate run/type/subtype event aggregate: {event.get('event_id', '')}")
            event_pairs.add(pair)
            expected_event_id = _event_id(
                manifest.get("dataset_version", ""),
                run_id,
                event_type,
                event_subtype,
            )
            if event.get("event_id") != expected_event_id:
                errors.append(f"Run event ID is not deterministic: {event.get('event_id', '')}")
            try:
                if int(event.get("event_count", "0")) < 1:
                    errors.append(f"Run event count is invalid: {event.get('event_id', '')}")
                event_duration = float(event.get("event_duration_hours", "-1"))
                run_duration = float(run["duration_hours"])
                if event_duration < 0:
                    errors.append(f"Run event duration is invalid: {event.get('event_id', '')}")
                if event_duration > run_duration:
                    errors.append(f"Run event duration exceeds parent run: {event.get('event_id', '')}")
            except ValueError:
                errors.append(f"Run event aggregate fields are invalid: {event.get('event_id', '')}")
            if event.get("is_synthetic") != "true":
                errors.append(f"Run event is not marked synthetic: {event.get('event_id', '')}")
            for field in [
                "dataset_version",
                "generator_version",
                "generation_run_id",
                "deterministic_seed",
                "generated_at_utc",
                "scenario",
            ]:
                if not event.get(field):
                    errors.append(f"Run event missing provenance field {field}: {event.get('event_id', '')}")

    for rows in [wells, sections, runs, issues, splits]:
        for row in rows:
            if row["is_synthetic"] != "true":
                errors.append("Record missing is_synthetic=true")
            for field in [
                "dataset_version",
                "generator_version",
                "generation_run_id",
                "deterministic_seed",
                "generated_at_utc",
                "scenario",
                "quality_status",
            ]:
                if not row[field]:
                    errors.append(f"Record missing provenance field {field}")

    prohibited = {"prediction", "predicted_footage", "prediction_score", "telemetry_hz"}
    for filename in ["wells.csv", "sections.csv", "drilling_runs.csv"]:
        with (release_path / filename).open(encoding="utf-8", newline="") as handle:
            headers = set(next(csv.reader(handle)))
        if headers & prohibited:
            errors.append(f"Prohibited prediction/telemetry field in {filename}")
    if run_events_path.is_file():
        with run_events_path.open(encoding="utf-8", newline="") as handle:
            event_headers = set(next(csv.reader(handle)))
        if {"event_rate", "event_rate_per_100_hours"} & event_headers:
            errors.append("Run-events artifact contains prohibited event-rate fields")

    if manifest.get("dataset_version") != HISTORICAL_REFERENCE_VERSION:
        schema = json.loads((release_path / "schema.json").read_text(encoding="utf-8"))
        schema_tables = schema.get("tables", {})
        target_headers = set(planned_targets[0]) if planned_targets else set()
        if not planned_targets_path.is_file():
            errors.append("Planned-target artifact is missing")
        if schema.get("schema_version") != manifest.get("generator_version"):
            errors.append("Schema version does not match the generator release")
        if schema.get("coordinate_reference") != COORDINATE_FRAME:
            errors.append("Schema coordinate reference does not match the local frame contract")
        if manifest.get("coordinate_reference") != COORDINATE_FRAME:
            errors.append("Manifest coordinate reference does not match the local frame contract")
        if manifest.get("proximity_caveat") != COORDINATE_FRAME["proximity_caveat"]:
            errors.append("Manifest proximity-equivalence caveat is missing or incorrect")
        if COORDINATE_FRAME["proximity_caveat"] not in schema.get(
            "interpretation_limits", []
        ):
            errors.append("Schema omits the proximity-equivalence caveat")
        if schema_tables.get("planned_targets.csv", {}).get("fields", {}).keys() != target_headers:
            errors.append("Planned-target schema fields do not match the CSV header")
        if manifest.get("generator_version") == CURRENT_GENERATOR_VERSION:
            event_headers = set(run_events[0]) if run_events else set()
            if not run_events_path.is_file():
                errors.append("Run-events artifact is missing")
            elif schema_tables.get("run_events.csv", {}).get("fields", {}).keys() != event_headers:
                errors.append("Run-event schema fields do not match the CSV header")

        cluster_by_field = {row["field_name"]: row for row in SPATIAL_CLUSTERS}
        cluster_by_pair = {
            (row["basin_name"], row["field_name"]): row for row in SPATIAL_CLUSTERS
        }

        def check_location(row: dict[str, str], identity: str, cluster: dict, label: str) -> None:
            if row.get("coordinate_frame_id") != COORDINATE_FRAME["frame_id"]:
                errors.append(f"{label} coordinate frame ID is invalid")
            if row.get("location_semantics") != LOCATION_SEMANTICS:
                errors.append(f"{label} does not identify a synthetic surface wellhead")
            try:
                x_ft = int(row["surface_x_ft"])
                y_ft = int(row["surface_y_ft"])
            except (KeyError, ValueError):
                errors.append(f"{label} coordinates are not integer feet")
                return
            bounds = COORDINATE_FRAME["bounds_ft"]
            if not (
                bounds["x_min"] <= x_ft <= bounds["x_max"]
                and bounds["y_min"] <= y_ft <= bounds["y_max"]
            ):
                errors.append(f"{label} coordinates are outside declared local bounds")
            expected_location = _surface_location(identity, cluster)
            if (x_ft, y_ft) != expected_location:
                errors.append(f"{label} coordinates are not identity-stable in its field cluster")
            if abs(x_ft - cluster["center_x_ft"]) > 2_500 or abs(
                y_ft - cluster["center_y_ft"]
            ) > 2_500:
                errors.append(f"{label} coordinates are outside the field's synthetic cluster")

        sections_by_well_id = defaultdict(list)
        runs_by_well_id = defaultdict(list)
        for section in sections:
            sections_by_well_id[section["well_id"]].append(section)
        for run in runs:
            runs_by_well_id[run["well_id"]].append(run)
        for well in wells:
            cluster = cluster_by_field.get(well["field_name"])
            if cluster is None or well["basin_name"] != cluster["basin_name"]:
                errors.append(f"Historical well has an incoherent fictional basin/field: {well['well_id']}")
                continue
            check_location(well, well["well_id"], cluster, f"Historical well {well['well_id']}")
            allowed_formations = set(cluster["formation_names"])
            for record in (
                sections_by_well_id[well["well_id"]]
                + runs_by_well_id[well["well_id"]]
            ):
                formation = record["formation_name"]
                if formation and formation not in allowed_formations:
                    errors.append(
                        f"Historical formation is outside its fictional field cluster: "
                        f"{record.get('section_id', record.get('run_id'))}"
                    )

        target_ids = [row.get("target_id", "") for row in planned_targets]
        if len(target_ids) != len(set(target_ids)):
            errors.append("Duplicate planned-target identities")
        if any(not target_id.startswith("SYN-TARGET-") for target_id in target_ids):
            errors.append("Planned-target identity does not use the SYN-TARGET namespace")
        historical_ids = well_ids | set(section_by_id) | {row["run_id"] for row in runs}
        if historical_ids.intersection(target_ids):
            errors.append("Planned-target identity overlaps historical wells, sections, or runs")

        target_policy = manifest.get("planned_target_policy")
        if target_policy != {
            "record_kind": "PLANNED_TARGET",
            "historical_summary_includes_targets": False,
            "included_in_quality_issues": False,
            "included_in_split_assignments": False,
            "contains_realized_outcomes": False,
            "planned_target_count": len(planned_targets),
        }:
            errors.append("Manifest planned-target exclusion policy is invalid")
        if manifest.get("summary", {}).get("well_count") != len(wells):
            errors.append("Historical well summary includes non-historical records")
        if manifest.get("summary", {}).get("run_count") != len(runs):
            errors.append("Historical run summary includes non-historical records")

        reference = manifest.get("reference_release", {})
        reference_path = release_path.parent / HISTORICAL_REFERENCE_VERSION
        reference_manifest_path = reference_path / "release_manifest.json"
        if (
            reference.get("dataset_version") != HISTORICAL_REFERENCE_VERSION
            or not reference_manifest_path.is_file()
            or reference.get("manifest_sha256") != sha256(reference_manifest_path)
        ):
            errors.append("Manifest reference to the historical release is invalid")
        reference_sha256 = reference.get("manifest_sha256")
        for target in planned_targets:
            target_id = target.get("target_id", "")
            if target.get("record_kind") != "PLANNED_TARGET":
                errors.append(f"Planned record kind is invalid: {target_id}")
            if target.get("dataset_version") != manifest.get("dataset_version"):
                errors.append(f"Planned target has incorrect release provenance: {target_id}")
            if target.get("generator_version") != manifest.get("generator_version"):
                errors.append(f"Planned target has incorrect generator provenance: {target_id}")
            if target.get("reference_dataset_version") != HISTORICAL_REFERENCE_VERSION:
                errors.append(f"Planned target lacks historical reference provenance: {target_id}")
            if target.get("reference_manifest_sha256") != reference_sha256:
                errors.append(f"Planned target reference manifest hash is invalid: {target_id}")
            cluster = cluster_by_pair.get((target.get("basin_name"), target.get("field_name")))
            if cluster is None:
                errors.append(f"Planned target has an incoherent fictional cluster: {target_id}")
                continue
            check_location(target, target_id, cluster, f"Planned target {target_id}")
            if target.get("expected_formation_name") not in cluster["formation_names"]:
                errors.append(f"Planned target formation is outside its field cluster: {target_id}")
            try:
                if int(target["planned_md_max_ft"]) <= int(target["planned_md_min_ft"]):
                    errors.append(f"Planned target MD interval is invalid: {target_id}")
                if float(target["planned_hole_size_in"]) not in {17.5, 12.25, 8.5, 6.125}:
                    errors.append(f"Planned target hole size is invalid: {target_id}")
            except (KeyError, ValueError):
                errors.append(f"Planned target interval or hole size is invalid: {target_id}")
            if target.get("planned_trajectory_profile") not in {
                "VERTICAL",
                "BUILD_AND_HOLD",
                "HORIZONTAL",
            }:
                errors.append(f"Planned target trajectory is invalid: {target_id}")
            for field, allowed in [
                ("planned_bit_type", {"", "PDC", "TRICONE", "HYBRID"}),
                ("planned_bha_type", {"", "ROTARY", "MOTOR", "RSS"}),
                ("planned_mud_type", {"", "WATER_BASED_SYNTHETIC", "OIL_BASED_SYNTHETIC"}),
            ]:
                if field in target and target.get(field) not in allowed:
                    errors.append(f"Planned target {field} is invalid: {target_id}")
            forbidden_target_fields = {
                "well_id",
                "section_id",
                "run_id",
                "footage_ft",
                "duration_hours",
                "start_time_utc",
                "end_time_utc",
                "spud_date",
                "completion_date",
                "split_assignment",
                "quality_status",
                "quality_reason_codes",
                "prediction",
                "predicted_footage",
            }
            if target_headers & forbidden_target_fields:
                errors.append("Planned-target artifact contains historical outcomes or classifications")
            if target.get("is_synthetic") != "true":
                errors.append(f"Planned target is not marked synthetic: {target_id}")

        if any(row["well_id"].startswith("SYN-TARGET-") for row in splits):
            errors.append("Planned target leaked into historical split assignments")
        if any(row["well_id"].startswith("SYN-TARGET-") for row in issues):
            errors.append("Planned target leaked into historical quality issues")

    return errors
