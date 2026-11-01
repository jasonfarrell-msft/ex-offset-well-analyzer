"""Deterministic synthetic well, section, and drilling-run generation."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import hashlib
import json
import logging
from pathlib import Path
import random
import shutil
import uuid

from .config import GeneratorConfig, SUPPORTED_COORDINATE_FRAME_ID


CURRENT_GENERATOR_VERSION = "1.2.0"
HISTORICAL_REFERENCE_VERSION = "v1.0.0"
SOURCE_FINGERPRINT_FORMAT_VERSION = 1
SOURCE_FINGERPRINT_ALGORITHM = "sha256"
SOURCE_FINGERPRINT_CANONICALIZATION = "length-prefixed-path-and-content-v1"
SOURCE_FINGERPRINT_INVENTORY_FORMAT_VERSION = 1
SOURCE_FINGERPRINT_INVENTORY_FILENAME = "source_fingerprint_inventory.json"
_LOGGER = logging.getLogger(__name__)
SOURCE_FINGERPRINT_PATHS = (
    "config/generator_config.json",
    "config/generator_config_v1.1.0.json",
    "config/generator_config_v1.2.0.json",
    "generate_dataset.py",
    "src/drillrun_synth/__init__.py",
    "src/drillrun_synth/cli.py",
    "src/drillrun_synth/config.py",
    "src/drillrun_synth/generator.py",
)

COMMON_FIELDS = [
    "is_synthetic",
    "dataset_version",
    "generator_version",
    "generation_run_id",
    "deterministic_seed",
    "generated_at_utc",
    "scenario",
    "quality_status",
    "quality_reason_codes",
]

WELL_FIELDS = [
    "well_id",
    "well_name",
    "operator_name",
    "basin_name",
    "field_name",
    "spud_date",
    "completion_date",
    "total_footage_ft",
    "total_duration_hours",
    "section_count",
    "run_count",
    "split_assignment",
    "coordinate_frame_id",
    "location_semantics",
    "surface_x_ft",
    "surface_y_ft",
] + COMMON_FIELDS

SECTION_FIELDS = [
    "section_id",
    "well_id",
    "section_sequence",
    "hole_size_in",
    "start_md_ft",
    "end_md_ft",
    "footage_ft",
    "duration_hours",
    "formation_name",
    "formation_name_raw",
    "trajectory_profile",
    "run_count",
] + COMMON_FIELDS

RUN_FIELDS = [
    "run_id",
    "well_id",
    "section_id",
    "run_sequence_in_section",
    "start_time_utc",
    "end_time_utc",
    "start_md_ft",
    "end_md_ft",
    "footage_ft",
    "duration_hours",
    "formation_name",
    "formation_name_raw",
    "bit_type",
    "bit_size_in",
    "bit_iadc_code",
    "bha_type",
    "mud_type",
    "mud_weight_ppg",
    "mud_funnel_viscosity_sec",
] + COMMON_FIELDS

QUALITY_FIELDS = [
    "quality_issue_id",
    "entity_type",
    "entity_id",
    "well_id",
    "section_id",
    "run_id",
    "reason_code",
    "severity",
    "field_name",
    "observed_value",
    "expected_constraint",
    "handling",
] + COMMON_FIELDS

SPLIT_FIELDS = [
    "well_id",
    "split_assignment",
    "assignment_basis",
] + COMMON_FIELDS

TARGET_PROVENANCE_FIELDS = [
    "is_synthetic",
    "dataset_version",
    "generator_version",
    "generation_run_id",
    "deterministic_seed",
    "generated_at_utc",
    "scenario",
]

PLANNED_TARGET_FIELDS = [
    "target_id",
    "record_kind",
    "basin_name",
    "field_name",
    "expected_formation_name",
    "planned_trajectory_profile",
    "planned_hole_size_in",
    "planned_md_min_ft",
    "planned_md_max_ft",
    "planned_bit_type",
    "planned_bha_type",
    "planned_mud_type",
    "coordinate_frame_id",
    "location_semantics",
    "surface_x_ft",
    "surface_y_ft",
    "reference_dataset_version",
    "reference_manifest_sha256",
] + TARGET_PROVENANCE_FIELDS

EVENT_FIELDS = [
    "event_id",
    "well_id",
    "section_id",
    "run_id",
    "event_type",
    "event_subtype",
    "event_count",
    "event_duration_hours",
] + COMMON_FIELDS

FORMATIONS = [
    "Synthetic Aster",
    "Synthetic Brimstone",
    "Synthetic Cobalt",
    "Synthetic Driftwood",
    "Synthetic Ember",
    "Synthetic Flint",
]
TRAJECTORIES = ["VERTICAL", "BUILD_AND_HOLD", "HORIZONTAL"]
BIT_TYPES = ["PDC", "TRICONE", "HYBRID"]
IADC_CODES = ["M323", "M423", "M433", "M442", "537", "627"]
BHA_TYPES = ["ROTARY", "MOTOR", "RSS"]
MUD_TYPES = ["WATER_BASED_SYNTHETIC", "OIL_BASED_SYNTHETIC"]
EVENT_SUBTYPES_BY_TYPE = {
    "LOSSES": ["SEEPAGE", "PARTIAL", "SEVERE"],
    "STUCK_PIPE": ["DIFFERENTIAL", "PACK_OFF", "KEYSEAT"],
    "VIBRATION": ["TORQUE", "LATERAL", "AXIAL"],
    "NPT": ["RIG_REPAIR", "WEATHER", "LOGISTICS"],
    "TRIP": ["BIT_CHANGE", "BHA_CHANGE", "CONNECTION"],
}
EVENT_TYPES = tuple(EVENT_SUBTYPES_BY_TYPE)
HOLE_SIZES = [17.5, 12.25, 8.5, 6.125]
LOCATION_SEMANTICS = "SYNTHETIC_SURFACE_WELLHEAD"
COORDINATE_FRAME = {
    "frame_id": SUPPORTED_COORDINATE_FRAME_ID,
    "axes": {
        "x": "Abstract local axis X; no east/west or geodetic orientation is asserted.",
        "y": "Abstract local axis Y; no north/south or geodetic orientation is asserted.",
    },
    "origin": (
        "Arbitrary fictional origin for this generated dataset; not tied to a "
        "survey monument, datum, or real-world location."
    ),
    "units": "ft",
    "precision_ft": 1,
    "bounds_ft": {
        "x_min": -1_000_000,
        "x_max": 1_000_000,
        "y_min": -1_000_000,
        "y_max": 1_000_000,
    },
    "coordinate_semantics": LOCATION_SEMANTICS,
    "not_geographic_crs": True,
    "proximity_caveat": (
        "Surface proximity is a candidate filter only and does not establish "
        "subsurface proximity, stratigraphic equivalence, or geological similarity."
    ),
}
SPATIAL_CLUSTERS = [
    {
        "basin_name": "Synthetic North Basin",
        "field_name": "Fictional Aurora Field",
        "center_x_ft": -700_000,
        "center_y_ft": -600_000,
        "formation_names": ["Synthetic Aster", "Synthetic Brimstone", "Synthetic Cobalt"],
    },
    {
        "basin_name": "Synthetic North Basin",
        "field_name": "Fictional Borealis Field",
        "center_x_ft": -680_000,
        "center_y_ft": -600_000,
        "formation_names": ["Synthetic Aster", "Synthetic Cobalt", "Synthetic Driftwood"],
    },
    {
        "basin_name": "Synthetic Central Basin",
        "field_name": "Fictional Comet Field",
        "center_x_ft": -100_000,
        "center_y_ft": 100_000,
        "formation_names": ["Synthetic Brimstone", "Synthetic Cobalt", "Synthetic Driftwood"],
    },
    {
        "basin_name": "Synthetic Central Basin",
        "field_name": "Fictional Delta Field",
        "center_x_ft": -80_000,
        "center_y_ft": 100_000,
        "formation_names": ["Synthetic Cobalt", "Synthetic Driftwood", "Synthetic Ember"],
    },
    {
        "basin_name": "Synthetic South Basin",
        "field_name": "Fictional Ember Field",
        "center_x_ft": 500_000,
        "center_y_ft": 600_000,
        "formation_names": ["Synthetic Driftwood", "Synthetic Ember", "Synthetic Flint"],
    },
    {
        "basin_name": "Synthetic South Basin",
        "field_name": "Fictional Flint Field",
        "center_x_ft": 520_000,
        "center_y_ft": 600_000,
        "formation_names": ["Synthetic Cobalt", "Synthetic Ember", "Synthetic Flint"],
    },
]


@dataclass(frozen=True)
class ReleaseResult:
    release_path: Path
    row_counts: dict[str, int]
    issue_counts: dict[str, int]
    hashes: dict[str, str]


def _metadata(config: GeneratorConfig, generation_run_id: str) -> dict:
    return {
        "is_synthetic": "true",
        "dataset_version": config.dataset_version,
        "generator_version": config.generator_version,
        "generation_run_id": generation_run_id,
        "deterministic_seed": str(config.deterministic_seed),
        "generated_at_utc": config.generated_at_utc,
        "scenario": config.scenario,
        "quality_status": "PASS",
        "quality_reason_codes": "",
    }


def _generation_run_id(config: GeneratorConfig) -> str:
    payload = json.dumps(config.as_json_dict(), sort_keys=True, separators=(",", ":"))
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"synthetic-drillrun:{payload}"))


def _stable_digest(namespace: str, identity: str) -> bytes:
    payload = f"drillrun-synthetic-v1\0{namespace}\0{identity}".encode("utf-8")
    return hashlib.sha256(payload).digest()


def _stable_index(namespace: str, identity: str, size: int) -> int:
    return int.from_bytes(_stable_digest(namespace, identity)[:8], "big") % size


def _event_id(
    dataset_version: str,
    run_id: str,
    event_type: str,
    event_subtype: str,
) -> str:
    payload = f"{dataset_version}:{run_id}:{event_type}:{event_subtype}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"synthetic-run-event:{payload}"))


def _cluster_for_well(well_id: str) -> dict:
    return SPATIAL_CLUSTERS[_stable_index("field-cluster", well_id, len(SPATIAL_CLUSTERS))]


def _surface_location(identity: str, cluster: dict) -> tuple[int, int]:
    digest = _stable_digest("surface-wellhead", identity)
    x_offset = int.from_bytes(digest[:4], "big") % 5001 - 2500
    y_offset = int.from_bytes(digest[4:8], "big") % 5001 - 2500
    return (
        cluster["center_x_ft"] + x_offset,
        cluster["center_y_ft"] + y_offset,
    )


def _location_fields(identity: str, cluster: dict) -> dict[str, str]:
    x_ft, y_ft = _surface_location(identity, cluster)
    return {
        "coordinate_frame_id": SUPPORTED_COORDINATE_FRAME_ID,
        "location_semantics": LOCATION_SEMANTICS,
        "surface_x_ft": str(x_ft),
        "surface_y_ft": str(y_ft),
    }


def _split_for_well(well_number: int) -> str:
    bucket = (well_number * 37) % 100
    if bucket < 70:
        return "TRAIN"
    if bucket < 85:
        return "VALIDATION"
    return "TEST"


def _add_quality_code(row: dict, code: str, severity: str) -> None:
    existing = set(filter(None, row["quality_reason_codes"].split("|")))
    existing.add(code)
    row["quality_reason_codes"] = "|".join(sorted(existing))
    if severity == "ERROR":
        row["quality_status"] = "ERROR"
    elif row["quality_status"] == "PASS":
        row["quality_status"] = "WARNING"


def _write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def source_fingerprint(source_root: Path) -> dict:
    """Hash the exact generator source and milestone config using canonical framing."""
    digest = hashlib.sha256()
    digest.update(b"drillrun-source-fingerprint-v1\0")
    included_paths = sorted(SOURCE_FINGERPRINT_PATHS)
    for relative_path in included_paths:
        path_bytes = relative_path.encode("utf-8")
        content = (source_root / relative_path).read_bytes()
        digest.update(len(path_bytes).to_bytes(8, "big"))
        digest.update(path_bytes)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return {
        "algorithm": SOURCE_FINGERPRINT_ALGORITHM,
        "canonicalization": SOURCE_FINGERPRINT_CANONICALIZATION,
        "format_version": SOURCE_FINGERPRINT_FORMAT_VERSION,
        "included_paths": included_paths,
        "value": digest.hexdigest(),
    }


def source_fingerprint_inventory(source_root: Path) -> dict:
    """List each fingerprint input and its independent SHA-256 digest."""
    return {
        "aggregate_source_fingerprint": source_fingerprint(source_root),
        "file_hash_algorithm": SOURCE_FINGERPRINT_ALGORITHM,
        "files": [
            {
                "path": relative_path,
                "sha256": _sha256(source_root / relative_path),
            }
            for relative_path in sorted(SOURCE_FINGERPRINT_PATHS)
        ],
        "format_version": SOURCE_FINGERPRINT_INVENTORY_FORMAT_VERSION,
    }


def _schema_document() -> dict:
    common = {
        "is_synthetic": {"type": "boolean", "constraint": "Always true."},
        "dataset_version": {"type": "string", "constraint": "Non-empty semantic release identifier."},
        "generator_version": {"type": "string", "constraint": "Non-empty generator release identifier."},
        "generation_run_id": {"type": "uuid", "constraint": "Deterministic UUID for the complete config."},
        "deterministic_seed": {"type": "integer", "constraint": "Same on every row in a release."},
        "generated_at_utc": {"type": "timestamp", "unit": "UTC", "constraint": "ISO 8601 with Z suffix."},
        "scenario": {"type": "string", "constraint": "Non-empty generation scenario."},
        "quality_status": {"type": "enum", "values": ["PASS", "WARNING", "ERROR"]},
        "quality_reason_codes": {"type": "string", "constraint": "Pipe-delimited documented codes; blank for PASS."},
    }
    return {
        "schema_version": CURRENT_GENERATOR_VERSION,
        "coordinate_reference": COORDINATE_FRAME,
        "interpretation_limits": [
            "All coordinates, basins, fields, and formations are fictional.",
            "The local frame is not latitude/longitude, an EPSG coordinate reference system, or transformable to real geography.",
            COORDINATE_FRAME["proximity_caveat"],
        ],
        "canonical_units": {
            "measured_depth": "ft",
            "footage": "ft",
            "duration": "hours",
            "hole_and_bit_size": "in",
            "mud_weight": "ppg",
            "mud_funnel_viscosity": "sec/quart",
            "timestamps": "UTC",
            "surface_coordinates": "ft in coordinate_reference.frame_id",
        },
        "tables": {
            "wells.csv": {
                "grain": "One row per fictional well.",
                "primary_key": ["well_id"],
                "fields": {
                    "well_id": {"type": "string", "constraint": "SYN-WELL-NNNN; unique."},
                    "well_name": {"type": "string", "constraint": "Contains Fictional."},
                    "operator_name": {"type": "string", "constraint": "Contains Synthetic Demonstration Operator."},
                    "basin_name": {"type": "string"},
                    "field_name": {"type": "string", "constraint": "Contains Fictional."},
                    "spud_date": {"type": "date"},
                    "completion_date": {"type": "date", "constraint": "On or after spud_date."},
                    "total_footage_ft": {"type": "decimal", "unit": "ft", "constraint": "> 0; equals child-run sum."},
                    "total_duration_hours": {"type": "decimal", "unit": "hours", "constraint": "> 0; equals child-run sum."},
                    "section_count": {"type": "integer", "constraint": "2..4; equals child count."},
                    "run_count": {"type": "integer", "constraint": ">= 4; equals descendant-run count."},
                    "split_assignment": {"type": "enum", "values": ["TRAIN", "VALIDATION", "TEST"]},
                    "coordinate_frame_id": {
                        "type": "string",
                        "constraint": f"Always {SUPPORTED_COORDINATE_FRAME_ID}.",
                    },
                    "location_semantics": {
                        "type": "enum",
                        "values": [LOCATION_SEMANTICS],
                    },
                    "surface_x_ft": {
                        "type": "integer",
                        "unit": "ft",
                        "constraint": "Within coordinate_reference bounds; precision 1 ft.",
                    },
                    "surface_y_ft": {
                        "type": "integer",
                        "unit": "ft",
                        "constraint": "Within coordinate_reference bounds; precision 1 ft.",
                    },
                    **common,
                },
            },
            "sections.csv": {
                "grain": "One row per hole section within a well.",
                "primary_key": ["section_id"],
                "foreign_keys": {"well_id": "wells.csv.well_id"},
                "fields": {
                    "section_id": {"type": "string", "constraint": "Unique."},
                    "well_id": {"type": "string"},
                    "section_sequence": {"type": "integer", "constraint": "Starts at 1 and is contiguous per well."},
                    "hole_size_in": {"type": "decimal", "unit": "in", "constraint": "One of 17.5, 12.25, 8.5, 6.125."},
                    "start_md_ft": {"type": "decimal", "unit": "ft", "constraint": ">= 0."},
                    "end_md_ft": {"type": "decimal", "unit": "ft", "constraint": "> start_md_ft."},
                    "footage_ft": {"type": "decimal", "unit": "ft", "constraint": "end_md_ft - start_md_ft."},
                    "duration_hours": {"type": "decimal", "unit": "hours", "constraint": "> 0; equals child-run sum."},
                    "formation_name": {"type": "string", "nullable": True},
                    "formation_name_raw": {"type": "string", "nullable": True},
                    "trajectory_profile": {"type": "enum", "values": TRAJECTORIES},
                    "run_count": {"type": "integer", "constraint": "2..5; equals child count."},
                    **common,
                },
            },
            "drilling_runs.csv": {
                "grain": "One row per drilling run within a section.",
                "primary_key": ["run_id"],
                "foreign_keys": {
                    "well_id": "wells.csv.well_id",
                    "section_id": "sections.csv.section_id",
                },
                "fields": {
                    "run_id": {"type": "string", "constraint": "Unique."},
                    "well_id": {"type": "string"},
                    "section_id": {"type": "string"},
                    "run_sequence_in_section": {"type": "integer", "constraint": "Starts at 1 and is contiguous."},
                    "start_time_utc": {"type": "timestamp", "unit": "UTC"},
                    "end_time_utc": {"type": "timestamp", "unit": "UTC", "constraint": "Normally after start; equality only for flagged NON_POSITIVE_DURATION."},
                    "start_md_ft": {"type": "decimal", "unit": "ft", "constraint": ">= 0."},
                    "end_md_ft": {"type": "decimal", "unit": "ft", "constraint": "> start_md_ft."},
                    "footage_ft": {"type": "decimal", "unit": "ft", "constraint": "> 0 and equals depth difference."},
                    "duration_hours": {"type": "decimal", "unit": "hours", "constraint": "> 0 except flagged intentional errors."},
                    "formation_name": {"type": "string", "nullable": True},
                    "formation_name_raw": {"type": "string", "nullable": True},
                    "bit_type": {"type": "enum", "values": BIT_TYPES},
                    "bit_size_in": {"type": "decimal", "unit": "in", "constraint": "Equals parent hole size."},
                    "bit_iadc_code": {"type": "string", "nullable": True},
                    "bha_type": {"type": "enum", "values": BHA_TYPES},
                    "mud_type": {"type": "enum", "values": MUD_TYPES},
                    "mud_weight_ppg": {
                        "type": "decimal",
                        "unit": "ppg",
                        "constraint": ">= 8.0 and <= 18.0.",
                    },
                    "mud_funnel_viscosity_sec": {
                        "type": "decimal",
                        "unit": "sec/quart",
                        "constraint": ">= 28 and <= 120.",
                    },
                    **common,
                },
            },
            "run_events.csv": {
                "grain": (
                    "One aggregate row per release/run/event_type/event_subtype; "
                    "synthetic comparative context only."
                ),
                "primary_key": ["event_id"],
                "foreign_keys": {
                    "well_id": "wells.csv.well_id",
                    "section_id": "sections.csv.section_id",
                    "run_id": "drilling_runs.csv.run_id",
                },
                "fields": {
                    "event_id": {
                        "type": "uuid",
                        "constraint": (
                            "Deterministic UUID derived from "
                            "dataset_version/run_id/event_type/event_subtype."
                        ),
                    },
                    "well_id": {"type": "string"},
                    "section_id": {"type": "string"},
                    "run_id": {"type": "string"},
                    "event_type": {"type": "enum", "values": list(EVENT_TYPES)},
                    "event_subtype": {
                        "type": "enum",
                        "values": sorted(
                            {
                                subtype
                                for values in EVENT_SUBTYPES_BY_TYPE.values()
                                for subtype in values
                            }
                        ),
                        "constraint": "Subtype must belong to its event_type.",
                    },
                    "event_count": {"type": "integer", "constraint": ">= 1."},
                    "event_duration_hours": {
                        "type": "decimal",
                        "unit": "hours",
                        "constraint": ">= 0.",
                    },
                    **common,
                },
            },
            "quality_issues.csv": {
                "grain": "One row per intentional data-quality issue.",
                "primary_key": ["quality_issue_id"],
                "foreign_keys": {
                    "well_id": "wells.csv.well_id",
                    "section_id": "sections.csv.section_id when entity is a section or run",
                    "run_id": "drilling_runs.csv.run_id when entity is a run",
                },
                "fields": {
                    "quality_issue_id": {"type": "string", "constraint": "SYN-DQ-NNNN; unique."},
                    "entity_type": {"type": "enum", "values": ["SECTION", "DRILLING_RUN"]},
                    "entity_id": {"type": "string", "constraint": "Identifies the affected row."},
                    "well_id": {"type": "string"},
                    "section_id": {"type": "string", "nullable": True},
                    "run_id": {"type": "string", "nullable": True},
                    "reason_code": {"type": "enum", "values": sorted([
                        "INCONSISTENT_FORMATION_LABEL",
                        "MISSING_BIT_IADC_CODE",
                        "MISSING_FORMATION",
                        "NON_POSITIVE_DURATION",
                    ])},
                    "severity": {"type": "enum", "values": ["WARNING", "ERROR"]},
                    "field_name": {"type": "string", "constraint": "Affected CSV field."},
                    "observed_value": {"type": "string", "nullable": True},
                    "expected_constraint": {"type": "string"},
                    "handling": {"type": "string", "constraint": "States how the observed value was preserved or represented."},
                    **common,
                },
            },
            "split_assignments.csv": {
                "grain": "One deterministic assignment per well.",
                "primary_key": ["well_id"],
                "fields": {
                    "well_id": {"type": "string"},
                    "split_assignment": {"type": "enum", "values": ["TRAIN", "VALIDATION", "TEST"]},
                    "assignment_basis": {"type": "string"},
                    **common,
                },
            },
            "planned_targets.csv": {
                "grain": "One planning-only record per synthetic target well; never a historical well, section, run, issue, or split.",
                "primary_key": ["target_id"],
                "fields": {
                    "target_id": {
                        "type": "string",
                        "constraint": "SYN-TARGET-NNNN; distinct from SYN-WELL identities.",
                    },
                    "record_kind": {
                        "type": "enum",
                        "values": ["PLANNED_TARGET"],
                    },
                    "basin_name": {"type": "string", "constraint": "Fictional cluster label."},
                    "field_name": {"type": "string", "constraint": "Fictional cluster label."},
                    "expected_formation_name": {
                        "type": "string",
                        "constraint": "Expected synthetic planning input, not a realized formation.",
                    },
                    "planned_trajectory_profile": {
                        "type": "enum",
                        "values": TRAJECTORIES,
                    },
                    "planned_hole_size_in": {
                        "type": "decimal",
                        "unit": "in",
                        "constraint": "One of 17.5, 12.25, 8.5, 6.125.",
                    },
                    "planned_md_min_ft": {
                        "type": "integer",
                        "unit": "ft",
                        "constraint": "Inclusive lower bound of planned measured-depth interval.",
                    },
                    "planned_md_max_ft": {
                        "type": "integer",
                        "unit": "ft",
                        "constraint": "Exclusive upper bound; greater than planned_md_min_ft.",
                    },
                    "planned_bit_type": {
                        "type": "enum",
                        "values": BIT_TYPES,
                        "nullable": True,
                    },
                    "planned_bha_type": {
                        "type": "enum",
                        "values": BHA_TYPES,
                        "nullable": True,
                    },
                    "planned_mud_type": {
                        "type": "enum",
                        "values": MUD_TYPES,
                        "nullable": True,
                    },
                    "coordinate_frame_id": {
                        "type": "string",
                        "constraint": f"Always {SUPPORTED_COORDINATE_FRAME_ID}.",
                    },
                    "location_semantics": {
                        "type": "enum",
                        "values": [LOCATION_SEMANTICS],
                    },
                    "surface_x_ft": {
                        "type": "integer",
                        "unit": "ft",
                        "constraint": "Within coordinate_reference bounds; precision 1 ft.",
                    },
                    "surface_y_ft": {
                        "type": "integer",
                        "unit": "ft",
                        "constraint": "Within coordinate_reference bounds; precision 1 ft.",
                    },
                    "reference_dataset_version": {
                        "type": "string",
                        "constraint": "Links to the historical/reference release.",
                    },
                    "reference_manifest_sha256": {
                        "type": "string",
                        "constraint": "SHA-256 of the referenced release_manifest.json.",
                    },
                    "is_synthetic": {"type": "boolean", "constraint": "Always true."},
                    "dataset_version": {
                        "type": "string",
                        "constraint": "Release containing this planning-only record.",
                    },
                    "generator_version": {"type": "string"},
                    "generation_run_id": {"type": "uuid"},
                    "deterministic_seed": {"type": "integer"},
                    "generated_at_utc": {"type": "timestamp", "unit": "UTC"},
                    "scenario": {"type": "string"},
                },
            },
        },
    }


def _data_dictionary_markdown() -> str:
    return f"""# Synthetic Drill-Run Data Dictionary

All records are entirely fictional and carry `is_synthetic=true`. Identifiers use
the `SYN-` prefix; well, operator, field, basin, and formation labels explicitly
contain `Synthetic` or `Fictional`.

## Grain and relationships

- `wells.csv`: one row per well.
- `sections.csv`: one row per hole section; `well_id` references `wells.csv`.
- `drilling_runs.csv`: one row per drilling run; `well_id` and `section_id`
  reference their parent records. Includes observed run-level drilling context
  (`bit_type`, `bha_type`, `mud_type`) plus observed mud properties
  (`mud_weight_ppg`, `mud_funnel_viscosity_sec`).
- `run_events.csv`: one aggregate row per release/run/event_type/event_subtype
  with synthetic comparative event counts and durations.
- `quality_issues.csv`: one row per deliberately injected issue.
- `split_assignments.csv`: deterministic whole-well train/validation/test assignment.
- `planned_targets.csv`: separate planning-only target-well inputs. These rows
  have `record_kind=PLANNED_TARGET`, `SYN-TARGET-NNNN` identities, and an
  explicit reference to the historical release. They are never joined into
  historical wells, sections, runs, quality issues, splits, or historical
  summary metrics.

## Synthetic surface-location reference

Historical wells and planned targets have deterministic synthetic wellhead
coordinates in `{SUPPORTED_COORDINATE_FRAME_ID}`. The X and Y axes are abstract
local axes with an arbitrary fictional origin; each coordinate is an integer
number of feet with 1-ft precision and lies within ±1,000,000 ft. This frame is
not latitude/longitude, is not an EPSG coordinate reference system, and has no
real-world transform or location claim. Coordinates are stable by record
identity and use independent namespaced derivation.

Basins, fields, coordinate clusters, and formation attributes are fictional
generation relationships. In v1.1.0, historical basin, field, and formation
labels are aligned to those fictional clusters; historical identities,
dates, sections, runs, drilling outcomes, quality-issue placements, and split
assignments are preserved from v1.0.0. The v1.0.0 release files are not changed.
**Surface proximity is a candidate filter only; it does not establish
subsurface proximity, stratigraphic equivalence, or geological similarity.**

Planned target fields are inputs only: expected formation, planned trajectory,
hole size, planned measured-depth interval, and optional planned drilling-system
intent (`planned_bit_type`, `planned_bha_type`, `planned_mud_type`). Optional
planned fields may be blank; blanks represent unavailable design intent and are
not inferred from observed runs. The file contains no realized footage, duration,
dates, run metrics, outcomes, predictions, or split membership. Its records are
excluded from all historical metrics, quality counts, split assignments, and
historical categories.

Run-event rows are synthetic comparative context for offset analysis only. They
are not telemetry, incident forensics, recommendation logic, or operational
guidance, and they are intentionally separate from `quality_issues.csv`.

## Canonical units

Measured depth and footage use feet (`ft`), duration uses hours, hole and bit
sizes use inches, mud weight uses ppg, mud funnel viscosity uses sec/quart, and
timestamps use ISO 8601 UTC (`Z`). The machine-readable field constraints are in
`schema.json`.

## Intentional quality codes

- `MISSING_FORMATION`: source and canonical formation are blank and preserved.
- `INCONSISTENT_FORMATION_LABEL`: the raw noncanonical label is preserved while
  the canonical formation remains in a separate field; no silent overwrite occurs.
- `MISSING_BIT_IADC_CODE`: the IADC value is blank and preserved.
- `NON_POSITIVE_DURATION`: duration is zero and end time equals start time. The
  invalid value is preserved and explicitly marked `ERROR`.

Issue frequencies are configuration choices, not estimates of real operations.
"""


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _issue_row(
    *,
    metadata: dict,
    number: int,
    entity_type: str,
    entity_id: str,
    well_id: str,
    section_id: str = "",
    run_id: str = "",
    reason_code: str,
    severity: str,
    field_name: str,
    observed_value: str,
    expected_constraint: str,
    handling: str,
) -> dict:
    row = {
        "quality_issue_id": f"SYN-DQ-{number:04d}",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "well_id": well_id,
        "section_id": section_id,
        "run_id": run_id,
        "reason_code": reason_code,
        "severity": severity,
        "field_name": field_name,
        "observed_value": observed_value,
        "expected_constraint": expected_constraint,
        "handling": handling,
        **metadata,
    }
    row["quality_status"] = severity
    row["quality_reason_codes"] = reason_code
    return row


def generate_release(
    config: GeneratorConfig,
    output_root: Path,
    *,
    source_root: Path | None = None,
) -> ReleaseResult:
    source_root = source_root or Path(__file__).resolve().parents[2]
    release_path = output_root / config.dataset_version
    if release_path.exists():
        raise ValueError(
            f"Immutable release already exists: {release_path}. "
            "Use a new dataset_version or output root."
        )
    if config.dataset_version == HISTORICAL_REFERENCE_VERSION:
        raise ValueError(
            "The archived v1.0.0 release is immutable; generate a new version "
            "with its versioned configuration instead."
        )
    if config.generator_version != CURRENT_GENERATOR_VERSION:
        raise ValueError(
            f"This generator produces version {CURRENT_GENERATOR_VERSION}; "
            f"config requested {config.generator_version}."
        )
    if config.spatial_frame_id != SUPPORTED_COORDINATE_FRAME_ID:
        raise ValueError(
            "A new release requires the supported synthetic local coordinate frame "
            f"{SUPPORTED_COORDINATE_FRAME_ID}."
        )
    if config.reference_dataset_version != HISTORICAL_REFERENCE_VERSION:
        raise ValueError(
            "The proximity-capable release must reference the preserved v1.0.0 release."
        )

    reference_release_path = output_root / config.reference_dataset_version
    if not reference_release_path.is_dir():
        raise ValueError(
            f"Historical reference release does not exist: {reference_release_path}"
        )
    from .validation import validate_release

    reference_errors = validate_release(
        reference_release_path,
        source_root=source_root,
    )
    if reference_errors:
        raise ValueError(
            "Historical reference release validation failed: "
            + "; ".join(reference_errors)
        )
    reference_manifest_path = reference_release_path / "release_manifest.json"
    reference_manifest = json.loads(reference_manifest_path.read_text(encoding="utf-8"))
    if reference_manifest.get("dataset_version") != config.reference_dataset_version:
        raise ValueError("Historical reference release ID does not match its manifest")
    reference_manifest_sha256 = _sha256(reference_manifest_path)

    release_path.mkdir(parents=True)

    rng = random.Random(config.deterministic_seed)
    run_id = _generation_run_id(config)
    metadata = _metadata(config, run_id)
    wells: list[dict] = []
    sections: list[dict] = []
    runs: list[dict] = []
    split_rows: list[dict] = []

    interval_days = (config.interval_end_date - config.interval_start_date).days
    latest_spud_offset = interval_days - 120
    if latest_spud_offset <= 0:
        raise ValueError("Configured interval is too short for well generation")

    for well_number in range(1, config.well_count + 1):
        well_id = f"SYN-WELL-{well_number:04d}"
        cluster = _cluster_for_well(well_id)
        section_count = 2 + rng.randrange(3)
        split = _split_for_well(well_number)
        spud_offset = ((well_number - 1) * latest_spud_offset) // config.well_count
        spud_offset += rng.randrange(0, min(20, latest_spud_offset - spud_offset + 1))
        spud_date = config.interval_start_date + timedelta(days=spud_offset)
        current_time = datetime.combine(spud_date, time(6, 0), tzinfo=timezone.utc)
        current_depth = 0.0
        well_run_start = len(runs)
        well_section_start = len(sections)

        for section_sequence in range(1, section_count + 1):
            section_id = f"SYN-SEC-{well_number:04d}-{section_sequence:02d}"
            formation_pool = cluster["formation_names"]
            rng.randrange(3)  # Preserve the v1 run-generation random stream.
            formation = formation_pool[
                _stable_index("formation", section_id, len(formation_pool))
            ]
            trajectory = TRAJECTORIES[min(section_sequence - 1, len(TRAJECTORIES) - 1)]
            run_count = 2 + rng.randrange(4)
            section_start_depth = current_depth
            section_run_start = len(runs)

            for run_sequence in range(1, run_count + 1):
                footage = float(rng.randrange(4500, 14501) / 10)
                duration_minutes = rng.randrange(480, 2401)
                run_start_time = current_time
                run_end_time = run_start_time + timedelta(minutes=duration_minutes)
                run_start_depth = current_depth
                run_end_depth = round(run_start_depth + footage, 1)
                run_row = {
                    "run_id": f"SYN-RUN-{well_number:04d}-{section_sequence:02d}-{run_sequence:02d}",
                    "well_id": well_id,
                    "section_id": section_id,
                    "run_sequence_in_section": str(run_sequence),
                    "start_time_utc": _iso_utc(run_start_time),
                    "end_time_utc": _iso_utc(run_end_time),
                    "start_md_ft": f"{run_start_depth:.1f}",
                    "end_md_ft": f"{run_end_depth:.1f}",
                    "footage_ft": f"{footage:.1f}",
                    "duration_hours": f"{duration_minutes / 60:.2f}",
                    "formation_name": formation,
                    "formation_name_raw": formation,
                    "bit_type": BIT_TYPES[rng.randrange(len(BIT_TYPES))],
                    "bit_size_in": f"{HOLE_SIZES[section_sequence - 1]:.3f}".rstrip("0").rstrip("."),
                    "bit_iadc_code": IADC_CODES[rng.randrange(len(IADC_CODES))],
                    "bha_type": BHA_TYPES[rng.randrange(len(BHA_TYPES))],
                    "mud_type": MUD_TYPES[rng.randrange(len(MUD_TYPES))],
                    "mud_weight_ppg": f"{(86 + _stable_index('mud-weight-ppg', f'{well_id}:{section_id}:{run_sequence}', 95)) / 10:.1f}",
                    "mud_funnel_viscosity_sec": str(
                        28
                        + _stable_index(
                            "mud-funnel-viscosity-sec",
                            f"{well_id}:{section_id}:{run_sequence}",
                            93,
                        )
                    ),
                    **metadata,
                }
                runs.append(run_row)
                current_depth = run_end_depth
                current_time = run_end_time + timedelta(minutes=rng.randrange(30, 181))

            section_runs = runs[section_run_start:]
            sections.append(
                {
                    "section_id": section_id,
                    "well_id": well_id,
                    "section_sequence": str(section_sequence),
                    "hole_size_in": f"{HOLE_SIZES[section_sequence - 1]:.3f}".rstrip("0").rstrip("."),
                    "start_md_ft": f"{section_start_depth:.1f}",
                    "end_md_ft": f"{current_depth:.1f}",
                    "footage_ft": f"{current_depth - section_start_depth:.1f}",
                    "duration_hours": f"{sum(float(row['duration_hours']) for row in section_runs):.2f}",
                    "formation_name": formation,
                    "formation_name_raw": formation,
                    "trajectory_profile": trajectory,
                    "run_count": str(run_count),
                    **metadata,
                }
            )
            current_time += timedelta(hours=rng.randrange(4, 25))

        well_runs = runs[well_run_start:]
        well_sections = sections[well_section_start:]
        completion_date = datetime.fromisoformat(well_runs[-1]["end_time_utc"].replace("Z", "+00:00")).date()
        wells.append(
            {
                "well_id": well_id,
                "well_name": f"Fictional Atlas Well {well_number:04d}",
                "operator_name": f"Synthetic Demonstration Operator {(well_number - 1) % 5 + 1:02d}",
                "basin_name": cluster["basin_name"],
                "field_name": cluster["field_name"],
                "spud_date": spud_date.isoformat(),
                "completion_date": completion_date.isoformat(),
                "total_footage_ft": f"{sum(float(row['footage_ft']) for row in well_runs):.1f}",
                "total_duration_hours": f"{sum(float(row['duration_hours']) for row in well_runs):.2f}",
                "section_count": str(len(well_sections)),
                "run_count": str(len(well_runs)),
                "split_assignment": split,
                **_location_fields(well_id, cluster),
                **metadata,
            }
        )
        split_rows.append(
            {
                "well_id": well_id,
                "split_assignment": split,
                "assignment_basis": "Deterministic whole-well modulo assignment; no row-level leakage.",
                **metadata,
            }
        )

    quality_issues: list[dict] = []
    issue_number = 1

    section_targets = rng.sample(
        range(len(sections)),
        config.intentional_issue_counts["MISSING_FORMATION"]
        + config.intentional_issue_counts["INCONSISTENT_FORMATION_LABEL"],
    )
    missing_formation_targets = section_targets[
        : config.intentional_issue_counts["MISSING_FORMATION"]
    ]
    inconsistent_targets = section_targets[
        config.intentional_issue_counts["MISSING_FORMATION"] :
    ]

    for index in missing_formation_targets:
        section = sections[index]
        section["formation_name"] = ""
        section["formation_name_raw"] = ""
        _add_quality_code(section, "MISSING_FORMATION", "WARNING")
        for run in runs:
            if run["section_id"] == section["section_id"]:
                run["formation_name"] = ""
                run["formation_name_raw"] = ""
                _add_quality_code(run, "MISSING_FORMATION", "WARNING")
        quality_issues.append(
            _issue_row(
                metadata=metadata,
                number=issue_number,
                entity_type="SECTION",
                entity_id=section["section_id"],
                well_id=section["well_id"],
                section_id=section["section_id"],
                reason_code="MISSING_FORMATION",
                severity="WARNING",
                field_name="formation_name",
                observed_value="",
                expected_constraint="Non-empty fictional formation label.",
                handling="Blank source value preserved in both raw and canonical fields.",
            )
        )
        issue_number += 1

    for index in inconsistent_targets:
        section = sections[index]
        raw_label = section["formation_name"].replace("Synthetic ", "SYN_").lower()
        section["formation_name_raw"] = raw_label
        _add_quality_code(section, "INCONSISTENT_FORMATION_LABEL", "WARNING")
        quality_issues.append(
            _issue_row(
                metadata=metadata,
                number=issue_number,
                entity_type="SECTION",
                entity_id=section["section_id"],
                well_id=section["well_id"],
                section_id=section["section_id"],
                reason_code="INCONSISTENT_FORMATION_LABEL",
                severity="WARNING",
                field_name="formation_name_raw",
                observed_value=raw_label,
                expected_constraint="Canonical labels use 'Synthetic <Name>'.",
                handling="Raw label preserved; explicit canonical value stored separately.",
            )
        )
        issue_number += 1

    available_run_indexes = [
        index
        for index, run in enumerate(runs)
        if "MISSING_FORMATION" not in run["quality_reason_codes"]
    ]
    run_targets = rng.sample(
        available_run_indexes,
        config.intentional_issue_counts["MISSING_BIT_IADC_CODE"]
        + config.intentional_issue_counts["NON_POSITIVE_DURATION"],
    )
    missing_iadc_targets = run_targets[
        : config.intentional_issue_counts["MISSING_BIT_IADC_CODE"]
    ]
    zero_duration_targets = run_targets[
        config.intentional_issue_counts["MISSING_BIT_IADC_CODE"] :
    ]

    for index in missing_iadc_targets:
        run = runs[index]
        run["bit_iadc_code"] = ""
        _add_quality_code(run, "MISSING_BIT_IADC_CODE", "WARNING")
        quality_issues.append(
            _issue_row(
                metadata=metadata,
                number=issue_number,
                entity_type="DRILLING_RUN",
                entity_id=run["run_id"],
                well_id=run["well_id"],
                section_id=run["section_id"],
                run_id=run["run_id"],
                reason_code="MISSING_BIT_IADC_CODE",
                severity="WARNING",
                field_name="bit_iadc_code",
                observed_value="",
                expected_constraint="Non-empty fictional IADC code.",
                handling="Blank source value preserved and explicitly flagged.",
            )
        )
        issue_number += 1

    for index in zero_duration_targets:
        run = runs[index]
        original_duration = float(run["duration_hours"])
        run["duration_hours"] = "0.00"
        run["end_time_utc"] = run["start_time_utc"]
        _add_quality_code(run, "NON_POSITIVE_DURATION", "ERROR")
        section = next(row for row in sections if row["section_id"] == run["section_id"])
        well = next(row for row in wells if row["well_id"] == run["well_id"])
        section["duration_hours"] = f"{float(section['duration_hours']) - original_duration:.2f}"
        well["total_duration_hours"] = f"{float(well['total_duration_hours']) - original_duration:.2f}"
        quality_issues.append(
            _issue_row(
                metadata=metadata,
                number=issue_number,
                entity_type="DRILLING_RUN",
                entity_id=run["run_id"],
                well_id=run["well_id"],
                section_id=run["section_id"],
                run_id=run["run_id"],
                reason_code="NON_POSITIVE_DURATION",
                severity="ERROR",
                field_name="duration_hours",
                observed_value="0.00",
                expected_constraint="Duration must be greater than zero and end after start.",
                handling="Invalid value and equal timestamps preserved; record marked ERROR.",
            )
        )
        issue_number += 1

    planned_targets = []
    for target_number in range(1, config.planned_target_count + 1):
        target_id = f"SYN-TARGET-{target_number:04d}"
        cluster = SPATIAL_CLUSTERS[(target_number - 1) % len(SPATIAL_CLUSTERS)]
        formation_pool = cluster["formation_names"]
        expected_formation = formation_pool[
            _stable_index("planned-formation", target_id, len(formation_pool))
        ]
        md_min_ft = 6_000 + 250 * _stable_index("planned-md-min", target_id, 25)
        planned_targets.append(
            {
                "target_id": target_id,
                "record_kind": "PLANNED_TARGET",
                "basin_name": cluster["basin_name"],
                "field_name": cluster["field_name"],
                "expected_formation_name": expected_formation,
                "planned_trajectory_profile": TRAJECTORIES[
                    _stable_index("planned-trajectory", target_id, len(TRAJECTORIES))
                ],
                "planned_hole_size_in": f"{HOLE_SIZES[_stable_index('planned-hole-size', target_id, len(HOLE_SIZES))]:.3f}".rstrip("0").rstrip("."),
                "planned_md_min_ft": str(md_min_ft),
                "planned_md_max_ft": str(
                    md_min_ft + 2_500 + 250 * _stable_index("planned-md-max", target_id, 15)
                ),
                "planned_bit_type": (
                    ""
                    if _stable_index("planned-bit-type-present", target_id, 5) == 0
                    else BIT_TYPES[
                        _stable_index("planned-bit-type", target_id, len(BIT_TYPES))
                    ]
                ),
                "planned_bha_type": (
                    ""
                    if _stable_index("planned-bha-type-present", target_id, 5) == 0
                    else BHA_TYPES[
                        _stable_index("planned-bha-type", target_id, len(BHA_TYPES))
                    ]
                ),
                "planned_mud_type": (
                    ""
                    if _stable_index("planned-mud-type-present", target_id, 5) == 0
                    else MUD_TYPES[
                        _stable_index("planned-mud-type", target_id, len(MUD_TYPES))
                    ]
                ),
                **_location_fields(target_id, cluster),
                "reference_dataset_version": config.reference_dataset_version,
                "reference_manifest_sha256": reference_manifest_sha256,
                **{field: metadata[field] for field in TARGET_PROVENANCE_FIELDS},
            }
        )

    run_events: list[dict] = []
    for run in runs:
        run_identity = run["run_id"]
        if float(run["duration_hours"]) <= 0:
            continue
        event_cardinality_bucket = _stable_index("run-event-cardinality", run_identity, 5)
        event_cardinality = 0 if event_cardinality_bucket == 0 else (1 if event_cardinality_bucket < 4 else 2)
        emitted_pairs: set[tuple[str, str]] = set()
        for event_ordinal in range(event_cardinality):
            event_type = EVENT_TYPES[
                _stable_index(
                    f"run-event-type-{event_ordinal}",
                    run_identity,
                    len(EVENT_TYPES),
                )
            ]
            subtypes = EVENT_SUBTYPES_BY_TYPE[event_type]
            event_subtype = subtypes[
                _stable_index(
                    f"run-event-subtype-{event_ordinal}",
                    run_identity,
                    len(subtypes),
                )
            ]
            pair = (event_type, event_subtype)
            if pair in emitted_pairs:
                event_subtype = subtypes[
                    (_stable_index(f"run-event-subtype-{event_ordinal}", run_identity, len(subtypes)) + 1)
                    % len(subtypes)
                ]
                pair = (event_type, event_subtype)
            if pair in emitted_pairs:
                continue
            emitted_pairs.add(pair)
            run_events.append(
                {
                    "event_id": _event_id(
                        config.dataset_version,
                        run_identity,
                        event_type,
                        event_subtype,
                    ),
                    "well_id": run["well_id"],
                    "section_id": run["section_id"],
                    "run_id": run_identity,
                    "event_type": event_type,
                    "event_subtype": event_subtype,
                    "event_count": str(
                        1
                        + _stable_index(
                            f"run-event-count-{event_ordinal}",
                            run_identity,
                            4,
                        )
                    ),
                    "event_duration_hours": f"{_stable_index(f'run-event-duration-{event_ordinal}', run_identity, 401) / 100:.2f}",
                    **metadata,
                }
            )

    files_and_rows = {
        "wells.csv": (WELL_FIELDS, wells),
        "sections.csv": (SECTION_FIELDS, sections),
        "drilling_runs.csv": (RUN_FIELDS, runs),
        "run_events.csv": (EVENT_FIELDS, run_events),
        "quality_issues.csv": (QUALITY_FIELDS, quality_issues),
        "split_assignments.csv": (SPLIT_FIELDS, split_rows),
        "planned_targets.csv": (PLANNED_TARGET_FIELDS, planned_targets),
    }
    for filename, (fields, rows) in files_and_rows.items():
        _write_csv(release_path / filename, fields, rows)

    schema_path = release_path / "schema.json"
    schema_path.write_text(
        json.dumps(_schema_document(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    dictionary_path = release_path / "data_dictionary.md"
    dictionary_path.write_text(_data_dictionary_markdown(), encoding="utf-8")
    config_path = release_path / "generator_config.json"
    config_path.write_text(
        json.dumps(config.as_json_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    inventory_path = release_path / SOURCE_FINGERPRINT_INVENTORY_FILENAME
    inventory_path.write_text(
        json.dumps(source_fingerprint_inventory(source_root), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    artifact_names = sorted(
        list(files_and_rows)
        + [
            "schema.json",
            "data_dictionary.md",
            "generator_config.json",
            SOURCE_FINGERPRINT_INVENTORY_FILENAME,
        ]
    )
    hashes = {name: _sha256(release_path / name) for name in artifact_names}
    row_counts = {name: len(rows) for name, (_, rows) in files_and_rows.items()}
    issue_counts = dict(sorted(Counter(row["reason_code"] for row in quality_issues).items()))
    summary = {
        "well_count": len(wells),
        "section_count": len(sections),
        "run_count": len(runs),
        "run_event_row_count": len(run_events),
        "total_footage_ft": round(sum(float(row["footage_ft"]) for row in runs), 1),
        "total_duration_hours": round(sum(float(row["duration_hours"]) for row in runs), 2),
        "total_event_duration_hours": round(
            sum(float(row["event_duration_hours"]) for row in run_events), 2
        ),
        "total_event_count": sum(int(row["event_count"]) for row in run_events),
        "formation_counts": dict(sorted(Counter(row["formation_name"] or "(missing)" for row in sections).items())),
        "bit_type_counts": dict(sorted(Counter(row["bit_type"] for row in runs).items())),
        "bha_type_counts": dict(sorted(Counter(row["bha_type"] for row in runs).items())),
        "event_type_counts": dict(
            sorted(Counter(row["event_type"] for row in run_events).items())
        ),
        "quality_status_counts": dict(sorted(Counter(row["quality_status"] for row in runs + sections + wells).items())),
        "quality_reason_counts": issue_counts,
        "split_counts": dict(sorted(Counter(row["split_assignment"] for row in wells).items())),
    }
    manifest = {
        "dataset_version": config.dataset_version,
        "generator_version": config.generator_version,
        "generation_run_id": run_id,
        "deterministic_seed": config.deterministic_seed,
        "generated_at_utc": config.generated_at_utc,
        "scenario": config.scenario,
        "is_synthetic": True,
        "contains_confidential_source_data": False,
        "release_status": "generated_unpublished",
        "source_control_status": "working_tree",
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
        "scope": (
            "Historical synthetic wells, sections, runs, and run-event comparative "
            "context plus a separate planning-only target artifact; no telemetry, "
            "recommendation logic, or prediction fields."
        ),
        "source_fingerprint": source_fingerprint(source_root),
        "source_fingerprint_inventory": {
            "artifact": SOURCE_FINGERPRINT_INVENTORY_FILENAME,
            "sha256": hashes[SOURCE_FINGERPRINT_INVENTORY_FILENAME],
        },
        "interval": {
            "start_date_inclusive": config.interval_start_date.isoformat(),
            "end_date_exclusive": config.interval_end_date.isoformat(),
            "years": config.interval_years,
        },
        "coordinate_reference": COORDINATE_FRAME,
        "spatial_clusters": SPATIAL_CLUSTERS,
        "proximity_caveat": COORDINATE_FRAME["proximity_caveat"],
        "reference_release": {
            "dataset_version": config.reference_dataset_version,
            "manifest_sha256": reference_manifest_sha256,
        },
        "historical_attribute_changes": {
            "reassigned_to_make_v1_1_clusters_coherent": [
                "basin_name",
                "field_name",
                "formation_name",
                "formation_name_raw",
            ],
            "preserved_from_v1_0_0": [
                "well_id",
                "well_name",
                "operator_name",
                "spud_date",
                "completion_date",
                "section_id",
                "run_id",
                "trajectory_profile",
                "depths",
                "footage",
                "duration",
                "bit_and_bha_attributes",
                "quality_issue_placements",
                "split_assignment",
            ],
            "v1_0_0_artifacts_mutated": False,
        },
        "planned_target_policy": {
            "record_kind": "PLANNED_TARGET",
            "historical_summary_includes_targets": False,
            "included_in_quality_issues": False,
            "included_in_split_assignments": False,
            "contains_realized_outcomes": False,
            "planned_target_count": len(planned_targets),
        },
        "row_counts": row_counts,
        "intentional_issue_counts": issue_counts,
        "summary": summary,
        "sha256": hashes,
    }
    (release_path / "release_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return ReleaseResult(release_path, row_counts, issue_counts, hashes)


def regenerate_release(
    config: GeneratorConfig,
    output_root: Path,
    *,
    source_root: Path | None = None,
) -> ReleaseResult:
    """Replace a release after staging and validation.

    Once the staged directory is promoted, cleanup errors are logged and the
    committed release is returned; a failed backup cleanup may leave an
    incomplete backup, so no rollback is attempted after promotion.
    """
    source_root = source_root or Path(__file__).resolve().parents[2]
    release_path = output_root / config.dataset_version
    if not release_path.is_dir():
        raise ValueError(f"Release does not exist for regeneration: {release_path}")

    staging_root = output_root / f".{config.dataset_version}.regeneration"
    backup_path = output_root / f".{config.dataset_version}.backup"
    if staging_root.exists() or backup_path.exists():
        raise ValueError(
            "Safe regeneration cannot start while staging or backup paths exist: "
            f"{staging_root}, {backup_path}"
        )

    staging_root.mkdir()
    try:
        shutil.copytree(
            output_root / HISTORICAL_REFERENCE_VERSION,
            staging_root / HISTORICAL_REFERENCE_VERSION,
        )
        staged_result = generate_release(
            config,
            staging_root,
            source_root=source_root,
        )
        from .validation import validate_release

        errors = validate_release(staged_result.release_path, source_root=source_root)
        if errors:
            raise ValueError("Staged release validation failed: " + "; ".join(errors))

        shutil.rmtree(staging_root / HISTORICAL_REFERENCE_VERSION)
        release_path.rename(backup_path)
        try:
            staged_result.release_path.rename(release_path)
        except Exception as promotion_error:
            try:
                backup_path.rename(release_path)
            except Exception as rollback_error:
                promotion_error.add_note(
                    "Promotion failed before commit and the original release could "
                    f"not be restored to {release_path}; its backup remains at "
                    f"{backup_path}: {rollback_error}"
                )
            raise
    except Exception as error:
        if staging_root.exists():
            try:
                shutil.rmtree(staging_root)
            except Exception as cleanup_error:
                error.add_note(
                    "Regeneration failed before promotion and generated staging "
                    f"could not be removed at {staging_root}: {cleanup_error}"
                )
        raise

    try:
        shutil.rmtree(backup_path)
    except Exception as cleanup_error:
        _LOGGER.warning(
            "Release promotion committed at %s, but backup cleanup failed at %s; "
            "the backup may be incomplete and no rollback was attempted: %s",
            release_path,
            backup_path,
            cleanup_error,
        )

    try:
        staging_root.rmdir()
    except Exception as cleanup_error:
        _LOGGER.warning(
            "Release promotion committed at %s, but generated staging cleanup "
            "failed at %s: %s",
            release_path,
            staging_root,
            cleanup_error,
        )

    return ReleaseResult(
        release_path,
        staged_result.row_counts,
        staged_result.issue_counts,
        staged_result.hashes,
    )
