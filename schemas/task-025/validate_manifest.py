#!/usr/bin/env python3
"""Offline TASK-025 schema, canonicalization, and cross-record validator."""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit


SCHEMA_DIR = Path(__file__).resolve().parent
SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_FILES = {
    "window-manifest.schema.json",
    "diagnostic-capture.schema.json",
    "sanitized-baseline.schema.json",
    "redaction-entry.schema.json",
    "unavailable-marker.schema.json",
    "detached-hash-record.schema.json",
    "review-signature.schema.json",
}


class ValidationError(ValueError):
    """Raised when an artifact fails a schema or cross-record assertion."""


def _reject_constant(value: str):
    raise ValidationError(f"non-JSON numeric constant is not permitted: {value}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _load_json(raw: bytes):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValidationError("artifact must be UTF-8") from error
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, ValidationError) as error:
        raise ValidationError(f"invalid JSON: {error}") from error


def _canonical_bytes(document) -> bytes:
    try:
        return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValidationError(f"artifact cannot be canonically serialized: {error}") from error


def _require_canonical(raw: bytes, document) -> None:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValidationError("artifact must not have a UTF-8 BOM")
    if b"\r" in raw or not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise ValidationError("artifact must use LF and have exactly one trailing LF")
    if raw != _canonical_bytes(document):
        raise ValidationError("artifact does not match canonical UTF-8 JSON serialization")


def _type_matches(value, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
        )
    return False


def _json_equal(left, right) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(_json_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_json_equal(left[k], right[k]) for k in left)
    return left == right


def _resolve_pointer(document, pointer: str):
    if not pointer:
        return document
    if not pointer.startswith("/"):
        raise ValidationError(f"unsupported JSON Pointer fragment: #{pointer}")
    value = document
    for part in pointer[1:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        try:
            value = value[int(key)] if isinstance(value, list) else value[key]
        except (KeyError, IndexError, ValueError, TypeError) as error:
            raise ValidationError(f"unresolved JSON Pointer fragment: #{pointer}") from error
    return value


class SchemaSet:
    """Small, dependency-free validator for the JSON Schema subset used here."""

    def __init__(self, schema_dir: Path = SCHEMA_DIR):
        self.schema_dir = schema_dir
        self.documents = {}
        for path in sorted(schema_dir.glob("*.schema.json")):
            try:
                document = _load_json(path.read_bytes())
            except OSError as error:
                raise ValidationError(f"cannot read schema {path.name}: {error}") from error
            if not isinstance(document, dict) or document.get("$schema") != SCHEMA_DRAFT:
                raise ValidationError(f"{path.name} must declare JSON Schema Draft 2020-12")
            self.documents[path.name] = document
        if not self.documents:
            raise ValidationError("no TASK-025 schemas found")
        self.validate_schema_set()

    def validate_schema_set(self) -> None:
        known_keywords = {
            "$schema", "$id", "$comment", "$defs", "title", "type", "properties", "required",
            "items", "minItems", "maxItems", "minLength", "maxLength", "pattern",
            "minimum", "maximum", "const", "enum", "format", "$ref", "oneOf",
            "anyOf", "allOf", "if", "then", "else", "additionalProperties",
        }

        def inspect(schema, owner: str):
            if isinstance(schema, list):
                for child in schema:
                    inspect(child, owner)
                return
            if not isinstance(schema, dict):
                return
            unsupported = set(schema) - known_keywords
            if unsupported:
                raise ValidationError(f"{owner} uses unsupported schema keywords: {sorted(unsupported)}")
            if schema.get("type") == "object" and schema.get("additionalProperties") is not False:
                raise ValidationError(f"{owner} contains an object not closed with additionalProperties:false")
            reference = schema.get("$ref")
            if reference is not None:
                file_part, separator, fragment = reference.partition("#")
                file_part = file_part.removeprefix("./")
                if not file_part or file_part not in self.documents:
                    raise ValidationError(f"{owner} has a non-local or unresolved $ref: {reference}")
                _resolve_pointer(self.documents[file_part], fragment if separator else "")
            for key, value in schema.items():
                if key in {"properties", "$defs"} and isinstance(value, dict):
                    for child in value.values():
                        inspect(child, owner)
                elif key in {"items", "additionalProperties"} and isinstance(value, dict):
                    inspect(value, owner)
                elif key in {"oneOf", "anyOf", "allOf"}:
                    inspect(value, owner)
                elif key in {"if", "then", "else"} and isinstance(value, dict):
                    inspect(value, owner)

        for name, document in self.documents.items():
            inspect(document, name)

    def _resolve_ref(self, ref: str):
        file_part, separator, fragment = ref.partition("#")
        file_part = file_part.removeprefix("./")
        if not file_part or file_part not in self.documents:
            raise ValidationError(f"non-local or unresolved $ref: {ref}")
        target = _resolve_pointer(self.documents[file_part], fragment if separator else "")
        return target, file_part

    def validate_instance(self, instance, schema_name: str) -> None:
        if schema_name not in self.documents:
            raise ValidationError(f"unknown schema: {schema_name}")

        def check(value, schema, owner: str, path: str):
            if not isinstance(schema, dict):
                raise ValidationError(f"{owner} has a malformed schema at {path}")
            if "$ref" in schema:
                target, ref_owner = self._resolve_ref(schema["$ref"])
                check(value, target, ref_owner, path)
                siblings = {key: item for key, item in schema.items() if key != "$ref"}
                if siblings:
                    check(value, siblings, owner, path)
                return

            expected_type = schema.get("type")
            if expected_type is not None:
                expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
                if not any(_type_matches(value, item) for item in expected_types):
                    raise ValidationError(f"{path}: expected type {expected_type}")

            if "const" in schema and not _json_equal(value, schema["const"]):
                raise ValidationError(f"{path}: value does not match const")
            if "enum" in schema and not any(_json_equal(value, item) for item in schema["enum"]):
                raise ValidationError(f"{path}: value is not in enum")

            if isinstance(value, str):
                if len(value) < schema.get("minLength", 0):
                    raise ValidationError(f"{path}: string shorter than minLength")
                if len(value) > schema.get("maxLength", sys.maxsize):
                    raise ValidationError(f"{path}: string longer than maxLength")
                if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
                    raise ValidationError(f"{path}: string does not match pattern")
                if schema.get("format") == "date-time":
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", value) is None:
                        raise ValidationError(f"{path}: timestamp must be UTC with millisecond precision and Z")
                    try:
                        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
                    except ValueError as error:
                        raise ValidationError(f"{path}: invalid calendar timestamp") from error
                elif schema.get("format") == "uri":
                    self._validate_uri(value, path)
                elif schema.get("format") is not None:
                    raise ValidationError(f"{path}: unsupported format {schema['format']}")

            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if "minimum" in schema and value < schema["minimum"]:
                    raise ValidationError(f"{path}: number below minimum")
                if "maximum" in schema and value > schema["maximum"]:
                    raise ValidationError(f"{path}: number above maximum")

            if isinstance(value, list):
                if len(value) < schema.get("minItems", 0):
                    raise ValidationError(f"{path}: array shorter than minItems")
                if len(value) > schema.get("maxItems", sys.maxsize):
                    raise ValidationError(f"{path}: array longer than maxItems")
                if "items" in schema:
                    for index, item in enumerate(value):
                        check(item, schema["items"], owner, f"{path}[{index}]")

            if isinstance(value, dict):
                required = schema.get("required", [])
                for key in required:
                    if key not in value:
                        raise ValidationError(f"{path}: missing required property {key!r}")
                properties = schema.get("properties", {})
                for key, child in value.items():
                    if key in properties:
                        check(child, properties[key], owner, f"{path}.{key}")
                    elif schema.get("additionalProperties") is False:
                        raise ValidationError(f"{path}: unexpected property {key!r}")
                    elif isinstance(schema.get("additionalProperties"), dict):
                        check(child, schema["additionalProperties"], owner, f"{path}.{key}")

            for keyword in ("allOf", "anyOf", "oneOf"):
                if keyword not in schema:
                    continue
                outcomes = []
                for branch in schema[keyword]:
                    try:
                        check(value, branch, owner, path)
                        outcomes.append(True)
                    except ValidationError:
                        outcomes.append(False)
                count = sum(outcomes)
                valid = count == len(outcomes) if keyword == "allOf" else (
                    count >= 1 if keyword == "anyOf" else count == 1
                )
                if not valid:
                    raise ValidationError(f"{path}: {keyword} constraint failed")

            if "if" in schema:
                try:
                    check(value, schema["if"], owner, path)
                    conditional = schema.get("then")
                except ValidationError:
                    conditional = schema.get("else")
                if conditional is not None:
                    check(value, conditional, owner, path)

        check(instance, self.documents[schema_name], schema_name, "$")

    @staticmethod
    def _validate_uri(value: str, path: str) -> None:
        if any(character.isspace() for character in value) or "\\" in value:
            raise ValidationError(f"{path}: URI contains whitespace or a backslash")
        if "?" in value or "#" in value:
            raise ValidationError(f"{path}: normalized URI must not contain query or fragment")
        try:
            parsed = urlsplit(value)
            host = parsed.hostname
            _ = parsed.port
        except ValueError as error:
            raise ValidationError(f"{path}: malformed URI authority") from error
        if (
            not parsed.scheme
            or parsed.scheme != parsed.scheme.lower()
            or not parsed.netloc
            or not host
            or host != host.lower()
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.geturl() != value
        ):
            raise ValidationError(f"{path}: URI must be normalized scheme/authority/path only")
        if any(segment in {".", ".."} for segment in unquote(parsed.path).split("/")):
            raise ValidationError(f"{path}: URI path must not contain dot segments")


def _canonical_key(value):
    if value is None:
        return (0, "")
    if isinstance(value, dict):
        return (2, json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    if isinstance(value, bool):
        return (1, int(value))
    if isinstance(value, (str, int, float)):
        return (1, value)
    if isinstance(value, list):
        return (1, tuple(_canonical_key(item) for item in value))
    return (3, repr(value))


def _assert_sorted(records, key_fn, name: str) -> None:
    keys = [tuple(_canonical_key(item) for item in key_fn(record)) for record in records]
    if keys != sorted(keys):
        raise ValidationError(f"{name} must be in REQ-009 stable order")


def _identity_key(identity):
    app_id = identity["application_id"]
    return (
        identity["principal_type"],
        identity["tenant_id"],
        identity["object_id"],
        (0, "") if app_id is None else (1, app_id),
    )


def validate_manifest_semantics(document) -> None:
    resource_ids = document["resource_ids"]
    if resource_ids != sorted(resource_ids):
        raise ValidationError("resource_ids must be in lexicographic order")
    if len(resource_ids) != len(set(resource_ids)):
        raise ValidationError("resource_ids must not contain duplicates")

    for field in ("caller_identities", "reviewers"):
        keys = [_identity_key(identity) for identity in document[field]]
        if keys != sorted(keys):
            raise ValidationError(f"{field} must be ordered by principal_type, tenant_id, object_id, application_id")

    sequences = [operation["sequence"] for operation in document["operations"]]
    if any(sequence < 0 for sequence in sequences):
        raise ValidationError("operation sequence values must be nonnegative")
    if len(sequences) != len(set(sequences)):
        raise ValidationError("operation sequence values must be unique")
    if sequences != sorted(sequences):
        raise ValidationError("operations must be ordered by ascending sequence")

    for field in ("success_criteria", "stop_criteria"):
        if document[field] != sorted(document[field]):
            raise ValidationError(f"{field} must be in lexicographic order")


def _marker_sort_key(entry, unavailable=False):
    if unavailable:
        marker = entry["marker"]
        return entry["json_path"], marker["marker_type"], marker["reason_code"]
    return entry["json_path"], entry["marker_type"], entry["reason_code"]


def validate_artifact_semantics(document, schema_name: str) -> None:
    if schema_name == "window-manifest.schema.json":
        validate_manifest_semantics(document)
        return

    if schema_name == "sanitized-baseline.schema.json":
        _assert_sorted(document["data_agents"], lambda x: (x["item_id"],), "data_agents")
        _assert_sorted(document["source_trees"], lambda x: (x["item_id"],), "source_trees")
        for agent in document["data_agents"]:
            _assert_sorted(agent["definition_parts"], lambda x: (x["item_id"], x["path"]), "definition_parts")
            _assert_sorted(agent["public_projection"], lambda x: (x["json_path"],), "public_projection")
        for tree in document["source_trees"]:
            _assert_sorted(
                tree["nodes"],
                lambda x: (x["item_id"], x["parent_id"], x["source_type"], x["source_id"]),
                "source-tree nodes",
            )
            for node in tree["nodes"]:
                _assert_sorted(node["public_fields"], lambda x: (x["field_name"],), "source public_fields")
        for entry in document["acl_evidence"]["entries"]:
            _assert_sorted(
                entry["group_expansion"]["expanded_principal_ids"],
                lambda x: (x,),
                "expanded_principal_ids",
            )
        _assert_sorted(
            document["acl_evidence"]["documented_permission_requirements"],
            lambda x: (x["operation"], x["required_permission"], x["source_reference"]),
            "documented_permission_requirements",
        )
        _assert_sorted(
            document["acl_evidence"]["entries"],
            lambda x: (
                x["scope_type"], x["scope_id"], x["principal_type"], x["principal_id"],
                x["role"], x["inheritance_path"],
            ),
            "ACL entries",
        )
        _assert_sorted(document["capacity_transitions"], lambda x: (x["observed_at"], x["state"]), "capacity transitions")
        _assert_sorted(document["requests"], lambda x: (x["started_at"], x["request_id"]), "requests")
        _assert_sorted(document["redactions"], lambda x: _marker_sort_key(x), "redactions")
        _assert_sorted(document["unavailable_fields"], lambda x: _marker_sort_key(x, unavailable=True), "unavailable_fields")
        _assert_sorted(document["reviews"], lambda x: (x["reviewed_at"], x["reviewer_id"]), "reviews")
        _validate_shared_binding(document, "window_manifest_sha256", None)
    elif schema_name == "diagnostic-capture.schema.json":
        _assert_sorted(document["request"]["safe_request_header_names"], lambda x: (x,), "safe request header names")
        _assert_sorted(document["request"]["response_header_names"], lambda x: (x,), "response header names")
        _assert_sorted(document["operation_ids"], lambda x: (x,), "operation_ids")
        _assert_sorted(document["part_manifest"], lambda x: (x["item_id"], x["path"]), "part_manifest")
        _assert_sorted(document["lro_timeline"], lambda x: (x["observed_at"],), "lro_timeline")
        _assert_sorted(
            document["source_tree_completeness"]["nodes"],
            lambda x: (x["item_id"], x["parent_id"], x["source_type"], x["source_id"]),
            "source-tree nodes",
        )
        for node in document["source_tree_completeness"]["nodes"]:
            _assert_sorted(node["public_fields"], lambda x: (x["field_name"],), "source public_fields")
        for entry in document["acl_evidence"]["entries"]:
            _assert_sorted(
                entry["group_expansion"]["expanded_principal_ids"],
                lambda x: (x,),
                "expanded_principal_ids",
            )
        _assert_sorted(
            document["acl_evidence"]["documented_permission_requirements"],
            lambda x: (x["operation"], x["required_permission"], x["source_reference"]),
            "documented_permission_requirements",
        )
        _assert_sorted(
            document["acl_evidence"]["entries"],
            lambda x: (
                x["scope_type"], x["scope_id"], x["principal_type"], x["principal_id"],
                x["role"], x["inheritance_path"],
            ),
            "ACL entries",
        )
        _assert_sorted(
            document["capacity_transitions"],
            lambda x: (x["observed_at"], x["state"]),
            "capacity transitions",
        )
        _assert_sorted(document["redactions"], lambda x: _marker_sort_key(x), "redactions")
        _assert_sorted(document["unavailable_fields"], lambda x: _marker_sort_key(x, unavailable=True), "unavailable_fields")
        _validate_shared_binding(document, "window_manifest_sha256", document["window_id"])
        tree = document["source_tree_completeness"]
        if tree["status"] == "COMPLETE" and not tree["nodes"]:
            raise ValidationError("a COMPLETE source tree must contain at least one node")
        if tree["status"] == "COMPLETE" and tree["continuation_state"] != "COMPLETE":
            raise ValidationError("a COMPLETE source tree must have COMPLETE continuation_state")
        acl = document["acl_evidence"]
        if acl["status"] == "COMPLETE" and (
            not acl["entries"] or not acl["documented_permission_requirements"]
        ):
            raise ValidationError("COMPLETE ACL evidence requires entries and documented permission requirements")
        if document["decode_status"] == "SUCCEEDED" and not document["part_manifest"]:
            raise ValidationError("successful decoding requires at least one definition part")
    elif schema_name == "detached-hash-record.schema.json":
        if "window_manifest_sha256" in document:
            raise ValidationError("detached hash records use the approved five-field contract without window linkage")
    elif schema_name == "review-signature.schema.json":
        scope = document["review_subject_type"]
        manifest_hash = document["window_manifest_sha256"]
        if scope == "live_window":
            if not isinstance(manifest_hash, str) or re.fullmatch(r"[0-9a-f]{64}", manifest_hash) is None:
                raise ValidationError("live_window reviews require a concrete lowercase SHA-256 manifest hash")
        elif isinstance(manifest_hash, dict):
            expected_marker = {
                "marker_type": "UNAVAILABLE",
                "reason_code": "NOT_DOCUMENTED",
                "source_reference": manifest_hash.get("source_reference"),
            }
            if manifest_hash != expected_marker:
                raise ValidationError(
                    "historical_artifact reviews require the exact UNAVAILABLE/NOT_DOCUMENTED marker"
                )


def _validate_shared_binding(document, hash_field: str, expected_window_id):
    manifest_hash = document[hash_field]
    window_ids = set()

    def visit(value):
        if isinstance(value, dict):
            historical_review = value.get("review_subject_type") == "historical_artifact"
            if (
                hash_field in value
                and value[hash_field] != manifest_hash
                and not historical_review
            ):
                raise ValidationError(f"nested {hash_field} does not match the top-level binding")
            if "window_id" in value and isinstance(value["window_id"], str):
                window_ids.add(value["window_id"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(document)
    if expected_window_id is not None:
        window_ids.add(expected_window_id)
    if len(window_ids) > 1:
        raise ValidationError("contributing live records do not share one window_id")
    return window_ids


def _schema_for_document(document, path: Path) -> str:
    if path.name in SCHEMA_FILES:
        return path.name
    artifact_type = document.get("artifact_type") if isinstance(document, dict) else None
    by_type = {
        "TASK-025_DIAGNOSTIC_CAPTURE": "diagnostic-capture.schema.json",
        "TASK-025_SANITIZED_BASELINE": "sanitized-baseline.schema.json",
    }
    if artifact_type in by_type:
        return by_type[artifact_type]
    if isinstance(document, dict) and "manifest_schema_version" in document:
        return "window-manifest.schema.json"
    if isinstance(document, dict) and "artifact_path" in document and "artifact_sha256" in document:
        return "detached-hash-record.schema.json"
    if isinstance(document, dict) and "reviewer_id" in document:
        return "review-signature.schema.json"
    if isinstance(document, dict) and "marker_type" in document:
        return "unavailable-marker.schema.json" if document.get("marker_type") == "UNAVAILABLE" else "redaction-entry.schema.json"
    raise ValidationError(f"cannot infer schema for {path.name}; pass --schema explicitly")


def validate_artifact_bytes(raw: bytes, schema_name: str, schemas: SchemaSet | None = None):
    schemas = schemas or SchemaSet()
    document = _load_json(raw)
    _require_canonical(raw, document)
    schemas.validate_instance(document, schema_name)
    validate_artifact_semantics(document, schema_name)
    return document


def validate_manifest_bytes(raw: bytes) -> dict:
    """Backward-compatible entry point for callers validating window manifests."""
    return validate_artifact_bytes(raw, "window-manifest.schema.json")


def validate_external_manifest(document, raw: bytes, manifest_path: Path, schemas: SchemaSet):
    manifest_document = _load_json(raw)
    _require_canonical(raw, manifest_document)
    schemas.validate_instance(manifest_document, "window-manifest.schema.json")
    validate_manifest_semantics(manifest_document)
    actual_hash = hashlib.sha256(raw).hexdigest()
    if document.get("window_manifest_sha256") != actual_hash:
        raise ValidationError("artifact window_manifest_sha256 does not match the supplied manifest bytes")
    _validate_shared_binding(
        document,
        "window_manifest_sha256",
        manifest_document["window_id"],
    )
    if "window_id" in document and document["window_id"] != manifest_document["window_id"]:
        raise ValidationError("artifact window_id does not match the supplied manifest")
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="canonical artifact JSON (or TASK-025 schema JSON)")
    parser.add_argument("--schema", choices=sorted(SCHEMA_FILES), help="schema to use when it cannot be inferred")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="canonical window manifest to verify shared hash linkage for baseline/diagnostic artifacts",
    )
    args = parser.parse_args()

    schemas = SchemaSet()
    raw = args.artifact.read_bytes()
    if args.artifact.name.endswith(".schema.json"):
        document = _load_json(raw)
        if args.artifact.name not in schemas.documents:
            raise ValidationError(f"unknown TASK-025 schema file: {args.artifact.name}")
        schemas.validate_schema_set()
        print(f"Draft 2020-12 schema structure and local references passed: {args.artifact.name}")
        return

    document = _load_json(raw)
    schema_name = args.schema or _schema_for_document(document, args.artifact)
    document = validate_artifact_bytes(raw, schema_name, schemas)
    is_live_evidence = schema_name in {
        "sanitized-baseline.schema.json",
        "diagnostic-capture.schema.json",
    }
    if is_live_evidence and not args.manifest:
        raise ValidationError("baseline and diagnostic evidence require --manifest for external hash verification")
    if args.manifest:
        if not is_live_evidence:
            raise ValidationError("--manifest is only valid for baseline or diagnostic artifacts")
        validate_external_manifest(document, args.manifest.read_bytes(), args.manifest, schemas)
    print(f"Canonical {schema_name} validation passed.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValidationError) as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
