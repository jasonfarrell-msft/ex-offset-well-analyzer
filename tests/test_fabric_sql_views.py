"""Static checks for SQL endpoint active-release views."""

from __future__ import annotations

from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = PROJECT_ROOT / "fabric" / "sql" / "create_active_release_views.sql"
CONTRACT_PATH = PROJECT_ROOT / "docs" / "data-transformation-contract.md"

EXPECTED_VIEWS = {
    "raw.well",
    "raw.section",
    "raw.drilling_run",
    "raw.run_event",
    "raw.quality_issue",
    "raw.split_assignment",
    "raw.rejected_record",
    "curated.well",
    "curated.section",
    "curated.drilling_run",
    "curated.run_event",
    "curated.drilling_run_quarantine",
    "curated.quality_issue",
    "curated.split_assignment",
    "curated.rejected_record",
    "serving.well_summary",
    "serving.dataset_summary",
    "serving.quality_summary",
    "serving.category_summary",
    "serving.offset_run_config_summary",
    "serving.offset_run_event_summary",
    "serving.planned_target_summary",
    "serving.offset_section_summary",
    "serving.offset_run_config_summary_release",
    "serving.offset_run_event_summary_release",
    "serving.planned_target_summary_release",
    "serving.offset_section_summary_release",
}

RELEASE_ADDRESSABLE_VIEWS = {
    "serving.offset_run_config_summary_release",
    "serving.offset_run_event_summary_release",
    "serving.planned_target_summary_release",
    "serving.offset_section_summary_release",
}

PROVENANCE_COLUMNS = (
    "_source_file",
    "_source_file_sha256",
    "_source_row_number",
    "_source_path",
    "_record_hash",
    "_transformation_contract_version",
    "_processed_at_utc",
)
WELL_COLUMNS = (
    "well_id", "well_name", "operator_name", "basin_name", "field_name",
    "spud_date", "completion_date", "total_footage_ft",
    "total_duration_hours", "section_count", "run_count", "split_assignment",
    "is_synthetic", "dataset_version", "generator_version",
    "generation_run_id", "deterministic_seed", "generated_at_utc", "scenario",
    "quality_status", "quality_reason_codes",
) + PROVENANCE_COLUMNS
SECTION_COLUMNS = (
    "section_id", "well_id", "section_sequence", "hole_size_in",
    "start_md_ft", "end_md_ft", "footage_ft", "duration_hours",
    "formation_name", "formation_name_raw", "trajectory_profile", "run_count",
    "is_synthetic", "dataset_version", "generator_version",
    "generation_run_id", "deterministic_seed", "generated_at_utc", "scenario",
    "quality_status", "quality_reason_codes",
) + PROVENANCE_COLUMNS
DRILLING_RUN_COLUMNS = (
    "run_id", "well_id", "section_id", "run_sequence_in_section",
    "start_time_utc", "end_time_utc", "start_md_ft", "end_md_ft",
    "footage_ft", "duration_hours", "formation_name", "formation_name_raw",
    "bit_type", "bit_size_in", "bit_iadc_code", "bha_type", "mud_type",
    "mud_weight_ppg", "mud_funnel_viscosity_sec",
    "is_synthetic", "dataset_version", "generator_version",
    "generation_run_id", "deterministic_seed", "generated_at_utc", "scenario",
    "quality_status", "quality_reason_codes",
) + PROVENANCE_COLUMNS
RUN_EVENT_COLUMNS = (
    "run_id", "well_id", "section_id", "event_type", "event_subtype",
    "event_count", "event_duration_hours", "is_synthetic", "dataset_version",
    "generator_version", "generation_run_id", "deterministic_seed",
    "generated_at_utc", "scenario", "quality_status", "quality_reason_codes",
) + PROVENANCE_COLUMNS
QUALITY_ISSUE_COLUMNS = (
    "quality_issue_id", "entity_type", "entity_id", "well_id", "section_id",
    "run_id", "reason_code", "severity", "field_name", "observed_value",
    "expected_constraint", "handling", "is_synthetic", "dataset_version",
    "generator_version", "generation_run_id", "deterministic_seed",
    "generated_at_utc", "scenario", "quality_status", "quality_reason_codes",
) + PROVENANCE_COLUMNS
SPLIT_ASSIGNMENT_COLUMNS = (
    "well_id", "split_assignment", "assignment_basis", "is_synthetic",
    "dataset_version", "generator_version", "generation_run_id",
    "deterministic_seed", "generated_at_utc", "scenario", "quality_status",
    "quality_reason_codes",
) + PROVENANCE_COLUMNS
REJECTED_COLUMNS = (
    "dataset_version", "source_file", "source_row_number", "raw_payload",
    "rejection_stage", "rejection_reason_code", "rejection_detail",
    "_source_file_sha256", "_source_path", "_record_hash",
    "_transformation_contract_version", "_processed_at_utc",
)
EXPECTED_COLUMNS = {
    "raw.well": WELL_COLUMNS,
    "raw.section": SECTION_COLUMNS,
    "raw.drilling_run": DRILLING_RUN_COLUMNS,
    "raw.run_event": RUN_EVENT_COLUMNS,
    "raw.quality_issue": QUALITY_ISSUE_COLUMNS,
    "raw.split_assignment": SPLIT_ASSIGNMENT_COLUMNS,
    "raw.rejected_record": REJECTED_COLUMNS,
    "curated.well": WELL_COLUMNS,
    "curated.section": SECTION_COLUMNS,
    "curated.drilling_run": DRILLING_RUN_COLUMNS,
    "curated.run_event": RUN_EVENT_COLUMNS,
    "curated.drilling_run_quarantine": DRILLING_RUN_COLUMNS
    + ("quarantine_reason_code", "quality_issue_id"),
    "curated.quality_issue": QUALITY_ISSUE_COLUMNS,
    "curated.split_assignment": SPLIT_ASSIGNMENT_COLUMNS,
    "curated.rejected_record": REJECTED_COLUMNS + ("curation_disposition",),
    "serving.well_summary": (
        "dataset_version", "generator_version", "generation_run_id", "scenario",
        "deterministic_seed", "is_synthetic", "well_id", "well_name",
        "operator_name", "basin_name", "field_name", "spud_date",
        "completion_date", "split_assignment", "section_count",
        "source_run_count", "accepted_run_count", "quarantined_run_count",
        "warning_section_count", "warning_run_count", "error_run_count",
        "issue_count", "source_total_footage_ft", "accepted_footage_ft",
        "quarantined_footage_ft", "source_total_duration_hours",
        "accepted_duration_hours", "quarantined_duration_hours",
        "first_run_start_time_utc", "last_run_end_time_utc",
        "has_quality_warning", "has_quarantined_run",
        "_transformation_contract_version",
    ),
    "serving.dataset_summary": (
        "dataset_version", "generator_version", "generation_run_id", "scenario",
        "deterministic_seed", "is_synthetic", "well_count", "section_count",
        "source_run_count", "accepted_run_count", "quarantined_run_count",
        "rejected_record_count", "quality_issue_count", "warning_issue_count",
        "error_issue_count", "source_total_footage_ft", "accepted_footage_ft",
        "quarantined_footage_ft", "source_total_duration_hours",
        "accepted_duration_hours", "quarantined_duration_hours",
        "manifest_sha256", "_transformation_contract_version",
    ),
    "serving.quality_summary": (
        "dataset_version", "generation_run_id", "scenario", "is_synthetic",
        "reason_code", "severity", "issue_count", "affected_well_count",
        "affected_section_count", "affected_run_count", "handling_text",
        "_transformation_contract_version",
    ),
    "serving.category_summary": (
        "dataset_version", "generation_run_id", "scenario", "is_synthetic",
        "category_name", "category_value", "record_count",
        "_transformation_contract_version",
    ),
    "serving.offset_run_config_summary": (
        "_release_id", "dataset_version", "generator_version", "generation_run_id", "scenario",
        "deterministic_seed", "is_synthetic", "target_id", "target_name",
        "well_id", "well_name", "bit_type", "bha_type", "mud_type",
        "mud_weight_ppg", "mud_funnel_viscosity_sec", "accepted_run_count",
        "accepted_footage_ft", "accepted_duration_hours",
        "_transformation_contract_version",
    ),
    "serving.offset_run_event_summary": (
        "_release_id", "dataset_version", "generator_version", "generation_run_id", "scenario",
        "deterministic_seed", "is_synthetic", "target_id", "target_name",
        "well_id", "well_name", "section_id", "run_id", "event_type",
        "event_subtype", "event_count", "event_duration_hours",
        "_transformation_contract_version",
    ),
    "serving.planned_target_summary": (
        "_release_id", "dataset_version", "generator_version", "generation_run_id", "scenario",
        "deterministic_seed", "is_synthetic", "target_id", "record_kind",
        "target_name", "basin_name", "field_name",
        "expected_formation_name", "planned_trajectory_profile",
        "planned_hole_size_in", "planned_md_min_ft", "planned_md_max_ft",
        "planned_bit_type", "planned_bha_type", "planned_mud_type",
        "coordinate_frame_id", "location_semantics", "coordinate_units", "surface_x_ft",
        "surface_y_ft", "reference_dataset_version",
        "reference_manifest_sha256", "_transformation_contract_version",
    ),
    "serving.offset_section_summary": (
        "_release_id", "dataset_version", "generator_version", "generation_run_id", "scenario",
        "deterministic_seed", "is_synthetic", "target_id", "target_name",
        "target_basin_name", "target_field_name",
        "basin_name", "field_name", "expected_formation_name",
        "planned_hole_size_in", "planned_md_min_ft", "planned_md_max_ft",
        "planned_trajectory_profile", "coordinate_frame_id",
        "location_semantics", "coordinate_units", "target_surface_x_ft", "target_surface_y_ft",
        "surface_x_ft", "surface_y_ft",
        "well_id", "well_name", "operator_name", "well_basin_name",
        "well_field_name", "well_surface_x_ft", "well_surface_y_ft",
        "section_id", "section_sequence", "formation_name",
        "hole_size_in", "start_md_ft", "end_md_ft",
        "trajectory_profile", "source_run_count", "accepted_run_count",
        "quarantined_run_count", "warning_run_count", "error_run_count",
        "warning_section_count", "warning_issue_count", "error_issue_count", "accepted_footage_ft",
        "accepted_duration_hours", "distance_squared_ft2",
        "_transformation_contract_version",
    ),
    "serving.offset_run_config_summary_release": (
        "_release_id", "dataset_version", "generator_version", "generation_run_id", "scenario",
        "deterministic_seed", "is_synthetic", "target_id", "target_name",
        "well_id", "well_name", "bit_type", "bha_type", "mud_type",
        "mud_weight_ppg", "mud_funnel_viscosity_sec", "accepted_run_count",
        "accepted_footage_ft", "accepted_duration_hours",
        "_transformation_contract_version",
    ),
    "serving.offset_run_event_summary_release": (
        "_release_id", "dataset_version", "generator_version", "generation_run_id", "scenario",
        "deterministic_seed", "is_synthetic", "target_id", "target_name",
        "well_id", "well_name", "section_id", "run_id", "event_type",
        "event_subtype", "event_count", "event_duration_hours",
        "_transformation_contract_version",
    ),
    "serving.planned_target_summary_release": (
        "_release_id", "dataset_version", "generator_version", "generation_run_id", "scenario",
        "deterministic_seed", "is_synthetic", "target_id", "record_kind",
        "target_name", "basin_name", "field_name",
        "expected_formation_name", "planned_trajectory_profile",
        "planned_hole_size_in", "planned_md_min_ft", "planned_md_max_ft",
        "planned_bit_type", "planned_bha_type", "planned_mud_type",
        "coordinate_frame_id", "location_semantics", "coordinate_units", "surface_x_ft",
        "surface_y_ft", "reference_dataset_version",
        "reference_manifest_sha256", "_transformation_contract_version",
    ),
    "serving.offset_section_summary_release": (
        "_release_id", "dataset_version", "generator_version", "generation_run_id", "scenario",
        "deterministic_seed", "is_synthetic", "target_id", "target_name",
        "target_basin_name", "target_field_name",
        "basin_name", "field_name", "expected_formation_name",
        "planned_hole_size_in", "planned_md_min_ft", "planned_md_max_ft",
        "planned_trajectory_profile", "coordinate_frame_id",
        "location_semantics", "coordinate_units", "target_surface_x_ft", "target_surface_y_ft",
        "surface_x_ft", "surface_y_ft",
        "well_id", "well_name", "operator_name", "well_basin_name",
        "well_field_name", "well_surface_x_ft", "well_surface_y_ft",
        "section_id", "section_sequence", "formation_name",
        "hole_size_in", "start_md_ft", "end_md_ft",
        "trajectory_profile", "source_run_count", "accepted_run_count",
        "quarantined_run_count", "warning_run_count", "error_run_count",
        "warning_section_count", "warning_issue_count", "error_issue_count", "accepted_footage_ft",
        "accepted_duration_hours", "distance_squared_ft2",
        "_transformation_contract_version",
    ),
}

VIEW_PATTERN = re.compile(
    r"CREATE\s+OR\s+ALTER\s+VIEW\s+\[(?P<schema>\w+)\]\.\[(?P<view>\w+)\]"
    r"\s+AS\s+(?P<body>.*?)\s*;\s*GO",
    re.IGNORECASE | re.DOTALL,
)


class FabricSqlViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = SQL_PATH.read_text(encoding="utf-8")
        cls.contract = CONTRACT_PATH.read_text(encoding="utf-8")
        cls.views = {
            f"{match.group('schema')}.{match.group('view')}": match.group("body")
            for match in VIEW_PATTERN.finditer(cls.sql)
        }

    def test_expected_public_view_inventory_is_complete(self) -> None:
        self.assertEqual(EXPECTED_VIEWS, set(self.views))

    def test_every_view_has_release_state_and_staged_row_gates(self) -> None:
        for name, body in self.views.items():
            with self.subTest(view=name):
                self.assertIn("[control].[dataset_release_registry]", body)
                self.assertIn("r.[release_state] = N'READY'", body)
                self.assertIn("d.[_publication_state] = N'STAGED'", body)

    def test_active_views_remain_pointer_gated(self) -> None:
        for name, body in self.views.items():
            if name in RELEASE_ADDRESSABLE_VIEWS:
                continue
            with self.subTest(view=name):
                self.assertIn("[control].[dataset_release_pointer]", body)
                self.assertIn("p.[dataset_name] = N'drill_run_history'", body)
                self.assertIn("p.[active_release_id] = d.[_release_id]", body)
                self.assertIn("r.[release_id] = p.[active_release_id]", body)

    def test_release_views_are_ready_gated_without_pointer_dependency(self) -> None:
        for name in RELEASE_ADDRESSABLE_VIEWS:
            body = self.views[name]
            with self.subTest(view=name):
                self.assertNotIn("[control].[dataset_release_pointer]", body)
                self.assertIn("r.[dataset_name] = N'drill_run_history'", body)
                self.assertIn("r.[release_id] = d.[_release_id]", body)

    def test_views_enumerate_contract_columns(self) -> None:
        for name, body in self.views.items():
            with self.subTest(view=name):
                select_clause = body.split("FROM", 1)[0]
                self.assertNotRegex(select_clause, r"(?i)SELECT\s+(?:\w+\.)?\*")
                actual_columns = []
                for raw_line in select_clause.splitlines():
                    line = raw_line.strip().rstrip(",")
                    if not line or line.upper() == "SELECT":
                        continue
                    alias = re.search(
                        r"(?i)\bAS\s+\[([A-Za-z_][A-Za-z0-9_]*)\]\s*$",
                        line,
                    )
                    if alias:
                        actual_columns.append(alias.group(1))
                        continue
                    direct = re.search(
                        r"d\.\[([A-Za-z_][A-Za-z0-9_]*)\]\s*$",
                        line,
                    )
                    if direct:
                        actual_columns.append(direct.group(1))
                self.assertEqual(EXPECTED_COLUMNS[name], tuple(actual_columns))

    def test_physical_tables_are_dependencies_not_public_contract_names(self) -> None:
        for name, body in self.views.items():
            schema, view = name.split(".", 1)
            with self.subTest(view=name):
                self.assertFalse(view.startswith("__"))
                physical_view_name = (
                    view.removesuffix("_release")
                    if view in {entry.split(".", 1)[1] for entry in RELEASE_ADDRESSABLE_VIEWS}
                    else view
                )
                expected_source = f"FROM [{schema}].[__{physical_view_name}_release_data] AS d"
                self.assertIn(expected_source, body)
        self.assertNotRegex(
            self.sql,
            r"(?i)CREATE\s+OR\s+ALTER\s+VIEW\s+\[\w+\]\.\[__",
        )

    def test_verification_is_read_only_and_contains_key_counts(self) -> None:
        verification = self.sql.split(
            "/* Read-only deployment verification: view inventory. */",
            1,
        )[1]
        for keyword in ("INSERT", "UPDATE", "DELETE", "MERGE", "TRUNCATE", "DROP"):
            self.assertNotRegex(verification, rf"(?i)\b{keyword}\b")
        for fragment in (
            "SELECT N'raw.drilling_run', CAST(937 AS BIGINT)",
            "SELECT N'raw.run_event', CAST(0 AS BIGINT)",
            "SELECT N'curated.drilling_run', CAST(932 AS BIGINT)",
            "SELECT N'curated.run_event', CAST(0 AS BIGINT)",
            "SELECT N'curated.drilling_run_quarantine', CAST(5 AS BIGINT)",
            "SELECT N'serving.dataset_summary', CAST(1 AS BIGINT)",
            "SELECT N'serving.category_summary', CAST(19 AS BIGINT)",
            "SELECT N'serving.offset_run_config_summary', CAST(0 AS BIGINT)",
            "SELECT N'serving.offset_run_event_summary', CAST(0 AS BIGINT)",
            "SELECT N'serving.planned_target_summary', CAST(12 AS BIGINT)",
            "SELECT N'serving.offset_section_summary', CAST(3288 AS BIGINT)",
            "N'NOT_APPLICABLE_TO_ACTIVE_RELEASE'",
        ):
            self.assertIn(fragment, verification)

    def test_offset_section_summary_generic_coordinates_are_well_coordinates(self) -> None:
        body = self.views["serving.offset_section_summary"]
        self.assertIn("d.[well_basin_name] AS [basin_name]", body)
        self.assertIn("d.[well_field_name] AS [field_name]", body)
        self.assertIn("d.[well_surface_x_ft] AS [surface_x_ft]", body)
        self.assertIn("d.[well_surface_y_ft] AS [surface_y_ft]", body)
        self.assertIn("d.[target_surface_x_ft] AS [target_surface_x_ft]", body)
        self.assertIn("d.[target_surface_y_ft] AS [target_surface_y_ft]", body)
        self.assertNotIn("d.[target_surface_x_ft] AS [surface_x_ft]", body)
        self.assertNotIn("d.[target_surface_y_ft] AS [surface_y_ft]", body)

    def test_sql_contains_no_prohibited_analytical_terms(self) -> None:
        lowered = self.sql.lower()
        prohibited = ("pred" + "iction", "simil" + "arity", "fore" + "cast")
        for term in prohibited:
            self.assertNotIn(term, lowered)

    def test_contract_declares_sql_endpoint_consumer_boundary(self) -> None:
        normalized_contract = " ".join(self.contract.split())
        for fragment in (
            "SQL analytics endpoint views are the semantic and Data Agent serving boundary",
            "Spark logical views alone are not sufficient",
            "`fabric/sql/create_active_release_views.sql`",
        ):
            self.assertIn(fragment, normalized_contract)


if __name__ == "__main__":
    unittest.main()
