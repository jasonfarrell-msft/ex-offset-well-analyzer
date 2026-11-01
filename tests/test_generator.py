"""End-to-end validation for deterministic, versioned synthetic releases."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sys
import unittest
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from drillrun_synth.config import GeneratorConfig
from drillrun_synth.generator import (
    COORDINATE_FRAME,
    SOURCE_FINGERPRINT_INVENTORY_FILENAME,
    SOURCE_FINGERPRINT_PATHS,
    generate_release,
    source_fingerprint,
    source_fingerprint_inventory,
)
from drillrun_synth.validation import read_csv, sha256, validate_release


V1_REFERENCE_ARCHIVE_HASHES = {
    "data_dictionary.md": "912b9a919d4be6ba2ab95dac78bc69f66deec45aa34662cc6fb2413ac481cd26",
    "drilling_runs.csv": "499705406f4479196845eb57ebd360afaacaad83551e360243372d782e23d58e",
    "generator_config.json": "62020fd960e8c940cbed9a94be572e8acf113ea0602cf3224d1891bb2a61b944",
    "quality_issues.csv": "c71d0e7c9cfeac97f047e5988fa75fb780302783628101fbbcaa050f96f9ec75",
    "release_manifest.json": "f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9",
    "schema.json": "e269e8540d9513d7c45023d18e8ccb3e5ae52646239b46d1076956fdb58d6965",
    "sections.csv": "fd6e9e55ea79d2956437fc1384a580359f1379400789e88a55727b8b8f56679b",
    "source_fingerprint_inventory.json": "0474206f9b9a6400243b3542b5ea97d86ba2b78382f66bc3e56716a4c203c9f4",
    "split_assignments.csv": "cf2a3ee384c7a191c0f18f0af7ca5e3b7a70ba1a5534035d5c00c9a6179e4d41",
    "wells.csv": "4a71825bf6b99f33fa3fe8f9b5b571c08723d4d768a2d589a1059f2bfcb3c7f3",
}


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scratch = PROJECT_ROOT / ".test-artifacts"
        shutil.rmtree(cls.scratch, ignore_errors=True)
        cls.config_path = PROJECT_ROOT / "config" / "generator_config_v1.2.0.json"
        cls.config = GeneratorConfig.load(cls.config_path)
        cls.canonical_release = PROJECT_ROOT / "data" / "releases" / "v1.0.0"
        cls.reference_root_first = cls.scratch / "first"
        cls.reference_root_second = cls.scratch / "second"
        for root in (cls.reference_root_first, cls.reference_root_second):
            root.mkdir(parents=True)
            shutil.copytree(cls.canonical_release, root / "v1.0.0")
        cls.first = generate_release(
            cls.config, cls.reference_root_first, source_root=PROJECT_ROOT
        )
        cls.second = generate_release(
            cls.config, cls.reference_root_second, source_root=PROJECT_ROOT
        )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.scratch, ignore_errors=True)

    def test_release_validation(self) -> None:
        self.assertEqual(
            [],
            validate_release(self.first.release_path, source_root=PROJECT_ROOT),
        )

    def test_on_disk_v1_reference_archive_validation_and_recorded_hashes(self) -> None:
        self.assertTrue(self.canonical_release.is_dir())
        self.assertEqual(
            [],
            validate_release(self.canonical_release, source_root=PROJECT_ROOT),
        )
        actual_files = {
            path.name: sha256(path)
            for path in self.canonical_release.iterdir()
            if path.is_file()
        }
        self.assertEqual(V1_REFERENCE_ARCHIVE_HASHES, actual_files)

    def test_on_disk_v1_1_release_validation_and_manifest_hashes(self) -> None:
        release = PROJECT_ROOT / "data" / "releases" / "v1.1.0"
        self.assertTrue(release.is_dir())
        self.assertEqual([], validate_release(release, source_root=PROJECT_ROOT))
        manifest = json.loads(
            (release / "release_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual("v1.1.0", manifest["dataset_version"])
        self.assertEqual(12, manifest["row_counts"]["planned_targets.csv"])
        for filename, expected_hash in manifest["sha256"].items():
            self.assertEqual(expected_hash, sha256(release / filename), filename)

    def test_on_disk_v1_2_release_validation_and_manifest_hashes(self) -> None:
        release = PROJECT_ROOT / "data" / "releases" / "v1.2.0"
        self.assertTrue(release.is_dir())
        self.assertEqual([], validate_release(release, source_root=PROJECT_ROOT))
        manifest = json.loads(
            (release / "release_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual("v1.2.0", manifest["dataset_version"])
        self.assertEqual(12, manifest["row_counts"]["planned_targets.csv"])
        self.assertIn("run_events.csv", manifest["row_counts"])
        for filename, expected_hash in manifest["sha256"].items():
            self.assertEqual(expected_hash, sha256(release / filename), filename)

    def test_v1_historical_identity_and_outcomes_are_preserved(self) -> None:
        historical_wells = read_csv(self.canonical_release / "wells.csv")
        new_wells = read_csv(self.first.release_path / "wells.csv")
        historical_sections = read_csv(self.canonical_release / "sections.csv")
        new_sections = read_csv(self.first.release_path / "sections.csv")
        historical_runs = read_csv(self.canonical_release / "drilling_runs.csv")
        new_runs = read_csv(self.first.release_path / "drilling_runs.csv")

        well_outcomes = [
            "well_id",
            "well_name",
            "operator_name",
            "spud_date",
            "completion_date",
            "total_footage_ft",
            "total_duration_hours",
            "section_count",
            "run_count",
            "split_assignment",
        ]
        for old, new in zip(historical_wells, new_wells, strict=True):
            self.assertEqual(
                {key: old[key] for key in well_outcomes},
                {key: new[key] for key in well_outcomes},
            )

        section_outcomes = [
            "section_id",
            "well_id",
            "section_sequence",
            "hole_size_in",
            "start_md_ft",
            "end_md_ft",
            "footage_ft",
            "duration_hours",
            "trajectory_profile",
            "run_count",
        ]
        for old, new in zip(historical_sections, new_sections, strict=True):
            self.assertEqual(
                {key: old[key] for key in section_outcomes},
                {key: new[key] for key in section_outcomes},
            )

        changed_formation_and_provenance = {
            "formation_name",
            "formation_name_raw",
            "mud_weight_ppg",
            "mud_funnel_viscosity_sec",
            "dataset_version",
            "generator_version",
            "generation_run_id",
            "generated_at_utc",
            "scenario",
        }
        for old, new in zip(historical_runs, new_runs, strict=True):
            self.assertEqual(
                {key: value for key, value in old.items() if key not in changed_formation_and_provenance},
                {key: value for key, value in new.items() if key not in changed_formation_and_provenance},
            )

    def test_historical_counts_unique_keys_and_intentional_issues(self) -> None:
        wells = read_csv(self.first.release_path / "wells.csv")
        sections = read_csv(self.first.release_path / "sections.csv")
        runs = read_csv(self.first.release_path / "drilling_runs.csv")
        issues = read_csv(self.first.release_path / "quality_issues.csv")
        self.assertEqual(100, len(wells))
        self.assertEqual(len(wells), len({row["well_id"] for row in wells}))
        self.assertEqual(len(sections), len({row["section_id"] for row in sections}))
        self.assertEqual(len(runs), len({row["run_id"] for row in runs}))
        actual = Counter(row["reason_code"] for row in issues)
        self.assertEqual(dict(self.config.intentional_issue_counts), dict(actual))
        zero_duration_runs = [row for row in runs if row["duration_hours"] == "0.00"]
        self.assertEqual(
            self.config.intentional_issue_counts["NON_POSITIVE_DURATION"],
            len(zero_duration_runs),
        )
        self.assertTrue(all(row["quality_status"] == "ERROR" for row in zero_duration_runs))
        self.assertTrue(all(row["mud_weight_ppg"] for row in runs))
        self.assertTrue(all(row["mud_funnel_viscosity_sec"] for row in runs))

    def test_deterministic_release_locations_and_targets(self) -> None:
        first_files = sorted(path.name for path in self.first.release_path.iterdir())
        second_files = sorted(path.name for path in self.second.release_path.iterdir())
        self.assertEqual(first_files, second_files)
        for filename in first_files:
            self.assertEqual(
                sha256(self.first.release_path / filename),
                sha256(self.second.release_path / filename),
                filename,
            )

    def test_manifest_counts_hashes_and_current_source_fingerprint(self) -> None:
        manifest = json.loads(
            (self.first.release_path / "release_manifest.json").read_text(encoding="utf-8")
        )
        for filename, count in manifest["row_counts"].items():
            self.assertEqual(count, len(read_csv(self.first.release_path / filename)))
        for filename, expected_hash in manifest["sha256"].items():
            self.assertEqual(expected_hash, sha256(self.first.release_path / filename))
        self.assertEqual("generated_unpublished", manifest["release_status"])
        self.assertEqual("working_tree", manifest["source_control_status"])
        self.assertIsNone(manifest["git_commit"])
        self.assertEqual(source_fingerprint(PROJECT_ROOT), manifest["source_fingerprint"])
        self.assertEqual(
            sorted(SOURCE_FINGERPRINT_PATHS),
            manifest["source_fingerprint"]["included_paths"],
        )
        inventory_path = self.first.release_path / SOURCE_FINGERPRINT_INVENTORY_FILENAME
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        self.assertEqual(source_fingerprint_inventory(PROJECT_ROOT), inventory)
        self.assertEqual(manifest["source_fingerprint"], inventory["aggregate_source_fingerprint"])

    def test_schema_documents_all_csv_columns_and_local_frame(self) -> None:
        schema = json.loads(
            (self.first.release_path / "schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(COORDINATE_FRAME, schema["coordinate_reference"])
        for filename, table in schema["tables"].items():
            headers = set(read_csv(self.first.release_path / filename)[0])
            self.assertEqual(headers, set(table["fields"]), filename)

    def test_planned_targets_are_planning_only_and_reference_v1(self) -> None:
        targets = read_csv(self.first.release_path / "planned_targets.csv")
        wells = read_csv(self.first.release_path / "wells.csv")
        manifest = json.loads(
            (self.first.release_path / "release_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(12, len(targets))
        self.assertEqual([f"SYN-TARGET-{i:04d}" for i in range(1, 13)],
                         [row["target_id"] for row in targets])
        self.assertTrue(all(row["record_kind"] == "PLANNED_TARGET" for row in targets))
        self.assertTrue(all(row["is_synthetic"] == "true" for row in targets))
        self.assertTrue(
            {row["target_id"] for row in targets}.isdisjoint(
                {row["well_id"] for row in wells}
            )
        )
        self.assertTrue(
            all(
                row["reference_dataset_version"] == "v1.0.0"
                and row["reference_manifest_sha256"]
                == manifest["reference_release"]["manifest_sha256"]
                for row in targets
            )
        )
        self.assertTrue(
            all(
                row["planned_bit_type"] in {"", "PDC", "TRICONE", "HYBRID"}
                and row["planned_bha_type"] in {"", "ROTARY", "MOTOR", "RSS"}
                and row["planned_mud_type"]
                in {"", "WATER_BASED_SYNTHETIC", "OIL_BASED_SYNTHETIC"}
                for row in targets
            )
        )
        target_headers = set(targets[0])
        forbidden = {
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
        self.assertFalse(target_headers & forbidden)
        self.assertEqual(100, manifest["summary"]["well_count"])
        self.assertEqual(12, manifest["planned_target_policy"]["planned_target_count"])
        self.assertFalse(manifest["planned_target_policy"]["historical_summary_includes_targets"])
        self.assertFalse(manifest["planned_target_policy"]["included_in_quality_issues"])
        self.assertFalse(manifest["planned_target_policy"]["included_in_split_assignments"])

    def test_run_events_are_deterministic_and_release_scoped(self) -> None:
        runs = read_csv(self.first.release_path / "drilling_runs.csv")
        events = read_csv(self.first.release_path / "run_events.csv")
        self.assertGreater(len(events), 0)
        runs_by_id = {row["run_id"]: row for row in runs}
        zero_duration_run_ids = {
            row["run_id"] for row in runs if float(row["duration_hours"]) <= 0
        }
        event_keys = set()
        for event in events:
            self.assertIn(event["run_id"], runs_by_id)
            run = runs_by_id[event["run_id"]]
            self.assertEqual(run["well_id"], event["well_id"])
            self.assertEqual(run["section_id"], event["section_id"])
            self.assertNotIn(event["run_id"], zero_duration_run_ids)
            self.assertLessEqual(
                float(event["event_duration_hours"]),
                float(run["duration_hours"]),
            )
            self.assertIn(
                event["event_type"],
                {"LOSSES", "STUCK_PIPE", "VIBRATION", "NPT", "TRIP"},
            )
            subtype_by_type = {
                "LOSSES": {"SEEPAGE", "PARTIAL", "SEVERE"},
                "STUCK_PIPE": {"DIFFERENTIAL", "PACK_OFF", "KEYSEAT"},
                "VIBRATION": {"TORQUE", "LATERAL", "AXIAL"},
                "NPT": {"RIG_REPAIR", "WEATHER", "LOGISTICS"},
                "TRIP": {"BIT_CHANGE", "BHA_CHANGE", "CONNECTION"},
            }
            self.assertIn(event["event_subtype"], subtype_by_type[event["event_type"]])
            self.assertGreaterEqual(int(event["event_count"]), 1)
            self.assertGreaterEqual(float(event["event_duration_hours"]), 0)
            self.assertEqual(
                event["event_id"],
                str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        "synthetic-run-event:"
                        + f"{self.config.dataset_version}:{event['run_id']}:"
                        + f"{event['event_type']}:{event['event_subtype']}",
                    )
                ),
            )
            key = (event["run_id"], event["event_type"], event["event_subtype"])
            self.assertNotIn(key, event_keys)
            event_keys.add(key)

    def test_local_coordinates_units_bounds_and_proximity_limit(self) -> None:
        manifest = json.loads(
            (self.first.release_path / "release_manifest.json").read_text(encoding="utf-8")
        )
        schema = json.loads(
            (self.first.release_path / "schema.json").read_text(encoding="utf-8")
        )
        self.assertTrue(COORDINATE_FRAME["not_geographic_crs"])
        self.assertEqual("ft", COORDINATE_FRAME["units"])
        self.assertEqual(1, COORDINATE_FRAME["precision_ft"])
        caveat = COORDINATE_FRAME["proximity_caveat"]
        self.assertEqual(caveat, manifest["proximity_caveat"])
        self.assertIn(caveat, schema["interpretation_limits"])
        dictionary = (self.first.release_path / "data_dictionary.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("not latitude/longitude", dictionary)
        self.assertIn("not an EPSG coordinate reference system", dictionary)
        normalized_dictionary = " ".join(dictionary.split())
        self.assertIn("Surface proximity is a candidate filter", normalized_dictionary)
        self.assertIn(
            "does not establish subsurface proximity, stratigraphic equivalence, "
            "or geological similarity",
            normalized_dictionary,
        )

        locations = read_csv(self.first.release_path / "wells.csv")
        locations += read_csv(self.first.release_path / "planned_targets.csv")
        bounds = COORDINATE_FRAME["bounds_ft"]
        for row in locations:
            self.assertEqual(COORDINATE_FRAME["frame_id"], row["coordinate_frame_id"])
            self.assertEqual("SYNTHETIC_SURFACE_WELLHEAD", row["location_semantics"])
            x_ft, y_ft = int(row["surface_x_ft"]), int(row["surface_y_ft"])
            self.assertGreaterEqual(x_ft, bounds["x_min"])
            self.assertLessEqual(x_ft, bounds["x_max"])
            self.assertGreaterEqual(y_ft, bounds["y_min"])
            self.assertLessEqual(y_ft, bounds["y_max"])
            self.assertEqual(str(x_ft), row["surface_x_ft"])
            self.assertEqual(str(y_ft), row["surface_y_ft"])

    def test_target_count_does_not_shift_historical_generation(self) -> None:
        variant_root = self.scratch / "target-count-variant"
        variant_root.mkdir()
        shutil.copytree(self.canonical_release, variant_root / "v1.0.0")
        variant_config = replace(
            self.config,
            dataset_version="v1.1.0-target-count-test",
            planned_target_count=self.config.planned_target_count + 1,
        )
        variant = generate_release(variant_config, variant_root, source_root=PROJECT_ROOT)
        for filename in [
            "wells.csv",
            "sections.csv",
            "drilling_runs.csv",
            "run_events.csv",
            "quality_issues.csv",
        ]:
            first_rows = read_csv(self.first.release_path / filename)
            variant_rows = read_csv(variant.release_path / filename)
            ignored = {
                "dataset_version",
                "generator_version",
                "generation_run_id",
                "scenario",
            }
            if filename == "run_events.csv":
                ignored.add("event_id")
            self.assertEqual(
                [
                    {key: value for key, value in row.items() if key not in ignored}
                    for row in first_rows
                ],
                [
                    {key: value for key, value in row.items() if key not in ignored}
                    for row in variant_rows
                ],
                filename,
            )

    def test_immutable_versioning_and_invalid_configs_fail(self) -> None:
        with self.assertRaisesRegex(ValueError, "Immutable release already exists"):
            generate_release(self.config, self.reference_root_first)

        historical_config = GeneratorConfig.load(
            PROJECT_ROOT / "config" / "generator_config.json"
        )
        with self.assertRaisesRegex(ValueError, "archived v1.0.0 release is immutable"):
            generate_release(historical_config, self.scratch / "historical")

        bad = self.config.as_json_dict()
        bad["well_count"] = 99
        bad_path = self.scratch / "invalid_config.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "well_count must be exactly 100"):
            GeneratorConfig.load(bad_path)

        bad["well_count"] = 100
        bad["planned_target_count"] = 0
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "planned_target_count"):
            GeneratorConfig.load(bad_path)


if __name__ == "__main__":
    unittest.main()
