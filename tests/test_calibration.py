"""Tests for the fail-closed local MCP calibration workflow."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import jsonschema
import pytest

from calibration import config, evidence, identity, invocation, scoring


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / ".test-artifacts" / "calibration"
SCHEMAS = ROOT / "calibration" / "schemas"
TEST_DATA_AGENT_ID = "11111111-2222-4333-8444-555555555555"
TEST_APPROVED_UPN = "@".join(("approved-user", "example.invalid"))
TEST_OTHER_UPN = "@".join(("other-user", "example.invalid"))
TEST_APPROVED_OBJECT_ID = "abcdefab-cdef-4abc-8def-abcdefabcdef"
TEST_OTHER_OBJECT_ID = "abcdefab-cdef-4abc-8def-abcdefabcdee"
TARGET = config.bind_approved_data_agent(
    TEST_DATA_AGENT_ID,
    TEST_DATA_AGENT_ID,
)


@pytest.fixture(autouse=True)
def clean_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.APPROVED_USER_PRINCIPAL_NAME_ENV, TEST_APPROVED_UPN)
    monkeypatch.setenv(
        config.APPROVED_USER_OBJECT_ID_ENV,
        TEST_APPROVED_OBJECT_ID,
    )
    shutil.rmtree(ARTIFACTS, ignore_errors=True)
    ARTIFACTS.mkdir(parents=True)
    yield
    shutil.rmtree(ARTIFACTS, ignore_errors=True)


def _run_manifest() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "run_id": "20261024T230000Z-1234abcd",
        "mode": "calibration",
        "status": "RUNNING",
        "started_at_utc": "2026-10-24T23:00:00Z",
        "expires_at_utc": "2027-01-22T23:00:00Z",
        "retention_days": config.RETENTION_DAYS,
        "workspace_id": config.WORKSPACE_ID,
        "data_agent_id": TARGET.data_agent_id,
        "model_id": config.MODEL_ID,
        "endpoint": TARGET.mcp_endpoint,
        "versions": invocation._fixed_versions(),
        "case_count": config.EXPECTED_CASE_COUNT,
        "attempts_per_case": config.EXPECTED_ATTEMPTS_PER_CASE,
        "authentication": "AzureCliCredential delegated user",
        "verified_identity": identity._identity_manifest(),
        "credentials_persisted": False,
        "cost_usd": None,
    }


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        " ",
        "not-a-upn",
        "@",
        "@".join(("user", "domain")),
        " " + TEST_APPROVED_UPN,
        TEST_APPROVED_UPN + "\n",
        TEST_APPROVED_UPN.replace("@", "@@"),
        "@".join(("x" * 255, "example.invalid")),
    ],
)
def test_approved_user_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    value: str | None,
) -> None:
    if value is None:
        monkeypatch.delenv(config.APPROVED_USER_PRINCIPAL_NAME_ENV)
    else:
        monkeypatch.setenv(config.APPROVED_USER_PRINCIPAL_NAME_ENV, value)
    monkeypatch.setattr(
        identity.shutil,
        "which",
        lambda _: pytest.fail("Configuration must fail before Azure CLI access"),
    )
    with pytest.raises(ValueError, match=config.APPROVED_USER_PRINCIPAL_NAME_ENV):
        config.approved_user_principal_name()
    with pytest.raises(
        identity.IdentityVerificationFailure,
        match=config.APPROVED_USER_PRINCIPAL_NAME_ENV,
    ):
        identity.verify_delegated_identity()


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "invalid",
        "00000000-0000-0000-0000-000000000000",
        TEST_APPROVED_OBJECT_ID.upper(),
        f" {TEST_APPROVED_OBJECT_ID}",
    ],
)
def test_approved_object_id_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    value: str | None,
) -> None:
    if value is None:
        monkeypatch.delenv(config.APPROVED_USER_OBJECT_ID_ENV)
    else:
        monkeypatch.setenv(config.APPROVED_USER_OBJECT_ID_ENV, value)
    monkeypatch.setattr(
        identity.shutil,
        "which",
        lambda _: pytest.fail("Configuration must fail before Azure CLI access"),
    )
    with pytest.raises(ValueError, match=config.APPROVED_USER_OBJECT_ID_ENV):
        config.approved_user_object_id()
    with pytest.raises(
        identity.IdentityVerificationFailure,
        match=config.APPROVED_USER_OBJECT_ID_ENV,
    ):
        identity.verify_delegated_identity()


def test_configured_approval_is_not_cached_or_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured = TEST_OTHER_UPN.upper()
    monkeypatch.setenv(config.APPROVED_USER_PRINCIPAL_NAME_ENV, configured)
    assert config.approved_user_principal_name() == configured
    verified = _verify_identity(monkeypatch)
    assert verified.manifest["user_principal_name"] == configured
    verified.close()
    _mock_cli(monkeypatch, upn=configured.lower())
    with pytest.raises(identity.IdentityVerificationFailure):
        identity.verify_delegated_identity()


def test_manifest_accepts_configured_synthetic_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(config.APPROVED_USER_PRINCIPAL_NAME_ENV, TEST_OTHER_UPN)
    monkeypatch.setenv(config.APPROVED_USER_OBJECT_ID_ENV, TEST_OTHER_OBJECT_ID)
    manifest = _run_manifest()
    manifest["verified_identity"] = identity._identity_manifest()

    evidence.validate_schema(manifest, "run-manifest.schema.json")


@pytest.mark.parametrize("boundary", ["validator", "producer", "consumer"])
@pytest.mark.parametrize(
    "violation",
    [
        "missing_upn_config",
        "missing_object_id_config",
        "wrong_upn",
        "wrong_object_id",
        "wrong_digest",
    ],
)
def test_manifest_identity_boundary_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
    violation: str,
) -> None:
    manifest = _run_manifest()
    claims = manifest["verified_identity"]
    if violation == "wrong_upn":
        monkeypatch.setenv(config.APPROVED_USER_PRINCIPAL_NAME_ENV, TEST_OTHER_UPN)
        claims.update(identity._identity_manifest())
        monkeypatch.setenv(config.APPROVED_USER_PRINCIPAL_NAME_ENV, TEST_APPROVED_UPN)
    elif violation == "wrong_object_id":
        claims["object_id"] = TEST_OTHER_OBJECT_ID
        canonical = {
            key: value for key, value in claims.items() if key != "claims_sha256"
        }
        claims["claims_sha256"] = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    elif violation == "wrong_digest":
        claims["claims_sha256"] = "0" * 64
    elif violation == "missing_upn_config":
        monkeypatch.delenv(config.APPROVED_USER_PRINCIPAL_NAME_ENV)
    else:
        monkeypatch.delenv(config.APPROVED_USER_OBJECT_ID_ENV)
    with pytest.raises((ValueError, identity.IdentityVerificationFailure)):
        if boundary == "validator":
            evidence.validate_schema(manifest, "run-manifest.schema.json")
        elif boundary == "producer":
            monkeypatch.setattr(evidence, "RUNS_ROOT", ARTIFACTS / "runs")
            fake_identity = SimpleNamespace(manifest=claims)
            asyncio.run(invocation._run_calibration_verified(fake_identity, TARGET))
            pytest.fail("Invalid identity reached calibration")
        else:
            runs = ARTIFACTS / "runs"
            run_dir = runs / manifest["run_id"]
            run_dir.mkdir(parents=True)
            (run_dir / "metadata.json").write_text(json.dumps(manifest))
            monkeypatch.setattr(scoring, "RUNS_ROOT", runs)
            scoring.prepare_grading_template(manifest["run_id"])
    if boundary == "producer":
        assert not list(ARTIFACTS.rglob("metadata.json"))
        assert not list(ARTIFACTS.rglob("attempts.jsonl"))
    if boundary == "consumer":
        assert not (run_dir / "grading-template.json").exists()


@pytest.mark.parametrize("upn", [None, "", "invalid", TEST_APPROVED_UPN + "\n"])
def test_manifest_schema_requires_structured_upn(upn: str | None) -> None:
    manifest = _run_manifest()
    claims = manifest["verified_identity"]
    if upn is None:
        del claims["user_principal_name"]
    else:
        claims["user_principal_name"] = upn
    with pytest.raises(jsonschema.ValidationError):
        evidence.validate_schema(manifest, "run-manifest.schema.json")


@pytest.mark.parametrize(
    "object_id",
    [None, "", "invalid", "not-a-uuid"],
)
def test_manifest_schema_requires_structured_object_id(
    object_id: str | None,
) -> None:
    manifest = _run_manifest()
    claims = manifest["verified_identity"]
    if object_id is None:
        del claims["object_id"]
    else:
        claims["object_id"] = object_id
    with pytest.raises(jsonschema.ValidationError):
        evidence.validate_schema(manifest, "run-manifest.schema.json")


def test_target_requires_exact_approval_and_derives_fixed_endpoint() -> None:
    config.validate_fixed_endpoint(TARGET)
    assert not hasattr(config, "DATA_AGENT_ID")
    assert not hasattr(config, "MCP_ENDPOINT")
    assert not hasattr(config, "DELETE_ENDPOINT")
    expected_data_agent_version = "da_drillrun_summary-definition-v1.0.1"
    assert config.DATA_AGENT_VERSION == expected_data_agent_version
    assert invocation._fixed_versions()["data_agent"] == expected_data_agent_version
    for schema_name in ("attempt.schema.json", "run-manifest.schema.json"):
        schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
        assert schema["properties"]["versions"]["properties"]["data_agent"] == {
            "const": expected_data_agent_version
        }
        agent_property = schema["properties"]["data_agent_id"]
        assert agent_property["type"] == "string"
        assert "pattern" in agent_property
        assert "const" not in agent_property
    manifest_schema = json.loads(
        (SCHEMAS / "run-manifest.schema.json").read_text(encoding="utf-8")
    )
    assert "pattern" in manifest_schema["properties"]["endpoint"]
    assert "const" not in manifest_schema["properties"]["endpoint"]
    upn_property = manifest_schema["properties"]["verified_identity"][
        "properties"
    ]["user_principal_name"]
    assert upn_property["type"] == "string"
    assert "const" not in upn_property
    object_id_property = manifest_schema["properties"]["verified_identity"][
        "properties"
    ]["object_id"]
    assert object_id_property["type"] == "string"
    assert "pattern" in object_id_property
    assert "const" not in object_id_property
    assert "not" not in object_id_property
    assert TARGET.mcp_endpoint == (
        "https://api.fabric.microsoft.com/v1/mcp/workspaces/"
        "4e1977a8-d7ff-487e-b42d-c4b3bc118f3d/dataagents/"
        f"{TEST_DATA_AGENT_ID}/agent"
    )
    for endpoint in (
        TARGET.mcp_endpoint.replace("https://", "http://"),
        TARGET.mcp_endpoint + "/",
        TARGET.mcp_endpoint + "?redirect=true",
        TARGET.mcp_endpoint.replace(
            TEST_DATA_AGENT_ID,
            "66666666-7777-4888-8999-aaaaaaaaaaaa",
        ),
    ):
        with pytest.raises(ValueError):
            config.validate_fixed_endpoint(TARGET, endpoint)

    invalid_bindings = (
        ("not-a-uuid", "not-a-uuid"),
        (
            "00000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000000",
        ),
        (
            "ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF",
            "ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF",
        ),
        (
            TEST_DATA_AGENT_ID,
            "66666666-7777-4888-8999-aaaaaaaaaaaa",
        ),
    )
    for runtime_id, approved_id in invalid_bindings:
        with pytest.raises(ValueError):
            config.bind_approved_data_agent(runtime_id, approved_id)


def test_approved_evaluation_loads_36_question_only_invocations() -> None:
    cases = invocation.load_invocation_cases()
    assert len(cases) == 36
    assert all(case.attempts == 3 for case in cases)
    assert set(cases[0].__dict__) == {"case_id", "question", "attempts"}

    source = (ROOT / "calibration" / "invocation.py").read_text(encoding="utf-8")
    assert "--workspace" not in source
    assert "--endpoint" not in source
    assert "--data-agent-id" in source
    assert "--approved-data-agent-id" in source
    assert "getenv" not in source
    assert "environ" not in source


def test_tool_validation_requires_one_string_argument() -> None:
    valid = SimpleNamespace(
        tools=[
            SimpleNamespace(
                name="ask",
                inputSchema={"properties": {"question": {"type": "string"}}},
            )
        ]
    )
    assert invocation._validate_tool(valid) == ("ask", "question")
    with pytest.raises(invocation.HardGateFailure):
        invocation._validate_tool(SimpleNamespace(tools=[]))
    with pytest.raises(invocation.HardGateFailure):
        invocation._validate_tool(
            SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="ask",
                        inputSchema={
                            "properties": {
                                "question": {"type": "string"},
                                "expected": {"type": "string"},
                            }
                        },
                    )
                ]
            )
        )


def test_response_hard_gates() -> None:
    invocation._detect_response_hard_gate(
        f"{config.SYNTHETIC_LABEL}\nAnswer"
    )
    invocation._detect_response_hard_gate(config.SYNTHETIC_LABEL)
    with pytest.raises(invocation.HardGateFailure) as missing:
        invocation._detect_response_hard_gate("Answer without the label")
    assert missing.value.reason_code == "missing_synthetic_label"
    with pytest.raises(invocation.HardGateFailure) as misplaced:
        invocation._detect_response_hard_gate(
            f"Answer\n{config.SYNTHETIC_LABEL}"
        )
    assert misplaced.value.reason_code == "missing_synthetic_label"
    with pytest.raises(invocation.HardGateFailure) as sensitive:
        invocation._detect_response_hard_gate(
            f"{config.SYNTHETIC_LABEL}\nAuthorization: Bearer abc.def.ghi"
        )
    assert sensitive.value.reason_code == "sensitive_material_detected"
    assert sensitive.value.security_category == "bearer_token"


@pytest.mark.parametrize(
    "response",
    [
        f"\n{config.SYNTHETIC_LABEL}\nAnswer",
        f"Answer\n{config.SYNTHETIC_LABEL}",
        f" {config.SYNTHETIC_LABEL}\nAnswer",
        f"{config.SYNTHETIC_LABEL.replace(' • ', ' - ')}\nAnswer",
        f"{config.SYNTHETIC_LABEL.replace(' / ', '/')}\nAnswer",
        f"{config.SYNTHETIC_LABEL.lower()}\nAnswer",
        "DATOS SINTÉTICOS • v1.0.0 • SOLO RESUMEN HISTÓRICO / DESARROLLO\nAnswer",
    ],
)
def test_response_hard_gate_rejects_nonexact_or_misplaced_label(
    response: str,
) -> None:
    with pytest.raises(invocation.HardGateFailure) as failure:
        invocation._detect_response_hard_gate(response)
    assert failure.value.reason_code == "missing_synthetic_label"


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (config.SYNTHETIC_LABEL, True),
        (f"{config.SYNTHETIC_LABEL}\nAnswer", True),
        (f"\n{config.SYNTHETIC_LABEL}\nAnswer", False),
        (f"Answer\n{config.SYNTHETIC_LABEL}", False),
        (f" {config.SYNTHETIC_LABEL}\nAnswer", False),
        (f"{config.SYNTHETIC_LABEL.replace(' • ', ' - ')}\nAnswer", False),
        (f"{config.SYNTHETIC_LABEL.replace(' / ', '/')}\nAnswer", False),
        (f"{config.SYNTHETIC_LABEL.lower()}\nAnswer", False),
    ],
)
def test_scorer_requires_exact_synthetic_label_first_line(
    response: str,
    expected: bool,
) -> None:
    assert scoring._has_exact_synthetic_label_first_line(response) is expected


@pytest.mark.parametrize(
    ("sensitive", "category"),
    [
        ("eyJhbGciOiJub25lIn0.eyJvaWQiOiJmYWtlIn0.signature", "jwt"),
        ("-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----", "private_key"),
        ("Bearer fake_access_token_value", "bearer_token"),
    ],
)
def test_sensitive_response_never_reaches_evidence_or_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    sensitive: str,
    category: str,
) -> None:
    monkeypatch.setattr(evidence, "RUNS_ROOT", ARTIFACTS / "runs")

    class FakeIdentity:
        manifest = identity._identity_manifest()

        def close(self) -> None:
            pass

    async def fake_invoke(
        question: str,
        verified_identity: object,
        target: config.CalibrationTarget,
    ) -> str:
        del question, verified_identity, target
        return f"{config.SYNTHETIC_LABEL}\n{sensitive}"

    monkeypatch.setattr(invocation, "invoke_once", fake_invoke)
    result = asyncio.run(
        invocation._run_calibration_verified(FakeIdentity(), TARGET)
    )
    assert result == 2

    written = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ARTIFACTS / "runs").rglob("*")
        if path.is_file()
    )
    captured = capsys.readouterr()
    assert sensitive not in written
    assert sensitive not in captured.out
    assert sensitive not in captured.err

    attempt_path = next((ARTIFACTS / "runs").glob("*/attempts.jsonl"))
    attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    assert attempt["response_text"] is None
    assert attempt["security_failure"] == {"pattern_category": category}
    assert attempt["error"]["message"] == (
        "Sensitive content was blocked before persistence"
    )


def test_sensitive_exception_never_reaches_evidence_or_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(evidence, "RUNS_ROOT", ARTIFACTS / "runs")
    sensitive = "client_secret=do-not-write-this-value"

    class FakeIdentity:
        manifest = identity._identity_manifest()

    async def fake_invoke(
        question: str,
        verified_identity: object,
        target: config.CalibrationTarget,
    ) -> str:
        del question, verified_identity, target
        raise RuntimeError(f"transport failed: {sensitive}")

    monkeypatch.setattr(invocation, "invoke_once", fake_invoke)
    result = asyncio.run(
        invocation._run_calibration_verified(FakeIdentity(), TARGET)
    )
    assert result == 2

    written = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ARTIFACTS / "runs").rglob("*")
        if path.is_file()
    )
    captured = capsys.readouterr()
    assert sensitive not in written
    assert sensitive not in captured.out
    assert sensitive not in captured.err
    attempt_path = next((ARTIFACTS / "runs").glob("*/attempts.jsonl"))
    attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    assert attempt["security_failure"] == {
        "pattern_category": "credential_assignment"
    }


def test_evidence_writer_refuses_sensitive_values() -> None:
    target = ARTIFACTS / "blocked.json"
    with pytest.raises(ValueError, match="jwt"):
        evidence.write_json(
            target,
            {"response_text": "eyJhbGciOiJub25lIn0.eyJvaWQiOiJmYWtlIn0.signature"},
        )
    assert not target.exists()
    adversarial = [
        ({"client_secret": "not-a-real-secret"}, "sensitive_key"),
        ('{"api_key":"not-a-real-api-key"}', "credential_assignment"),
        ("Bear" + "er not-a-real-bearer-token", "bearer_token"),
        (
            ".".join(
                ("eyJhbGciOiJub25lIn0", "eyJzdWIiOiJ0ZXN0In0", "signature")
            ),
            "jwt",
        ),
        ("-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----", "private_key"),
        (
            "https://storage.example.invalid/container?sv=2025-01-01&sp=r&se="
            "2030-01-01T00%3A00%3A00Z&sr=b&sig=not-a-real-signature",
            "azure_sas",
        ),
        (
            "DefaultEndpointsProtocol=https;AccountName=example;"
            "AccountKey=not-a-real-account-key;EndpointSuffix=core.windows.net",
            "connection_string",
        ),
        ("Cookie: sessionid=not-a-real-session; theme=dark", "cookie"),
        (
            base64.b64encode(b"client_secret=not-a-real-secret").decode(),
            "base64_credential",
        ),
        (
            {"response": SimpleNamespace(error={"password": "not-a-real-password"})},
            "sensitive_key",
        ),
        (
            "Qz9wNG1UMFZ4UjdLYkYyV3pONkhlUThTYUR5SjV1TG9HaUE",
            "opaque_token",
        ),
    ]
    for value, category in adversarial:
        _check_recursive_detector_blocks_adversarial_secret_forms(value, category)
    for value in (
        "aGVsbG8gd29ybGQ=",
        "4e1977a8-d7ff-487e-b42d-c4b3bc118f3d",
        "f" * 64,
        "summary-v1.0.0-A01",
        {"token_count": 42, "session_duration_seconds": 10},
    ):
        _check_recursive_detector_allows_benign_base64_and_ids(value)
    _check_recursive_detector_handles_cycles_without_looping()


@pytest.mark.parametrize(
    ("value", "category"),
    [
        ({"client_secret": "not-a-real-secret"}, "sensitive_key"),
        ({"outer": [{"headers": {"Authorization": "Bearer not-a-real-token"}}]}, "sensitive_key"),
        ('{"api_key":"not-a-real-api-key"}', "credential_assignment"),
        ("Bearer not-a-real-bearer-token", "bearer_token"),
        ("eyJhbGciOiJub25lIn0.eyJzdWIiOiJ0ZXN0In0.signature", "jwt"),
        ("-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----", "private_key"),
        (
            "https://storage.example.invalid/container?sv=2025-01-01&sp=r&se="
            "2030-01-01T00%3A00%3A00Z&sr=b&sig=not-a-real-signature",
            "azure_sas",
        ),
        (
            "DefaultEndpointsProtocol=https;AccountName=example;"
            "AccountKey=not-a-real-account-key;EndpointSuffix=core.windows.net",
            "connection_string",
        ),
        (
            "Server=tcp:example.invalid;User ID=test;Password=not-a-real-password;"
            "Encrypt=true",
            "connection_string",
        ),
        ("Cookie: sessionid=not-a-real-session; theme=dark", "cookie"),
        (
            base64.b64encode(b"client_secret=not-a-real-secret").decode(),
            "base64_credential",
        ),
        (
            {"response": SimpleNamespace(error={"password": "not-a-real-password"})},
            "sensitive_key",
        ),
        (
            "Qz9wNG1UMFZ4UjdLYkYyV3pONkhlUThTYUR5SjV1TG9HaUE",
            "opaque_token",
        ),
    ],
)
def _check_recursive_detector_blocks_adversarial_secret_forms(
    value: object,
    category: str,
) -> None:
    assert evidence.sensitive_material_category(value) == category
    json_target = ARTIFACTS / "blocked.json"
    jsonl_target = ARTIFACTS / "blocked.jsonl"
    with pytest.raises(ValueError, match=category):
        evidence.write_json(json_target, {"payload": value})
    with pytest.raises(ValueError, match=category):
        evidence.append_jsonl(jsonl_target, {"payload": value})
    assert not json_target.exists()
    assert not jsonl_target.exists()


@pytest.mark.parametrize(
    "value",
    [
        "aGVsbG8gd29ybGQ=",
        "4e1977a8-d7ff-487e-b42d-c4b3bc118f3d",
        "f" * 64,
        "summary-v1.0.0-A01",
        {"token_count": 42, "session_duration_seconds": 10},
        {"encoded_label": base64.b64encode(b"synthetic calibration data").decode()},
    ],
)
def _check_recursive_detector_allows_benign_base64_and_ids(value: object) -> None:
    assert evidence.sensitive_material_category(value) is None


def _check_recursive_detector_handles_cycles_without_looping() -> None:
    value: dict[str, object] = {"label": "safe"}
    value["self"] = value
    assert evidence.sensitive_material_category(value) is None


def test_secure_evidence_permissions_and_stop_marker(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(evidence, "RUNS_ROOT", ARTIFACTS / "runs")
    _, run_dir, _, _ = evidence.create_run_directory()
    evidence.write_json(run_dir / "record.json", {"cost_usd": None})
    evidence.write_stop_marker(
        run_dir,
        reason_code="test_failure",
        case_id="summary-v1.0.0-A01",
        attempt=1,
    )
    assert os.stat(run_dir).st_mode & 0o777 == 0o700
    assert os.stat(run_dir / "record.json").st_mode & 0o777 == 0o600
    assert os.stat(run_dir / "STOP_REQUIRED.json").st_mode & 0o777 == 0o600
    stop = json.loads((run_dir / "STOP_REQUIRED.json").read_text(encoding="utf-8"))
    assert stop["rollback_required"] is True
    assert stop["automatic_rollback_available"] is False

    for failure_stage, expected_reason in (
        ("endpoint", "local_integrity_failure"),
        ("evaluation", "local_integrity_failure"),
        ("schema", "local_integrity_failure"),
        ("identity", "identity_verification_failure"),
        ("manifest", "calibration_failure"),
    ):
        shutil.rmtree(ARTIFACTS / "runs", ignore_errors=True)
        with monkeypatch.context() as stage_patch:
            _check_all_prerun_failures_write_stop_marker_without_mcp(
                stage_patch,
                failure_stage,
                expected_reason,
            )

    shutil.rmtree(ARTIFACTS / "runs", ignore_errors=True)
    with monkeypatch.context() as detector_patch:
        detector_patch.setattr(evidence, "RUNS_ROOT", ARTIFACTS / "runs")
        detector_patch.setattr(
            invocation,
            "validate_fixed_endpoint",
            lambda target: (_ for _ in ()).throw(ValueError("invalid fixed endpoint")),
        )
        detector_patch.setattr(
            invocation,
            "sensitive_material_category",
            lambda value: (_ for _ in ()).throw(RuntimeError("detector failed")),
        )
        with pytest.raises(ValueError):
            asyncio.run(invocation.run_calibration(TARGET))
    detector_run_dir = next((ARTIFACTS / "runs").iterdir())
    detector_stop = json.loads(
        (detector_run_dir / "STOP_REQUIRED.json").read_text(encoding="utf-8")
    )
    assert detector_stop["reason_code"] == "sensitive_material_detection_failure"

    shutil.rmtree(ARTIFACTS / "runs", ignore_errors=True)
    with monkeypatch.context() as preflight_patch:
        _check_preflight_auth_failure_writes_stop_without_tool_invocation(
            preflight_patch
        )

    for secret in (
        "******",
        "-----BEGIN PRIVATE KEY-----\nnot-real\n-----END PRIVATE KEY-----",
        "https://storage.example.invalid/c?sv=2025-01-01&sp=r&sig=not-real",
        "Server=example.invalid;User ID=test;Password=not-real",
        "Cookie: sessionid=not-real",
    ):
        with monkeypatch.context() as output_patch:
            _check_main_sanitizes_all_top_level_errors(output_patch, capsys, secret)
    with monkeypatch.context() as sanitizer_patch:
        _check_sanitizer_failure_emits_only_fixed_constant(sanitizer_patch, capsys)
    _check_dependency_logs_are_sanitized(caplog)


class _RunnerIdentity:
    @property
    def manifest(self) -> dict[str, str]:
        return identity._identity_manifest()

    def close(self) -> None:
        pass


@pytest.mark.parametrize(
    ("failure_stage", "expected_reason"),
    [
        ("endpoint", "local_integrity_failure"),
        ("evaluation", "local_integrity_failure"),
        ("schema", "local_integrity_failure"),
        ("identity", "identity_verification_failure"),
        ("manifest", "calibration_failure"),
    ],
)
def _check_all_prerun_failures_write_stop_marker_without_mcp(
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
    expected_reason: str,
) -> None:
    monkeypatch.setattr(evidence, "RUNS_ROOT", ARTIFACTS / "runs")
    invoked = False

    async def forbidden_invoke(*args: object, **kwargs: object) -> str:
        nonlocal invoked
        invoked = True
        raise AssertionError("MCP invocation must not occur")

    monkeypatch.setattr(invocation, "invoke_once", forbidden_invoke)
    monkeypatch.setattr(invocation, "verify_delegated_identity", lambda: _RunnerIdentity())

    if failure_stage == "endpoint":
        monkeypatch.setattr(
            invocation,
            "validate_fixed_endpoint",
            lambda target: (_ for _ in ()).throw(ValueError("invalid fixed endpoint")),
        )
    elif failure_stage == "evaluation":
        monkeypatch.setattr(
            invocation,
            "load_invocation_cases",
            lambda: (_ for _ in ()).throw(ValueError("evaluation integrity failure")),
        )
    elif failure_stage == "schema":
        monkeypatch.setattr(
            jsonschema.Draft202012Validator,
            "check_schema",
            lambda schema: (_ for _ in ()).throw(
                jsonschema.SchemaError("schema integrity failure")
            ),
        )
    elif failure_stage == "identity":
        monkeypatch.setattr(
            invocation,
            "verify_delegated_identity",
            lambda: (_ for _ in ()).throw(
                identity.IdentityVerificationFailure("identity mismatch")
            ),
        )
    else:
        original_validate = invocation.validate_schema

        def fail_manifest(value: object, schema_name: str) -> None:
            if schema_name == "run-manifest.schema.json":
                raise jsonschema.ValidationError("manifest rejected")
            original_validate(value, schema_name)

        monkeypatch.setattr(invocation, "validate_schema", fail_manifest)

    with pytest.raises(Exception):
        asyncio.run(invocation.run_calibration(TARGET))

    assert invoked is False
    run_dir = next((ARTIFACTS / "runs").iterdir())
    stop_path = run_dir / "STOP_REQUIRED.json"
    assert stop_path.exists()
    assert os.stat(stop_path).st_mode & 0o777 == 0o600
    stop = json.loads(stop_path.read_text(encoding="utf-8"))
    assert stop["reason_code"] == expected_reason
    assert stop["case_id"] is None
    assert stop["attempt"] is None
    assert (run_dir / "control.json").exists()
    assert not (run_dir / "attempts.jsonl").exists()


def _check_preflight_auth_failure_writes_stop_without_tool_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(evidence, "RUNS_ROOT", ARTIFACTS / "runs")
    monkeypatch.setattr(invocation, "verify_delegated_identity", lambda: _RunnerIdentity())
    monkeypatch.setattr(
        invocation,
        "_run_preflight_verified",
        lambda verified, target, **kwargs: (_ for _ in ()).throw(
            invocation.HardGateFailure(
                "authentication_rejection_failure",
                "post-publication authentication check failed",
            )
        ),
    )
    called = False

    async def forbidden_invoke(*args: object, **kwargs: object) -> str:
        nonlocal called
        called = True
        raise AssertionError("tool invocation must not occur")

    monkeypatch.setattr(invocation, "invoke_once", forbidden_invoke)
    with pytest.raises(invocation.HardGateFailure):
        asyncio.run(invocation.run_preflight(TARGET))

    assert called is False
    run_dir = next((ARTIFACTS / "runs").iterdir())
    stop = json.loads((run_dir / "STOP_REQUIRED.json").read_text(encoding="utf-8"))
    assert stop["reason_code"] == "authentication_rejection_failure"
    diagnostic = json.loads((run_dir / "preflight.json").read_text(encoding="utf-8"))
    assert diagnostic["status"] == "FAIL"
    assert diagnostic["failure"]["category"] == "authentication_rejection_failure"
    assert diagnostic["raw_response_bodies_persisted"] is False


@pytest.mark.parametrize(
    "secret",
    [
        "Bearer not-a-real-top-level-token",
        "-----BEGIN PRIVATE KEY-----\nnot-real\n-----END PRIVATE KEY-----",
        "https://storage.example.invalid/c?sv=2025-01-01&sp=r&sig=not-real",
        "Server=example.invalid;User ID=test;Password=not-real",
        "Cookie: sessionid=not-real",
    ],
)
def _check_main_sanitizes_all_top_level_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    secret: str,
) -> None:
    async def fail(target: config.CalibrationTarget) -> int:
        del target
        raise invocation.HardGateFailure("test_gate", f"failed with {secret}")

    monkeypatch.setattr(invocation, "run_calibration", fail)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "runner",
            "run",
            "--data-agent-id",
            TEST_DATA_AGENT_ID,
            "--approved-data-agent-id",
            TEST_DATA_AGENT_ID,
        ],
    )
    with pytest.raises(SystemExit) as exited:
        invocation.main()
    assert exited.value.code == 2
    captured = capsys.readouterr()
    assert secret not in captured.err
    assert "FAIL CLOSED:" in captured.err


def _check_sanitizer_failure_emits_only_fixed_constant(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "client_secret=not-a-real-secret"

    async def fail(target: config.CalibrationTarget) -> int:
        del target
        raise RuntimeError(secret)

    monkeypatch.setattr(invocation, "run_calibration", fail)
    monkeypatch.setattr(invocation, "sanitize_output", lambda value: 1 / 0)
    monkeypatch.setattr(
        invocation,
        "sensitive_material_category",
        lambda value: (_ for _ in ()).throw(RuntimeError("detector failed")),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "runner",
            "run",
            "--data-agent-id",
            TEST_DATA_AGENT_ID,
            "--approved-data-agent-id",
            TEST_DATA_AGENT_ID,
        ],
    )
    with pytest.raises(SystemExit) as exited:
        invocation.main()
    assert exited.value.code == 2
    captured = capsys.readouterr()
    assert captured.err.strip() == evidence.SAFE_OUTPUT_FAILURE
    assert secret not in captured.err
    assert "Traceback" not in captured.err


def _check_dependency_logs_are_sanitized(
    caplog: pytest.LogCaptureFixture,
) -> None:
    evidence.install_logging_sanitizer()
    secret = "Bearer not-a-real-dependency-token"
    with caplog.at_level(logging.ERROR):
        logging.getLogger("dependency").error("transport failed: %s", secret)
        try:
            raise RuntimeError("client_secret=not-a-real-traceback-secret")
        except RuntimeError:
            logging.getLogger("dependency").exception("dependency failed")
    rendered = "\n".join(record.getMessage() for record in caplog.records)
    assert secret not in rendered
    assert "not-a-real-traceback-secret" not in rendered
    assert all(record.exc_info is None for record in caplog.records)
    assert "[REDACTED:bearer_token]" in rendered


def test_attempt_schema_rejects_grader_fields() -> None:
    schema = json.loads(
        (SCHEMAS / "attempt.schema.json").read_text(encoding="utf-8")
    )
    record = {
        "schema_version": "1.0.0",
        "run_id": "20261024T230000Z-1234abcd",
        "case_id": "summary-v1.0.0-A01",
        "attempt": 1,
        "workspace_id": config.WORKSPACE_ID,
        "data_agent_id": TARGET.data_agent_id,
        "model_id": config.MODEL_ID,
        "versions": invocation._fixed_versions(),
        "model_input": {"question": "How many wells?"},
        "started_at_utc": "2026-10-24T23:00:00Z",
        "ended_at_utc": "2026-10-24T23:00:01Z",
        "latency_seconds": 1.0,
        "status": "SUCCESS",
        "response_text": config.SYNTHETIC_LABEL,
        "error": None,
        "security_failure": None,
        "cost_usd": None,
    }
    jsonschema.validate(record, schema)
    record["model_input"]["expected_facts"] = [100]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(record, schema)


def test_offline_scorer_keeps_missing_cost_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs = ARTIFACTS / "runs"
    run_id = "20261024T230000Z-1234abcd"
    run_dir = runs / run_id
    run_dir.mkdir(parents=True)
    monkeypatch.setattr(scoring, "RUNS_ROOT", runs)
    evidence.write_json(run_dir / "metadata.json", _run_manifest())

    first_case = invocation.load_invocation_cases()[0]
    attempt = {
        "case_id": first_case.case_id,
        "attempt": 1,
        "status": "SUCCESS",
        "response_text": config.SYNTHETIC_LABEL,
        "latency_seconds": 1.25,
        "cost_usd": None,
    }
    (run_dir / "attempts.jsonl").write_text(
        json.dumps(attempt) + "\n",
        encoding="utf-8",
    )
    grades = {
        "schema_version": "1.0.0",
        "grades": [
            {
                "schema_version": "1.0.0",
                "case_id": first_case.case_id,
                "attempt": 1,
                "grader_context": {},
                "judgment": {
                    "expected_behavior_correct": True,
                    "critical_factual_failure": False,
                    "scope_boundary_violation": False,
                    "unauthorized_disclosure_or_security_failure": False,
                    "normalized_semantics": "100 wells",
                    "citation_claims": [
                        {
                            "claim": "well count",
                            "citation_present": True,
                            "citation_valid": True,
                        }
                    ],
                },
                "review": {
                    "reviewer_type": "human",
                    "reviewer_id_or_model": "reviewer",
                    "reviewed_at_utc": "2026-10-24T23:05:00Z",
                    "notes": None,
                },
            }
        ],
    }
    grades_path = run_dir / "grades.json"
    grades_path.write_text(json.dumps(grades), encoding="utf-8")
    report_path = scoring.score_run(run_id, grades_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "INCOMPLETE"
    assert report["cost"] == {
        "status": "UNKNOWN",
        "total_usd": None,
        "missing_cost_is_not_zero": True,
    }
    assert report["gates"]["critical_factual_failures"] is None


def test_preflight_requires_explicit_live_acknowledgement() -> None:
    script = ROOT / "scripts" / "run_data_agent_calibration.py"
    result = subprocess.run(
        [
            str(ROOT / ".calibration-venv" / "bin" / "python")
            if (ROOT / ".calibration-venv" / "bin" / "python").exists()
            else "python3",
            str(script),
            "preflight",
            "--data-agent-id",
            TEST_DATA_AGENT_ID,
            "--approved-data-agent-id",
            TEST_DATA_AGENT_ID,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "--execute-live-checks" in result.stderr


def test_cli_requires_explicit_runtime_and_approved_agent_ids() -> None:
    script = ROOT / "scripts" / "run_data_agent_calibration.py"
    result = subprocess.run(
        [
            str(ROOT / ".calibration-venv" / "bin" / "python")
            if (ROOT / ".calibration-venv" / "bin" / "python").exists()
            else "python3",
            str(script),
            "run",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "--data-agent-id" in result.stderr
    assert "--approved-data-agent-id" in result.stderr


class _TransportIdentity:
    manifest = {"claims_sha256": "a" * 64}

    def fabric_token(self) -> str:
        return "mock-token-not-a-jwt"


def _negative_auth_transport():
    import httpx

    async def reject(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload == invocation._initialize_payload()
        assert "MCP-Protocol-Version" not in request.headers
        return httpx.Response(401, request=request)

    return httpx.MockTransport(reject)


def _mcp_transport(*, tools: list[dict[str, object]] | None = None):
    import httpx2

    advertised = (
        [
            {
                "name": "ask_data_agent",
                "description": "Mock Fabric data agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {"question": {"type": "string"}},
                    "required": ["question"],
                },
            }
        ]
        if tools is None
        else tools
    )

    async def respond(request: httpx2.Request) -> httpx2.Response:
        if request.method == "GET":
            return httpx2.Response(405, request=request)
        if request.method == "DELETE":
            return httpx2.Response(204, request=request)
        payload = json.loads(request.content)
        if payload["method"] == "initialize":
            return httpx2.Response(
                200,
                headers={"content-type": "application/json", "mcp-session-id": "mock"},
                json={
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "protocolVersion": payload["params"]["protocolVersion"],
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "mock-fabric", "version": "1.0"},
                    },
                },
                request=request,
            )
        if payload["method"] == "notifications/initialized":
            return httpx2.Response(202, request=request)
        if payload["method"] == "tools/list":
            assert request.headers["MCP-Protocol-Version"] == "2025-11-25"
            return httpx2.Response(
                200,
                headers={"content-type": "application/json"},
                json={
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {"tools": advertised},
                },
                request=request,
            )
        raise AssertionError("preflight must not call an MCP tool")

    return httpx2.MockTransport(respond)


def test_preflight_uses_pinned_sdk_protocol_and_lists_tools_without_calling() -> None:
    diagnostics = invocation.PreflightDiagnostics(checks=[])
    result = asyncio.run(
        invocation._run_preflight_verified(
            _TransportIdentity(),
            TARGET,
            diagnostics=diagnostics,
            negative_client_transport=_negative_auth_transport(),
            mcp_client_transport=_mcp_transport(),
        )
    )
    assert result == 0
    assert diagnostics.stage == "complete"
    assert [check["check"] for check in diagnostics.checks] == [
        "unauthenticated",
        "wrong_token",
        "authenticated_handshake",
        "tool_inventory",
        "transport_cleanup",
    ]
    assert invocation._initialize_payload()["params"]["protocolVersion"] == "2025-11-25"


def test_preflight_distinguishes_authenticated_inventory_failure() -> None:
    diagnostics = invocation.PreflightDiagnostics(checks=[])
    with pytest.raises(BaseExceptionGroup) as caught:
        asyncio.run(
            invocation._run_preflight_verified(
                _TransportIdentity(),
                TARGET,
                diagnostics=diagnostics,
                negative_client_transport=_negative_auth_transport(),
                mcp_client_transport=_mcp_transport(tools=[]),
            )
        )
    failure = invocation._preflight_failure(diagnostics.stage, caught.value)
    assert diagnostics.stage == "tool_inventory"
    assert failure["category"] == "unexpected_mcp_tool_surface"
    assert failure["message"] == "The authenticated MCP tool inventory check failed"


def test_exception_group_diagnostics_flatten_and_never_copy_messages() -> None:
    secret = "client_secret=not-a-real-secret"
    grouped = ExceptionGroup(
        f"outer {secret}",
        [
            ValueError(secret),
            ExceptionGroup("nested", [TimeoutError(f"timeout {secret}")]),
        ],
    )
    failure = invocation._preflight_failure("authenticated_handshake", grouped)
    rendered = json.dumps(failure)
    assert failure["leaf_types"] == ["ValueError", "TimeoutError"]
    assert failure["category"] == "authenticated_handshake_failure"
    assert secret not in rendered
    assert "outer" not in rendered
    failure_line = invocation._safe_failure_line(
        ExceptionGroup("outer", [ValueError("bad"), TimeoutError("late")])
    )
    assert failure_line == "FAIL CLOSED: exception_group_failure: [ValueError,TimeoutError]"
    assert secret not in failure_line


def test_streamable_transport_connect_failure_is_a_flattenable_task_group() -> None:
    import httpx2

    async def fail(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("credential-shaped raw detail", request=request)

    diagnostics = invocation.PreflightDiagnostics(checks=[])
    with pytest.raises(BaseExceptionGroup) as caught:
        asyncio.run(
            invocation._run_preflight_verified(
                _TransportIdentity(),
                TARGET,
                diagnostics=diagnostics,
                negative_client_transport=_negative_auth_transport(),
                mcp_client_transport=httpx2.MockTransport(fail),
            )
        )
    failure = invocation._preflight_failure(diagnostics.stage, caught.value)
    assert diagnostics.stage == "authenticated_handshake"
    assert failure["leaf_types"] == ["ConnectError"]
    assert "credential-shaped raw detail" not in json.dumps(failure)


def test_preflight_distinguishes_wrong_token_rejection_failure() -> None:
    import httpx

    requests = 0

    async def respond(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(401 if requests == 1 else 200, request=request)

    diagnostics = invocation.PreflightDiagnostics(checks=[])
    with pytest.raises(invocation.HardGateFailure) as caught:
        asyncio.run(
            invocation._run_preflight_verified(
                _TransportIdentity(),
                TARGET,
                diagnostics=diagnostics,
                negative_client_transport=httpx.MockTransport(respond),
            )
        )
    failure = invocation._preflight_failure(diagnostics.stage, caught.value)
    assert diagnostics.stage == "wrong_token"
    assert failure["category"] == "authentication_rejection_failure"
    assert diagnostics.checks == [
        {"check": "unauthenticated", "status": "PASS", "http_status": 401}
    ]


def test_preflight_persists_fixed_identity_cleanup_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CleanupFailureIdentity:
        manifest = identity._identity_manifest()

        def close(self) -> None:
            raise RuntimeError("client_secret=must-not-be-persisted")

    async def pass_transport(
        verified: object,
        target: config.CalibrationTarget,
        *,
        diagnostics: invocation.PreflightDiagnostics,
    ) -> int:
        del verified, target
        diagnostics.stage = "complete"
        return 0

    shutil.rmtree(ARTIFACTS / "runs", ignore_errors=True)
    monkeypatch.setattr(evidence, "RUNS_ROOT", ARTIFACTS / "runs")
    monkeypatch.setattr(
        invocation, "verify_delegated_identity", lambda: CleanupFailureIdentity()
    )
    monkeypatch.setattr(invocation, "_run_preflight_verified", pass_transport)
    with pytest.raises(RuntimeError):
        asyncio.run(invocation.run_preflight(TARGET))

    run_dir = next((ARTIFACTS / "runs").iterdir())
    diagnostic_text = (run_dir / "preflight.json").read_text(encoding="utf-8")
    diagnostic = json.loads(diagnostic_text)
    assert diagnostic["status"] == "FAIL"
    assert diagnostic["cleanup"] == {
        "stage": "identity_cleanup",
        "status": "FAIL",
        "category": "identity_cleanup_failure",
        "message": "Delegated identity cleanup failed",
        "leaf_types": ["RuntimeError"],
    }
    assert "must-not-be-persisted" not in diagnostic_text


def _fake_jwt(**overrides: object) -> str:
    claims: dict[str, object] = {
        "tid": config.APPROVED_TENANT_ID,
        "oid": config.approved_user_object_id(),
        "upn": config.approved_user_principal_name(),
        "scp": "User.Read",
        "idtyp": "user",
    }
    claims.update(overrides)

    def encode(value: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(
            json.dumps(value, separators=(",", ":")).encode()
        ).decode().rstrip("=")

    return f"{encode({'alg': 'none'})}.{encode(claims)}.signature"


class _FakeCredential:
    def __init__(self, token: str):
        self.token = token
        self.closed = False

    def get_token(self, scope: str) -> SimpleNamespace:
        assert scope in {config.GRAPH_SCOPE, config.FABRIC_SCOPE}
        return SimpleNamespace(token=self.token)

    def close(self) -> None:
        self.closed = True


class _FakeGraphClient:
    def __init__(
        self,
        graph_me: dict[str, object],
        *,
        status_code: int = 200,
        redirected: bool = False,
    ):
        self.response = SimpleNamespace(
            status_code=status_code,
            is_redirect=redirected,
            request=SimpleNamespace(url=config.GRAPH_ME_ENDPOINT),
            json=lambda: graph_me,
        )

    def __enter__(self) -> "_FakeGraphClient":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def get(self, url: str, *, headers: dict[str, str]) -> SimpleNamespace:
        assert url == config.GRAPH_ME_ENDPOINT
        assert headers["Authorization"].startswith("Bearer ")
        return self.response


def _mock_cli(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tenant: str = config.APPROVED_TENANT_ID,
    upn: str | None = None,
    principal_type: str = "user",
) -> None:
    if upn is None:
        upn = config.approved_user_principal_name()
    monkeypatch.setattr(identity.shutil, "which", lambda executable: f"/bin/{executable}")
    monkeypatch.setattr(
        identity.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "tenantId": tenant,
                    "user": {"name": upn, "type": principal_type},
                }
            ),
        ),
    )


def _verify_identity(
    monkeypatch: pytest.MonkeyPatch,
    *,
    token: str | None = None,
    graph_me: dict[str, object] | None = None,
    status_code: int = 200,
) -> identity.VerifiedDelegatedIdentity:
    _mock_cli(monkeypatch)
    credential = _FakeCredential(token or _fake_jwt())
    graph = graph_me or {
        "id": config.approved_user_object_id(),
        "userPrincipalName": config.approved_user_principal_name(),
    }
    return identity.verify_delegated_identity(
        credential_factory=lambda: credential,
        http_client_factory=lambda **kwargs: _FakeGraphClient(
            graph,
            status_code=status_code,
        ),
    )


def test_exact_delegated_identity_is_verified_and_manifest_is_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = _verify_identity(monkeypatch)
    assert verified.manifest == {
        "tenant_id": config.APPROVED_TENANT_ID,
        "user_principal_name": config.approved_user_principal_name(),
        "object_id": config.approved_user_object_id(),
        "principal_type": "User",
        "claims_sha256": verified.manifest["claims_sha256"],
    }
    assert len(verified.manifest["claims_sha256"]) == 64
    assert "token" not in json.dumps(verified.manifest).casefold()
    verified.close()


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [
        ("tenant", "00000000-0000-0000-0000-000000000000"),
        ("upn", TEST_OTHER_UPN),
        ("principal_type", "servicePrincipal"),
        ("principal_type", "managedIdentity"),
    ],
)
def test_cli_identity_mismatch_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    wrong_value: str,
) -> None:
    values = {
        "tenant": config.APPROVED_TENANT_ID,
        "upn": config.approved_user_principal_name(),
        "principal_type": "user",
    }
    values[field] = wrong_value
    _mock_cli(monkeypatch, **values)
    with pytest.raises(identity.IdentityVerificationFailure):
        identity.verify_delegated_identity(
            credential_factory=lambda: _FakeCredential(_fake_jwt()),
            http_client_factory=lambda **kwargs: _FakeGraphClient({}),
        )


@pytest.mark.parametrize(
    "claims",
    [
        {"tid": "00000000-0000-0000-0000-000000000000"},
        {"oid": TEST_OTHER_OBJECT_ID},
        {"upn": TEST_OTHER_UPN},
        {"scp": ""},
        {"idtyp": "app"},
    ],
)
def test_acquired_credential_mismatch_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    claims: dict[str, object],
) -> None:
    with pytest.raises(identity.IdentityVerificationFailure):
        _verify_identity(monkeypatch, token=_fake_jwt(**claims))


@pytest.mark.parametrize(
    ("graph_me", "status_code"),
    [
        ({}, 401),
        ({"userPrincipalName": TEST_APPROVED_UPN}, 200),
        (
            {
                "id": TEST_APPROVED_OBJECT_ID,
                "userPrincipalName": TEST_OTHER_UPN,
            },
            200,
        ),
        (
            {
                "id": TEST_OTHER_OBJECT_ID,
                "userPrincipalName": TEST_APPROVED_UPN,
            },
            200,
        ),
        (
            {
                "id": TEST_APPROVED_OBJECT_ID,
                "userPrincipalName": TEST_APPROVED_UPN,
                "unexpected": "ambiguous",
            },
            200,
        ),
    ],
)
def test_missing_or_ambiguous_graph_confirmation_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    graph_me: dict[str, object],
    status_code: int,
) -> None:
    with pytest.raises(identity.IdentityVerificationFailure):
        _verify_identity(
            monkeypatch,
            graph_me=graph_me,
            status_code=status_code,
        )
