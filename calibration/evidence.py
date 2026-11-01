"""Secure local evidence creation with restrictive permissions."""

from __future__ import annotations

import json
import base64
import binascii
import logging
import math
import os
import re
import secrets
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import jsonschema

from calibration.config import RETENTION_DAYS, RUNS_ROOT, SCHEMAS_ROOT


SAFE_OUTPUT_FAILURE = "FAIL CLOSED: output sanitization failure"
_MAX_INSPECTION_DEPTH = 12
_MAX_INSPECTION_NODES = 10_000
_MAX_STRING_LENGTH = 1_000_000
_MAX_BASE64_INPUT = 8_192
_MAX_BASE64_DECODED = 8_192
_MAX_BASE64_DEPTH = 2

_SENSITIVE_PATTERNS = (
    ("bearer_token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")),
    ("authorization_header", re.compile(r"(?i)\bauthorization\s*:\s*\S.+")),
    ("basic_auth", re.compile(r"(?i)\bBasic\s+[A-Za-z0-9+/=_-]{8,}")),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    ),
    (
        "private_key",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ),
    (
        "connection_string",
        re.compile(
            r"(?i)(?:^|[;\s])(?:AccountKey|SharedAccessKey|Password|Pwd)="
            r"[^;\s]+(?:;|$)"
        ),
    ),
    (
        "cookie",
        re.compile(
            r"(?i)\b(?:set-cookie|cookie)\s*:\s*[^\r\n]*"
            r"(?:session|sessionid|sid|auth|token)[^=\s;]*=[^;\s]+"
        ),
    ),
    (
        "credential_assignment",
        re.compile(
            r"""(?ix)
            ["']?\b(?:api[_-]?key|x[_-]?api[_-]?key|access[_-]?token|
            refresh[_-]?token|client[_-]?secret|password|passwd|pwd|
            account[_-]?key|shared[_-]?access[_-]?key|session[_-]?id)
            \b["']?\s*[:=]\s*["']?[^\s,"'};]+
            """
        ),
    ),
)

_SENSITIVE_KEYS = {
    "accesstoken",
    "accountkey",
    "apikey",
    "authorization",
    "clientsecret",
    "connectionstring",
    "cookie",
    "password",
    "passwd",
    "privatekey",
    "pwd",
    "refreshtoken",
    "session",
    "sessionid",
    "setcookie",
    "sharedaccesskey",
    "sharedaccesssignature",
    "xapikey",
}
_OPAQUE_TOKEN = re.compile(r"^[A-Za-z0-9_~+=-]{40,}$")
_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
_HEX = re.compile(r"^[0-9a-fA-F]+$")


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _text_pattern_category(text: str) -> str | None:
    for category, pattern in _SENSITIVE_PATTERNS:
        if pattern.search(text):
            return category
    if _sas_category(text):
        return "azure_sas"
    return None


def _sas_category(text: str) -> bool:
    candidates = re.findall(r"https?://[^\s\"'<>]+|(?:\b[a-z]{2,3}=[^&\s]+&?){3,}", text)
    for candidate in candidates:
        query = urlsplit(candidate).query if "://" in candidate else candidate
        keys = {key.casefold() for key, _ in parse_qsl(query, keep_blank_values=True)}
        if "sig" in keys and keys.intersection({"se", "sp", "sr", "sv", "spr", "st"}):
            return True
    return False


def _shannon_entropy(value: str) -> float:
    counts = {character: value.count(character) for character in set(value)}
    return -sum(
        (count / len(value)) * math.log2(count / len(value))
        for count in counts.values()
    )


def _opaque_token_category(text: str) -> bool:
    for candidate in re.findall(r"[A-Za-z0-9_~+=-]{40,}", text):
        stripped = candidate.rstrip("=")
        if (
            not _OPAQUE_TOKEN.fullmatch(candidate)
            or _UUID.fullmatch(candidate)
            or _HEX.fullmatch(stripped)
            or not any(character.islower() for character in stripped)
            or not any(character.isupper() for character in stripped)
            or not any(character.isdigit() for character in stripped)
        ):
            continue
        if _shannon_entropy(stripped) >= 4.2:
            return True
    return False


def _decoded_base64(value: str) -> str | None:
    compact = "".join(value.split())
    if not 16 <= len(compact) <= _MAX_BASE64_INPUT:
        return None
    if not re.fullmatch(r"[A-Za-z0-9+/_-]+={0,2}", compact):
        return None
    padded = compact + "=" * (-len(compact) % 4)
    try:
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError):
        return None
    if not decoded or len(decoded) > _MAX_BASE64_DECODED:
        return None
    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError:
        return None
    printable = sum(character.isprintable() or character in "\r\n\t" for character in text)
    return text if printable / len(text) >= 0.9 else None


def sensitive_material_category(value: Any) -> str | None:
    """Return only the first secret category found in a bounded object walk."""
    seen: set[int] = set()
    nodes = 0

    def inspect(item: Any, depth: int, base64_depth: int) -> str | None:
        nonlocal nodes
        nodes += 1
        if nodes > _MAX_INSPECTION_NODES or depth > _MAX_INSPECTION_DEPTH:
            return "inspection_limit"
        if item is None or isinstance(item, (bool, int, float)):
            return None
        if isinstance(item, bytes):
            if len(item) > _MAX_STRING_LENGTH:
                return "inspection_limit"
            item = item.decode("utf-8", errors="replace")
        if isinstance(item, str):
            if len(item) > _MAX_STRING_LENGTH:
                return "inspection_limit"
            category = _text_pattern_category(item)
            if category is not None:
                return category
            if base64_depth < _MAX_BASE64_DEPTH:
                decoded = _decoded_base64(item)
                if decoded is not None:
                    decoded_category = inspect(decoded, depth + 1, base64_depth + 1)
                    if decoded_category is not None:
                        return "base64_credential"
            if _opaque_token_category(item):
                return "opaque_token"
            return None

        identity = id(item)
        if identity in seen:
            return None
        seen.add(identity)

        if isinstance(item, BaseException):
            category = inspect(item.args, depth + 1, base64_depth)
            if category is not None:
                return category
        if isinstance(item, Mapping):
            for key, child in item.items():
                if _normalized_key(key) in _SENSITIVE_KEYS and child not in (None, "", False):
                    return "sensitive_key"
                category = inspect(key, depth + 1, base64_depth)
                if category is not None:
                    return category
                category = inspect(child, depth + 1, base64_depth)
                if category is not None:
                    return category
            return None
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            for child in item:
                category = inspect(child, depth + 1, base64_depth)
                if category is not None:
                    return category
            return None
        if isinstance(item, (set, frozenset)):
            for child in item:
                category = inspect(child, depth + 1, base64_depth)
                if category is not None:
                    return category
            return None
        attributes = getattr(item, "__dict__", None)
        if isinstance(attributes, dict):
            return inspect(attributes, depth + 1, base64_depth)
        return "unsupported_object"

    return inspect(value, 0, 0)


def contains_sensitive_material(value: Any) -> bool:
    return sensitive_material_category(value) is not None


def safe_error(exc: BaseException) -> dict[str, str]:
    category = sensitive_material_category(exc)
    if category is not None:
        return {
            "type": "SecurityDisclosureDetected",
            "message": f"Sensitive content blocked ({category})",
        }
    return {
        "type": type(exc).__name__[:100],
        "message": str(exc)[:1000],
    }


def sanitize_output(value: Any) -> str:
    category = sensitive_material_category(value)
    if category is not None:
        return f"[REDACTED:{category}]"
    return str(value)[:2000]


class _SanitizingLogRecordFactory:
    def __init__(self, original: Any):
        self.original = original

    def __call__(self, *args: Any, **kwargs: Any) -> logging.LogRecord:
        record = self.original(*args, **kwargs)
        try:
            rendered = record.getMessage()
            record.msg = sanitize_output(rendered)
            record.args = ()
        except Exception:
            record.msg = SAFE_OUTPUT_FAILURE
            record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return record


def install_logging_sanitizer() -> None:
    current = logging.getLogRecordFactory()
    if not isinstance(current, _SanitizingLogRecordFactory):
        logging.setLogRecordFactory(_SanitizingLogRecordFactory(current))


def _assert_safe_to_persist(value: Any) -> None:
    category = sensitive_material_category(value)
    if category is not None:
        raise ValueError(
            f"Evidence persistence blocked by sensitive-material category: {category}"
        )


def create_run_directory() -> tuple[str, Path, datetime, datetime]:
    RUNS_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(RUNS_ROOT, 0o700)
    started = utc_now()
    run_id = f"{started:%Y%m%dT%H%M%SZ}-{secrets.token_hex(4)}"
    run_dir = RUNS_ROOT / run_id
    run_dir.mkdir(mode=0o700)
    os.chmod(run_dir, 0o700)
    return run_id, run_dir, started, started + timedelta(days=RETENTION_DAYS)


def _open_secure(path: Path, flags: int) -> int:
    descriptor = os.open(path, flags, 0o600)
    os.chmod(path, 0o600)
    return descriptor


def write_json(path: Path, value: Any, *, replace: bool = False) -> None:
    _assert_safe_to_persist(value)
    flags = os.O_WRONLY | os.O_CREAT
    flags |= os.O_TRUNC if replace else os.O_EXCL
    descriptor = _open_secure(path, flags)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def append_jsonl(path: Path, value: Any) -> None:
    _assert_safe_to_persist(value)
    descriptor = _open_secure(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")))
        handle.write("\n")


def validate_schema(value: Any, schema_name: str) -> None:
    schema = json.loads((SCHEMAS_ROOT / schema_name).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(value)
    if schema_name == "run-manifest.schema.json":
        from calibration.identity import validate_identity_manifest

        validate_identity_manifest(value["verified_identity"])


def write_stop_marker(
    run_dir: Path,
    *,
    reason_code: str,
    case_id: str | None,
    attempt: int | None,
) -> None:
    write_json(
        run_dir / "STOP_REQUIRED.json",
        {
            "status": "STOP_REQUIRED",
            "detected_at_utc": iso_utc(utc_now()),
            "reason_code": reason_code,
            "case_id": case_id,
            "attempt": attempt,
            "rollback_required": True,
            "rollback_runbook": "docs/data-agent-calibration.md#rollback-runbook",
            "automatic_rollback_available": False,
        },
    )
