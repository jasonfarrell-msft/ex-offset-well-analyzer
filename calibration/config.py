"""Fixed calibration boundaries and approval-controlled Data Agent binding."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID


ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = ROOT / "calibration" / "runs"
EVALUATION_PATH = ROOT / "evaluation" / "summary-v1.0.0" / "questions.jsonl"
SCORING_PATH = ROOT / "evaluation" / "summary-v1.0.0" / "scoring.json"
SCHEMAS_ROOT = ROOT / "calibration" / "schemas"

WORKSPACE_ID = "4e1977a8-d7ff-487e-b42d-c4b3bc118f3d"
WORKSPACE_VERSION = "security-posture-v1.0.0"
DATA_AGENT_VERSION = "da_drillrun_summary-definition-v1.0.1"
MODEL_ID = "ee7583b6-5be7-4802-83a8-530ce7dd8351"
MODEL_VERSION = "sm_drillrun_summary-v1.0.0"
EVALUATION_VERSION = "summary-v1.0.0"
RUNNER_VERSION = "1.1.0"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_ME_ENDPOINT = (
    "https://graph.microsoft.com/v1.0/me?$select=id,userPrincipalName"
)
APPROVED_TENANT_ID = "e90bd921-0e00-4e6f-b87c-713670ee27bf"
APPROVED_USER_PRINCIPAL_NAME_ENV = "DRILLRUN_APPROVED_USER_PRINCIPAL_NAME"
APPROVED_USER_OBJECT_ID_ENV = "DRILLRUN_APPROVED_USER_OBJECT_ID"
APPROVED_PRINCIPAL_TYPE = "User"
SYNTHETIC_LABEL = (
    "SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY"
)
RETENTION_DAYS = 90
EXPECTED_CASE_COUNT = 36
EXPECTED_ATTEMPTS_PER_CASE = 3


def approved_user_principal_name() -> str:
    """Require explicit local approval; never infer it from the signed-in user."""
    value = os.environ.get(APPROVED_USER_PRINCIPAL_NAME_ENV)
    if (
        value is None
        or len(value) > 254
        or re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value) is None
        or not value.isprintable()
    ):
        raise ValueError(
            f"{APPROVED_USER_PRINCIPAL_NAME_ENV} must be explicitly set "
            "to a non-empty, plausible approved UPN in the local environment"
        )
    return value


def approved_user_object_id() -> str:
    """Require the independently approved object ID from the local environment."""
    value = os.environ.get(APPROVED_USER_OBJECT_ID_ENV)
    if value is None:
        raise ValueError(
            f"{APPROVED_USER_OBJECT_ID_ENV} must be explicitly set to a "
            "canonical, non-nil lowercase UUID in the local environment"
        )
    try:
        return _canonical_uuid(value, field=APPROVED_USER_OBJECT_ID_ENV)
    except ValueError:
        raise ValueError(
            f"{APPROVED_USER_OBJECT_ID_ENV} must be explicitly set to a "
            "canonical, non-nil lowercase UUID in the local environment"
        ) from None


@dataclass(frozen=True)
class CalibrationTarget:
    """A future published Data Agent bound to its separately approved UUID."""

    data_agent_id: str

    @property
    def mcp_endpoint(self) -> str:
        return (
            "https://api.fabric.microsoft.com/v1/mcp/workspaces/"
            f"{WORKSPACE_ID}/dataagents/{self.data_agent_id}/agent"
        )


def _canonical_uuid(value: str, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a canonical UUID")
    try:
        parsed = UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a canonical UUID") from exc
    if parsed.int == 0 or str(parsed) != value:
        raise ValueError(f"{field} must be a canonical non-nil lowercase UUID")
    return value


def bind_approved_data_agent(
    data_agent_id: str,
    approved_data_agent_id: str,
) -> CalibrationTarget:
    """Fail closed unless runtime and independently approved item IDs match."""
    runtime_id = _canonical_uuid(data_agent_id, field="data_agent_id")
    approval_id = _canonical_uuid(
        approved_data_agent_id,
        field="approved_data_agent_id",
    )
    if runtime_id != approval_id:
        raise ValueError("Data Agent ID does not match the explicitly approved ID")
    target = CalibrationTarget(data_agent_id=runtime_id)
    validate_fixed_endpoint(target)
    return target


def validate_fixed_endpoint(
    target: CalibrationTarget,
    endpoint: str | None = None,
) -> None:
    """Reject substitution or decoration of the endpoint derived from approval."""
    expected_endpoint = target.mcp_endpoint
    candidate = expected_endpoint if endpoint is None else endpoint
    if candidate != expected_endpoint:
        raise ValueError("MCP endpoint substitution is prohibited")
    parsed = urlsplit(candidate)
    expected_path = (
        f"/v1/mcp/workspaces/{WORKSPACE_ID}/dataagents/{target.data_agent_id}/agent"
    )
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.fabric.microsoft.com"
        or parsed.port is not None
        or parsed.path != expected_path
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ValueError("MCP endpoint must match the approved HTTPS host and path")
