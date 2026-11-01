# Local Fabric Data Agent calibration and rollback

## Scope

This runbook covers local calibration of a future user-approved, synthetic-data
Fabric Data Agent. **No Data Agent currently exists in the fixed workspace.**
Recreation, source/ACL verification, publication while unshared, capacity
resume, preflight, and calibration are future milestones that each require the
applicable explicit user approval. The repository changes neither publish nor
invoke Fabric.

The runner has no endpoint, workspace, or model override. The workspace and
semantic-model boundary remains fixed; a future Data Agent has no default:

| Field | Fixed value |
| --- | --- |
| Workspace | `4e1977a8-d7ff-487e-b42d-c4b3bc118f3d` |
| Data Agent | None currently; future canonical UUID must be supplied twice and match its recorded approval |
| Semantic model | `ee7583b6-5be7-4802-83a8-530ce7dd8351` (`sm_drillrun_summary-v1.0.0`) |
| Evaluation | `summary-v1.0.0` |
| MCP endpoint | Derived only as `https://api.fabric.microsoft.com/v1/mcp/workspaces/4e1977a8-d7ff-487e-b42d-c4b3bc118f3d/dataagents/<approved-data-agent-id>/agent` |

The predecessor Data Agent was deleted after failed calibration, and a
subsequent inventory verified that no Data Agents remain. Its UUID is
historical evidence, not an operational target. The runner contains no old ID,
arbitrary fallback, environment fallback, mock fallback, or caller-supplied
endpoint.

Both `--data-agent-id` and `--approved-data-agent-id` are required. Each must
be a canonical, lowercase, non-nil UUID, and they must match exactly. The
second value represents the ID named by the separate approval record; entering
an arbitrary value in both fields does not create authorization. The endpoint
is derived from that matched ID and the fixed workspace. Redirects, query
parameters, fragments, alternate ports, credentials in the URL, and endpoint
substitution fail closed.

## Dependencies and isolated setup

Use Python 3.10 or later and an isolated virtual environment:

```bash
python3 -m venv .calibration-venv
source .calibration-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-calibration.txt
```

Dependencies are pinned at the repository-root path
`requirements-calibration.txt` (repository root:
`requirements-calibration.txt` at the repository root):

- `mcp` for the official Python SDK streamable HTTP client;
- `mcp-types` for the SDK's pinned Python/wire-name models;
- `anyio` for the tested task-group behavior used by the SDK;
- `azure-identity` for delegated `AzureCliCredential`;
- `httpx2` for the MCP SDK transport with explicit redirect rejection;
- `httpx` for negative-auth preflight;
- `jsonschema` for evidence-contract validation; and
- `pytest` for local tests;
- `bandit` for static security analysis; and
- `pip-audit` for pinned dependency vulnerability checks.

Authenticate interactively with Azure CLI using the sole approved user before
the authorized live window:

```bash
az login
```

Before any Fabric request, the runner fails closed unless all identity sources
agree on the sole approved delegated user:

| Claim | Required value |
| --- | --- |
| Tenant | `e90bd921-0e00-4e6f-b87c-713670ee27bf` |
| UPN | Required local-only `DRILLRUN_APPROVED_USER_PRINCIPAL_NAME` |
| Object ID | Required local-only `DRILLRUN_APPROVED_USER_OBJECT_ID` |
| Principal type | `User` |

Set both `DRILLRUN_APPROVED_USER_PRINCIPAL_NAME` and
`DRILLRUN_APPROVED_USER_OBJECT_ID` in the local process environment to the exact
UPN and canonical object ID from the independently approved identity record.
Keep both values out of source, shell-history entries, shared configuration, and
committed evidence. No example identity, default, or identity environment file is
provided. Missing, empty, malformed, or whitespace-padded values fail closed
before Azure CLI or network access. Neither value is derived from the currently
signed-in account; changing either value does not approve a different user or
change the fixed tenant.

It verifies tenant, UPN, and user type from `az account show`, requires both
configured values to match the `oid` and UPN token claims, and confirms the same
object ID and UPN through
`https://graph.microsoft.com/v1.0/me?$select=id,userPrincipalName`. A service
principal, managed identity, wrong or ambiguous claim, missing Graph
confirmation, redirect, or identity-source disagreement stops execution before
Fabric access. Graph and Fabric tokens remain in memory, are never printed, and
are never written to evidence.

## Security preflight after publication

Do not run preflight unless a recreated agent has been independently verified
as unshared and published and the live window is explicitly authorized. The
MCP endpoint is published-only; no draft endpoint or implicit mock is accepted.
During that future authorized post-publication window, replace both
placeholders with the same UUID from the approval record and run:

```bash
python scripts/run_data_agent_calibration.py preflight \
  --data-agent-id <approved-data-agent-id> \
  --approved-data-agent-id <approved-data-agent-id> \
  --execute-live-checks
```

Preflight performs no question/tool invocation. It verifies:

1. an unauthenticated MCP initialize request is rejected with HTTP 401 or 403;
2. a deliberately invalid in-memory bearer value is rejected with HTTP 401 or
   403;
3. redirects are rejected;
4. the authenticated MCP handshake succeeds using `AzureCliCredential`; and
5. the endpoint exposes exactly one tool with exactly one string question
   argument; and
6. MCP transport and delegated-identity cleanup complete.

Any other result is a security hard-gate failure. Stop and use the rollback
runbook below.

The two negative checks send a specification-conforming JSON-RPC `initialize`
request. Its protocol version comes from the pinned SDK's
`LATEST_HANDSHAKE_VERSION` (`2025-11-25` for `mcp==2.3.0`) rather than a second
hard-coded protocol constant. No `MCP-Protocol-Version` HTTP header is sent on
that initial negotiation request; the SDK adds it to subsequent authenticated
requests after negotiation.

The authenticated path follows the official Fabric sample sequence:
`streamable_http_client`, `ClientSession.initialize()`, then
`ClientSession.list_tools()`. With SDK 2.3.0 the streamable client accepts a
preconfigured `httpx2.AsyncClient` via `http_client=`. The separate pinned
`httpx` client is used only for the two raw negative-auth requests. The custom
`httpx2` client disables environment proxies and rejects every redirect and
every endpoint substitution; this is intentionally stricter than the SDK's
same-origin redirect support.

The Fabric Learn sample currently spells the helper
`streamablehttp_client(..., headers=...)` and unpacks three values. That shape
does not exist in pinned `mcp==2.3.0`; the SDK's own v2.3.0 sample and inspected
signature use `streamable_http_client(..., http_client=...)` and unpack two
streams. The runner intentionally follows the pinned SDK API rather than the
out-of-sync Learn snippet.

## Calibration execution

After preflight passes and the live window is authorized:

```bash
python scripts/run_data_agent_calibration.py run \
  --data-agent-id <approved-data-agent-id> \
  --approved-data-agent-id <approved-data-agent-id>
```

The runner starts from zero: it loads the approved 36-case JSONL evaluation and
executes all cases sequentially, with no reuse of historical attempts. Every
deterministic case receives exactly three attempts. Every attempt opens a new
streamable HTTP transport and MCP `ClientSession`, performs `initialize` and
`tools/list`, and calls the sole advertised tool. There is no concurrency and
no conversation/session reuse.

Only this payload enters the tool call:

```json
{"<discovered-question-argument>": "<case question>"}
```

Expected facts, expected behavior, citations, disclosures, forbidden claims,
governance evidence, severity, and grader fields never enter MCP arguments.

Before evaluation loading, endpoint validation, identity verification, Graph
confirmation, or any post-publication preflight request, the runner creates a
restricted run directory and a minimal non-secret `control.json`. Any failure
from that point through initial manifest persistence writes a mode `0600`
`STOP_REQUIRED.json` with a category-only reason and no case/attempt. These
paths never initialize or call an MCP tool. Preflight hard-gate failures also
write the marker and cannot proceed to calibration invocation.

The live runner immediately stops when it detects:

- any Azure CLI, token-claim, or Microsoft Graph identity mismatch;
- an endpoint, redirect, or MCP tool-surface mismatch;
- any response whose first line is not exactly
  `SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY`;
- token-, credential-, or private-key-like response material;
- an MCP tool error; or
- any transport/authentication/invocation error.

The label check performs no separator normalization. A paraphrase, translation,
case change, alternate punctuation, leading text, or later-position label fails
the hard gate.

It writes `STOP_REQUIRED.json` with `rollback_required: true`. The runner does
not and cannot unpublish or delete the agent.

## Local evidence

Each run is stored under ignored `calibration/runs/<run-id>/`. The runner
creates directories with mode `0700` and files with mode `0600`. Metadata
includes a 90-day expiry timestamp. Delete the entire run directory by that
date under the approved retention process.

`metadata.json` conforms to `run-manifest.schema.json` and records the fixed
workspace and semantic model, the explicitly approval-bound Data Agent,
derived endpoint, evaluation and runner versions, and only the approved
identity claims plus a SHA-256 hash of their canonical form. It never contains
tokens. `attempts.jsonl` records only:

- case ID and attempt number;
- exact question-only model input;
- response text;
- UTC start/end and monotonic latency;
- fixed workspace/model/evaluation identifiers and versions plus the
  approval-bound agent UUID;
- status and sanitized errors; and
- a nullable sanitized `security_failure.pattern_category`; and
- cost as a nullable value.

The checked-in Data Agent definition version recorded in new calibration metadata is
`da_drillrun_summary-definition-v1.0.1`. Workspace, semantic-model, evaluation,
and runner versions remain unchanged.

Preflight writes `preflight.json`, validated by `preflight.schema.json`. It
records only completed check names, 401/403 status categories, fixed failure
stage/category messages, bounded exception leaf type names, and explicit
booleans confirming that credentials and raw response bodies were not
persisted. It distinguishes unauthenticated rejection, invalid-token rejection,
authenticated handshake, tool inventory, MCP transport cleanup, and delegated
identity cleanup. Nested `ExceptionGroup` text and exception messages are never
copied into this evidence.

### 2026-10-25 failed-preflight diagnosis

The most likely cause of the failed preflight at runner commit `1578b2e` was a
Python model-name mismatch after a successful authenticated handshake and
`tools/list`: MCP uses wire field `inputSchema`, while `mcp-types==2.3.0`
exposes that parsed field as Python attribute `input_schema`. The old validator
read only `tool.inputSchema`, so it rejected a valid tool as having no input
schema. Raising that local hard-gate exception inside nested SDK/AnyIO context
managers wrapped it as `ExceptionGroup: unhandled errors in a TaskGroup`, which
hid the leaf exception. The validator now accepts the SDK Python attribute
while retaining wire-name compatibility.

The manual negative-auth request was neither malformed nor on an unsupported
version for the pinned SDK. The official MCP lifecycle specification and SDK
2.3.0 both use `2025-11-25` for this handshake. Mock-transport integration
tests cover the complete initialize/list flow, invalid inventory, transport
failure wrapping, and safe exception-group flattening without any Fabric
request.

Every JSON/JSONL evidence write has a final sensitive-material guard. Bearer
tokens, JWTs, private keys, and credential assignments are blocked before file
creation or append. If raw response or exception text matches, the runner
writes only case/attempt/timing, a generic error, and the pattern category,
creates `STOP_REQUIRED.json`, and halts. Sensitive content is not included in
evidence, exceptions, logs, or console output.

The guard is a bounded recursive inspection of nested mappings, sequences,
exception arguments, and object attributes; decoded content is never
persisted. It additionally blocks sensitive key names (including quoted JSON
keys), authorization material, Azure SAS queries, storage and SQL connection
strings, cookies/session IDs, safely identifiable high-entropy opaque tokens,
and base64-encoded credential text. Depth, node count, string size, and base64
decode depth/size are bounded. Inspection-limit or unsupported-object results
fail closed, while benign UUIDs, hexadecimal hashes, ordinary IDs, and
non-credential base64 remain allowed.

All top-level hard-gate, generic, preflight, dependency-log, and cleanup errors
use the same sanitizer before console/log output. If detection or sanitization
fails, the only emitted text is the fixed constant
`FAIL CLOSED: output sanitization failure`.

Missing cost remains `null`/`UNKNOWN`; it is never converted to zero or treated
as a pass. No auth headers, tokens, or cookies are evidence fields.

Schemas are in `calibration/schemas/`. Runtime evidence is ignored; source,
schemas, tests, and documentation remain tracked.

## Local validation

Run the complete pinned validation suite from the dedicated environment:

```bash
source .calibration-venv/bin/activate
python -m pytest -q
python -m bandit -q -r calibration scripts
python -m pip_audit -r requirements-calibration.txt
python - <<'PY'
import json
from pathlib import Path
import jsonschema

for path in Path("calibration/schemas").glob("*.json"):
    jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text()))
print("JSON schemas valid")
PY
git diff --check
```

## Separate offline scoring

Invocation never scores and never uses grader-only fields.
Offline manifest validation and scoring also require the same explicitly
approved local environment value used for capture. The JSON schema validates
UPN structure, not authorization; the producer and scoring consumer additionally
compare all identity claims and their digest against that runtime approval.
Neither trusts an identity copied from the manifest as approval. Captured
manifests retain approved identity audit claims only in ignored, restricted local
run directories; do not commit or publish those artifacts.

After a complete run, create an ignored grader-only document:

```bash
python scripts/score_data_agent_calibration.py prepare --run-id <run-id>
```

Review each response using `grading-template.json`. Set the explicit
human/LLM judgment fields, identify each citation-required material claim, and
record citation presence and validity. `reviewer_type` must be `human` or
`llm`; record the reviewer identity or model and review timestamp.

Then score without network access:

```bash
python scripts/score_data_agent_calibration.py score \
  --run-id <run-id> \
  --grades-file grading-template.json
```

The scorer deterministically calculates hard-gate counts, synthetic-label
rate, citation aggregates, clarify/refuse correctness, nearest-rank p95
latency, and repeat consistency from reviewer-normalized response-body
semantics. Synthetic-label credit requires the exact first line
`SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY`; label text
is never normalized. Missing judgments produce `INCOMPLETE`, never pass. A
failed gate produces `FAIL_ROLLBACK_REQUIRED`.

## Rollback runbook

### Trigger

Rollback is required for any source/ACL regression, unauthorized access,
redirect or endpoint substitution, unexpected MCP tool surface, credential
disclosure, hard-gate failure, or final `FAIL_ROLLBACK_REQUIRED` score.

### Immediate containment

1. Stop calibration immediately. Do not retry another case.
2. Preserve the local `STOP_REQUIRED.json`, attempt record, and relevant score
   report with their existing restrictive permissions.
3. Do not share, copy, or commit runtime evidence.
4. Reverify the approved workspace and item ACLs through the separately
   authorized read-only process.
5. Record the incident and obtain security/reviewer direction before any
   remediation or retest.

### Guaranteed fallback: delete the Data Agent

There is no documented unpublish operation in this runbook. Do not invent or
guess an unpublish endpoint. The guaranteed fallback is the dedicated,
documented Data Agent delete operation:

```http
DELETE https://api.fabric.microsoft.com/v1/workspaces/4e1977a8-d7ff-487e-b42d-c4b3bc118f3d/dataAgents/<approved-data-agent-id>
```

The official operation requires Data Agent write permission and delegated
scope `Item.ReadWrite.All`. Use a separately reviewed operational procedure
with the approved identity. This local runner intentionally contains no delete
implementation and cannot execute rollback.

If normal deletion is unavailable or leaves a recoverable item when permanent
removal is explicitly approved, the same official API supports the irreversible
fallback:

```http
DELETE https://api.fabric.microsoft.com/v1/workspaces/4e1977a8-d7ff-487e-b42d-c4b3bc118f3d/dataAgents/<approved-data-agent-id>?hardDelete=true
```

Hard delete is permanent. Require separate deletion approval, verify the fixed
workspace and approval-bound Data Agent UUID, use no redirects, and capture
only non-secret status/evidence. HTTP 200 is the documented success response.
For HTTP 429, honor `Retry-After`; do not improvise another endpoint.

Official references:

- [Data agent as Model Context Protocol server](https://learn.microsoft.com/fabric/data-science/data-agent-mcp-server)
- [Delete Data Agent](https://learn.microsoft.com/rest/api/fabric/dataagent/items/delete-data-agent)

### Recovery

After rollback, calibration remains blocked. Recreate and publish only through
a newly user-approved milestone, keep the item unshared, repeat source and ACL
verification, bind the new UUID through both required CLI values, rerun the
security preflight, start a new calibration run ID from zero, and obtain
reviewer approval. Never resume a partially failed run.
