import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate_manifest as validator  # noqa: E402


def canonical_bytes(document):
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def generated_example(schemas, schema, owner=None):
    owner = owner or schema
    if "$ref" in schema:
        target, target_owner = schemas._resolve_ref(schema["$ref"])
        return generated_example(schemas, target, target_owner)
    if "const" in schema:
        return copy.deepcopy(schema["const"])
    if "enum" in schema:
        return copy.deepcopy(schema["enum"][0])
    if "oneOf" in schema:
        return generated_example(schemas, schema["oneOf"][0], owner)
    if "anyOf" in schema:
        return generated_example(schemas, schema["anyOf"][0], owner)
    if "if" in schema:
        return {}
    if "allOf" in schema and "type" not in schema:
        values = [generated_example(schemas, item, owner) for item in schema["allOf"]]
        return values[0] if values else None

    expected = schema.get("type")
    if isinstance(expected, list):
        expected = "string" if "string" in expected else expected[0]
    if expected == "object":
        properties = schema.get("properties", {})
        return {
            key: generated_example(schemas, properties[key], owner)
            for key in schema.get("required", [])
        }
    if expected == "array":
        count = schema.get("minItems", 0)
        return [generated_example(schemas, schema["items"], owner) for _ in range(count)]
    if expected == "string":
        if schema.get("format") == "date-time":
            return "2026-10-28T12:00:00.000Z"
        if schema.get("format") == "uri":
            return "https://example.test/v1/items"
        pattern = schema.get("pattern", "")
        if "[0-9a-f]{64}" in pattern:
            return "a" * 64
        if "0|[1-9]" in pattern:
            return "0"
        return "safe_value"
    if expected == "integer":
        return max(0, schema.get("minimum", 0))
    if expected == "number":
        return 0
    if expected == "boolean":
        return False
    if expected == "null":
        return None
    if "pattern" in schema:
        return "approval.md"
    raise AssertionError(f"Cannot generate fixture from {owner}: {schema}")


class Task025ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = validator.SchemaSet(HERE)

    def artifact(self, schema_name):
        schema = self.schemas.documents[schema_name]
        value = generated_example(self.schemas, schema, schema_name)
        if schema_name == "diagnostic-capture.schema.json":
            value["diagnosis_status"] = "DIAGNOSIS_BLOCKED_DOCUMENTATION"
            value["request"]["normalized_uri"] = {
                "marker_type": "UNAVAILABLE",
                "reason_code": "NOT_DOCUMENTED",
                "source_reference": "offline-fixture",
            }
            value["source_tree_completeness"]["status"] = "NOT_ATTEMPTED"
            value["source_tree_completeness"]["continuation_state"] = "NOT_ATTEMPTED"
            value["acl_evidence"]["status"] = "NOT_ATTEMPTED"
        return value

    def assert_rejected(self, document, schema_name):
        with self.assertRaises(validator.ValidationError):
            validator.validate_artifact_bytes(canonical_bytes(document), schema_name, self.schemas)

    def test_schemas_parse_use_draft_2020_12_and_resolve_local_refs(self):
        self.assertEqual(
            set(self.schemas.documents),
            {
                "common.schema.json",
                "detached-hash-record.schema.json",
                "diagnostic-capture.schema.json",
                "redaction-entry.schema.json",
                "review-signature.schema.json",
                "sanitized-baseline.schema.json",
                "unavailable-marker.schema.json",
                "window-manifest.schema.json",
            },
        )
        self.schemas.validate_schema_set()

    def test_existing_contract_invariants_remain_intact(self):
        review_signature = self.schemas.documents["review-signature.schema.json"]
        self.assertIn("review_subject_type", review_signature["required"])
        self.assertEqual(
            review_signature["properties"]["review_subject_type"]["enum"],
            ["historical_artifact", "live_window"],
        )
        baseline = self.schemas.documents["sanitized-baseline.schema.json"]
        self.assertEqual(
            set(baseline["required"]),
            {
                "schema_version", "artifact_type", "generated_at", "window_manifest_sha256",
                "documentation_reconciliation_approval", "foundry", "data_agents", "source_trees",
                "identity_chain", "acl_evidence", "capacity_transitions", "requests", "redactions",
                "unavailable_fields", "hashes", "reviews",
            },
        )
        common = self.schemas.documents["common.schema.json"]["$defs"]
        self.assertEqual(common["unavailableMarker"]["properties"]["marker_type"]["const"], "UNAVAILABLE")
        self.assertEqual(common["redactedMarker"]["properties"]["marker_type"]["const"], "REDACTED")
        self.assertIn("NOT_APPLICABLE", common["unavailableMarker"]["properties"]["reason_code"]["enum"])
        self.assertIn("CAPABILITY_TOKEN", common["redactedMarker"]["properties"]["reason_code"]["enum"])
        manifest = self.schemas.documents["window-manifest.schema.json"]["properties"]
        self.assertEqual(manifest["cost_ceiling_decimal"]["type"], "string")
        self.assertIn("[0-9]", manifest["cost_ceiling_decimal"]["pattern"])
        detached = self.schemas.documents["detached-hash-record.schema.json"]
        self.assertEqual(
            set(detached["required"]),
            {"artifact_path", "artifact_sha256", "canonicalization_version", "computed_at", "computed_by"},
        )

        def assert_no_defaults(value):
            if isinstance(value, dict):
                self.assertNotIn("default", value)
                for child in value.values():
                    assert_no_defaults(child)
            elif isinstance(value, list):
                for child in value:
                    assert_no_defaults(child)

        for schema in self.schemas.documents.values():
            assert_no_defaults(schema)

    def test_valid_manifest_and_historical_detached_hash_fixtures(self):
        manifest_path = HERE / "fixtures" / "window-manifest.valid.json"
        manifest = validator.validate_manifest_bytes(manifest_path.read_bytes())
        self.assertEqual(manifest["window_id"], "offline-window-001")
        detached_path = HERE / "fixtures" / "detached-hash-record-historical.valid.json"
        detached = validator.validate_artifact_bytes(
            detached_path.read_bytes(),
            "detached-hash-record.schema.json",
            self.schemas,
        )
        self.assertNotIn("window_manifest_sha256", detached)

    def test_valid_generated_examples_cover_all_artifact_schemas(self):
        for schema_name in sorted(validator.SCHEMA_FILES):
            with self.subTest(schema=schema_name):
                document = self.artifact(schema_name)
                validator.validate_artifact_bytes(canonical_bytes(document), schema_name, self.schemas)

    def test_review_signature_historical_and_live_manifest_linkage(self):
        historical = self.artifact("review-signature.schema.json")
        historical["review_subject_type"] = "historical_artifact"
        historical["window_manifest_sha256"] = {
            "marker_type": "UNAVAILABLE",
            "reason_code": "NOT_DOCUMENTED",
            "source_reference": None,
        }
        validator.validate_artifact_bytes(
            canonical_bytes(historical),
            "review-signature.schema.json",
            self.schemas,
        )

        missing_subject_type = copy.deepcopy(historical)
        missing_subject_type.pop("review_subject_type")
        self.assert_rejected(missing_subject_type, "review-signature.schema.json")

        invalid_subject_type = copy.deepcopy(historical)
        invalid_subject_type["review_subject_type"] = "unknown"
        self.assert_rejected(invalid_subject_type, "review-signature.schema.json")

        historical_hash = copy.deepcopy(historical)
        historical_hash["window_manifest_sha256"] = "b" * 64
        validator.validate_artifact_bytes(
            canonical_bytes(historical_hash),
            "review-signature.schema.json",
            self.schemas,
        )

        live_hash = copy.deepcopy(historical)
        live_hash["review_subject_type"] = "live_window"
        live_hash["window_manifest_sha256"] = "a" * 64
        validator.validate_artifact_bytes(
            canonical_bytes(live_hash),
            "review-signature.schema.json",
            self.schemas,
        )

        live_missing = copy.deepcopy(live_hash)
        live_missing.pop("window_manifest_sha256")
        self.assert_rejected(live_missing, "review-signature.schema.json")

        live_marker = copy.deepcopy(live_hash)
        live_marker["window_manifest_sha256"] = historical["window_manifest_sha256"]
        self.assert_rejected(live_marker, "review-signature.schema.json")

        historical_wrong_reason = copy.deepcopy(historical)
        historical_wrong_reason["window_manifest_sha256"]["reason_code"] = "NOT_AUTHORIZED"
        self.assert_rejected(historical_wrong_reason, "review-signature.schema.json")

    def test_historical_review_marker_is_not_mistaken_for_live_baseline_linkage(self):
        baseline = self.artifact("sanitized-baseline.schema.json")
        review = self.artifact("review-signature.schema.json")
        review["review_subject_type"] = "historical_artifact"
        review["window_manifest_sha256"] = {
            "marker_type": "UNAVAILABLE",
            "reason_code": "NOT_DOCUMENTED",
            "source_reference": None,
        }
        baseline["reviews"] = [review]
        validator.validate_artifact_bytes(
            canonical_bytes(baseline),
            "sanitized-baseline.schema.json",
            self.schemas,
        )

        live_review = copy.deepcopy(review)
        live_review["review_subject_type"] = "live_window"
        live_review["window_manifest_sha256"] = baseline["window_manifest_sha256"]
        baseline["reviews"] = [live_review]
        validator.validate_artifact_bytes(
            canonical_bytes(baseline),
            "sanitized-baseline.schema.json",
            self.schemas,
        )

        mismatched_live_review = copy.deepcopy(live_review)
        mismatched_live_review["window_manifest_sha256"] = "b" * 64
        baseline["reviews"] = [mismatched_live_review]
        self.assert_rejected(baseline, "sanitized-baseline.schema.json")

    def test_manifest_required_fields_minimums_and_nonnegative_unique_sequences(self):
        valid = self.artifact("window-manifest.schema.json")
        for mutation in (
            lambda value: value.pop("purpose"),
            lambda value: value.update(resource_ids=[]),
            lambda value: value.update(caller_identities=[]),
            lambda value: value.update(operations=[]),
            lambda value: value["operations"][0].update(sequence=-1),
        ):
            candidate = copy.deepcopy(valid)
            mutation(candidate)
            with self.subTest(mutation=mutation):
                self.assert_rejected(candidate, "window-manifest.schema.json")

        duplicate = copy.deepcopy(valid)
        duplicate["operations"].append(copy.deepcopy(duplicate["operations"][0]))
        self.assert_rejected(duplicate, "window-manifest.schema.json")

        float_cost = copy.deepcopy(valid)
        float_cost["cost_ceiling_decimal"] = 0.25
        self.assert_rejected(float_cost, "window-manifest.schema.json")

    def test_calendar_invalid_timestamps_are_rejected(self):
        for timestamp in (
            "2026-00-15T12:00:00.000Z",
            "2026-02-31T12:00:00.000Z",
            "2026-04-31T12:00:00.000Z",
        ):
            candidate = self.artifact("window-manifest.schema.json")
            candidate["pause_deadline"] = timestamp
            with self.subTest(timestamp=timestamp):
                self.assert_rejected(candidate, "window-manifest.schema.json")

    def test_baseline_requires_hash_and_nonempty_required_collections(self):
        candidate = self.artifact("sanitized-baseline.schema.json")
        candidate["hashes"] = []
        self.assert_rejected(candidate, "sanitized-baseline.schema.json")

        candidate = self.artifact("sanitized-baseline.schema.json")
        candidate["reviews"] = []
        self.assert_rejected(candidate, "sanitized-baseline.schema.json")

        candidate = self.artifact("sanitized-baseline.schema.json")
        candidate["data_agents"][0]["definition_parts"] = []
        self.assert_rejected(candidate, "sanitized-baseline.schema.json")

    def test_public_primitives_are_bounded_and_floats_are_rejected(self):
        baseline = self.artifact("sanitized-baseline.schema.json")
        projection = {"json_path": "$.public.label", "value": "safe_label"}
        baseline["data_agents"][0]["public_projection"] = [projection]
        validator.validate_artifact_bytes(canonical_bytes(baseline), "sanitized-baseline.schema.json", self.schemas)

        for unsafe_value in (0.25, "Personal data with spaces and !", "safe_label\n"):
            candidate = copy.deepcopy(baseline)
            candidate["data_agents"][0]["public_projection"][0]["value"] = unsafe_value
            with self.subTest(value=unsafe_value):
                self.assert_rejected(candidate, "sanitized-baseline.schema.json")

    def test_diagnostic_uri_requires_normalized_scheme_authority_and_path(self):
        diagnostic = self.artifact("diagnostic-capture.schema.json")
        diagnostic["request"]["normalized_uri"] = "https://fabric.example.test/v1/items"
        validator.validate_artifact_bytes(canonical_bytes(diagnostic), "diagnostic-capture.schema.json", self.schemas)

        for unsafe_uri in (
            "https://user@fabric.example.test/v1/items",
            "https://fabric.example.test/v1/items?token=value",
            "https://fabric.example.test/v1/items#fragment",
        ):
            candidate = copy.deepcopy(diagnostic)
            candidate["request"]["normalized_uri"] = unsafe_uri
            with self.subTest(uri=unsafe_uri):
                self.assert_rejected(candidate, "diagnostic-capture.schema.json")

    def test_array_order_is_enforced_for_baseline_records(self):
        baseline = self.artifact("sanitized-baseline.schema.json")
        first = copy.deepcopy(baseline["requests"][0])
        first.update(started_at="2026-10-28T12:00:00.000Z", request_id="request-a")
        second = copy.deepcopy(first)
        second.update(started_at="2026-10-28T13:00:00.000Z", request_id="request-b")
        baseline["requests"] = [second, first]
        self.assert_rejected(baseline, "sanitized-baseline.schema.json")

    def test_diagnostic_part_array_order_is_enforced(self):
        diagnostic = self.artifact("diagnostic-capture.schema.json")
        part_schema = self.schemas.documents["diagnostic-capture.schema.json"]["properties"]["part_manifest"]["items"]
        first = generated_example(self.schemas, part_schema, "diagnostic-part")
        first.update(item_id="item-a", path="part-a")
        second = copy.deepcopy(first)
        second.update(item_id="item-b", path="part-b")
        diagnostic["part_manifest"] = [second, first]
        self.assert_rejected(diagnostic, "diagnostic-capture.schema.json")

    def test_nested_manifest_hash_linkage_is_required(self):
        baseline = self.artifact("sanitized-baseline.schema.json")
        baseline["data_agents"][0]["window_manifest_sha256"] = "b" * 64
        self.assert_rejected(baseline, "sanitized-baseline.schema.json")

    def test_external_manifest_hash_linkage_is_verified(self):
        manifest_path = HERE / "fixtures" / "window-manifest.valid.json"
        manifest_bytes = manifest_path.read_bytes()
        manifest = validator.validate_manifest_bytes(manifest_bytes)
        manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
        baseline = self.artifact("sanitized-baseline.schema.json")

        def bind(value):
            if isinstance(value, dict):
                if "window_manifest_sha256" in value:
                    value["window_manifest_sha256"] = manifest_hash
                if "window_id" in value:
                    value["window_id"] = manifest["window_id"]
                for child in value.values():
                    bind(child)
            elif isinstance(value, list):
                for child in value:
                    bind(child)

        bind(baseline)
        baseline["window_manifest_sha256"] = manifest_hash
        raw = canonical_bytes(baseline)
        validated = validator.validate_artifact_bytes(raw, "sanitized-baseline.schema.json", self.schemas)
        validator.validate_external_manifest(validated, manifest_bytes, manifest_path, self.schemas)

        wrong_hash = copy.deepcopy(baseline)
        def rebind_hash(value):
            if isinstance(value, dict):
                if "window_manifest_sha256" in value:
                    value["window_manifest_sha256"] = "c" * 64
                for child in value.values():
                    rebind_hash(child)
            elif isinstance(value, list):
                for child in value:
                    rebind_hash(child)

        rebind_hash(wrong_hash)
        wrong_hash["window_manifest_sha256"] = "c" * 64
        wrong_raw = canonical_bytes(wrong_hash)
        wrong_validated = validator.validate_artifact_bytes(
            wrong_raw,
            "sanitized-baseline.schema.json",
            self.schemas,
        )
        with self.assertRaises(validator.ValidationError):
            validator.validate_external_manifest(wrong_validated, manifest_bytes, manifest_path, self.schemas)

    def test_duplicate_keys_and_noncanonical_bytes_are_rejected(self):
        with self.assertRaises(validator.ValidationError):
            validator.validate_manifest_bytes(b'{"a":1,"a":2}\n')
        fixture = (HERE / "fixtures" / "window-manifest.valid.json").read_bytes()
        with self.assertRaises(validator.ValidationError):
            validator.validate_manifest_bytes(fixture.replace(b"\n", b"\r\n"))


if __name__ == "__main__":
    unittest.main()
