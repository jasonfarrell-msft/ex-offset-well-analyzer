"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path
import re
from typing import Mapping


ISSUE_CODES = {
    "INCONSISTENT_FORMATION_LABEL",
    "MISSING_BIT_IADC_CODE",
    "MISSING_FORMATION",
    "NON_POSITIVE_DURATION",
}
SUPPORTED_COORDINATE_FRAME_ID = "SYN-LOCAL-FT-V1"


@dataclass(frozen=True)
class GeneratorConfig:
    dataset_version: str
    generator_version: str
    deterministic_seed: int
    generated_at_utc: str
    interval_start_date: date
    interval_years: int
    well_count: int
    scenario: str
    intentional_issue_counts: Mapping[str, int]
    spatial_frame_id: str | None = None
    planned_target_count: int = 0
    reference_dataset_version: str | None = None

    @property
    def interval_end_date(self) -> date:
        return self.interval_start_date.replace(
            year=self.interval_start_date.year + self.interval_years
        )

    @classmethod
    def load(cls, path: Path) -> "GeneratorConfig":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unable to read valid JSON config {path}: {exc}") from exc

        required = {
            "dataset_version",
            "generator_version",
            "deterministic_seed",
            "generated_at_utc",
            "interval_start_date",
            "interval_years",
            "well_count",
            "scenario",
            "intentional_issue_counts",
        }
        optional = {
            "spatial_frame_id",
            "planned_target_count",
            "reference_dataset_version",
        }
        missing = sorted(required - raw.keys())
        unknown = sorted(raw.keys() - required - optional)
        if missing or unknown:
            raise ValueError(f"Invalid config keys; missing={missing}, unknown={unknown}")

        try:
            start = date.fromisoformat(raw["interval_start_date"])
            generated = datetime.fromisoformat(
                raw["generated_at_utc"].replace("Z", "+00:00")
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid date or timestamp: {exc}") from exc

        if generated.tzinfo is None or generated.utcoffset() is None:
            raise ValueError("generated_at_utc must include a UTC offset")
        if not raw["generated_at_utc"].endswith("Z"):
            raise ValueError("generated_at_utc must use canonical UTC Z notation")
        if not isinstance(raw["deterministic_seed"], int):
            raise ValueError("deterministic_seed must be an integer")
        if raw["interval_years"] != 10:
            raise ValueError("interval_years must be exactly 10 for this milestone")
        if raw["well_count"] != 100:
            raise ValueError("well_count must be exactly 100 for this milestone")
        dataset_version = raw["dataset_version"]
        if (
            not isinstance(dataset_version, str)
            or dataset_version in {".", ".."}
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", dataset_version) is None
        ):
            raise ValueError(
                "dataset_version must be path-safe and contain only letters, "
                "numbers, dots, underscores, and hyphens"
            )
        if not raw["generator_version"]:
            raise ValueError("generator_version must be non-empty")
        if not raw["scenario"]:
            raise ValueError("scenario must be non-empty")

        issue_counts = raw["intentional_issue_counts"]
        if not isinstance(issue_counts, dict):
            raise ValueError("intentional_issue_counts must be an object")
        if set(issue_counts) != ISSUE_CODES:
            raise ValueError(
                "intentional_issue_counts must contain exactly: "
                + ", ".join(sorted(ISSUE_CODES))
            )
        if any(not isinstance(value, int) or value < 0 for value in issue_counts.values()):
            raise ValueError("intentional issue counts must be non-negative integers")

        spatial_frame_id = raw.get("spatial_frame_id")
        planned_target_count = raw.get("planned_target_count", 0)
        reference_dataset_version = raw.get("reference_dataset_version")
        if (
            not isinstance(planned_target_count, int)
            or isinstance(planned_target_count, bool)
            or not 0 <= planned_target_count <= 100
        ):
            raise ValueError("planned_target_count must be an integer from 0 to 100")
        if spatial_frame_id is None:
            if planned_target_count != 0 or reference_dataset_version is not None:
                raise ValueError(
                    "planned targets and a reference release require spatial_frame_id"
                )
        else:
            if spatial_frame_id != SUPPORTED_COORDINATE_FRAME_ID:
                raise ValueError(
                    f"spatial_frame_id must be {SUPPORTED_COORDINATE_FRAME_ID}"
                )
            if (
                not isinstance(planned_target_count, int)
                or isinstance(planned_target_count, bool)
                or not 1 <= planned_target_count <= 100
            ):
                raise ValueError("planned_target_count must be an integer from 1 to 100")
            if (
                not isinstance(reference_dataset_version, str)
                or re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9._-]*", reference_dataset_version
                )
                is None
                or reference_dataset_version == dataset_version
            ):
                raise ValueError(
                    "reference_dataset_version must be a distinct path-safe release ID"
                )

        return cls(
            dataset_version=raw["dataset_version"],
            generator_version=raw["generator_version"],
            deterministic_seed=raw["deterministic_seed"],
            generated_at_utc=raw["generated_at_utc"],
            interval_start_date=start,
            interval_years=raw["interval_years"],
            well_count=raw["well_count"],
            scenario=raw["scenario"],
            intentional_issue_counts=dict(sorted(issue_counts.items())),
            spatial_frame_id=spatial_frame_id,
            planned_target_count=planned_target_count,
            reference_dataset_version=reference_dataset_version,
        )

    def as_json_dict(self) -> dict:
        return {
            "dataset_version": self.dataset_version,
            "generator_version": self.generator_version,
            "deterministic_seed": self.deterministic_seed,
            "generated_at_utc": self.generated_at_utc,
            "interval_start_date": self.interval_start_date.isoformat(),
            "interval_years": self.interval_years,
            "well_count": self.well_count,
            "scenario": self.scenario,
            "intentional_issue_counts": dict(self.intentional_issue_counts),
            "spatial_frame_id": self.spatial_frame_id,
            "planned_target_count": self.planned_target_count,
            "reference_dataset_version": self.reference_dataset_version,
        }
