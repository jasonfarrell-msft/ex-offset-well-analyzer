"""Grader-only, independent CSV/Decimal offset oracle; never a runtime source.

Run with unittest or the existing pytest runner. Only Python stdlib is imported.
The schema checker intentionally implements only this document's vocabulary,
rejecting unsupported assertions rather than claiming general JSON Schema support.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import re
import unittest
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs/contracts/offset-well-analysis-v1.schema.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
VERSION = "offset-well-analysis-v1"
PINS = {
    "v1.0.0": "f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9",
    "v1.1.0": "904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
}
RELEASE = f"v1.1.0:{PINS['v1.1.0']}"
FRAME = "SYN-LOCAL-FT-V1"
SEMANTICS = "SYNTHETIC_SURFACE_WELLHEAD"
LABEL = "SYNTHETIC DATA • v1.1.0 • DEVELOPMENT / OFFSET COMPARISON ONLY"
PROPOSED_CRITERIA = {
    "radiusFt": "10000", "formationMatch": True,
    "holeSizeMatch": True, "mdOverlap": False,
}


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def number(value):
    require(not isinstance(value, (bool, float)), "Decimal text/integer required")
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise ContractError("Invalid decimal") from None
    require(result.is_finite(), "Finite decimal required")
    return result


def canonical(value):
    result = format(number(value), "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if number(result) == 0 else result


def ratio(numerator, denominator):
    if numerator is None or denominator is None or denominator <= 0:
        return None
    with localcontext() as ctx:
        ctx.prec = 50
        return format(
            (numerator / denominator).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
            "f",
        )


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def schema_check(value, schema=None):
    """Return evaluated property names for this schema's closed-union vocabulary."""
    schema = CONTRACT if schema is None else schema
    known = {
        "$schema", "$id", "$defs", "title", "description", "examples",
        "$ref", "type", "const", "enum", "not", "oneOf", "anyOf", "allOf",
        "properties", "required", "additionalProperties", "unevaluatedProperties",
        "items", "minItems", "maxItems", "uniqueItems", "pattern",
        "minLength", "maxLength", "minimum", "maximum",
    }
    require(not set(schema) - known, "Unsupported schema vocabulary")
    evaluated = set()
    if "$ref" in schema:
        require(schema["$ref"].startswith("#/$defs/"), "Local schema reference required")
        evaluated |= schema_check(value, CONTRACT["$defs"][schema["$ref"].split("/")[-1]])
    if "type" in schema:
        valid = {
            "object": isinstance(value, dict), "array": isinstance(value, list),
            "string": isinstance(value, str), "integer": type(value) is int,
            "boolean": type(value) is bool, "null": value is None,
        }
        require(valid[schema["type"]], "Wrong JSON type")
    # JSON equality distinguishes booleans from numeric values.
    encoded = json.dumps(value, sort_keys=True)
    if "const" in schema:
        require(encoded == json.dumps(schema["const"], sort_keys=True), "Wrong constant")
    if "enum" in schema:
        require(encoded in [json.dumps(v, sort_keys=True) for v in schema["enum"]], "Wrong enum")
    if "not" in schema:
        try:
            schema_check(value, schema["not"])
        except ContractError:
            pass
        else:
            raise ContractError("Forbidden value")
    for mode in ("allOf", "oneOf", "anyOf"):
        if mode not in schema:
            continue
        successes = []
        for branch in schema[mode]:
            try:
                successes.append(schema_check(value, branch))
            except ContractError:
                if mode == "allOf":
                    raise
        require(bool(successes), f"No valid {mode} branch")
        if mode == "oneOf":
            require(len(successes) == 1, "Ambiguous union")
        evaluated.update(set().union(*successes))
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        require(set(schema.get("required", [])) <= value.keys(), "Missing required field")
        for key in value.keys() & properties.keys():
            schema_check(value[key], properties[key])
            evaluated.add(key)
        if schema.get("additionalProperties") is False:
            require(not value.keys() - properties.keys(), "Unexpected property")
        if schema.get("unevaluatedProperties") is False:
            require(not value.keys() - evaluated, "Unevaluated property")
    if isinstance(value, list):
        require(len(value) >= schema.get("minItems", 0), "Too few items")
        require(len(value) <= schema.get("maxItems", len(value)), "Too many items")
        if schema.get("uniqueItems"):
            require(len({json.dumps(v, sort_keys=True) for v in value}) == len(value), "Duplicate item")
        for item in value:
            if "items" in schema:
                schema_check(item, schema["items"])
    if isinstance(value, str):
        require(len(value) >= schema.get("minLength", 0), "String too short")
        require(len(value) <= schema.get("maxLength", len(value)), "String too long")
        if "pattern" in schema:
            require(re.search(schema["pattern"], value) is not None, "Pattern mismatch")
    if type(value) is int:
        require(value >= schema.get("minimum", value), "Below minimum")
        require(value <= schema.get("maximum", value), "Above maximum")
    return evaluated


def decode_request(text):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON member")
            result[key] = value
        return result

    require(len(text.encode("utf-8")) <= 8192, "Request byte bound")
    try:
        request = json.loads(
            text, object_pairs_hook=unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ContractError("Nonfinite JSON")),
        )
    except (json.JSONDecodeError, UnicodeError):
        raise ContractError("Malformed JSON") from None
    validate_request(request)
    return request


def validate_request(request, eligible_ids=None):
    operation = request.get("operation") if isinstance(request, dict) else None
    require(operation in {"targets", "candidates", "compare", "chat"}, "Unsupported operation")
    schema_check(request, CONTRACT["$defs"][operation + "Request"])
    if operation == "targets":
        return
    context = request["context"]
    radius = number(context["criteria"]["radiusFt"])
    require(0 <= radius <= 3000000, "Radius outside proposed bounds")
    selected = context["selectedWellIds"]
    require(selected == sorted(set(selected)), "Selection must be sorted and unique")
    if eligible_ids is not None:
        require(set(selected) <= set(eligible_ids), "Ineligible selection")
    if operation == "chat":
        require(bool(request["message"].strip()), "Blank message")


def context_hash(request):
    validate_request(request)
    normalized = copy.deepcopy(request["context"])
    normalized["criteria"]["radiusFt"] = canonical(normalized["criteria"]["radiusFt"])
    normalized.update(contractVersion=VERSION, releaseId=request["releaseId"])
    return digest(normalized)


def index_rows(rows, field, release):
    result = {}
    for row in rows:
        require(row.get("_release_id") == release, "Cross-release row")
        require(bool(row.get(field)), "Missing entity key")
        key = (release, row[field])
        require(key not in result, "Duplicate entity key")
        result[key] = row
    return result


def joined(parent_index, child, field, release):
    require(child.get("_release_id") == release, "Cross-release join")
    require((release, child.get(field)) in parent_index, "Missing release-bound parent")
    parent = parent_index[release, child[field]]
    if field == "section_id":
        require(child.get("well_id") == parent["well_id"], "Run/section well mismatch")
    return parent


def checked_md_interval(start, end):
    """Validate known MD endpoints; incomplete intervals remain unknown."""
    values = []
    for value in (start, end):
        if value in (None, ""):
            values.append(None)
            continue
        endpoint = number(value)
        require(endpoint >= 0, "Negative MD endpoint")
        values.append(endpoint)
    if None in values:
        return None
    require(values[0] < values[1], "Invalid MD interval")
    return tuple(values)


def load_archive(version):
    require(version in PINS, "Unsupported release")
    path = ROOT / "data/releases" / version
    require((path / "release_manifest.json").is_file(), f"Required immutable archive missing: {path}")
    manifest_bytes = (path / "release_manifest.json").read_bytes()
    require(hashlib.sha256(manifest_bytes).hexdigest() == PINS[version], "Manifest hash mismatch")
    manifest = json.loads(manifest_bytes)
    require(manifest["dataset_version"] == version, "Manifest release mismatch")
    for filename, expected in manifest["sha256"].items():
        require(Path(filename).name == filename, "Nonlocal archive member")
        require(hashlib.sha256((path / filename).read_bytes()).hexdigest() == expected, filename)
    source_schema = json.loads((path / "schema.json").read_text())
    release = version + ":" + PINS[version]
    tables = {}
    for filename, count in manifest["row_counts"].items():
        with (path / filename).open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = source_schema["tables"][filename]["fields"]
            require(set(reader.fieldnames) == set(fields), "Source header mismatch")
            require(len(reader.fieldnames) == len(fields), "Duplicate source header")
            rows = list(reader)
        require(len(rows) == count, "Source row count mismatch")
        for row in rows:
            require(None not in row and None not in row.values(), "Malformed source row")
            for name, spec in fields.items():
                if row[name] == "" and spec.get("nullable", False):
                    row[name] = None
            for name in (
                "dataset_version", "generator_version", "generation_run_id",
                "deterministic_seed", "generated_at_utc", "scenario",
            ):
                require(str(row[name]) == str(manifest[name]), "Source release constant mismatch")
            require(row["is_synthetic"] == "true", "Nonsynthetic source")
            row["_release_id"] = release
            if "surface_x_ft" in row:
                row["coordinate_units"] = "ft"
                for name in ("surface_x_ft", "surface_y_ft"):
                    coordinate = number(row[name])
                    require(coordinate == coordinate.to_integral_value(), "Nonintegral coordinate")
                    require(-1000000 <= coordinate <= 1000000, "Coordinate bounds")
        if "sections" in filename:
            for section in rows:
                checked_md_interval(section["start_md_ft"], section["end_md_ft"])
        tables[filename.removesuffix(".csv")] = rows
    keys = {
        "wells": "well_id", "sections": "section_id", "drilling_runs": "run_id",
        "quality_issues": "quality_issue_id", "split_assignments": "well_id",
        "planned_targets": "target_id",
    }
    indices = {name: index_rows(rows, keys[name], release) for name, rows in tables.items()}
    for section in tables["sections"]:
        joined(indices["wells"], section, "well_id", release)
    for run in tables["drilling_runs"]:
        joined(indices["wells"], run, "well_id", release)
        joined(indices["sections"], run, "section_id", release)
    for issue in tables["quality_issues"]:
        joined(indices["wells"], issue, "well_id", release)
        section = joined(indices["sections"], issue, "section_id", release)
        require(section["well_id"] == issue["well_id"], "Issue section mismatch")
        if issue["entity_type"] == "DRILLING_RUN":
            run = joined(indices["drilling_runs"], issue, "run_id", release)
            require(run["well_id"] == issue["well_id"] and run["section_id"] == issue["section_id"],
                    "Issue run mismatch")
            require(issue["entity_id"] == issue["run_id"], "Issue entity mismatch")
        else:
            require(issue["entity_type"] == "SECTION" and issue["entity_id"] == issue["section_id"],
                    "Issue entity mismatch")
    for split in tables["split_assignments"]:
        well = joined(indices["wells"], split, "well_id", release)
        require(split["split_assignment"] == well["split_assignment"], "Split mismatch")
    for target in tables.get("planned_targets", []):
        require(target["reference_dataset_version"] == "v1.0.0", "Reference release mismatch")
        require(target["reference_manifest_sha256"] == PINS["v1.0.0"], "Reference hash mismatch")
        schema_check(wire_target(target), CONTRACT["$defs"]["target"])
        require(number(target["planned_md_min_ft"]) < number(target["planned_md_max_ft"]),
                "Target MD interval")
    return tables


def wire_target(row):
    names = {
        "target_id": "targetId", "record_kind": "recordKind", "basin_name": "basinName",
        "field_name": "fieldName", "expected_formation_name": "expectedFormationName",
        "planned_trajectory_profile": "plannedTrajectoryProfile",
        "planned_hole_size_in": "plannedHoleSizeIn", "planned_md_min_ft": "plannedMdMinFt",
        "planned_md_max_ft": "plannedMdMaxFt", "coordinate_frame_id": "coordinateFrameId",
        "location_semantics": "locationSemantics", "surface_x_ft": "surfaceXFt",
        "surface_y_ft": "surfaceYFt", "reference_dataset_version": "referenceDatasetVersion",
        "reference_manifest_sha256": "referenceManifestSha256",
    }
    return {**{wire: row[source] for source, wire in names.items()},
            "coordinateUnits": "ft", "isSynthetic": row["is_synthetic"] == "true"}


def squared_distance(target, well):
    for name, expected in (
        ("coordinate_frame_id", FRAME), ("location_semantics", SEMANTICS),
        ("coordinate_units", "ft"),
    ):
        require(target.get(name) == well.get(name) == expected, "Incompatible coordinates")
    with localcontext() as ctx:
        ctx.prec = 50
        dx = number(target.get("surface_x_ft")) - number(well.get("surface_x_ft"))
        dy = number(target.get("surface_y_ft")) - number(well.get("surface_y_ft"))
        return dx * dx + dy * dy


def within_radius(target, well, radius):
    radius = number(radius)
    require(0 <= radius <= 3000000, "Radius outside proposed bounds")
    return squared_distance(target, well) <= radius * radius


def md_overlap(start, end, lower, upper):
    section_interval = checked_md_interval(start, end)
    target_interval = checked_md_interval(lower, upper)
    if section_interval is None or target_interval is None:
        return False
    start, end = section_interval
    lower, upper = target_interval
    return max(start, lower) < min(end, upper)


def known(value):
    return value not in (None, "", "UNKNOWN")


def matches_section(section, target, criteria):
    checked_md_interval(section["start_md_ft"], section["end_md_ft"])
    if criteria["formationMatch"]:
        if not known(section["formation_name"]) or not known(target["expected_formation_name"]):
            return False
        if section["formation_name"] != target["expected_formation_name"]:
            return False
    if criteria["holeSizeMatch"]:
        if not known(section["hole_size_in"]) or not known(target["planned_hole_size_in"]):
            return False
        if number(section["hole_size_in"]) != number(target["planned_hole_size_in"]):
            return False
    return not criteria["mdOverlap"] or md_overlap(
        section["start_md_ft"], section["end_md_ft"],
        target["planned_md_min_ft"], target["planned_md_max_ft"],
    )


def aggregate(sections, runs, issues):
    """Aggregate facts once, independently of target-pair or issue joins."""
    section_ids = {row["section_id"] for row in sections}
    require(len(section_ids) == len(sections), "Duplicate matching section")
    scoped = [row for row in runs if row["section_id"] in section_ids]
    require(len({r["run_id"] for r in scoped}) == len(scoped), "Duplicate run")
    require(all(r["quality_status"] in {"PASS", "WARNING", "ERROR"} for r in scoped),
            "Unsupported quality")
    accepted = [r for r in scoped if r["quality_status"] in {"PASS", "WARNING"}]
    unique_issues = {}
    for issue in issues:
        if issue["section_id"] in section_ids:
            previous = unique_issues.setdefault(issue["quality_issue_id"], issue)
            require(previous == issue, "Contradictory duplicate issue")
    reasons = []
    if not accepted:
        reasons.append("NO_ACCEPTED_RUNS")

    def sum_quantity(name):
        if not accepted:
            return None
        if any(r.get(name) in (None, "") for r in accepted):
            if "MISSING_ACCEPTED_QUANTITY" not in reasons:
                reasons.append("MISSING_ACCEPTED_QUANTITY")
            return None
        # Build section sums first so the same section cannot multiply across joins.
        sums = defaultdict(Decimal)
        for run in accepted:
            sums[run["section_id"]] += number(run[name])
        return sum(sums.values(), Decimal(0))

    footage = sum_quantity("footage_ft")
    duration = sum_quantity("duration_hours")
    require(footage is None or all(
        number(r["footage_ft"]) >= 0 for r in accepted if r.get("footage_ft") not in (None, "")
    ), "Negative accepted footage")
    invalid_duration = any(
        number(r["duration_hours"]) <= 0 for r in accepted
        if r.get("duration_hours") not in (None, "")
    )
    if invalid_duration:
        reasons.append("NON_POSITIVE_DURATION")
    return {
        "matchingSectionCount": len(sections), "acceptedRunCount": len(accepted),
        "acceptedFootageFt": None if footage is None else canonical(footage),
        "acceptedDurationHours": None if duration is None else canonical(duration),
        "averageFootagePerRunFt": ratio(footage, Decimal(len(accepted))),
        "summaryPenetrationRateFtPerHour": None if invalid_duration else ratio(footage, duration),
        "quarantinedRunCount": len(scoped) - len(accepted),
        "warningRunCount": sum(r["quality_status"] == "WARNING" for r in accepted),
        "warningSectionCount": sum(s["quality_status"] == "WARNING" for s in sections),
        "warningIssueCount": sum(i["severity"] == "WARNING" for i in unique_issues.values()),
        "scope": "MATCHING_WHOLE_SECTIONS", "unavailableReasons": sorted(reasons),
    }


class OffsetOracle:
    def __init__(self, tables):
        self.tables = tables
        self.wells = index_rows(tables["wells"], "well_id", RELEASE)
        self.sections = index_rows(tables["sections"], "section_id", RELEASE)
        self.targets = index_rows(tables["planned_targets"], "target_id", RELEASE)
        index_rows(tables["drilling_runs"], "run_id", RELEASE)
        index_rows(tables["quality_issues"], "quality_issue_id", RELEASE)
        index_rows(tables["split_assignments"], "well_id", RELEASE)
        for section in tables["sections"]:
            joined(self.wells, section, "well_id", RELEASE)
        for run in tables["drilling_runs"]:
            joined(self.wells, run, "well_id", RELEASE)
            joined(self.sections, run, "section_id", RELEASE)
        for issue in tables["quality_issues"]:
            issue_well = joined(self.wells, issue, "well_id", RELEASE)
            issue_section = joined(self.sections, issue, "section_id", RELEASE)
            require(issue_section["well_id"] == issue_well["well_id"],
                    "Issue section/well mismatch")
            if issue["entity_type"] == "DRILLING_RUN":
                issue_run = joined(index_rows(tables["drilling_runs"], "run_id", RELEASE),
                                   issue, "run_id", RELEASE)
                require(issue_run["well_id"] == issue_well["well_id"] and
                        issue_run["section_id"] == issue["section_id"] and
                        issue["entity_id"] == issue["run_id"], "Issue run mismatch")
            else:
                require(issue["entity_type"] == "SECTION" and
                        issue["entity_id"] == issue["section_id"], "Issue entity mismatch")

    def candidates(self, target_id, criteria=None):
        criteria = copy.deepcopy(PROPOSED_CRITERIA if criteria is None else criteria)
        request = copy.deepcopy(CONTRACT["examples"][1])
        request["context"].update(targetId=target_id, criteria=criteria)
        validate_request(request)
        require((RELEASE, target_id) in self.targets, "Unknown target")
        target = self.targets[RELEASE, target_id]
        rows, exclusions = [], []
        for (_, well_id), well in self.wells.items():
            reasons = []
            try:
                distance = squared_distance(target, well)
            except ContractError:
                reasons.append("INCOMPATIBLE_COORDINATES")
            else:
                if not within_radius(target, well, criteria["radiusFt"]):
                    reasons.append("OUTSIDE_RADIUS")
            sections = [
                s for s in self.sections.values()
                if s["well_id"] == well_id and matches_section(s, target, criteria)
            ]
            if not reasons and not sections:
                reasons.append("NO_MATCHING_SECTION")
                well_sections = [s for s in self.sections.values() if s["well_id"] == well_id]
                for enabled, field, reason in (
                    (criteria["formationMatch"], "formation_name", "UNKNOWN_FORMATION"),
                    (criteria["holeSizeMatch"], "hole_size_in", "UNKNOWN_HOLE_SIZE"),
                    (criteria["mdOverlap"], "start_md_ft", "UNKNOWN_MD"),
                    (criteria["mdOverlap"], "end_md_ft", "UNKNOWN_MD"),
                ):
                    if enabled and any(not known(s[field]) for s in well_sections):
                        if reason not in reasons:
                            reasons.append(reason)
            metrics = aggregate(
                sections,
                [r for r in self.tables["drilling_runs"] if r["well_id"] == well_id],
                [i for i in self.tables["quality_issues"] if i["well_id"] == well_id],
            )
            if not reasons and not metrics["acceptedRunCount"]:
                reasons.append("NO_ACCEPTED_RUNS")
            if reasons:
                exclusions.append({"wellId": well_id, "reasons": reasons})
                continue
            require(not metrics["unavailableReasons"], "Invalid accepted metrics")
            with localcontext() as ctx:
                ctx.prec = 50
                display = format(distance.sqrt().quantize(Decimal("0.1"), rounding=ROUND_HALF_UP), "f")
            rows.append({
                "wellId": well_id, "wellName": well["well_name"],
                "basinName": well["basin_name"], "fieldName": well["field_name"],
                "coordinateFrameId": FRAME, "locationSemantics": SEMANTICS, "coordinateUnits": "ft",
                "distanceSquaredFt2": canonical(distance), "distanceFt": display, "metrics": metrics,
                "matchingSections": [{
                    "sectionId": s["section_id"], "formationName": s["formation_name"],
                    "holeSizeIn": s["hole_size_in"], "startMdFt": s["start_md_ft"],
                    "endMdFt": s["end_md_ft"], "trajectoryProfile": s["trajectory_profile"],
                } for s in sorted(sections, key=lambda s: s["section_id"])],
            })
        rows.sort(key=lambda r: (number(r["distanceSquaredFt2"]), r["wellId"]))
        return rows, sorted(exclusions, key=lambda r: r["wellId"])

    def compare(self, target_id, selected, criteria=None):
        candidates, _ = self.candidates(target_id, criteria)
        request = copy.deepcopy(CONTRACT["examples"][2])
        request["context"].update(targetId=target_id, selectedWellIds=selected)
        request["context"]["criteria"] = copy.deepcopy(
            PROPOSED_CRITERIA if criteria is None else criteria
        )
        validate_request(request, [r["wellId"] for r in candidates])
        by_id = {r["wellId"]: r for r in candidates}
        return [{"wellId": well_id, "metrics": by_id[well_id]["metrics"],
                 "matchingSections": by_id[well_id]["matchingSections"]} for well_id in selected]


def legacy_view_oracle(tables):
    """Independent answers for all four existing v1.0.0 serving-view grains."""
    version = "v1.0.0"
    well0 = tables["wells"][0]
    common = {k: well0[k] for k in ("dataset_version", "generation_run_id", "scenario")}
    common.update(is_synthetic=True, _transformation_contract_version="1.0.0")
    runs = tables["drilling_runs"]
    accepted = [r for r in runs if r["quality_status"] in {"PASS", "WARNING"}]
    errors = [r for r in runs if r["quality_status"] == "ERROR"]
    wells = []
    for well in sorted(tables["wells"], key=lambda r: r["well_id"]):
        sections = [s for s in tables["sections"] if s["well_id"] == well["well_id"]]
        wruns = [r for r in runs if r["well_id"] == well["well_id"]]
        issues = [i for i in tables["quality_issues"] if i["well_id"] == well["well_id"]]
        metrics = aggregate(sections, wruns, issues)
        row = {**common, **{k: well[k] for k in (
            "generator_version", "well_id", "well_name", "operator_name", "basin_name",
            "field_name", "spud_date", "completion_date", "split_assignment",
        )}, "deterministic_seed": int(well["deterministic_seed"])}
        row.update(
            section_count=len(sections), source_run_count=len(wruns),
            accepted_run_count=metrics["acceptedRunCount"],
            quarantined_run_count=metrics["quarantinedRunCount"],
            warning_section_count=metrics["warningSectionCount"],
            warning_run_count=metrics["warningRunCount"],
            error_run_count=metrics["quarantinedRunCount"], issue_count=len(issues),
            source_total_footage_ft=canonical(sum(number(r["footage_ft"]) for r in wruns)),
            source_total_duration_hours=canonical(sum(number(r["duration_hours"]) for r in wruns)),
            accepted_footage_ft=metrics["acceptedFootageFt"],
            accepted_duration_hours=metrics["acceptedDurationHours"],
            quarantined_footage_ft=canonical(sum(
                (number(r["footage_ft"]) for r in wruns if r["quality_status"] == "ERROR"), Decimal(0))),
            quarantined_duration_hours=canonical(sum(
                (number(r["duration_hours"]) for r in wruns if r["quality_status"] == "ERROR"), Decimal(0))),
            first_run_start_time_utc=min(r["start_time_utc"] for r in wruns),
            last_run_end_time_utc=max(r["end_time_utc"] for r in wruns),
            has_quality_warning=metrics["warningRunCount"] + metrics["warningSectionCount"] > 0,
            has_quarantined_run=metrics["quarantinedRunCount"] > 0,
        )
        require(number(well["total_footage_ft"]) == number(row["source_total_footage_ft"]),
                "Legacy source reconciliation")
        wells.append(row)
    dataset = {**common, "generator_version": well0["generator_version"],
               "deterministic_seed": int(well0["deterministic_seed"]),
               "well_count": len(wells), "section_count": len(tables["sections"]),
               "source_run_count": len(runs), "accepted_run_count": len(accepted),
               "quarantined_run_count": len(errors), "rejected_record_count": 0,
               "quality_issue_count": len(tables["quality_issues"]),
               "warning_issue_count": sum(i["severity"] == "WARNING" for i in tables["quality_issues"]),
               "error_issue_count": sum(i["severity"] == "ERROR" for i in tables["quality_issues"]),
               "manifest_sha256": PINS[version]}
    for prefix, rows in (("source_total", runs), ("accepted", accepted), ("quarantined", errors)):
        for field in ("footage_ft", "duration_hours"):
            dataset[f"{prefix}_{field}"] = canonical(sum((number(r[field]) for r in rows), Decimal(0)))
    categories = []
    for category, rows, field in (
        ("FORMATION_NAME", tables["sections"], "formation_name"),
        ("BHA_TYPE", runs, "bha_type"), ("BIT_TYPE", runs, "bit_type"),
        ("SPLIT_ASSIGNMENT", tables["wells"], "split_assignment"),
        ("ENTITY_QUALITY_STATUS", tables["wells"] + tables["sections"] + runs, "quality_status"),
    ):
        counts = Counter(r[field] if r[field] is not None else "(missing)" for r in rows)
        categories.extend({**common, "category_name": category, "category_value": value,
                           "record_count": count} for value, count in sorted(counts.items()))
    groups = defaultdict(list)
    for issue in tables["quality_issues"]:
        groups[issue["reason_code"], issue["severity"]].append(issue)
    quality = []
    for (reason, severity), issues in sorted(groups.items()):
        handling = {i["handling"] for i in issues}
        require(len(handling) == 1, "Ambiguous issue handling")
        quality.append({
            **common, "reason_code": reason, "severity": severity, "issue_count": len(issues),
            **{f"affected_{entity}_count": len({i[f"{entity}_id"] for i in issues if i[f"{entity}_id"]})
               for entity in ("well", "section", "run")},
            "handling_text": next(iter(handling)),
        })
    return {"serving.well_summary": wells, "serving.dataset_summary": [dataset],
            "serving.quality_summary": quality, "serving.category_summary": categories}


def fixture_section(section_id="s1", formation="A", hole="8.5", start="0", end="100"):
    return {
        "section_id": section_id, "well_id": "w1", "formation_name": formation,
        "formation_name_raw": formation, "hole_size_in": hole,
        "start_md_ft": start, "end_md_ft": end, "quality_status": "PASS",
    }


def fixture_run(run_id="r1", section_id="s1", footage="100", duration="10", status="PASS"):
    return {
        "run_id": run_id, "section_id": section_id, "well_id": "w1",
        "footage_ft": footage, "duration_hours": duration, "quality_status": status,
    }


def fixture_point(x="0", y="0"):
    return {
        "coordinate_frame_id": FRAME, "location_semantics": SEMANTICS,
        "coordinate_units": "ft", "surface_x_ft": x, "surface_y_ft": y,
    }


def response_envelope(operation, request=None):
    return {
        "operation": operation, "status": "success", "contractVersion": VERSION,
        "queryContractVersion": VERSION, "transformationContractVersion": "1.1.0",
        "datasetVersion": "v1.1.0", "releaseId": RELEASE, "manifestSha256": PINS["v1.1.0"],
        "context": None if request is None else copy.deepcopy(request["context"]),
        "contextHash": None if request is None else context_hash(request),
        "evidence": copy.deepcopy(CONTRACT["$defs"]["evidence"]["examples"][0]),
    }


def fixture_association(response):
    """Test-only stand-in for a future server-owned authenticated association."""
    evidence = response["evidence"]
    return {
        "operation": response["operation"], "contextHash": response["contextHash"],
        **{key: evidence[key] for key in ("receiptId", "requestId", "toolCallId", "resultId")},
    }


def grade_response(response, request, expected_rows, expected_exclusions, association):
    """Offline evidence grading, NOT live authentication or runtime fallback."""
    schema_check(response)
    require(response["status"] in {"success", "empty"}, "No analytical evidence on failures")
    require(response["operation"] == request["operation"], "Operation mismatch")
    require(association == fixture_association(response), "Unbound result/correlation")
    expected_context = request.get("context")
    require(response["context"] == expected_context, "Context mismatch")
    require(response["contextHash"] == (
        context_hash(request) if expected_context is not None else None
    ), "Context hash mismatch")
    evidence = response["evidence"]
    for source in evidence["sources"]:
        require(bool(source["columns"] or source["measures"]), "Empty source reference")
    if request["operation"] == "chat":
        for claim in response["claims"]:
            require(claim["receiptId"] == evidence["receiptId"], "Forged claim receipt")
            require(claim["sourceIndex"] < len(evidence["sources"]), "Unresolvable source")
            require(set(claim["wellIds"]) <= set(expected_context["selectedWellIds"]),
                    "Unselected claim well")
        # Claim text numerical fidelity still requires real result-value binding.
        return
    require(response["rows"] == expected_rows, "Incomplete/incorrect/unordered result")
    require(response["exclusions"] == expected_exclusions, "Incomplete exclusion coverage")
    require(response["totalCount"] == len(expected_rows), "Untrusted count assertion")
    key = "targetId" if request["operation"] == "targets" else "wellId"
    ids = [row[key] for row in response["rows"]]
    require(len(ids) == len(set(ids)), "Duplicate entity IDs")
    if request["operation"] == "compare":
        require(ids == expected_context["selectedWellIds"], "Partial selected comparison")
    for row in response["rows"]:
        if "matchingSections" not in row:
            continue
        section_ids = [s["sectionId"] for s in row["matchingSections"]]
        require(section_ids == sorted(set(section_ids)), "Duplicate/unordered sections")
        require(len(section_ids) == row["metrics"]["matchingSectionCount"], "Section count mismatch")
        require(not row["metrics"]["unavailableReasons"], "Invalid successful metrics")


class OffsetAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = load_archive("v1.1.0")
        cls.legacy = load_archive("v1.0.0")
        cls.oracle = OffsetOracle(cls.archive)

    def test_release_hash_inventory_and_planning_separation(self):
        self.assertEqual([len(self.archive[k]) for k in (
            "wells", "sections", "drilling_runs", "quality_issues", "split_assignments",
            "planned_targets")], [100, 274, 937, 20, 100, 12])
        target_ids = {r["target_id"] for r in self.archive["planned_targets"]}
        self.assertEqual(len(target_ids), 12)
        for name in ("wells", "sections", "drilling_runs", "quality_issues", "split_assignments"):
            self.assertFalse(target_ids & {r["well_id"] for r in self.archive[name]})
        self.assertNotIn("planned_targets", self.legacy)
        schema = json.loads((ROOT / "data/releases/v1.1.0/schema.json").read_text())
        expected_target_fields = {
            "target_id", "record_kind", "basin_name", "field_name", "expected_formation_name",
            "planned_trajectory_profile", "planned_hole_size_in", "planned_md_min_ft",
            "planned_md_max_ft", "coordinate_frame_id", "location_semantics", "surface_x_ft",
            "surface_y_ft", "reference_dataset_version", "reference_manifest_sha256", "is_synthetic",
            "dataset_version", "generator_version", "generation_run_id", "deterministic_seed",
            "generated_at_utc", "scenario",
        }
        self.assertEqual(set(schema["tables"]["planned_targets.csv"]["fields"]), expected_target_fields)
        old_fields = json.loads((ROOT / "data/releases/v1.0.0/schema.json").read_text())
        location_fields = {
            "coordinate_frame_id": ("string", None),
            "location_semantics": ("enum", None),
            "surface_x_ft": ("integer", "ft"),
            "surface_y_ft": ("integer", "ft"),
        }
        well_fields = schema["tables"]["wells.csv"]["fields"]
        for field, (field_type, unit) in location_fields.items():
            with self.subTest(field=field):
                self.assertEqual(well_fields[field]["type"], field_type)
                self.assertEqual(well_fields[field].get("unit"), unit)
                self.assertFalse(well_fields[field].get("nullable", False))
        target_source_fields = schema["tables"]["planned_targets.csv"]["fields"]
        self.assertEqual(target_source_fields["planned_hole_size_in"]["type"], "decimal")
        self.assertEqual(target_source_fields["planned_md_min_ft"]["type"], "integer")
        self.assertEqual(target_source_fields["planned_md_max_ft"]["type"], "integer")
        self.assertEqual(target_source_fields["surface_x_ft"]["type"], "integer")
        self.assertEqual(target_source_fields["surface_y_ft"]["type"], "integer")
        self.assertFalse(any(field.get("nullable", False) for field in target_source_fields.values()))
        self.assertEqual(
            set(schema["tables"]["wells.csv"]["fields"]) - set(old_fields["tables"]["wells.csv"]["fields"]),
            {"coordinate_frame_id", "location_semantics", "surface_x_ft", "surface_y_ft"},
        )
        with self.assertRaises(ContractError):
            load_archive("v9.0.0")

    def test_release_safe_keys_duplicates_and_wrong_well(self):
        index = index_rows(self.archive["sections"], "section_id", RELEASE)
        run = copy.deepcopy(self.archive["drilling_runs"][0])
        with self.assertRaises(ContractError):
            joined(index, {**run, "_release_id": "v1.0.0:" + PINS["v1.0.0"]}, "section_id", RELEASE)
        with self.assertRaises(ContractError):
            joined(index, {**run, "well_id": "SYN-WELL-0100"}, "section_id", RELEASE)
        with self.assertRaises(ContractError):
            joined(index, {**run, "section_id": "missing"}, "section_id", RELEASE)
        for name, key in (("wells", "well_id"), ("sections", "section_id"),
                          ("drilling_runs", "run_id"), ("planned_targets", "target_id"),
                          ("quality_issues", "quality_issue_id"), ("split_assignments", "well_id")):
            with self.subTest(entity=name), self.assertRaises(ContractError):
                index_rows(self.archive[name] + [self.archive[name][0]], key, RELEASE)
        old = self.legacy["wells"][0]
        new = self.archive["wells"][0]
        self.assertEqual(old["well_id"], new["well_id"])
        with self.assertRaises(ContractError):
            index_rows([old, new], "well_id", RELEASE)
        corrupted = copy.deepcopy(self.archive)
        corrupted["quality_issues"][0]["_release_id"] = old["_release_id"]
        with self.assertRaises(ContractError):
            OffsetOracle(corrupted)

    def test_distance_exact_boundary_rounding_zero_and_invalid_coordinates(self):
        origin, pythagorean = fixture_point(), fixture_point("3", "4")
        self.assertEqual(squared_distance(origin, pythagorean), Decimal(25))
        for radius, expected in (("5", True), ("4.999", False), ("5.001", True),
                                 ("0", False)):
            self.assertEqual(within_radius(origin, pythagorean, radius), expected)
        self.assertTrue(within_radius(origin, origin, "0"))
        self.assertTrue(within_radius(origin, fixture_point("-3", "-4"), "5"))
        farthest = squared_distance(fixture_point("-1000000", "-1000000"),
                                    fixture_point("1000000", "1000000"))
        self.assertEqual(farthest, Decimal("8000000000000"))
        # Rounded display is 5.0, but this point is outside the exact radius.
        self.assertFalse(within_radius(origin, fixture_point("5.00001", "0"), "5"))
        for field, value in (
            ("coordinate_frame_id", "EPSG:4326"), ("location_semantics", "SUBSURFACE"),
            ("coordinate_units", "m"), ("surface_x_ft", None), ("surface_y_ft", "NaN"),
            ("surface_x_ft", "Infinity"), ("surface_y_ft", "-Infinity"),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(ContractError):
                squared_distance(origin, {**pythagorean, field: value})
        for radius in ("-1", "3000000.000001", "NaN", "Infinity"):
            with self.assertRaises(ContractError):
                within_radius(origin, origin, radius)

    def test_same_section_formation_and_hole_conjunction_and_unknowns(self):
        target = {"expected_formation_name": "A", "planned_hole_size_in": "8.5",
                  "planned_md_min_ft": "25", "planned_md_max_ft": "75"}
        sections = [fixture_section("s1", "A", "12.25"), fixture_section("s2", "B", "8.5")]
        self.assertFalse(any(matches_section(s, target, PROPOSED_CRITERIA) for s in sections))
        self.assertTrue(matches_section(fixture_section(hole="8.500"), target, PROPOSED_CRITERIA))
        for unknown in (None, "", "UNKNOWN"):
            self.assertFalse(matches_section(fixture_section(formation=unknown), target, PROPOSED_CRITERIA))
        self.assertTrue(matches_section(
            fixture_section(formation=None), target, {**PROPOSED_CRITERIA, "formationMatch": False}))
        self.assertFalse(matches_section(
            fixture_section(hole="6.12"), {**target, "planned_hole_size_in": "6.125"}, PROPOSED_CRITERIA))
        aliases = [s for s in self.archive["sections"]
                   if s["formation_name"] != s["formation_name_raw"]]
        self.assertEqual(len(aliases), 5)
        for section in aliases:
            target.update(expected_formation_name=section["formation_name"],
                          planned_hole_size_in=section["hole_size_in"])
            self.assertTrue(matches_section(section, target, PROPOSED_CRITERIA))
            self.assertNotEqual(section["formation_name"], section["formation_name_raw"])

    def test_md_strict_overlap_and_whole_section_scope(self):
        for args, expected in (
            (("0", "10", "10", "20"), False), (("20", "30", "10", "20"), False),
            (("0", "10.001", "10", "20"), True), (("10", "20", "10", "20"), True),
            (("11", "19", "10", "20"), True), ((None, "20", "10", "20"), False),
        ):
            self.assertEqual(md_overlap(*args), expected)
        for args in (("10", "10", "0", "20"), ("20", "10", "0", "20"),
                     ("0", "10", "20", "10"), ("NaN", "10", "0", "20")):
            with self.assertRaises(ContractError):
                md_overlap(*args)
        malformed_without_md_filter = fixture_section(start="20", end="10")
        with self.assertRaises(ContractError):
            matches_section(malformed_without_md_filter, {
                "expected_formation_name": "A", "planned_hole_size_in": "8.5",
                "planned_md_min_ft": "0", "planned_md_max_ft": "100",
            }, PROPOSED_CRITERIA)
        section = fixture_section()
        target = {"expected_formation_name": "A", "planned_hole_size_in": "8.5",
                  "planned_md_min_ft": "100", "planned_md_max_ft": "200"}
        self.assertTrue(matches_section(section, target, PROPOSED_CRITERIA))
        self.assertFalse(matches_section(section, target, {**PROPOSED_CRITERIA, "mdOverlap": True}))
        target.update(planned_md_min_ft="99")
        self.assertTrue(matches_section(section, target, {**PROPOSED_CRITERIA, "mdOverlap": True}))
        self.assertEqual(aggregate([section], [fixture_run()], [])["acceptedFootageFt"], "100")

    def test_quality_counts_source_vs_accepted_and_no_fanout(self):
        metrics = aggregate(self.archive["sections"], self.archive["drilling_runs"],
                            self.archive["quality_issues"])
        self.assertEqual(Counter(r["quality_status"] for r in self.archive["drilling_runs"]),
                         {"PASS": 912, "WARNING": 20, "ERROR": 5})
        self.assertEqual(metrics, {
            "matchingSectionCount": 274, "acceptedRunCount": 932,
            "acceptedFootageFt": "909010.2", "acceptedDurationHours": "22358.76",
            "averageFootagePerRunFt": "975.332833",
            "summaryPenetrationRateFtPerHour": "40.655662",
            "quarantinedRunCount": 5, "warningRunCount": 20,
            "warningSectionCount": 10, "warningIssueCount": 15,
            "scope": "MATCHING_WHOLE_SECTIONS", "unavailableReasons": [],
        })
        runs = [fixture_run("r1", "s1", "100", "1", "WARNING"),
                fixture_run("r2", "s2", "300", "9"),
                fixture_run("r3", "s2", "99", "0", "ERROR")]
        sections = [fixture_section("s1"), fixture_section("s2")]
        issues = [{"quality_issue_id": "i1", "section_id": "s1", "severity": "WARNING"},
                  {"quality_issue_id": "i2", "section_id": "s1", "severity": "WARNING"}]
        expected = aggregate(sections, runs, issues)
        self.assertEqual(expected["summaryPenetrationRateFtPerHour"], "40.000000")
        self.assertEqual(expected["averageFootagePerRunFt"], "200.000000")
        self.assertEqual(expected["warningIssueCount"], 2)
        self.assertEqual(expected["quarantinedRunCount"], 1)
        self.assertEqual(aggregate(sections, runs, issues + issues), expected)
        self.assertEqual(aggregate(sections, runs, []), {**expected, "warningIssueCount": 0})
        with self.assertRaises(ContractError):
            aggregate(sections + [sections[0]], runs, issues)
        with self.assertRaises(ContractError):
            aggregate(sections, runs + [runs[0]], issues)
        with self.assertRaises(ContractError):
            aggregate(sections, runs, issues + [{**issues[0], "severity": "ERROR"}])

    def test_null_zero_and_nonpositive_denominators(self):
        section = fixture_section()
        empty = aggregate([section], [], [])
        quarantined = aggregate([section], [fixture_run(status="ERROR", duration="0")], [])
        for metrics in (empty, quarantined):
            self.assertEqual(metrics["acceptedRunCount"], 0)
            for field in ("acceptedFootageFt", "acceptedDurationHours", "averageFootagePerRunFt",
                          "summaryPenetrationRateFtPerHour"):
                self.assertIsNone(metrics[field])
            self.assertEqual(metrics["unavailableReasons"], ["NO_ACCEPTED_RUNS"])
        zero = aggregate([section], [fixture_run(footage="0")], [])
        self.assertEqual(zero["acceptedFootageFt"], "0")
        self.assertEqual(zero["averageFootagePerRunFt"], "0.000000")
        self.assertEqual(zero["summaryPenetrationRateFtPerHour"], "0.000000")
        for duration in ("0", "-1"):
            metrics = aggregate([section], [fixture_run(duration=duration)], [])
            self.assertIsNone(metrics["summaryPenetrationRateFtPerHour"])
            self.assertIn("NON_POSITIVE_DURATION", metrics["unavailableReasons"])
        mixed = aggregate([section], [fixture_run("r1", duration="0"), fixture_run("r2", duration="10")], [])
        self.assertIsNone(mixed["summaryPenetrationRateFtPerHour"])
        for footage, duration in ((None, "10"), ("100", None)):
            metrics = aggregate([section], [fixture_run(footage=footage, duration=duration)], [])
            self.assertIsNone(metrics["summaryPenetrationRateFtPerHour"])
            self.assertIn("MISSING_ACCEPTED_QUANTITY", metrics["unavailableReasons"])
        with self.assertRaises(ContractError):
            aggregate([section], [fixture_run(footage="-1")], [])

    def test_all_targets_complete_sets_metrics_and_deterministic_digest(self):
        actual = {}
        md_counts = []
        for target in self.archive["planned_targets"]:
            target_id = target["target_id"]
            rows, exclusions = self.oracle.candidates(target_id)
            actual[target_id] = {"rows": rows, "exclusions": exclusions}
            self.assertEqual(len(rows) + len(exclusions), 100)
            self.assertEqual(len({r["wellId"] for r in rows + exclusions}), 100)
            self.assertEqual(rows, sorted(rows, key=lambda r: (number(r["distanceSquaredFt2"]), r["wellId"])))
            for row in rows:
                schema_check(row, CONTRACT["$defs"]["candidate"])
            if rows:
                selected = sorted(r["wellId"] for r in rows[:5])
                compared = self.oracle.compare(target_id, selected)
                self.assertEqual(compared, [
                    {"wellId": well_id,
                     **{field: next(r[field] for r in rows if r["wellId"] == well_id)
                        for field in ("metrics", "matchingSections")}}
                    for well_id in selected
                ])
            for criteria in (
                {**PROPOSED_CRITERIA, "mdOverlap": True},
                {**PROPOSED_CRITERIA, "radiusFt": "3000000", "formationMatch": False,
                 "holeSizeMatch": False},
            ):
                other, excluded = self.oracle.candidates(target_id, criteria)
                self.assertEqual(len(other) + len(excluded), 100)
                if criteria["mdOverlap"]:
                    md_counts.append(len(other))
                else:
                    self.assertEqual(len(other), 100)
                    self.assertEqual(sum(r["metrics"]["acceptedRunCount"] for r in other), 932)
                    self.assertEqual(sum(number(r["metrics"]["acceptedFootageFt"]) for r in other),
                                     Decimal("909010.2"))
        # Golden sets are grader-only and never supplied to an analytical model.
        self.assertEqual([len(v["rows"]) for v in actual.values()], EXPECTED_COUNTS)
        self.assertEqual([[r["wellId"] for r in v["rows"]] for v in actual.values()], EXPECTED_IDS)
        self.assertEqual(md_counts, [0, 4, 0, 1, 0, 2, 1, 5, 3, 1, 2, 0])
        self.assertEqual(digest(actual), EXPECTED_OFFSET_DIGEST)
        reversed_tables = {k: list(reversed(v)) for k, v in self.archive.items()}
        reversed_oracle = OffsetOracle(reversed_tables)
        self.assertEqual(actual, {
            target_id: dict(zip(("rows", "exclusions"), reversed_oracle.candidates(target_id)))
            for target_id in actual
        })

    def test_proximity_tie_break_and_two_targets_do_not_multiply_facts(self):
        tables = copy.deepcopy(self.archive)
        target = tables["planned_targets"][0]
        for well in tables["wells"]:
            well.update(surface_x_ft=target["surface_x_ft"], surface_y_ft=target["surface_y_ft"])
        oracle = OffsetOracle(tables)
        criteria = {**PROPOSED_CRITERIA, "formationMatch": False, "holeSizeMatch": False, "radiusFt": "0"}
        rows, excluded = oracle.candidates(target["target_id"], criteria)
        self.assertFalse(excluded)
        self.assertEqual([r["wellId"] for r in rows], sorted(r["wellId"] for r in rows))
        self.assertEqual(sum(r["metrics"]["acceptedRunCount"] for r in rows), 932)
        original = self.oracle.candidates("SYN-TARGET-0001")
        self.oracle.candidates("SYN-TARGET-0002")
        self.assertEqual(self.oracle.candidates("SYN-TARGET-0001"), original)
        # All-quarantined well is excluded, even if section predicates match.
        for run in tables["drilling_runs"]:
            if run["well_id"] == rows[0]["wellId"]:
                run["quality_status"] = "ERROR"
        remaining, excluded = OffsetOracle(tables).candidates(target["target_id"], criteria)
        self.assertEqual(len(remaining), 99)
        self.assertEqual(excluded, [{"wellId": rows[0]["wellId"], "reasons": ["NO_ACCEPTED_RUNS"]}])

    def test_legacy_four_views_oracle_and_fixed_digest(self):
        views = legacy_view_oracle(self.legacy)
        self.assertEqual([len(views[k]) for k in views], [100, 1, 4, 19])
        summary = views["serving.dataset_summary"][0]
        self.assertEqual(summary["source_total_footage_ft"], "914297.6")
        self.assertEqual(summary["accepted_footage_ft"], "909010.2")
        self.assertEqual(summary["quarantined_footage_ft"], "5287.4")
        self.assertEqual(summary["source_total_duration_hours"], "22358.76")
        self.assertEqual(summary["quarantined_duration_hours"], "0")
        for field in ("source_run_count", "accepted_run_count", "quarantined_run_count"):
            self.assertEqual(sum(r[field] for r in views["serving.well_summary"]), summary[field])
        self.assertEqual(digest(views), EXPECTED_LEGACY_DIGEST)

    def test_request_examples_and_defensive_negative_cases(self):
        for example in CONTRACT["examples"]:
            self.assertEqual(decode_request(json.dumps(example)), example)
        base = copy.deepcopy(CONTRACT["examples"][2])
        invalid = []
        for radius in ("-1", "3000001", "3000000.000001", "NaN", "Infinity", "1e4",
                       " 10000", "10000\n", 10000, None, "0.0000001", "01", "-0"):
            value = copy.deepcopy(base)
            value["context"]["criteria"]["radiusFt"] = radius
            invalid.append(value)
        for selected in ([], ["SYN-WELL-0001"] * 2, ["SYN-WELL-0100", "SYN-WELL-0001"],
                         ["SYN-WELL-0000"], ["SYN-WELL-0101"],
                         ["SYN-WELL-0019\n"],
                         [f"SYN-WELL-{i:04d}" for i in range(1, 7)]):
            value = copy.deepcopy(base)
            value["context"]["selectedWellIds"] = selected
            invalid.append(value)
        invalid.extend([
            {**base, "operation": "predict"}, {**base, "releaseId": "v1.0.0"},
            {**base, "contractVersion": "offset-well-analysis-v2"},
            {**base, "sql": "SELECT 1"}, {**base, "endpointUrl": "https://invalid.example"},
            {**base, "metrics": {}}, {**base, "contextHash": "a" * 64},
            {**base, "context": {**base["context"], "targetId": "SYN-TARGET-0013"}},
            {**base, "context": {**base["context"], "contextRevision": True}},
        ])
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ContractError):
                decode_request(json.dumps(value))
        chat = copy.deepcopy(CONTRACT["examples"][3])
        for message in ("", " ", "a" * 2001):
            with self.assertRaises(ContractError):
                validate_request({**chat, "message": message})
        for raw in ('{"operation":"targets","operation":"compare"}', "{", '{"n":NaN}'):
            with self.assertRaises(ContractError):
                decode_request(raw)
        with self.assertRaises(ContractError):
            decode_request(" " * 8193)
        with self.assertRaises(ContractError):
            decode_request(json.dumps({**chat, "message": "🛢" * 2000}, ensure_ascii=False))
        with self.assertRaises(ContractError):
            validate_request(base, [])

    def test_context_hash_normalization_and_every_mutation_invalidates(self):
        request = copy.deepcopy(CONTRACT["examples"][2])
        hashed = context_hash(request)
        normalized = copy.deepcopy(request)
        normalized["context"]["criteria"]["radiusFt"] = "10000.000000"
        self.assertEqual(context_hash(normalized), hashed)
        for key, value in (
            ("targetId", "SYN-TARGET-0002"), ("contextRevision", 2),
            ("selectedWellIds", ["SYN-WELL-0001"]),
        ):
            changed = copy.deepcopy(request)
            changed["context"][key] = value
            self.assertNotEqual(context_hash(changed), hashed)
        for key, value in (("radiusFt", "9999"), ("formationMatch", False),
                           ("holeSizeMatch", False), ("mdOverlap", True)):
            changed = copy.deepcopy(request)
            changed["context"]["criteria"][key] = value
            self.assertNotEqual(context_hash(changed), hashed)
        changed = copy.deepcopy(request)
        changed["releaseId"] = "v1.0.0"
        with self.assertRaises(ContractError):
            context_hash(changed)

    def test_target_outcome_fields_and_unknown_null_constraints(self):
        target = copy.deepcopy(CONTRACT["$defs"]["target"]["examples"][0])
        for field in ("footageFt", "durationHours", "acceptedRunCount", "qualityStatus",
                      "splitAssignment", "predictedFootageFt", "actualTrajectory"):
            with self.assertRaises(ContractError):
                schema_check({**target, field: 0}, CONTRACT["$defs"]["target"])
        for field in target:
            with self.subTest(field=field), self.assertRaises(ContractError):
                schema_check({**target, field: None}, CONTRACT["$defs"]["target"])
        for coordinate in ("1000001", "-1000001", "-0", "0\n"):
            with self.assertRaises(ContractError):
                schema_check({**target, "surfaceXFt": coordinate}, CONTRACT["$defs"]["target"])
        section = copy.deepcopy(CONTRACT["$defs"]["matchingSection"]["examples"][0])
        schema_check(section, CONTRACT["$defs"]["matchingSection"])
        schema_check({**section, "trajectoryProfile": None}, CONTRACT["$defs"]["matchingSection"])
        with self.assertRaises(ContractError):
            schema_check({**section, "formationName": "UNKNOWN"}, CONTRACT["$defs"]["matchingSection"])

    def test_full_request_response_fixtures_bind_each_operation(self):
        for name in ("target", "context", "candidate", "comparison", "chatResponse"):
            definition = CONTRACT["$defs"][name]
            for example in definition.get("examples", []):
                with self.subTest(schema_example=name):
                    schema_check(example, definition)
                    with self.assertRaises(ContractError):
                        schema_check({**example, "unmodeledProperty": True}, definition)
        targets = response_envelope("targets")
        targets.update(rows=[wire_target(t) for t in self.archive["planned_targets"]],
                       totalCount=12, truncated=False, exclusions=[])
        targets["evidence"]["grain"] = "RELEASE_TARGET"
        targets["evidence"]["sources"] = [{
            "view": "serving.planned_target_summary",
            "columns": ["_release_id", "target_id", "record_kind"], "measures": [],
        }]
        candidate_request = copy.deepcopy(CONTRACT["examples"][1])
        rows, exclusions = self.oracle.candidates(candidate_request["context"]["targetId"])
        candidates = response_envelope("candidates", candidate_request)
        candidates.update(rows=rows, totalCount=len(rows), truncated=False, exclusions=exclusions)
        compare_request = copy.deepcopy(CONTRACT["examples"][2])
        compare_request["context"]["selectedWellIds"] = sorted(r["wellId"] for r in rows[:5])
        compare = response_envelope("compare", compare_request)
        compare.update(rows=self.oracle.compare(
            compare_request["context"]["targetId"], compare_request["context"]["selectedWellIds"]),
            totalCount=len(compare_request["context"]["selectedWellIds"]), truncated=False, exclusions=[])
        empty_request = copy.deepcopy(candidate_request)
        empty_request["context"]["criteria"]["radiusFt"] = "0"
        empty_rows, empty_excluded = self.oracle.candidates(
            empty_request["context"]["targetId"], empty_request["context"]["criteria"])
        self.assertEqual(empty_rows, [])
        empty = response_envelope("candidates", empty_request)
        empty.update(status="empty", rows=[], totalCount=0, truncated=False, exclusions=empty_excluded)
        chat = response_envelope("chat", compare_request)
        chat.update(message=LABEL + "\nThe selection contains accepted historical runs, not target outcomes.",
                    conversationId="fixture_conversation_001",
                    claims=[{"claimId": "fixture_claim_0001", "text": "Accepted historical runs.",
                             "receiptId": chat["evidence"]["receiptId"], "sourceIndex": 0,
                             "wellIds": compare_request["context"]["selectedWellIds"]}])
        for response in (targets, candidates, compare, empty, chat):
            schema_check(response)
        grade_response(targets, CONTRACT["examples"][0], targets["rows"], [],
                       fixture_association(targets))
        grade_response(candidates, candidate_request, rows, exclusions, fixture_association(candidates))
        grade_response(compare, compare_request, compare["rows"], [], fixture_association(compare))
        grade_response(empty, empty_request, [], empty_excluded, fixture_association(empty))
        chat_request = {**compare_request, "operation": "chat", "message": "Explain the selection."}
        grade_response(chat, chat_request, [], [], fixture_association(chat))
        for status in ("unavailable", "stale", "error"):
            failure = response_envelope("chat", compare_request)
            failure.update(status=status, evidence=None, contextHash=None,
                           error={"code": "CAPABILITY_UNPROVEN", "retryable": False})
            schema_check(failure)
        malformed = copy.deepcopy(failure)
        malformed.update(operation=None, context=None, error={"code": "INVALID_REQUEST", "retryable": False})
        schema_check(malformed)
        with self.assertRaises(ContractError):
            schema_check({**malformed, "context": CONTRACT["examples"][2]["context"]})
        for bad in (
            {**compare, "rows": []}, {**compare, "truncated": True},
            {**compare, "evidence": None}, {**compare, "manifestSha256": "0" * 64},
            {**compare, "unexpected": True}, {**chat, "message": "No disclosure"},
            {**compare, "evidence": {**compare["evidence"], "units": {}}},
            {**compare, "evidence": {**compare["evidence"], "denominators": {}}},
            {**compare, "evidence": {**compare["evidence"], "sources": [
                {"view": "raw.drilling_run", "columns": [], "measures": []}]}},
        ):
            with self.assertRaises(ContractError):
                schema_check(bad)

    def test_forged_counts_context_and_result_correlation_fail_offline_grading(self):
        request = copy.deepcopy(CONTRACT["examples"][1])
        rows, exclusions = self.oracle.candidates(request["context"]["targetId"])
        response = response_envelope("candidates", request)
        response.update(rows=rows, totalCount=len(rows), truncated=False, exclusions=exclusions)
        association = fixture_association(response)
        corruptions = [
            {"rows": rows[:-1]}, {"rows": rows + [rows[0]]},
            {"rows": list(reversed(rows))}, {"totalCount": len(rows) + 1},
            {"exclusions": exclusions[:-1]}, {"contextHash": "0" * 64},
            {"context": {**response["context"], "targetId": "SYN-TARGET-0002"}},
        ]
        for key in ("receiptId", "requestId", "toolCallId", "resultId"):
            corruptions.append({"evidence": {**response["evidence"], key: "forged_fixture_id_01"}})
        for corruption in corruptions:
            changed = copy.deepcopy(response)
            changed.update(corruption)
            with self.subTest(corruption=corruption), self.assertRaises(ContractError):
                grade_response(changed, request, rows, exclusions, association)
        second_request = copy.deepcopy(request)
        second_request["context"]["targetId"] = "SYN-TARGET-0002"
        second_response = response_envelope("candidates", second_request)
        # Source-authenticated-looking identifiers and echoed context are still not association.
        with self.assertRaises(ContractError):
            grade_response(response, request, rows, exclusions, fixture_association(second_response))
        with self.assertRaises(ContractError):
            grade_response(response, request, rows, exclusions, {})


# Grader-only archive-derived expected results; not application prompts or data.
EXPECTED_COUNTS = [6, 7, 6, 1, 5, 3, 3, 6, 5, 1, 5, 4]
EXPECTED_IDS = [
    ["SYN-WELL-0019", "SYN-WELL-0099", "SYN-WELL-0065", "SYN-WELL-0025", "SYN-WELL-0071", "SYN-WELL-0002"],
    ["SYN-WELL-0084", "SYN-WELL-0059", "SYN-WELL-0063", "SYN-WELL-0022", "SYN-WELL-0053", "SYN-WELL-0037", "SYN-WELL-0068"],
    ["SYN-WELL-0091", "SYN-WELL-0076", "SYN-WELL-0090", "SYN-WELL-0005", "SYN-WELL-0086", "SYN-WELL-0046"],
    ["SYN-WELL-0041"],
    ["SYN-WELL-0043", "SYN-WELL-0008", "SYN-WELL-0098", "SYN-WELL-0024", "SYN-WELL-0075"],
    ["SYN-WELL-0074", "SYN-WELL-0100", "SYN-WELL-0015"],
    ["SYN-WELL-0065", "SYN-WELL-0039", "SYN-WELL-0038"],
    ["SYN-WELL-0053", "SYN-WELL-0022", "SYN-WELL-0047", "SYN-WELL-0032", "SYN-WELL-0063", "SYN-WELL-0003"],
    ["SYN-WELL-0017", "SYN-WELL-0085", "SYN-WELL-0046", "SYN-WELL-0061", "SYN-WELL-0005"],
    ["SYN-WELL-0013"],
    ["SYN-WELL-0055", "SYN-WELL-0001", "SYN-WELL-0058", "SYN-WELL-0098", "SYN-WELL-0007"],
    ["SYN-WELL-0088", "SYN-WELL-0051", "SYN-WELL-0052", "SYN-WELL-0029"],
]
EXPECTED_OFFSET_DIGEST = "e74085fe3187fae81af906baf82d7ad0a8d624024c53b3861abd6d9d0f35cb90"
EXPECTED_LEGACY_DIGEST = "fe32342322571c9e4793254d68215ec884388a07a713899dff97ec7fd4343764"


if __name__ == "__main__":
    unittest.main()
