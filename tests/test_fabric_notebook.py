"""Static checks for the tracked Fabric transformation notebook."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_ROOT = (
    PROJECT_ROOT / "fabric" / "nb_10_build_drillrun_summary.Notebook"
)
PLATFORM_PATH = NOTEBOOK_ROOT / ".platform"
NOTEBOOK_PATH = NOTEBOOK_ROOT / "notebook-content.ipynb"


class FabricNotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.platform = json.loads(PLATFORM_PATH.read_text(encoding="utf-8"))
        cls.notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
        cls.source = "\n".join(
            "".join(cell.get("source", []))
            for cell in cls.notebook["cells"]
        )
        cls.publication_source = "".join(cls.notebook["cells"][-1]["source"])

    def test_valid_fabric_notebook_metadata(self) -> None:
        self.assertEqual("Notebook", self.platform["metadata"]["type"])
        self.assertEqual(
            "nb_10_build_drillrun_summary",
            self.platform["metadata"]["displayName"],
        )
        lakehouse = self.notebook["metadata"]["dependencies"]["lakehouse"]
        self.assertEqual(
            "4e1977a8-d7ff-487e-b42d-c4b3bc118f3d",
            lakehouse["default_lakehouse_workspace_id"],
        )
        self.assertEqual(
            "964afbf5-6a33-46dc-98c1-be726d0f4999",
            lakehouse["default_lakehouse"],
        )
        self.assertEqual(
            "lh_drillrun_summary",
            lakehouse["default_lakehouse_name"],
        )
        self.assertEqual("synapse_pyspark", self.notebook["metadata"]["kernel_info"]["name"])

    def test_authorized_release_source_paths_are_allowlisted(self) -> None:
        self.assertIn('RELEASE_PROFILES = {', self.source)
        self.assertIn('"v1.1.0": {', self.source)
        self.assertIn('"v1.2.0": {', self.source)
        self.assertIn('"source_root": "Files/landing/synthetic/drill_run/v1.1.0"', self.source)
        self.assertIn('"source_root": "Files/landing/synthetic/drill_run/v1.2.0"', self.source)
        self.assertIn('SOURCE_ROOT = RELEASE_PROFILE["source_root"]', self.source)
        self.assertNotIn("latest", self.source.lower())

    def test_fabric_csv_parsing_uses_spark_compatible_paths_and_schema(self) -> None:
        self.assertIn(
            "spark.sparkContext.textFile(source_path)",
            self.source,
        )
        self.assertNotIn(
            "spark.sparkContext.textFile(physical_path)",
            self.source,
        )
        self.assertIn(
            "parse_schema.simpleString()",
            self.source,
        )
        self.assertNotIn(
            'F.from_csv(\n            "raw_payload",\n            parse_schema,',
            self.source,
        )

    def test_trailing_blank_quality_codes_are_normalized_after_csv_parsing(self) -> None:
        self.assertIn(
            'if name == "quality_reason_codes":\n'
            '        return F.coalesce(value, F.lit(""))',
            self.source,
        )
        self.assertEqual(2, self.source.count("parsed_value(name)"))
        self.assertIn(
            "original = parsed_value(name)",
            self.source,
        )
        self.assertIn(
            "typed_value(parsed_value(name), data_type, nullable).alias(name)",
            self.source,
        )

    def test_well_summary_disambiguates_source_and_derived_section_counts(self) -> None:
        self.assertIn(
            'F.count("*").cast("int").alias("curated_section_count")',
            self.source,
        )
        self.assertIn(
            'F.col("curated_section_count").alias("section_count")',
            self.source,
        )

    def test_required_tables_are_declared(self) -> None:
        required = {
            "raw.well", "raw.section", "raw.drilling_run", "raw.quality_issue",
            "raw.split_assignment", "raw.rejected_record", "curated.well",
            "curated.section", "curated.drilling_run",
            "curated.drilling_run_quarantine", "curated.quality_issue",
            "curated.split_assignment", "curated.rejected_record",
            "serving.well_summary", "serving.dataset_summary",
            "serving.quality_summary", "serving.category_summary",
            "serving.planned_target_summary", "serving.offset_section_summary",
        }
        for table in required:
            self.assertIn(f'"{table}"', self.source)

    def test_contract_counts_and_failure_gates_are_present(self) -> None:
        required_fragments = [
            '"drilling_runs.csv": 937',
            '"run_events.csv": 927',
            "require_count(curated_run, 932",
            "require_count(curated_run_quarantine, 5",
            "require_count(curated_rejected, 0",
            "SOURCE_HASH_MISMATCH",
            "SOURCE_ROW_COUNT_MISMATCH",
            "RELATIONSHIP_VIOLATION",
            "RECONCILIATION_FAILED",
            "PUBLICATION_FAILED_LOCK_RETAINED",
            "ACTIVE_VIEW_CONTENT_HASH_MISMATCH",
            "reconciliation_result",
        ]
        for fragment in required_fragments:
            self.assertIn(fragment, self.source)

    def test_release_data_is_staged_in_internal_tables_not_directly_published(self) -> None:
        self.assertIn('LOGICAL_TABLES = {', self.publication_source)
        self.assertIn('return f"{schema_name}.__{table_name}_release_data"', self.publication_source)
        self.assertIn('F.lit(STAGED_ROW_STATE)', self.publication_source)
        self.assertIn('writer.saveAsTable(physical_table_name)', self.publication_source)
        self.assertNotIn("def publish_release", self.source)
        self.assertNotIn("RESTORE TABLE", self.source)
        self.assertNotIn("PUBLICATION_ROLLED_BACK", self.source)
        self.assertNotIn('saveAsTable("raw.', self.source)
        self.assertNotIn('saveAsTable("curated.', self.source)
        self.assertNotIn('saveAsTable("serving.', self.source)

    def test_inactive_registry_state_precedes_all_release_data_writes(self) -> None:
        staging_merge = self.publication_source.index(
            "MERGE INTO {RELEASE_REGISTRY_TABLE} target"
        )
        staging_assertion = self.publication_source.index(
            "RELEASE_NOT_INACTIVE_BEFORE_WRITES"
        )
        first_release_write = self.publication_source.index(
            "writer.saveAsTable(physical_table_name)"
        )
        self.assertLess(staging_merge, staging_assertion)
        self.assertLess(staging_assertion, first_release_write)
        self.assertIn("release_state = source.release_state", self.publication_source)
        self.assertIn("WHEN MATCHED THEN UPDATE SET", self.publication_source)

    def test_reconciliation_precedes_single_atomic_pointer_activation(self) -> None:
        reconciliation = self.publication_source.index(
            "RECONCILIATION_COMPLETE_BEFORE_ACTIVATION = True"
        )
        ready_gate = self.publication_source.index("RELEASE_NOT_READY_AFTER_EVIDENCE")
        activation = self.publication_source.index(
            "MERGE INTO {ACTIVE_RELEASE_POINTER_TABLE} target"
        )
        self.assertLess(reconciliation, ready_gate)
        self.assertLess(ready_gate, activation)
        self.assertEqual(
            1,
            self.publication_source.count(
                "MERGE INTO {ACTIVE_RELEASE_POINTER_TABLE} target"
            ),
        )
        self.assertIn(
            "This is the only activation boundary",
            self.publication_source,
        )

    def test_consumers_resolve_only_the_active_ready_release(self) -> None:
        for fragment in [
            "CREATE OR REPLACE VIEW {logical_table_name}",
            "INNER JOIN {ACTIVE_RELEASE_POINTER_TABLE} p",
            "p.active_release_id = d._release_id",
            "INNER JOIN {RELEASE_REGISTRY_TABLE} r",
            "r.release_state = '{READY_STATE}'",
            "WHERE d._publication_state = '{STAGED_ROW_STATE}'",
        ]:
            self.assertIn(fragment, self.publication_source)
        self.assertNotIn("_release_id`", self.publication_source)

    def test_active_rerun_verifies_without_rewriting_release_rows(self) -> None:
        for fragment in [
            "DEFAULT_ACTIVATE_RELEASE_POINTER = True",
            'globals().get("ACTIVATE_RELEASE_POINTER", DEFAULT_ACTIVATE_RELEASE_POINTER)',
            "INVALID_ACTIVATE_RELEASE_POINTER_PARAMETER",
            "release_already_active = active_release_id == RELEASE_ID",
            "if not release_already_active:",
            "DELETE FROM {physical_table_name} WHERE _release_id",
            "else:",
            "ACTIVE_RELEASE_CONTENT_HASH_MISMATCH",
            "ACTIVATION_POINTER_MISMATCH",
            "ACTIVE_RELEASE_LOCK_CLEANUP_REQUIRED",
        ]:
            self.assertIn(fragment, self.publication_source)
        cleanup = self.publication_source.index(
            "DELETE FROM {physical_table_name} WHERE _release_id"
        )
        write = self.publication_source.index(
            "writer.saveAsTable(physical_table_name)"
        )
        self.assertLess(cleanup, write)

    def test_notebook_parameters_cell_defaults_pointer_activation(self) -> None:
        parameter_cells = [
            cell
            for cell in self.notebook["cells"]
            if "parameters" in cell.get("metadata", {}).get("tags", [])
        ]
        self.assertEqual(1, len(parameter_cells))
        parameter_source = "".join(parameter_cells[0].get("source", []))
        self.assertIn('RELEASE_VERSION = "v1.2.0"', parameter_source)
        self.assertIn("ACTIVATE_RELEASE_POINTER = True", parameter_source)
        self.assertIn("CONTROL_ONLY_PROMOTION = True", parameter_source)
        self.assertIn("RECOVERY_MODE = False", parameter_source)
        self.assertIn('RECOVERY_OPERATOR = ""', parameter_source)
        self.assertIn('RECOVERY_REASON = ""', parameter_source)
        self.assertIn('RECOVERY_EXPECTED_DATASET_NAME = ""', parameter_source)
        self.assertIn('RECOVERY_EXPECTED_RELEASE_ID = ""', parameter_source)
        self.assertIn('RECOVERY_EXPECTED_ATTEMPT_ID = ""', parameter_source)
        self.assertIn('RECOVERY_EXPECTED_APPLICATION_ID = ""', parameter_source)
        self.assertIn('RECOVERY_EXPECTED_JOB_INSTANCE_ID = ""', parameter_source)
        self.assertIn('RECOVERY_EXPECTED_JOB_RESPONSE_JSON = ""', parameter_source)

    def test_publication_cell_reads_recovery_inputs_from_runtime_parameters(self) -> None:
        self.assertIn(
            'raw_recovery_mode = globals().get("RECOVERY_MODE", DEFAULT_RECOVERY_MODE)',
            self.publication_source,
        )
        self.assertIn(
            'RECOVERY_EXPECTED_JOB_RESPONSE_JSON = optional_recovery_parameter("RECOVERY_EXPECTED_JOB_RESPONSE_JSON")',
            self.publication_source,
        )
        self.assertNotIn("\nRECOVERY_MODE = False\n", self.publication_source)

    def test_release_profile_identity_mapping_is_explicit(self) -> None:
        for fragment in [
            '"manifest_sha256": "904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d"',
            '"source_inventory_sha256": "e50b76b80d6229a7f26bb719a6c937ac83e94762aeb056f3341de8b5014d6dd0"',
            '"aggregate_source_sha256": "197d65dd19ff59c6ba9ab93fdb1f5cce7020836bec9f6e80550ff07a328b893f"',
            '"manifest_sha256": "6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0"',
            '"source_inventory_sha256": "6d41ceaadd69c35fb558c00c87c3b6c7a9ce3efe614e4ffd16ad4a7787c62ddc"',
            '"aggregate_source_sha256": "8c1164c27b41b1fe3a359185a4992a2bf02737083b753e1dc3d30d7a8cb12826"',
            '"include_run_events": False',
            '"expected_release_table_rows": {',
            '"serving.__offset_run_config_summary_release_data": 11184',
            '"serving.__offset_run_event_summary_release_data": 11124',
            '"planned_target_non_null_minimums": {',
            '"planned_bit_type": 1',
            '"planned_bha_type": 1',
            '"planned_mud_type": 1',
            '"include_run_events": True',
            'if INCLUDE_RUN_EVENTS:',
            'SOURCE_DEFINITIONS["run_events.csv"] = RUN_EVENT_FIELDS',
            'raw_run_event = raw_frames.get("run_events.csv")',
            'RUN_EVENTS_REQUIRED_BY_RELEASE',
            'RUN_EVENTS_UNEXPECTED_FOR_RELEASE',
        ]:
            self.assertIn(fragment, self.source)

    def test_v12_schema_includes_extended_run_and_target_columns(self) -> None:
        required_fragments = [
            '"v1.2.0": {',
            '"contract_version": "1.2.0"',
            '("mud_weight_ppg", DECIMAL, False), ("mud_funnel_viscosity_sec", DECIMAL, False)',
            '("planned_bit_type", STRING, True), ("planned_bha_type", STRING, True)',
            '("planned_mud_type", STRING, True),',
            '"planned_bit_type", "planned_bha_type", "planned_mud_type",',
            '"raw.run_event": raw_event,',
            '"curated.run_event": curated_event,',
            '"serving.offset_run_config_summary": offset_run_config_summary,',
            '"serving.offset_run_event_summary": offset_run_event_summary,',
        ]
        for fragment in required_fragments:
            self.assertIn(fragment, self.source)

    def test_run_event_fallback_schema_reuses_run_event_fields(self) -> None:
        code_source = "\n".join(
            "".join(cell.get("source", []))
            for cell in self.notebook["cells"]
            if cell.get("cell_type") == "code"
        )
        notebook_tree = ast.parse(code_source)
        fallback_if: ast.If | None = None
        for node in ast.walk(notebook_tree):
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "raw_event"
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Is)
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value is None
            ):
                fallback_if = node
                break

        self.assertIsNotNone(fallback_if, "raw_event fallback branch not found")

        fallback_assignment = next(
            (
                statement
                for statement in fallback_if.body
                if isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and statement.targets[0].id == "raw_event"
            ),
            None,
        )
        self.assertIsNotNone(fallback_assignment, "raw_event fallback assignment not found")

        list_comprehensions = [
            child
            for child in ast.walk(fallback_assignment.value)
            if isinstance(child, ast.ListComp)
        ]
        self.assertTrue(list_comprehensions, "raw_event fallback schema list comprehension not found")

        self.assertTrue(
            any(
                isinstance(generator.iter, ast.Name)
                and generator.iter.id == "RUN_EVENT_FIELDS"
                for list_comp in list_comprehensions
                for generator in list_comp.generators
            ),
            "raw_event fallback schema must be derived from RUN_EVENT_FIELDS",
        )

    def test_logical_tables_only_reference_assigned_frames(self) -> None:
        code_source = "\n".join(
            "".join(cell.get("source", []))
            for cell in self.notebook["cells"]
            if cell.get("cell_type") == "code"
        )
        notebook_tree = ast.parse(code_source)
        publication_tree = ast.parse(self.publication_source)

        assigned_names: set[str] = set()

        def collect_assigned_names(target: ast.expr) -> None:
            if isinstance(target, ast.Name):
                assigned_names.add(target.id)
                return
            if isinstance(target, (ast.Tuple, ast.List)):
                for element in target.elts:
                    collect_assigned_names(element)

        for node in ast.walk(notebook_tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    collect_assigned_names(target)
            elif isinstance(node, ast.AnnAssign):
                collect_assigned_names(node.target)

        logical_tables_assignment = next(
            (
                node
                for node in publication_tree.body
                if isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "LOGICAL_TABLES"
                and isinstance(node.value, ast.Dict)
            ),
            None,
        )
        self.assertIsNotNone(logical_tables_assignment, "LOGICAL_TABLES assignment was not found")

        logical_table_values = [
            value.id
            for value in logical_tables_assignment.value.values
            if isinstance(value, ast.Name)
        ]
        self.assertIn("offset_run_config_summary", logical_table_values)
        self.assertIn("offset_run_event_summary", logical_table_values)

        missing_names = sorted(
            name for name in logical_table_values if name not in assigned_names
        )
        self.assertEqual(
            [],
            missing_names,
            f"LOGICAL_TABLES references unassigned frames: {missing_names}",
        )

    def test_v12_source_headers_align_with_notebook_parser_columns(self) -> None:
        v12_root = PROJECT_ROOT / "data" / "releases" / "v1.2.0"
        with (v12_root / "drilling_runs.csv").open(newline="", encoding="utf-8") as stream:
            run_header = next(csv.reader(stream))
        with (v12_root / "planned_targets.csv").open(newline="", encoding="utf-8") as stream:
            target_header = next(csv.reader(stream))

        self.assertIn("mud_weight_ppg", run_header)
        self.assertIn("mud_funnel_viscosity_sec", run_header)
        self.assertEqual(28, len(run_header))
        self.assertIn('("mud_weight_ppg", DECIMAL, False), ("mud_funnel_viscosity_sec", DECIMAL, False)', self.source)

        self.assertIn("planned_bit_type", target_header)
        self.assertIn("planned_bha_type", target_header)
        self.assertIn("planned_mud_type", target_header)
        self.assertEqual(25, len(target_header))
        self.assertIn('("planned_bit_type", STRING, True), ("planned_bha_type", STRING, True)', self.source)
        self.assertIn('("planned_mud_type", STRING, True),', self.source)

    def test_release_selection_fails_closed_for_unknown_or_mismatched_inputs(self) -> None:
        for fragment in [
            'DEFAULT_RELEASE_VERSION = "v1.2.0"',
            'globals().get("RELEASE_VERSION", DEFAULT_RELEASE_VERSION)',
            "INVALID_RELEASE_VERSION_PARAMETER",
            "UNKNOWN_RELEASE_VERSION",
            "MISMATCHED_RELEASE_INPUT_OVERRIDE",
            'override_name, expected_value in {',
            '"DATASET_VERSION": RELEASE_PROFILE["dataset_version"]',
            '"SOURCE_ROOT": RELEASE_PROFILE["source_root"]',
            '"MANIFEST_SHA256": RELEASE_PROFILE["manifest_sha256"]',
            '"SOURCE_INVENTORY_SHA256": RELEASE_PROFILE["source_inventory_sha256"]',
            '"AGGREGATE_SOURCE_SHA256": RELEASE_PROFILE["aggregate_source_sha256"]',
        ]:
            self.assertIn(fragment, self.source)

    def test_stage_only_path_is_supported_by_tracked_parameterized_notebook(self) -> None:
        self.assertIn(
            "elif not ACTIVATE_RELEASE_POINTER:",
            self.publication_source,
        )
        self.assertIn(
            "STAGED_ONLY_NO_POINTER_UPDATE",
            self.publication_source,
        )
        self.assertIn(
            "active_release_id if not ACTIVATE_RELEASE_POINTER else RELEASE_ID",
            self.publication_source,
        )
        self.assertIn(
            "active_pointer[0][\"active_release_id\"] == active_release_id",
            self.publication_source,
        )

    def test_lock_is_non_expiring_compare_and_set_with_one_transactional_winner(self) -> None:
        normal_claim_guard = self.publication_source.index(
            "if not lock_claimed_by_recovery_transfer:"
        )
        lock_claim = self.publication_source.index(
            "UPDATE {PUBLICATION_LOCK_TABLE}\n"
            "        SET attempt_id = '{attempt_literal}'",
            normal_claim_guard,
        )
        lock_assertion = self.publication_source.index(
            "assert_publication_lock_owned()"
        )
        pointer_read = self.publication_source.index("active_pointer_rows = (")
        registry_reset = self.publication_source.index(
            "MERGE INTO {RELEASE_REGISTRY_TABLE} target"
        )
        cleanup = self.publication_source.index(
            "DELETE FROM {physical_table_name} WHERE _release_id"
        )
        activation = self.publication_source.index(
            "MERGE INTO {ACTIVE_RELEASE_POINTER_TABLE} target"
        )
        self.assertLess(lock_claim, pointer_read)
        self.assertLess(lock_assertion, pointer_read)
        self.assertLess(pointer_read, registry_reset)
        self.assertLess(registry_reset, cleanup)
        self.assertGreaterEqual(
            self.publication_source[:activation].count(
                "assert_publication_lock_owned()"
            ),
            4,
        )
        lock_update = self.publication_source[
            lock_claim:self.publication_source.index(
                "assert_publication_lock_owned()", lock_claim
            )
        ]
        self.assertIn("AND attempt_id IS NULL", lock_update)
        self.assertNotIn("OR ", lock_update)
        self.assertIn(
            "require(len(lock_sentinel_rows) == 1, "
            '"PUBLICATION_LOCK_SENTINEL_INVALID"',
            self.publication_source,
        )
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS {PUBLICATION_LOCK_TABLE}\n"
            "    USING DELTA AS",
            self.publication_source,
        )
        self.assertIn("ATTEMPT_ID = str(uuid.uuid4())", self.publication_source)
        self.assertIn("PUBLICATION_LOCK_NOT_OWNED", self.publication_source)
        for prohibited in [
            "lease_expires_at",
            "PUBLICATION_LEASE_HOURS",
            "renew_and_assert_publication_lock",
            "target.lease_expires_at",
        ]:
            self.assertNotIn(prohibited, self.publication_source)

    def test_manual_recovery_requires_terminal_job_attestation_and_audit(self) -> None:
        for fragment in [
            "DEFAULT_RECOVERY_MODE = False",
            'raw_recovery_mode = globals().get("RECOVERY_MODE", DEFAULT_RECOVERY_MODE)',
            "RECOVERY_LOCK_REQUIRED",
            "RECOVERY_OPERATOR_REQUIRED",
            "RECOVERY_REASON_REQUIRED",
            "RECOVERY_PARAMETER_REQUIRED",
            "RECOVERY_PARAMETERS_REQUIRE_RECOVERY_MODE",
            "RECOVERY_EXPECTED_DATASET_NAME",
            "RECOVERY_EXPECTED_RELEASE_ID",
            "RECOVERY_EXPECTED_ATTEMPT_ID",
            "RECOVERY_EXPECTED_APPLICATION_ID",
            "RECOVERY_EXPECTED_JOB_INSTANCE_ID",
            "RECOVERY_EXPECTED_JOB_RESPONSE_JSON",
            "RECOVERY_JOB_PROOF_INVALID_JSON",
            "RECOVERY_JOB_NOT_TERMINAL_FAILED",
            "RECOVERY_TERMINAL_JOB_CONFIRMATION_MISMATCH",
            "RECOVERY_JOB_PROOF_MISMATCH",
            "RECOVERY_ATTEMPT_NOT_FAILED",
            "INSERT INTO {PUBLICATION_RECOVERY_AUDIT_TABLE}",
            "terminal_job_confirmed BOOLEAN NOT NULL",
            "PUBLICATION_LOCK_HELD_NO_AUTOMATIC_TAKEOVER",
            "fetch_job_instance_record(",
        ]:
            self.assertIn(fragment, self.publication_source)
        audit = self.publication_source.index(
            "INSERT INTO {PUBLICATION_RECOVERY_AUDIT_TABLE}"
        )
        attempt_insert = self.publication_source.index(
            "INSERT INTO {PUBLICATION_ATTEMPT_TABLE}"
        )
        cas_transfer = self.publication_source.index(
            "UPDATE {PUBLICATION_LOCK_TABLE}\n"
            "        SET attempt_id = '{attempt_literal}'"
        )
        normal_claim = self.publication_source.index(
            "UPDATE {PUBLICATION_LOCK_TABLE}\n"
            "        SET attempt_id = '{attempt_literal}'",
            cas_transfer + 1,
        )
        self.assertLess(audit, cas_transfer)
        self.assertLess(attempt_insert, cas_transfer)
        self.assertLess(cas_transfer, normal_claim)
        self.assertIn(
            "if not lock_claimed_by_recovery_transfer:\n"
            "    spark.sql(\n"
            "        f\"\"\"\n"
            "        UPDATE {PUBLICATION_LOCK_TABLE}\n"
            "        SET attempt_id = '{attempt_literal}'",
            self.publication_source,
        )
        self.assertNotIn("failure_message = 'OPERATOR_RECOVERY:", self.publication_source)
        self.assertNotIn(
            "UPDATE {PUBLICATION_LOCK_TABLE}\n"
            "        SET attempt_id = NULL,\n"
            "            attempt_application_id = NULL,\n"
            "            acquired_at_utc = NULL",
            self.publication_source,
        )

    def test_recovery_fail_closed_guards_cover_wrong_owner_release_and_nonterminal_job(self) -> None:
        for fragment in [
            "RECOVERY_LOCK_ATTEMPT_MISMATCH",
            "RECOVERY_LOCK_APPLICATION_MISMATCH",
            "RECOVERY_ATTEMPT_RELEASE_MISMATCH",
            "RECOVERY_ATTEMPT_APPLICATION_MISMATCH",
            "RECOVERY_ATTEMPT_NOT_FAILED",
            "RECOVERY_JOB_NOT_TERMINAL_FAILED",
            "RECOVERY_TERMINAL_JOB_CONFIRMATION_MISMATCH",
            "RECOVERY_JOB_PROOF_MISMATCH",
            "RECOVERY_JOB_PROOF_INVALID_JSON",
            "RECOVERY_TERMINAL_JOB_FETCH_HTTP_ERROR",
        ]:
            self.assertIn(fragment, self.publication_source)
        self.assertIn(
            "WHERE dataset_name = '{DATASET_NAME}'\n"
            "          AND attempt_id = '{interrupted_attempt_literal}'\n"
            "          AND attempt_application_id = '{interrupted_application_literal}'",
            self.publication_source,
        )

    def test_recovery_terminal_failed_status_guard_uses_fabric_failed_literal_and_rejects_nonterminal_states(self) -> None:
        publication_tree = ast.parse(self.publication_source)

        failed_status_literal = next(
            (
                node.value.value
                for node in publication_tree.body
                if isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "FABRIC_FAILED_JOB_STATUS"
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ),
            None,
        )
        self.assertEqual("Failed", failed_status_literal)

        terminal_guard = next(
            (
                node
                for node in publication_tree.body
                if isinstance(node, ast.FunctionDef)
                and node.name == "require_terminal_failed_job_status"
            ),
            None,
        )
        self.assertIsNotNone(terminal_guard, "terminal failed-status guard helper not found")

        guard_module = ast.Module(body=[terminal_guard], type_ignores=[])
        ast.fix_missing_locations(guard_module)

        def require(condition: bool, code: str, detail: str) -> None:
            if not condition:
                raise RuntimeError(f"{code}: {detail}")

        namespace = {
            "require": require,
            "FABRIC_FAILED_JOB_STATUS": failed_status_literal,
        }
        exec(compile(guard_module, filename="<recovery_terminal_status_guard>", mode="exec"), namespace)
        guard_fn = namespace["require_terminal_failed_job_status"]

        guard_fn({"status": "Failed"})
        for non_terminal_status in ("Running", "Completed", "Cancelled"):
            with self.assertRaisesRegex(
                RuntimeError,
                f"RECOVERY_JOB_NOT_TERMINAL_FAILED: {non_terminal_status}",
            ):
                guard_fn({"status": non_terminal_status})

        self.assertIn(
            "require_terminal_failed_job_status(operator_job_summary)",
            self.publication_source,
        )
        self.assertIn(
            "require_terminal_failed_job_status(trusted_job_summary)",
            self.publication_source,
        )

    def test_validation_activation_full_evidence_and_release_are_ordered(self) -> None:
        validation = self.publication_source.index(
            "RECONCILIATION_COMPLETE_BEFORE_ACTIVATION = True"
        )
        evidence_payload = self.publication_source.index(
            "reconciliation_result = {"
        )
        evidence = self.publication_source.index(
            "INSERT INTO {PUBLICATION_EVIDENCE_TABLE}"
        )
        ready_gate = self.publication_source.index("RELEASE_NOT_READY_AFTER_EVIDENCE")
        activation = self.publication_source.index(
            "MERGE INTO {ACTIVE_RELEASE_POINTER_TABLE} target"
        )
        release = self.publication_source.rindex(
            "UPDATE {PUBLICATION_LOCK_TABLE}"
        )
        self.assertLess(validation, evidence_payload)
        self.assertLess(evidence_payload, evidence)
        self.assertLess(evidence, ready_gate)
        self.assertLess(ready_gate, activation)
        self.assertLess(evidence, release)
        self.assertIn(
            "PUBLICATION_LOCK_RELEASE_FAILED_OPERATOR_CLEANUP_REQUIRED",
            self.publication_source,
        )
        self.assertIn(
            "try:\n"
            "    assert_publication_lock_owned()\n"
            "    pointer_history = spark.sql(",
            self.publication_source,
        )
        self.assertIn(
            "physical_table_name = physical_table_for(logical_table_name)",
            self.publication_source,
        )
        self.assertIn(
            "assert_publication_lock_owned()\n"
            "        # This is the only activation boundary",
            self.publication_source,
        )
        self.assertIn(
            "ACTIVATION_AFTER_READY_FAILED",
            self.publication_source,
        )
        self.assertIn(
            "assert_publication_lock_owned()\nspark.sql(\n"
            "    f\"\"\"\n"
            "    UPDATE {PUBLICATION_LOCK_TABLE}\n"
            "    SET attempt_id = NULL",
            self.publication_source,
        )

    def test_persisted_evidence_contains_complete_bounded_payload(self) -> None:
        required_fragments = [
            'EVIDENCE_SCHEMA_VERSION = "1.0.0"',
            "EVIDENCE_RETENTION_DAYS = 400",
            "MAX_EVIDENCE_JSON_BYTES = 1024 * 1024",
            "evidence_schema_version STRING NOT NULL",
            "payload_sha256 STRING NOT NULL",
            "payload_json STRING NOT NULL",
            "'delta.appendOnly' = 'true'",
            "'drillrun.evidence.schemaVersion' = '{EVIDENCE_SCHEMA_VERSION}'",
            "'drillrun.evidence.maxPayloadBytes' = '{MAX_EVIDENCE_JSON_BYTES}'",
            "'drillrun.evidence.minimumRetentionDays' = '{EVIDENCE_RETENTION_DAYS}'",
            '"authorized_file_sha256"',
            '"observed_file_sha256"',
            '"dataset_fingerprint"',
            '"aggregate_source_fingerprint"',
            '"source_files"',
            '"raw"',
            '"curated"',
            '"serving"',
            '"accepted_run_count"',
            '"quarantined_run_count"',
            '"rejected_record_count"',
            '"quarantine_issues"',
            '"quality_issue_id"',
            '"reason_code"',
            '"summary_reconciliation_measures"',
            '"physical_tables"',
            '"physical_table"',
            '"delta_version"',
            '"business_content_sha256"',
            '"attempt_id"',
            '"generation_run_id"',
            '"spark_application_id"',
            '"user"',
            '"workspace_id"',
            '"lakehouse_id"',
            '"lakehouse_name"',
            '"notebook_name"',
            '"activation_result"',
            '"pointer_delta_version"',
            '"evidence_written_at_utc"',
            '"evidence_contract"',
            '"schema_version"',
            '"retention_days"',
            '"max_payload_bytes"',
            '"canonicalization"',
            '"integrity"',
            '"content_sha256"',
            '"verification"',
            "integrity_content_sha256",
            "persisted_content_sha256",
            "EVIDENCE_PAYLOAD_TOO_LARGE",
        ]
        for fragment in required_fragments:
            self.assertIn(fragment, self.publication_source)

    def test_entire_post_activation_evidence_phase_is_fail_closed(self) -> None:
        activation_verification = self.publication_source.index(
            "ACTIVE_VIEW_CONTENT_HASH_MISMATCH"
        )
        boundary = self.publication_source.index(
            "# Every operation needed to create, persist, and verify evidence is fail-closed."
        )
        handler = self.publication_source.index(
            "except Exception as evidence_error:"
        )
        phase_operations = [
            "pointer_history = spark.sql(",
            "quarantine_evidence = [",
            "reconciliation_result = {",
            "integrity_content_json = json.dumps(",
            "integrity_content_sha256 = hashlib.sha256(",
            "reconciliation_json = json.dumps(",
            "EVIDENCE_PAYLOAD_TOO_LARGE",
            "evidence_payload_sha256 = hashlib.sha256(",
            "INSERT INTO {PUBLICATION_EVIDENCE_TABLE}",
            "persisted_evidence = (",
            "PUBLICATION_EVIDENCE_PAYLOAD_MISMATCH",
            "persisted_payload = json.loads(",
            "PUBLICATION_EVIDENCE_CONTENT_HASH_MISMATCH",
        ]
        self.assertLess(activation_verification, boundary)
        for operation in phase_operations:
            position = self.publication_source.index(operation, boundary)
            self.assertLess(boundary, position, operation)
            self.assertLess(position, handler, operation)

    def test_internal_integrity_hash_precedes_final_payload_serialization(self) -> None:
        payload = self.publication_source.index(
            "reconciliation_result = {"
        )
        null_integrity = self.publication_source.index(
            '"content_sha256": None',
            payload,
        )
        content_serialization = self.publication_source.index(
            "integrity_content_json = json.dumps(",
            null_integrity,
        )
        content_hash = self.publication_source.index(
            "integrity_content_sha256 = hashlib.sha256(",
            content_serialization,
        )
        embed_hash = self.publication_source.index(
            '["content_sha256"] = integrity_content_sha256',
            content_hash,
        )
        final_serialization = self.publication_source.index(
            "reconciliation_json = json.dumps(",
            embed_hash,
        )
        size_check = self.publication_source.index(
            "EVIDENCE_PAYLOAD_TOO_LARGE",
            final_serialization,
        )
        insert = self.publication_source.index(
            "INSERT INTO {PUBLICATION_EVIDENCE_TABLE}",
            size_check,
        )
        self.assertLess(null_integrity, content_serialization)
        self.assertLess(content_serialization, content_hash)
        self.assertLess(content_hash, embed_hash)
        self.assertLess(embed_hash, final_serialization)
        self.assertLess(final_serialization, size_check)
        self.assertLess(size_check, insert)

    def test_evidence_is_read_back_before_attempt_completion_and_release(self) -> None:
        insert = self.publication_source.index(
            "INSERT INTO {PUBLICATION_EVIDENCE_TABLE}"
        )
        read_back = self.publication_source.index(
            "persisted_evidence = ("
        )
        payload_check = self.publication_source.index(
            "PUBLICATION_EVIDENCE_PAYLOAD_MISMATCH"
        )
        attempt_success = self.publication_source.index(
            "SET attempt_state = 'SUCCEEDED'"
        )
        attempt_check = self.publication_source.index(
            "PUBLICATION_ATTEMPT_COMPLETION_FAILED_LOCK_RETAINED"
        )
        release = self.publication_source.rindex(
            "UPDATE {PUBLICATION_LOCK_TABLE}"
        )
        self.assertLess(insert, read_back)
        self.assertLess(read_back, payload_check)
        self.assertLess(payload_check, attempt_success)
        self.assertLess(attempt_success, attempt_check)
        self.assertLess(attempt_check, release)
        for fragment in [
            "PUBLICATION_EVIDENCE_NOT_UNIQUE",
            "PUBLICATION_EVIDENCE_RELEASE_MISMATCH",
            "PUBLICATION_EVIDENCE_SCHEMA_MISMATCH",
            "PUBLICATION_EVIDENCE_HASH_MISMATCH",
            "PUBLICATION_EVIDENCE_PAYLOAD_MISMATCH",
            "PUBLICATION_EVIDENCE_PAYLOAD_SCHEMA_MISMATCH",
            "PUBLICATION_EVIDENCE_RETENTION_MISMATCH",
            "PUBLICATION_EVIDENCE_MAX_SIZE_MISMATCH",
            "PUBLICATION_EVIDENCE_CANONICALIZATION_MISMATCH",
            "PUBLICATION_EVIDENCE_INTEGRITY_ALGORITHM_MISMATCH",
            "PUBLICATION_EVIDENCE_INTEGRITY_FIELD_MISMATCH",
            "PUBLICATION_EVIDENCE_INTEGRITY_VERIFICATION_MISMATCH",
            "PUBLICATION_EVIDENCE_CONTENT_HASH_FORMAT_INVALID",
            "PUBLICATION_EVIDENCE_CONTENT_HASH_MISMATCH",
        ]:
            self.assertIn(fragment, self.publication_source)

    def test_evidence_failure_retains_lock_for_manual_recovery(self) -> None:
        failure = self.publication_source.index(
            "EVIDENCE_PERSISTENCE_FAILED_LOCK_RETAINED"
        )
        release = self.publication_source.rindex(
            "UPDATE {PUBLICATION_LOCK_TABLE}"
        )
        self.assertLess(failure, release)
        self.assertIn(
            "except Exception as evidence_error:",
            self.publication_source,
        )
        self.assertIn(
            'evidence_failure_literal = sql_literal(f"EVIDENCE_PERSISTENCE_FAILED:{evidence_failure_type}")',
            self.publication_source,
        )
        self.assertIn(
            "except Exception as attempt_mark_error:",
            self.publication_source,
        )
        self.assertIn(
            "EVIDENCE_ATTEMPT_FAILURE_MARK_FAILED",
            self.publication_source,
        )
        self.assertIn(
            "attempt_mark_error_type={attempt_mark_failure_type}",
            self.publication_source,
        )
        self.assertNotIn(
            "str(evidence_error)",
            self.publication_source[
                self.publication_source.index("except Exception as evidence_error:"):release
            ],
        )
        self.assertNotIn("finally:", self.publication_source[failure:release])
        self.assertIn(
            "Display mirrors the already persisted payload and is not evidence authority.",
            self.publication_source,
        )

    def test_legacy_direct_tables_fail_closed_before_release_writes(self) -> None:
        legacy_guard = self.publication_source.index(
            "LEGACY_DIRECT_TABLE_REQUIRES_ONE_TIME_MIGRATION"
        )
        first_release_write = self.publication_source.index(
            "writer.saveAsTable(physical_table_name)"
        )
        self.assertLess(legacy_guard, first_release_write)
        self.assertIn(
            'if object_type != "VIEW":',
            self.publication_source,
        )

    def test_first_release_ready_transition_precedes_optional_pointer_activation(self) -> None:
        pointer_read = self.publication_source.index(
            "active_pointer_rows = ("
        )
        stage_branch = self.publication_source.index(
            "if not release_already_active:"
        )
        ready_gate = self.publication_source.index(
            "RELEASE_NOT_READY_AFTER_EVIDENCE"
        )
        activation = self.publication_source.index(
            "MERGE INTO {ACTIVE_RELEASE_POINTER_TABLE} target"
        )
        self.assertLess(pointer_read, stage_branch)
        self.assertLess(stage_branch, ready_gate)
        self.assertLess(ready_gate, activation)

    def test_control_only_promotion_requires_ready_gates_before_pointer_update(self) -> None:
        for fragment in [
            "DEFAULT_CONTROL_ONLY_PROMOTION = True",
            'globals().get("CONTROL_ONLY_PROMOTION", DEFAULT_CONTROL_ONLY_PROMOTION)',
            "INVALID_CONTROL_ONLY_PROMOTION_PARAMETER",
            'normalized_control_only_promotion in {"true", "false"}',
            'CONTROL_ONLY_PROMOTION = normalized_control_only_promotion == "true"',
            "CONTROL_ONLY_PROMOTION_REQUIRES_POINTER_ACTIVATION",
            "CONTROL_ONLY_RELEASE_NOT_STAGING",
            "CONTROL_ONLY_REGISTRY_ATTEMPT_MISMATCH",
            "RELEASE_GATE_TABLE_MISSING",
            "RELEASE_GATE_ROW_COUNT_MISMATCH",
            "RELEASE_TABLE_EXPECTATIONS",
            "PLANNED_TARGET_FIELD_MINIMUM_NOT_MET",
            "ACTIVE_VIEW_PROJECTION_DRIFT",
            '"control_only_promotion": CONTROL_ONLY_PROMOTION',
            '"activation_result": "CONTROL_ONLY_ACTIVATED"',
        ]:
            self.assertIn(fragment, self.publication_source)

        release_gate = self.publication_source.index("RELEASE_GATE_ROW_COUNT_MISMATCH")
        ready_gate = self.publication_source.index("RELEASE_NOT_READY_AFTER_EVIDENCE")
        activation = self.publication_source.index(
            "MERGE INTO {ACTIVE_RELEASE_POINTER_TABLE} target"
        )
        self.assertLess(release_gate, ready_gate)
        self.assertLess(ready_gate, activation)

    def test_execution_mode_diagnostic_emits_effective_release_mode_before_mutations(self) -> None:
        for fragment in [
            "EXECUTION_MODE = (",
            '"CONTROL_ONLY"',
            '"FULL_REBUILD_AND_ACTIVATE"',
            '"FULL_REBUILD_STAGE_ONLY"',
            "pre_mutation_pointer_rows = (",
            '"stage": "execution_mode"',
            '"pre_mutation_active_release_id": pre_mutation_active_release_id',
            '"pre_mutation_release_already_active": pre_mutation_active_release_id == RELEASE_ID',
            "INSERT INTO {PUBLICATION_ATTEMPT_TABLE}",
        ]:
            self.assertIn(fragment, self.publication_source)

        mode_diagnostic = self.publication_source.index('"stage": "execution_mode"')
        first_attempt_write = self.publication_source.index(
            "INSERT INTO {PUBLICATION_ATTEMPT_TABLE}"
        )
        self.assertLess(mode_diagnostic, first_attempt_write)

    def test_control_only_default_true_keeps_explicit_false_available_for_deliberate_rebuild(self) -> None:
        self.assertIn("DEFAULT_CONTROL_ONLY_PROMOTION = True", self.publication_source)
        self.assertIn(
            'normalized_control_only_promotion in {"true", "false"}',
            self.publication_source,
        )
        self.assertIn(
            'CONTROL_ONLY_PROMOTION = normalized_control_only_promotion == "true"',
            self.publication_source,
        )

    def test_control_only_path_checks_mode_before_release_table_rewrites(self) -> None:
        mode_guard = self.publication_source.index("if not CONTROL_ONLY_PROMOTION:")
        release_delete = self.publication_source.index(
            "DELETE FROM {physical_table_name} WHERE _release_id"
        )
        release_write = self.publication_source.index(
            "writer.saveAsTable(physical_table_name)"
        )
        self.assertLess(mode_guard, release_delete)
        self.assertLess(mode_guard, release_write)

    def test_control_only_path_populates_staged_tables_for_evidence_from_persisted_release_tables(self) -> None:
        publication_tree = ast.parse(self.publication_source)

        parent_by_node: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(publication_tree):
            for child in ast.iter_child_nodes(node):
                parent_by_node[child] = node

        candidate_assignments: list[ast.Assign] = []
        for node in ast.walk(publication_tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == "staged_tables"
            ):
                continue
            if not (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "capture_verified_staged_table"
            ):
                continue
            candidate_assignments.append(node)

        self.assertTrue(candidate_assignments, "control-only staged evidence assignment not found")

        for assignment in candidate_assignments:
            cursor: ast.AST | None = assignment
            for_parent: ast.For | None = None
            control_only_if_found = False
            not_release_already_active_if_found = False

            while cursor is not None:
                cursor = parent_by_node.get(cursor)
                if isinstance(cursor, ast.For) and for_parent is None:
                    for_parent = cursor
                if isinstance(cursor, ast.If):
                    if (
                        isinstance(cursor.test, ast.Name)
                        and cursor.test.id == "CONTROL_ONLY_PROMOTION"
                    ):
                        control_only_if_found = True
                    if (
                        isinstance(cursor.test, ast.UnaryOp)
                        and isinstance(cursor.test.op, ast.Not)
                        and isinstance(cursor.test.operand, ast.Name)
                        and cursor.test.operand.id == "CONTROL_ONLY_PROMOTION"
                    ):
                        control_only_if_found = True
                    if (
                        isinstance(cursor.test, ast.UnaryOp)
                        and isinstance(cursor.test.op, ast.Not)
                        and isinstance(cursor.test.operand, ast.Name)
                        and cursor.test.operand.id == "release_already_active"
                    ):
                        not_release_already_active_if_found = True

            if for_parent is None:
                continue

            expected_loop = (
                isinstance(for_parent.target, ast.Name)
                and for_parent.target.id == "logical_table_name"
                and isinstance(for_parent.iter, ast.Name)
                and for_parent.iter.id == "EXPECTED_TABLE_ROWS"
            )
            if expected_loop and control_only_if_found and not_release_already_active_if_found:
                return

        self.fail(
            "control-only evidence assignment must execute inside "
            "`if not release_already_active` and `if CONTROL_ONLY_PROMOTION` "
            "while iterating EXPECTED_TABLE_ROWS"
        )

    def test_projection_drift_helpers_enforce_canonical_business_columns(self) -> None:
        publication_tree = ast.parse(self.publication_source)
        helper_names = {
            "canonical_business_columns",
            "projection_drift_details",
            "require_expected_business_columns",
        }
        helper_nodes = [
            node
            for node in publication_tree.body
            if isinstance(node, ast.FunctionDef) and node.name in helper_names
        ]
        self.assertEqual(helper_names, {node.name for node in helper_nodes})

        helper_module = ast.Module(body=helper_nodes, type_ignores=[])
        ast.fix_missing_locations(helper_module)

        def require(condition: bool, code: str, detail: str) -> None:
            if not condition:
                raise RuntimeError(f"{code}: {detail}")

        namespace = {
            "DataFrame": object,
            "HASH_EXCLUDED_COLUMNS": {"_processed_at_utc", "_release_id", "_publication_state"},
            "json": json,
            "require": require,
        }
        exec(compile(helper_module, "<fabric_notebook_helpers>", "exec"), namespace)

        canonical_business_columns = namespace["canonical_business_columns"]
        projection_drift_details = namespace["projection_drift_details"]
        require_expected_business_columns = namespace["require_expected_business_columns"]

        self.assertEqual(
            ["dataset_version", "run_id", "well_id"],
            canonical_business_columns(
                [
                    "well_id",
                    "_publication_state",
                    "run_id",
                    "dataset_version",
                    "_processed_at_utc",
                    "_release_id",
                ]
            ),
        )

        drift = projection_drift_details(
            ["dataset_version", "run_id", "well_id"],
            ["dataset_version", "run_id", "trajectory_family"],
        )
        self.assertEqual(["well_id"], drift["missing"])
        self.assertEqual(["trajectory_family"], drift["extra"])

        class FakeFrame:
            def __init__(self, columns: list[str]) -> None:
                self.columns = columns

        valid_columns = require_expected_business_columns(
            "raw.drilling_run",
            FakeFrame(
                [
                    "_release_id",
                    "run_id",
                    "_publication_state",
                    "dataset_version",
                    "well_id",
                ]
            ),
            ["dataset_version", "run_id", "well_id"],
            "HASH_SCHEMA_DRIFT",
        )
        self.assertEqual(["dataset_version", "run_id", "well_id"], valid_columns)

        with self.assertRaisesRegex(RuntimeError, "HASH_SCHEMA_DRIFT"):
            require_expected_business_columns(
                "raw.drilling_run",
                FakeFrame(["dataset_version", "run_id", "trajectory_family"]),
                ["dataset_version", "run_id", "well_id"],
                "HASH_SCHEMA_DRIFT",
            )

    def test_deterministic_content_hash_reports_schema_drift_and_hashes_business_content(self) -> None:
        publication_tree = ast.parse(self.publication_source)
        helper_names = {
            "canonical_business_columns",
            "projection_drift_details",
            "require_expected_business_columns",
            "deterministic_content_hash",
        }
        helper_nodes = [
            node
            for node in publication_tree.body
            if isinstance(node, ast.FunctionDef) and node.name in helper_names
        ]
        self.assertEqual(helper_names, {node.name for node in helper_nodes})

        helper_module = ast.Module(body=helper_nodes, type_ignores=[])
        ast.fix_missing_locations(helper_module)

        def require(condition: bool, code: str, detail: str) -> None:
            if not condition:
                raise RuntimeError(f"{code}: {detail}")

        class FakeExpr:
            def __init__(self, kind: str, value: object) -> None:
                self.kind = kind
                self.value = value
                self.alias_name: str | None = None

            def alias(self, name: str) -> "FakeExpr":
                self.alias_name = name
                return self

        class FakeFunctions:
            @staticmethod
            def col(name: str) -> FakeExpr:
                return FakeExpr("col", name)

            @staticmethod
            def struct(*columns: FakeExpr) -> FakeExpr:
                column_names = [column.value for column in columns]
                return FakeExpr("struct", column_names)

            @staticmethod
            def to_json(expression: FakeExpr) -> FakeExpr:
                return FakeExpr("to_json", expression.value)

            @staticmethod
            def collect_list(column_name: str) -> FakeExpr:
                return FakeExpr("collect_list", column_name)

            @staticmethod
            def sort_array(expression: FakeExpr) -> FakeExpr:
                return FakeExpr("sort_array", expression)

            @staticmethod
            def concat_ws(delimiter: str, expression: FakeExpr) -> FakeExpr:
                return FakeExpr("concat_ws", {"delimiter": delimiter, "expression": expression})

            @staticmethod
            def lit(value: str) -> FakeExpr:
                return FakeExpr("lit", value)

            @staticmethod
            def coalesce(left: FakeExpr, right: FakeExpr) -> FakeExpr:
                return FakeExpr("coalesce", {"left": left, "right": right})

            @staticmethod
            def sha2(expression: FakeExpr, bit_size: int) -> FakeExpr:
                return FakeExpr("sha2", {"expression": expression, "bit_size": bit_size})

        class FakeHashCollectResult:
            def __init__(self, digest: str) -> None:
                self.digest = digest

            def collect(self) -> list[dict[str, str]]:
                return [{"_hash": self.digest}]

        class FakeFrame:
            def __init__(self, rows: list[dict[str, object]], columns: list[str]) -> None:
                self._rows = rows
                self.columns = columns

            def select(self, expression: FakeExpr) -> "FakeFrame":
                if expression.kind != "to_json":
                    raise AssertionError(f"unexpected select expression: {expression.kind}")
                if expression.alias_name != "_row":
                    raise AssertionError(f"unexpected alias: {expression.alias_name}")
                selected_columns = expression.value
                projected_rows = []
                for row in self._rows:
                    payload = {
                        column: row.get(column)
                        for column in selected_columns
                    }
                    projected_rows.append(
                        {"_row": json.dumps(payload, separators=(",", ":"), ensure_ascii=False)}
                    )
                return FakeFrame(projected_rows, ["_row"])

            def agg(self, _expression: FakeExpr) -> FakeHashCollectResult:
                concatenated = "||".join(sorted(row["_row"] for row in self._rows)) if self._rows else ""
                digest = hashlib.sha256(concatenated.encode("utf-8")).hexdigest()
                return FakeHashCollectResult(digest)

        namespace = {
            "DataFrame": object,
            "HASH_EXCLUDED_COLUMNS": {"_processed_at_utc", "_release_id", "_publication_state"},
            "F": FakeFunctions(),
            "json": json,
            "require": require,
        }
        exec(compile(helper_module, "<fabric_notebook_hash_helpers>", "exec"), namespace)
        deterministic_content_hash = namespace["deterministic_content_hash"]

        expected_business_columns = ["dataset_version", "run_id", "well_id"]
        aligned_rows = [
            {
                "dataset_version": "v1.2.0",
                "run_id": "R-002",
                "well_id": "W-1002",
                "_release_id": "v1.2.0:manifest",
                "_publication_state": "STAGED",
                "_processed_at_utc": "2026-10-30T00:00:01Z",
            },
            {
                "dataset_version": "v1.2.0",
                "run_id": "R-001",
                "well_id": "W-1001",
                "_release_id": "v1.2.0:manifest",
                "_publication_state": "STAGED",
                "_processed_at_utc": "2026-10-30T00:00:00Z",
            },
        ]

        aligned_view = FakeFrame(
            aligned_rows,
            [
                "_publication_state",
                "well_id",
                "dataset_version",
                "_release_id",
                "run_id",
                "_processed_at_utc",
            ],
        )
        aligned_hash = deterministic_content_hash(
            aligned_view,
            logical_table_name="raw.drilling_run",
            expected_business_columns=expected_business_columns,
            schema_error_code="ACTIVE_VIEW_CONTENT_HASH_SCHEMA_DRIFT",
        )
        expected_row_payloads = [
            json.dumps(
                {
                    "dataset_version": row["dataset_version"],
                    "run_id": row["run_id"],
                    "well_id": row["well_id"],
                },
                separators=(",", ":"),
                ensure_ascii=False,
            )
            for row in aligned_rows
        ]
        expected_aligned_hash = hashlib.sha256(
            "||".join(sorted(expected_row_payloads)).encode("utf-8")
        ).hexdigest()
        self.assertEqual(expected_aligned_hash, aligned_hash)

        reordered_projection_view = FakeFrame(
            aligned_rows,
            [
                "run_id",
                "_processed_at_utc",
                "dataset_version",
                "_publication_state",
                "well_id",
                "_release_id",
            ],
        )
        reordered_hash = deterministic_content_hash(
            reordered_projection_view,
            logical_table_name="raw.drilling_run",
            expected_business_columns=expected_business_columns,
            schema_error_code="ACTIVE_VIEW_CONTENT_HASH_SCHEMA_DRIFT",
        )
        self.assertEqual(aligned_hash, reordered_hash)

        changed_value_rows = [
            {**row} for row in aligned_rows
        ]
        changed_value_rows[0]["well_id"] = "W-UPDATED"
        changed_value_view = FakeFrame(
            changed_value_rows,
            aligned_view.columns,
        )
        changed_value_hash = deterministic_content_hash(
            changed_value_view,
            logical_table_name="raw.drilling_run",
            expected_business_columns=expected_business_columns,
            schema_error_code="ACTIVE_VIEW_CONTENT_HASH_SCHEMA_DRIFT",
        )
        self.assertNotEqual(aligned_hash, changed_value_hash)

        stale_view = FakeFrame(
            [
                {
                    "dataset_version": "v1.2.0",
                    "run_id": "R-001",
                    "trajectory_family": "build_hold",
                    "_release_id": "v1.2.0:manifest",
                }
            ],
            ["dataset_version", "run_id", "trajectory_family", "_release_id"],
        )
        with self.assertRaisesRegex(RuntimeError, "ACTIVE_VIEW_CONTENT_HASH_SCHEMA_DRIFT") as context:
            deterministic_content_hash(
                stale_view,
                logical_table_name="raw.drilling_run",
                expected_business_columns=expected_business_columns,
                schema_error_code="ACTIVE_VIEW_CONTENT_HASH_SCHEMA_DRIFT",
            )
        self.assertIn('"missing": ["well_id"]', str(context.exception))
        self.assertIn('"extra": ["trajectory_family"]', str(context.exception))

    def test_capture_verified_staged_table_returns_release_scoped_metadata(self) -> None:
        publication_tree = ast.parse(self.publication_source)
        function_node = next(
            node
            for node in publication_tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "capture_verified_staged_table"
        )
        isolated_module = ast.Module(body=[function_node], type_ignores=[])
        ast.fix_missing_locations(isolated_module)

        class FakeExpression:
            def __eq__(self, _other: object) -> "FakeExpression":
                return self

            def __and__(self, _other: object) -> "FakeExpression":
                return self

        class FakeFunctions:
            @staticmethod
            def col(_name: str) -> FakeExpression:
                return FakeExpression()

        class FakeDataFrame:
            def __init__(self, row_count: int) -> None:
                self._row_count = row_count

            def filter(self, _predicate: object) -> "FakeDataFrame":
                return self

            def count(self) -> int:
                return self._row_count

        class FakeCollectResult:
            def collect(self) -> list[dict[str, int]]:
                return [{"version": 11}]

        class FakeCatalog:
            @staticmethod
            def tableExists(table_name: str) -> bool:
                return table_name == "raw.__drilling_run_release_data"

        class FakeSpark:
            def __init__(self, frame: FakeDataFrame) -> None:
                self.catalog = FakeCatalog()
                self._frame = frame
                self.sql_queries: list[str] = []

            def table(self, table_name: str) -> FakeDataFrame:
                if table_name != "raw.__drilling_run_release_data":
                    raise AssertionError(f"unexpected table lookup: {table_name}")
                return self._frame

            def sql(self, query: str) -> FakeCollectResult:
                self.sql_queries.append(query)
                return FakeCollectResult()

        def require(condition: bool, code: str, detail: str) -> None:
            if not condition:
                raise AssertionError(f"{code}:{detail}")

        def require_unique(_frame: object, _keys: list[str], _code: str) -> None:
            return None

        fake_frame = FakeDataFrame(row_count=932)
        fake_spark = FakeSpark(fake_frame)

        namespace = {
            "spark": fake_spark,
            "F": FakeFunctions(),
            "RELEASE_ID": "v1.2.0:manifest",
            "STAGED_ROW_STATE": "STAGED",
            "EXPECTED_TABLE_ROWS": {"raw.drilling_run": 932},
            "TABLE_KEYS": {"raw.drilling_run": ["dataset_version", "run_id"]},
            "prepublication_hashes": {"raw.drilling_run": "abc123"},
            "EXPECTED_BUSINESS_COLUMNS": {"raw.drilling_run": ["dataset_version", "run_id"]},
            "json": json,
            "physical_table_for": lambda _logical: "raw.__drilling_run_release_data",
            "deterministic_content_hash": lambda _frame, **_kwargs: "abc123",
            "require": require,
            "require_unique": require_unique,
        }
        exec(compile(isolated_module, "<fabric_notebook>", "exec"), namespace)
        capture_verified_staged_table = namespace["capture_verified_staged_table"]

        metadata = capture_verified_staged_table(
            "raw.drilling_run",
            "ROW_COUNT_ERROR",
            "CONTENT_HASH_ERROR",
            "ACTIVE_VIEW",
        )

        self.assertEqual(
            {
                "physical_table": "raw.__drilling_run_release_data",
                "row_count": 932,
                "delta_version": 11,
                "business_content_sha256": "abc123",
            },
            metadata,
        )
        self.assertEqual(1, len(fake_spark.sql_queries))
        self.assertIn(
            "DESCRIBE HISTORY raw.__drilling_run_release_data LIMIT 1",
            fake_spark.sql_queries[0],
        )

    def test_explicit_schemas_and_quality_preservation_are_present(self) -> None:
        for fragment in [
            "T.StructType",
            "T.DecimalType(18, 2)",
            "MISSING_FORMATION",
            "INCONSISTENT_FORMATION_LABEL",
            "MISSING_BIT_IADC_CODE",
            "NON_POSITIVE_DURATION",
            "formation_name_raw",
            "quality_reason_codes",
            "_record_hash",
            "_processed_at_utc",
            '"nullValue": "__FABRIC_CONTRACT_NULL_SENTINEL__"',
            '"emptyValue": ""',
        ]:
            self.assertIn(fragment, self.source)
        self.assertNotIn("inferSchema", self.source)

    def test_excluded_analytical_language_is_absent(self) -> None:
        lowered = self.source.lower()
        for prohibited in ("prediction", "similarity", "forecast"):
            self.assertNotIn(prohibited, lowered)

    def test_repository_commit_metadata_is_verified_with_git_c(self) -> None:
        root = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        commits = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "log", "-3", "--oneline"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip().splitlines()
        self.assertEqual(str(PROJECT_ROOT), root)
        self.assertEqual(3, len(commits))


if __name__ == "__main__":
    unittest.main()
