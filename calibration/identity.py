"""Fail-closed verification of the sole approved delegated Azure identity."""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
# Only a fixed Azure CLI argument vector is executed.
import subprocess  # nosec B404
from dataclasses import dataclass, field
from typing import Any, Callable

from calibration.config import (
    APPROVED_PRINCIPAL_TYPE,
    APPROVED_TENANT_ID,
    FABRIC_SCOPE,
    GRAPH_ME_ENDPOINT,
    GRAPH_SCOPE,
    approved_user_object_id,
    approved_user_principal_name,
)


class IdentityVerificationFailure(RuntimeError):
    """Raised without embedding token, CLI, or Graph response content."""


def _fail(reason: str) -> None:
    raise IdentityVerificationFailure(reason)


def _azure_cli_identity() -> dict[str, str]:
    approved_upn = approved_user_principal_name()
    az_path = shutil.which("az")
    if az_path is None:
        _fail("Azure CLI is unavailable")
    result = subprocess.run(
        [az_path, "account", "show", "--output", "json", "--only-show-errors"],
        check=False,
        capture_output=True,
        text=True,
    )  # nosec B603
    if result.returncode != 0:
        _fail("Azure CLI account context could not be verified")
    try:
        account = json.loads(result.stdout)
        user = account["user"]
    except (KeyError, TypeError, json.JSONDecodeError):
        _fail("Azure CLI account context is missing required identity claims")
    if not isinstance(user.get("type"), str):
        _fail("Azure CLI account context is missing the principal type")
    claims = {
        "tenant_id": account.get("tenantId"),
        "user_principal_name": user.get("name"),
        "principal_type": user["type"].casefold(),
    }
    if claims != {
        "tenant_id": APPROVED_TENANT_ID,
        "user_principal_name": approved_upn,
        "principal_type": APPROVED_PRINCIPAL_TYPE.casefold(),
    }:
        _fail("Azure CLI account context is not the approved delegated user")
    return claims


def _token_claims(token: str) -> dict[str, Any]:
    try:
        encoded = token.split(".")[1]
        padded = encoded + "=" * (-len(encoded) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    except (IndexError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        _fail("Acquired credential did not provide verifiable delegated claims")
    if not isinstance(claims, dict):
        _fail("Acquired credential claims are ambiguous")
    return claims


def _validate_delegated_claims(token: str) -> None:
    claims = _token_claims(token)
    upn = claims.get("upn") or claims.get("preferred_username")
    try:
        approved_upn = approved_user_principal_name()
        approved_object_id = approved_user_object_id()
    except ValueError as exc:
        _fail(str(exc))
    if (
        claims.get("tid") != APPROVED_TENANT_ID
        or claims.get("oid") != approved_object_id
        or upn != approved_upn
        or not isinstance(claims.get("scp"), str)
        or not claims["scp"].strip()
        or claims.get("idtyp") == "app"
    ):
        _fail("Acquired credential is not the approved delegated user")


def _identity_manifest() -> dict[str, str]:
    claims = {
        "tenant_id": APPROVED_TENANT_ID,
        "user_principal_name": approved_user_principal_name(),
        "object_id": approved_user_object_id(),
        "principal_type": APPROVED_PRINCIPAL_TYPE,
    }
    canonical = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
    return {**claims, "claims_sha256": hashlib.sha256(canonical).hexdigest()}


def validate_identity_manifest(manifest: Any) -> None:
    """Check audit claims and their digest against explicit runtime approval."""
    if manifest != _identity_manifest():
        _fail("Run manifest identity does not match the explicitly approved user")


@dataclass
class VerifiedDelegatedIdentity:
    """Holds tokens only in memory and exposes only approved audit claims."""

    credential: Any = field(repr=False)
    manifest: dict[str, str]

    def fabric_token(self) -> str:
        token = self.credential.get_token(FABRIC_SCOPE).token
        _validate_delegated_claims(token)
        return token

    def close(self) -> None:
        self.credential.close()


def verify_delegated_identity(
    *,
    credential_factory: Callable[[], Any] | None = None,
    http_client_factory: Callable[..., Any] | None = None,
) -> VerifiedDelegatedIdentity:
    """Verify CLI, token claims, and Graph /me before any Fabric request."""
    import httpx

    try:
        approved_upn = approved_user_principal_name()
        approved_object_id = approved_user_object_id()
    except ValueError as exc:
        raise IdentityVerificationFailure(str(exc)) from None
    _azure_cli_identity()
    if credential_factory is None:
        from azure.identity import AzureCliCredential

        credential_factory = AzureCliCredential
    credential = credential_factory()
    try:
        graph_token = credential.get_token(GRAPH_SCOPE).token
        _validate_delegated_claims(graph_token)
        client_factory = http_client_factory or httpx.Client
        with client_factory(follow_redirects=False, timeout=15.0) as client:
            response = client.get(
                GRAPH_ME_ENDPOINT,
                headers={"Authorization": f"Bearer {graph_token}"},
            )
        if response.is_redirect or str(response.request.url) != GRAPH_ME_ENDPOINT:
            _fail("Microsoft Graph identity confirmation redirected or changed endpoint")
        if response.status_code != 200:
            _fail("Microsoft Graph identity confirmation failed")
        try:
            graph_me = response.json()
        except (TypeError, ValueError, json.JSONDecodeError):
            _fail("Microsoft Graph identity confirmation was invalid")
        if (
            not isinstance(graph_me, dict)
            or graph_me.get("id") != approved_object_id
            or graph_me.get("userPrincipalName") != approved_upn
            or set(graph_me) - {"id", "userPrincipalName", "@odata.context"}
        ):
            _fail("Microsoft Graph identity confirmation was missing or ambiguous")
        verified = VerifiedDelegatedIdentity(
            credential=credential,
            manifest=_identity_manifest(),
        )
        verified.fabric_token()
        return verified
    except Exception:
        credential.close()
        raise
