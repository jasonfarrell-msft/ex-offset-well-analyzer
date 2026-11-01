"""Sequential, fail-closed MCP invocation and security preflight."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from calibration import __version__
from calibration.config import (
    DATA_AGENT_VERSION,
    EVALUATION_PATH,
    EVALUATION_VERSION,
    EXPECTED_ATTEMPTS_PER_CASE,
    EXPECTED_CASE_COUNT,
    MODEL_ID,
    MODEL_VERSION,
    RUNNER_VERSION,
    SYNTHETIC_LABEL,
    WORKSPACE_ID,
    WORKSPACE_VERSION,
    CalibrationTarget,
    bind_approved_data_agent,
    validate_fixed_endpoint,
)
from calibration.evidence import (
    append_jsonl,
    create_run_directory,
    install_logging_sanitizer,
    iso_utc,
    SAFE_OUTPUT_FAILURE,
    safe_error,
    sanitize_output,
    sensitive_material_category,
    utc_now,
    validate_schema,
    write_json,
    write_stop_marker,
)
from calibration.identity import VerifiedDelegatedIdentity, verify_delegated_identity


@dataclass(frozen=True)
class InvocationCase:
    case_id: str
    question: str
    attempts: int


@dataclass(frozen=True)
class RunControl:
    run_id: str
    run_dir: Path
    started: Any
    expires: Any
    mode: str


@dataclass
class PreflightDiagnostics:
    checks: list[dict[str, Any]]
    stage: str = "endpoint_validation"
    failure: dict[str, Any] | None = None
    cleanup: dict[str, Any] | None = None


class HardGateFailure(RuntimeError):
    def __init__(
        self,
        reason_code: str,
        message: str,
        *,
        security_category: str | None = None,
    ):
        super().__init__(message)
        self.reason_code = reason_code
        self.security_category = security_category


def load_invocation_cases() -> list[InvocationCase]:
    cases: list[InvocationCase] = []
    for line in EVALUATION_PATH.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        case_id = record.get("id")
        question = record.get("question")
        deterministic = record.get("deterministic")
        attempts = record.get("repeat_runs")
        if (
            not isinstance(case_id, str)
            or not isinstance(question, str)
            or not question.strip()
            or deterministic is not True
            or attempts != EXPECTED_ATTEMPTS_PER_CASE
        ):
            raise ValueError("Approved evaluation invocation controls are invalid")
        cases.append(
            InvocationCase(
                case_id=case_id,
                question=question,
                attempts=attempts,
            )
        )
    if len(cases) != EXPECTED_CASE_COUNT:
        raise ValueError("Approved evaluation must contain exactly 36 cases")
    if len({case.case_id for case in cases}) != EXPECTED_CASE_COUNT:
        raise ValueError("Approved evaluation case IDs must be unique")
    return cases


def _create_run_control(mode: str) -> RunControl:
    run_id, run_dir, started, expires = create_run_directory()
    control = RunControl(run_id, run_dir, started, expires, mode)
    try:
        write_json(
            run_dir / "control.json",
            {
                "run_id": run_id,
                "mode": mode,
                "status": "VERIFYING",
                "started_at_utc": iso_utc(started),
                "credentials_persisted": False,
            },
        )
    except Exception:
        write_stop_marker(
            run_dir,
            reason_code="run_control_initialization_failure",
            case_id=None,
            attempt=None,
        )
        raise
    return control


def _reason_code(exc: BaseException, default: str) -> str:
    try:
        category = sensitive_material_category(exc)
    except Exception:
        return "sensitive_material_detection_failure"
    if category is not None:
        return "sensitive_material_detected"
    candidates = [getattr(exc, "reason_code", None)]
    if isinstance(exc, BaseExceptionGroup):
        candidates.extend(
            getattr(leaf, "reason_code", None) for leaf in _exception_leaves(exc)
        )
    for candidate in candidates:
        if isinstance(candidate, str) and re.fullmatch(r"[a-z0-9_]{1,80}", candidate):
            return candidate
    return default


def _stop(control: RunControl, exc: BaseException, default: str) -> None:
    marker = control.run_dir / "STOP_REQUIRED.json"
    if marker.exists():
        return
    write_stop_marker(
        control.run_dir,
        reason_code=_reason_code(exc, default),
        case_id=None,
        attempt=None,
    )


def _validate_local_run_inputs(target: CalibrationTarget) -> list[InvocationCase]:
    validate_fixed_endpoint(target)
    cases = load_invocation_cases()
    for schema_name in ("run-manifest.schema.json", "attempt.schema.json"):
        schema = json.loads(
            (Path(__file__).parent / "schemas" / schema_name).read_text(encoding="utf-8")
        )
        import jsonschema

        jsonschema.Draft202012Validator.check_schema(schema)
    return cases


def _fixed_versions() -> dict[str, Any]:
    return {
        "runner": RUNNER_VERSION,
        "workspace": WORKSPACE_VERSION,
        "data_agent": DATA_AGENT_VERSION,
        "model": MODEL_VERSION,
        "evaluation": EVALUATION_VERSION,
    }


def _validate_tool(tools: Any) -> tuple[str, str]:
    advertised = getattr(tools, "tools", None)
    if not isinstance(advertised, list) or len(advertised) != 1:
        raise HardGateFailure(
            "unexpected_mcp_tool_surface",
            "The Data Agent MCP endpoint must expose exactly one tool",
        )
    tool = advertised[0]
    schema = getattr(tool, "inputSchema", None)
    if schema is None:
        schema = getattr(tool, "input_schema", None)
    properties = schema.get("properties") if isinstance(schema, dict) else None
    if not isinstance(properties, dict) or len(properties) != 1:
        raise HardGateFailure(
            "unexpected_mcp_input_schema",
            "The Data Agent tool must expose exactly one question argument",
        )
    question_arg, question_schema = next(iter(properties.items()))
    if not isinstance(question_arg, str) or not isinstance(question_schema, dict):
        raise HardGateFailure(
            "unexpected_mcp_input_schema",
            "The Data Agent question argument schema is invalid",
        )
    if question_schema.get("type") != "string":
        raise HardGateFailure(
            "unexpected_mcp_input_schema",
            "The Data Agent question argument must be a string",
        )
    return str(getattr(tool, "name")), question_arg


def _response_text(result: Any) -> str:
    blocks = getattr(result, "content", None)
    if not isinstance(blocks, list):
        raise HardGateFailure("invalid_mcp_response", "MCP response has no content list")
    texts = [
        block.text
        for block in blocks
        if getattr(block, "type", None) == "text"
        and isinstance(getattr(block, "text", None), str)
    ]
    if not texts:
        raise HardGateFailure("invalid_mcp_response", "MCP response has no text")
    return "\n".join(texts)


def _detect_response_hard_gate(response_text: str) -> None:
    category = sensitive_material_category(response_text)
    if category is not None:
        raise HardGateFailure(
            "sensitive_material_detected",
            "Response blocked by sensitive-material detection",
            security_category=category,
        )
    if not response_text.startswith(f"{SYNTHETIC_LABEL}\n") and response_text != SYNTHETIC_LABEL:
        raise HardGateFailure(
            "missing_synthetic_label",
            "Response did not start with the exact synthetic-data label",
        )


def _mcp_http_client(
    headers: dict[str, str],
    target: CalibrationTarget,
    *,
    transport: Any = None,
):
    import httpx2

    async def reject_redirect(response: httpx2.Response) -> None:
        if response.is_redirect:
            raise HardGateFailure(
                "redirect_rejected",
                "Redirects from the approved MCP endpoint are prohibited",
            )
        if str(response.request.url).split("#", 1)[0] != target.mcp_endpoint:
            raise HardGateFailure(
                "endpoint_substitution_rejected",
                "An HTTP request targeted an unapproved endpoint",
            )

    return httpx2.AsyncClient(
        headers=headers,
        follow_redirects=False,
        timeout=httpx2.Timeout(120.0, connect=15.0),
        event_hooks={"response": [reject_redirect]},
        transport=transport,
        trust_env=False,
    )


async def invoke_once(
    question: str,
    identity: VerifiedDelegatedIdentity,
    target: CalibrationTarget,
) -> str:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    validate_fixed_endpoint(target)
    token = identity.fabric_token()
    headers = {"Authorization": f"Bearer {token}"}
    async with _mcp_http_client(headers, target) as http_client:
        async with streamable_http_client(
            target.mcp_endpoint,
            http_client=http_client,
        ) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_name, question_arg = _validate_tool(await session.list_tools())
                arguments = {question_arg: question}
                if list(arguments.values()) != [question]:
                    raise HardGateFailure(
                        "model_input_isolation_failure",
                        "Only the exact evaluation question may be sent",
                    )
                result = await session.call_tool(tool_name, arguments=arguments)
                if getattr(result, "isError", False):
                    raise RuntimeError("The Data Agent MCP tool returned an error")
                return _response_text(result)


def _populate_failure_record(
    record: dict[str, Any],
    exc: BaseException,
    *,
    monotonic_started: float,
    status: str,
) -> str | None:
    category = getattr(exc, "security_category", None)
    if category is None:
        category = sensitive_material_category(str(exc))
    record.update(
        {
            "ended_at_utc": iso_utc(utc_now()),
            "latency_seconds": round(time.monotonic() - monotonic_started, 6),
            "status": "HARD_GATE_FAILURE" if category is not None else status,
            "response_text": None,
            "error": (
                {
                    "type": "SecurityDisclosureDetected",
                    "message": "Sensitive content was blocked before persistence",
                }
                if category is not None
                else safe_error(exc)
            ),
            "security_failure": (
                {"pattern_category": category} if category is not None else None
            ),
        }
    )
    return category


async def run_calibration(target: CalibrationTarget) -> int:
    control = _create_run_control("calibration")
    identity: VerifiedDelegatedIdentity | None = None
    try:
        try:
            cases = _validate_local_run_inputs(target)
        except Exception as exc:
            _stop(control, exc, "local_integrity_failure")
            raise
        try:
            identity = verify_delegated_identity()
        except Exception as exc:
            _stop(control, exc, "identity_verification_failure")
            raise
        return await _run_calibration_verified(
            identity,
            target,
            control=control,
            cases=cases,
        )
    except Exception as exc:
        _stop(control, exc, "calibration_failure")
        raise
    finally:
        if identity is not None:
            try:
                identity.close()
            except Exception as exc:
                _stop(control, exc, "identity_cleanup_failure")
                raise


async def _run_calibration_verified(
    identity: VerifiedDelegatedIdentity,
    target: CalibrationTarget,
    *,
    control: RunControl | None = None,
    cases: list[InvocationCase] | None = None,
) -> int:
    if control is None:
        control = _create_run_control("calibration")
    if cases is None:
        cases = _validate_local_run_inputs(target)
    run_id = control.run_id
    run_dir = control.run_dir
    started = control.started
    expires = control.expires
    metadata = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "mode": "calibration",
        "status": "RUNNING",
        "started_at_utc": iso_utc(started),
        "expires_at_utc": iso_utc(expires),
        "retention_days": 90,
        "workspace_id": WORKSPACE_ID,
        "data_agent_id": target.data_agent_id,
        "model_id": MODEL_ID,
        "endpoint": target.mcp_endpoint,
        "versions": _fixed_versions(),
        "case_count": len(cases),
        "attempts_per_case": EXPECTED_ATTEMPTS_PER_CASE,
        "authentication": "AzureCliCredential delegated user",
        "verified_identity": identity.manifest,
        "credentials_persisted": False,
        "cost_usd": None,
    }
    validate_schema(metadata, "run-manifest.schema.json")
    write_json(run_dir / "metadata.json", metadata)
    attempts_path = run_dir / "attempts.jsonl"
    completed = 0
    for case in cases:
        for attempt_number in range(1, case.attempts + 1):
            wall_started = utc_now()
            monotonic_started = time.monotonic()
            record: dict[str, Any] = {
                "schema_version": "1.0.0",
                "run_id": run_id,
                "case_id": case.case_id,
                "attempt": attempt_number,
                "workspace_id": WORKSPACE_ID,
                "data_agent_id": target.data_agent_id,
                "model_id": MODEL_ID,
                "versions": _fixed_versions(),
                "model_input": {"question": case.question},
                "started_at_utc": iso_utc(wall_started),
                "cost_usd": None,
                "security_failure": None,
            }
            try:
                response = await invoke_once(case.question, identity, target)
                _detect_response_hard_gate(response)
                wall_ended = utc_now()
                record.update(
                    {
                        "ended_at_utc": iso_utc(wall_ended),
                        "latency_seconds": round(
                            time.monotonic() - monotonic_started, 6
                        ),
                        "status": "SUCCESS",
                        "response_text": response,
                        "error": None,
                    }
                )
                validate_schema(record, "attempt.schema.json")
                append_jsonl(attempts_path, record)
                completed += 1
            except HardGateFailure as exc:
                category = _populate_failure_record(
                    record,
                    exc,
                    monotonic_started=monotonic_started,
                    status="HARD_GATE_FAILURE",
                )
                validate_schema(record, "attempt.schema.json")
                append_jsonl(attempts_path, record)
                write_stop_marker(
                    run_dir,
                    reason_code=(
                        "sensitive_material_detected"
                        if category is not None
                        else exc.reason_code
                    ),
                    case_id=case.case_id,
                    attempt=attempt_number,
                )
                return 2
            except Exception as exc:
                category = _populate_failure_record(
                    record,
                    exc,
                    monotonic_started=monotonic_started,
                    status="ERROR",
                )
                validate_schema(record, "attempt.schema.json")
                append_jsonl(attempts_path, record)
                write_stop_marker(
                    run_dir,
                    reason_code=(
                        "sensitive_material_detected"
                        if category is not None
                        else "invocation_error"
                    ),
                    case_id=case.case_id,
                    attempt=attempt_number,
                )
                return 2

    metadata.update(
        {
            "status": "COMPLETED_UNSCORED",
            "completed_at_utc": iso_utc(utc_now()),
            "completed_attempts": completed,
        }
    )
    validate_schema(metadata, "run-manifest.schema.json")
    write_json(run_dir / "metadata.json", metadata, replace=True)
    _safe_print(run_dir)
    return 0


def _initialize_payload() -> dict[str, Any]:
    from mcp_types.version import LATEST_HANDSHAKE_VERSION

    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": LATEST_HANDSHAKE_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "local-calibration-preflight", "version": __version__},
        },
    }


def _exception_leaves(exc: BaseException) -> list[BaseException]:
    leaves: list[BaseException] = []
    pending = [exc]
    while pending and len(leaves) < 16:
        current = pending.pop()
        if isinstance(current, BaseExceptionGroup):
            pending.extend(reversed(current.exceptions[:16]))
        else:
            leaves.append(current)
    return leaves


def _safe_leaf_types(exc: BaseException) -> list[str]:
    result: list[str] = []
    for leaf in _exception_leaves(exc):
        name = type(leaf).__name__
        try:
            name_is_sensitive = sensitive_material_category(name) is not None
        except Exception:
            name_is_sensitive = True
        safe_name = (
            name
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,99}", name)
            and not name_is_sensitive
            else "Exception"
        )
        if safe_name not in result:
            result.append(safe_name)
    return result


def _preflight_failure(stage: str, exc: BaseException) -> dict[str, Any]:
    fixed = {
        "endpoint_validation": (
            "endpoint_validation_failure",
            "The fixed endpoint validation failed",
        ),
        "identity_verification": (
            "identity_verification_failure",
            "Delegated identity verification failed",
        ),
        "unauthenticated": (
            "authentication_rejection_failure",
            "The unauthenticated request was not rejected as required",
        ),
        "wrong_token": (
            "authentication_rejection_failure",
            "The invalid-token request was not rejected as required",
        ),
        "authenticated_handshake": (
            "authenticated_handshake_failure",
            "The authenticated MCP handshake failed",
        ),
        "tool_inventory": (
            "tool_inventory_failure",
            "The authenticated MCP tool inventory check failed",
        ),
        "transport_cleanup": (
            "transport_cleanup_failure",
            "The MCP transport cleanup failed",
        ),
        "identity_cleanup": (
            "identity_cleanup_failure",
            "Delegated identity cleanup failed",
        ),
    }
    category, message = fixed.get(
        stage,
        ("transport_protocol_failure", "The MCP transport or protocol failed"),
    )
    reasons = [getattr(exc, "reason_code", None)]
    if isinstance(exc, BaseExceptionGroup):
        reasons.extend(
            getattr(leaf, "reason_code", None) for leaf in _exception_leaves(exc)
        )
    for reason in reasons:
        if isinstance(reason, str) and re.fullmatch(r"[a-z0-9_]{1,80}", reason):
            category = reason
            break
    return {
        "stage": stage,
        "category": category,
        "message": message,
        "leaf_types": _safe_leaf_types(exc),
    }


def _write_preflight_diagnostics(
    control: RunControl, diagnostics: PreflightDiagnostics
) -> None:
    record = {
        "schema_version": "1.0.0",
        "run_id": control.run_id,
        "status": (
            "FAIL"
            if diagnostics.failure
            or (diagnostics.cleanup and diagnostics.cleanup["status"] == "FAIL")
            else "PASS"
        ),
        "checks": diagnostics.checks,
        "failure": diagnostics.failure,
        "cleanup": diagnostics.cleanup,
        "credentials_persisted": False,
        "raw_response_bodies_persisted": False,
    }
    validate_schema(record, "preflight.schema.json")
    write_json(control.run_dir / "preflight.json", record)


async def run_preflight(target: CalibrationTarget) -> int:
    control = _create_run_control("preflight")
    diagnostics = PreflightDiagnostics(checks=[])
    identity: VerifiedDelegatedIdentity | None = None
    result = 2
    failure: Exception | None = None
    try:
        validate_fixed_endpoint(target)
        diagnostics.checks.append({"check": "endpoint_validation", "status": "PASS"})
        diagnostics.stage = "identity_verification"
        identity = verify_delegated_identity()
        diagnostics.checks.append(
            {
                "check": "delegated_identity",
                "status": "PASS",
                "claims_sha256": identity.manifest["claims_sha256"],
            }
        )
        result = await _run_preflight_verified(
            identity,
            target,
            diagnostics=diagnostics,
        )
    except Exception as exc:
        diagnostics.failure = _preflight_failure(diagnostics.stage, exc)
        _stop(control, exc, "preflight_failure")
        failure = exc

    if identity is not None:
        try:
            identity.close()
            diagnostics.cleanup = {"stage": "identity_cleanup", "status": "PASS"}
        except Exception as exc:
            diagnostics.cleanup = {
                "status": "FAIL",
                **_preflight_failure("identity_cleanup", exc),
            }
            _stop(control, exc, "identity_cleanup_failure")
            if failure is None:
                failure = exc

    try:
        _write_preflight_diagnostics(control, diagnostics)
    except Exception as exc:
        _stop(control, exc, "preflight_diagnostics_failure")
        if failure is None:
            failure = exc

    if failure is not None:
        raise failure
    _safe_print(json.dumps({"status": "PASS", "checks": diagnostics.checks}, indent=2))
    return result


async def _run_preflight_verified(
    identity: VerifiedDelegatedIdentity,
    target: CalibrationTarget,
    *,
    diagnostics: PreflightDiagnostics | None = None,
    negative_client_transport: Any = None,
    mcp_client_transport: Any = None,
) -> int:
    import httpx

    validate_fixed_endpoint(target)
    state = diagnostics or PreflightDiagnostics(checks=[])
    for name, headers in (
        ("unauthenticated", {}),
        ("wrong_token", {"Authorization": "Bearer invalid-preflight-token"}),
    ):
        state.stage = name
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(30.0, connect=15.0),
            transport=negative_client_transport,
            trust_env=False,
        ) as client:
            response = await client.post(
                target.mcp_endpoint,
                headers={
                    **headers,
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
                json=_initialize_payload(),
            )
        if response.is_redirect:
            raise HardGateFailure("redirect_rejected", f"{name} check redirected")
        if str(response.request.url) != target.mcp_endpoint:
            raise HardGateFailure(
                "endpoint_substitution_rejected", f"{name} used another endpoint"
            )
        if response.status_code not in {401, 403}:
            raise HardGateFailure(
                "authentication_rejection_failure",
                f"{name} check returned {response.status_code}, expected 401 or 403",
            )
        state.checks.append(
            {"check": name, "status": "PASS", "http_status": response.status_code}
        )

    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    token = identity.fabric_token()
    headers = {"Authorization": f"Bearer {token}"}
    state.stage = "authenticated_handshake"
    async with _mcp_http_client(
        headers,
        target,
        transport=mcp_client_transport,
    ) as http_client:
        async with streamable_http_client(
            target.mcp_endpoint,
            http_client=http_client,
        ) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                state.checks.append(
                    {"check": "authenticated_handshake", "status": "PASS"}
                )
                state.stage = "tool_inventory"
                _validate_tool(await session.list_tools())
                state.checks.append({"check": "tool_inventory", "status": "PASS"})
                state.stage = "transport_cleanup"
    state.checks.append({"check": "transport_cleanup", "status": "PASS"})
    state.stage = "complete"
    return 0


def _safe_print(value: Any, *, file: Any = None) -> None:
    destination = file or sys.stdout
    try:
        print(sanitize_output(value), file=destination)
    except Exception:
        print(SAFE_OUTPUT_FAILURE, file=destination)


def _safe_failure_line(exc: BaseException) -> str:
    try:
        category = sensitive_material_category(exc)
        if category is not None:
            return f"FAIL CLOSED: sensitive_material_detected: {category}"
        reason = getattr(exc, "reason_code", None)
        if isinstance(reason, str) and re.fullmatch(r"[a-z0-9_]{1,80}", reason):
            return f"FAIL CLOSED: {reason}"
        if isinstance(exc, BaseExceptionGroup):
            nested_reason = _reason_code(exc, "exception_group_failure")
            leaf_types = ",".join(_safe_leaf_types(exc))
            return f"FAIL CLOSED: {nested_reason}: [{leaf_types}]"
        safe = safe_error(exc)
        return f"FAIL CLOSED: {safe['type']}: {safe['message']}"
    except Exception:
        return SAFE_OUTPUT_FAILURE


def main() -> None:
    install_logging_sanitizer()
    parser = argparse.ArgumentParser(
        description=(
            "Run calibration only for a future published Fabric Data Agent whose "
            "runtime UUID exactly matches a separately approved UUID."
        )
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)
    run = subparsers.add_parser(
        "run",
        help="Run all 36 cases sequentially, three times each.",
    )
    preflight = subparsers.add_parser(
        "preflight",
        help="After publication, verify auth rejection and MCP handshake without questions.",
    )
    for command in (run, preflight):
        command.add_argument(
            "--data-agent-id",
            required=True,
            help="Canonical UUID of the future recreated, published, unshared Data Agent.",
        )
        command.add_argument(
            "--approved-data-agent-id",
            required=True,
            help="UUID from the separate user approval; must match exactly.",
        )
    preflight.add_argument(
        "--execute-live-checks",
        action="store_true",
        help="Required acknowledgement that this mode performs live endpoint checks.",
    )
    args = parser.parse_args()
    if args.mode == "preflight" and not args.execute_live_checks:
        parser.error("preflight requires --execute-live-checks")
    try:
        target = bind_approved_data_agent(
            args.data_agent_id,
            args.approved_data_agent_id,
        )
        exit_code = asyncio.run(
            run_calibration(target)
            if args.mode == "run"
            else run_preflight(target)
        )
    except Exception as exc:
        _safe_print(_safe_failure_line(exc), file=sys.stderr)
        exit_code = 2
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
