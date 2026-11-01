"""Behavioral checks for operative squad routing and assignment gates."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = PROJECT_ROOT / ".squad" / "casting" / "registry.json"
TEAM_PATH = PROJECT_ROOT / ".squad" / "team.md"
ROUTING_PATH = PROJECT_ROOT / ".squad" / "routing.md"
RALPH_PATH = PROJECT_ROOT / ".squad" / "templates" / "ralph-triage.js"
WORKFLOW_DIR = PROJECT_ROOT / ".github" / "workflows"
TEMPLATE_WORKFLOW_DIR = PROJECT_ROOT / ".squad" / "templates" / "workflows"

ACTIVE_ROUTING_WORKFLOW_NAMES = {
    "squad-heartbeat.yml",
    "squad-issue-assign.yml",
    "squad-triage.yml",
    "sync-squad-labels.yml",
}
ACTIVE_ROUTING_WORKFLOWS = tuple(
    WORKFLOW_DIR / name for name in sorted(ACTIVE_ROUTING_WORKFLOW_NAMES)
)
ROUTING_TEMPLATE_PATHS = tuple(
    TEMPLATE_WORKFLOW_DIR / path.name for path in ACTIVE_ROUTING_WORKFLOWS
)

DORMANT_MEMBER_IDS = {"beru", "cha-hae-in", "choi-jong-in"}
REJECTED_TARGET_IDS = ("copilot", *sorted(DORMANT_MEMBER_IDS), "arbitrary-unknown")
ACTIVE_FABRIC_MEMBER_IDS = {
    "baek-yoonho",
    "go-gunhee",
    "igris",
    "sung-jinwoo",
    "thomas-andre",
    "woo-jinchul",
    "yoo-jinho",
}

NODE_WORKFLOW_HARNESS = r"""
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const actualFs = require('node:fs');
const source = Buffer.from(process.env.SCRIPT_B64, 'base64').toString('utf8');
const scenario = JSON.parse(Buffer.from(process.env.SCENARIO_B64, 'base64').toString('utf8'));
const calls = [];
const outputs = {};
const messages = [];
const files = scenario.files || {};
const fakeFs = {
  ...actualFs,
  existsSync(file) {
    return Object.prototype.hasOwnProperty.call(files, file) || actualFs.existsSync(file);
  },
  readFileSync(file, encoding) {
    if (Object.prototype.hasOwnProperty.call(files, file)) return files[file];
    return actualFs.readFileSync(file, encoding);
  },
};
const fakeRequire = (name) => name === 'fs' ? fakeFs : require(name);
const record = (api, payload) => {
  calls.push({ api, payload });
  return { data: {} };
};
const missingLabels = new Set(scenario.missingLabels || []);
const github = {
  rest: {
    issues: {
      addLabels: async (payload) => record('issues.addLabels', payload),
      createComment: async (payload) => record('issues.createComment', payload),
      addAssignees: async (payload) => record('issues.addAssignees', payload),
      getLabel: async (payload) => {
        calls.push({ api: 'issues.getLabel', payload });
        if (missingLabels.has(payload.name)) {
          const error = new Error(`Label not found: ${payload.name}`);
          error.status = 404;
          throw error;
        }
        return { data: {} };
      },
      updateLabel: async (payload) => record('issues.updateLabel', payload),
      createLabel: async (payload) => record('issues.createLabel', payload),
      listForRepo: async (payload) => {
        calls.push({ api: 'issues.listForRepo', payload });
        return { data: scenario.issues || [] };
      },
    },
    repos: {
      get: async (payload) => {
        calls.push({ api: 'repos.get', payload });
        return { data: { default_branch: 'main' } };
      },
    },
  },
  request: async (route, payload) => {
    calls.push({ api: 'github.request', route, payload });
    return { data: {} };
  },
};
const context = {
  repo: { owner: 'owner', repo: 'repo' },
  payload: scenario.payload || {
    label: { name: 'squad:unknown' },
    issue: { number: 42, title: 'Test issue', body: '' },
  },
};
const core = {
  setOutput: (name, value) => { outputs[name] = String(value); },
  setFailed: (message) => { messages.push({ level: 'failed', message }); },
  info: (message) => { messages.push({ level: 'info', message }); },
  warning: (message) => { messages.push({ level: 'warning', message }); },
};
(async () => {
  try {
    await new AsyncFunction('github', 'context', 'core', 'require', source)(
      github, context, core, fakeRequire
    );
    console.log(JSON.stringify({ calls, outputs, messages }));
  } catch (error) {
    console.log(JSON.stringify({ calls, outputs, messages, error: error.message }));
    process.exitCode = 1;
  }
})();
"""


def _load_registry() -> dict[str, dict[str, Any]]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["agents"]


def _parse_team_statuses() -> dict[str, str]:
    statuses: dict[str, str] = {}
    in_members = False
    for line in TEAM_PATH.read_text(encoding="utf-8").splitlines():
        if line == "## Members":
            in_members = True
            continue
        if in_members and line.startswith("## "):
            break
        if not in_members or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 4 and cells[0] not in {"Name", "------"}:
            statuses[cells[0]] = cells[3]
    return statuses


def _load_routing_state() -> dict[str, Any]:
    match = re.search(
        r"## Operative Named-Member Routing.*?```json\s*(\{.*?\})\s*```",
        ROUTING_PATH.read_text(encoding="utf-8"),
        flags=re.DOTALL,
    )
    assert match is not None, "routing.md lacks operative routing JSON"
    return json.loads(match.group(1))


def _extract_step_script(workflow_path: Path, step_name: str) -> str:
    lines = workflow_path.read_text(encoding="utf-8").splitlines()
    step_index = next(
        index for index, line in enumerate(lines) if line.strip() == f"- name: {step_name}"
    )
    script_index = next(
        index
        for index in range(step_index + 1, len(lines))
        if lines[index].strip() == "script: |"
    )
    script_indent = len(lines[script_index]) - len(lines[script_index].lstrip())
    body: list[str] = []
    for line in lines[script_index + 1 :]:
        indent = len(line) - len(line.lstrip())
        if line.strip() and indent <= script_indent:
            break
        body.append(line[script_indent + 2 :] if line.strip() else "")
    assert body, f"No script found for {step_name} in {workflow_path}"
    return "\n".join(body)


def _run_workflow_script(
    workflow_path: Path,
    step_name: str,
    scenario: dict[str, Any],
    *,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = os.environ.copy()
    env["SCRIPT_B64"] = base64.b64encode(
        _extract_step_script(workflow_path, step_name).encode()
    ).decode()
    env["SCENARIO_B64"] = base64.b64encode(json.dumps(scenario).encode()).decode()
    env.update(extra_env or {})
    completed = subprocess.run(
        ["node", "-e", NODE_WORKFLOW_HARNESS],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


def _run_node(source: str) -> Any:
    completed = subprocess.run(
        ["node", "-e", source],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout.strip())


def _normalized_workflow(path: Path) -> bytes:
    """Normalize line endings only; every other workflow byte must match."""
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _calls(result: dict[str, Any], api: str) -> list[dict[str, Any]]:
    return [call for call in result["calls"] if call["api"] == api]


def _member_name(member_id: str) -> str:
    registry = _load_registry()
    if member_id in registry:
        return str(registry[member_id]["persistent_name"])
    if member_id == "copilot":
        return "@copilot"
    return member_id.replace("-", " ").title()


def _team_fixture(member_ids: list[str] | tuple[str, ...]) -> str:
    rows = "\n".join(
        f"| {_member_name(member_id)} | Lead | fixture | Active |"
        for member_id in member_ids
    )
    return "\n".join(
        (
            "## Members",
            "",
            "| Name | Role | Charter | Status |",
            "|------|------|---------|--------|",
            rows,
            "",
            "## Project Context",
        )
    )


def test_dormant_names_and_labels_fail_closed_to_coordinator() -> None:
    registry = _load_registry()
    routing = _load_routing_state()
    active = set(routing["active_members"])
    inactive = set(routing["inactive_members"])

    assert DORMANT_MEMBER_IDS.isdisjoint(active)
    assert DORMANT_MEMBER_IDS <= inactive
    assert routing["coordinator"] == "sung-jinwoo"
    assert routing["inactive_or_unlisted_action"] == "route_to_coordinator"
    for member_id in DORMANT_MEMBER_IDS:
        assert registry[member_id]["status"] == "inactive"


def test_current_fabric_roles_are_active_and_routable() -> None:
    registry = _load_registry()
    routing = _load_routing_state()
    assert set(routing["active_members"]) == ACTIVE_FABRIC_MEMBER_IDS
    for member_id in ACTIVE_FABRIC_MEMBER_IDS:
        assert registry[member_id]["status"] == "active"
        assert f"squad:{member_id}" == routing["issue_label_pattern"].replace(
            "{member-id}", member_id
        )


def test_registry_team_and_routing_statuses_cannot_diverge() -> None:
    registry = _load_registry()
    team_statuses = _parse_team_statuses()
    routing = _load_routing_state()
    active_ids = {
        member_id
        for member_id, member in registry.items()
        if member["status"] == "active"
    }
    inactive_ids = {
        member_id
        for member_id, member in registry.items()
        if member["status"] == "inactive"
    }
    assert active_ids | inactive_ids == set(registry)
    assert active_ids.isdisjoint(inactive_ids)
    assert set(routing["active_members"]) == active_ids
    assert set(routing["inactive_members"]) == inactive_ids
    for member_id, member in registry.items():
        prose_status = team_statuses[member["persistent_name"]].casefold()
        assert prose_status == "active" if member_id in active_ids else (
            "inactive" in prose_status and "dormant" in prose_status
        )


def test_every_active_workflow_has_exact_normalized_template_parity() -> None:
    assert {path.name for path in WORKFLOW_DIR.glob("*.yml")} == (
        ACTIVE_ROUTING_WORKFLOW_NAMES
    )
    for workflow_path, template_path in zip(
        ACTIVE_ROUTING_WORKFLOWS, ROUTING_TEMPLATE_PATHS, strict=True
    ):
        assert template_path.is_file(), f"Missing workflow template: {template_path}"
        assert _normalized_workflow(template_path) == _normalized_workflow(
            workflow_path
        ), f"Workflow template drift: {template_path} != {workflow_path}"


@pytest.mark.parametrize("target", REJECTED_TARGET_IDS)
def test_issue_assignment_outputs_rejection_and_never_calls_assignment_api(
    target: str,
) -> None:
    result = _run_workflow_script(
        WORKFLOW_DIR / "squad-issue-assign.yml",
        "Resolve operative routing state",
        {
            "payload": {
                "label": {"name": f"squad:{target}"},
                "issue": {"number": 42, "title": "Rejected route", "body": ""},
            }
        },
    )
    assert result["outputs"]["routing_approved"] == "false"
    assert result["outputs"]["target"] == target
    assert not {
        call["api"] for call in result["calls"]
    } & {"issues.addAssignees", "github.request"}


@pytest.mark.parametrize("target", sorted(ACTIVE_FABRIC_MEMBER_IDS))
def test_issue_assignment_approves_active_fabric_targets(target: str) -> None:
    result = _run_workflow_script(
        WORKFLOW_DIR / "squad-issue-assign.yml",
        "Resolve operative routing state",
        {
            "payload": {
                "label": {"name": f"squad:{target}"},
                "issue": {"number": 43, "title": "Approved route", "body": ""},
            }
        },
    )
    assert result["outputs"]["routing_approved"] == "true"
    assert result["outputs"]["target"] == target
    assert result["outputs"]["assigned_name"] == _member_name(target)
    assert not {
        call["api"] for call in result["calls"]
    } & {"issues.addLabels", "issues.addAssignees", "github.request"}


def test_issue_assignment_acknowledges_only_approved_active_fabric_route() -> None:
    target = "sung-jinwoo"
    assigned_name = _member_name(target)
    assigned_role = "POC Lead / Solution Architect"
    scenario = {
        "payload": {
            "label": {"name": f"squad:{target}"},
            "issue": {
                "number": 46,
                "title": "Approved acknowledgment",
                "body": "",
            },
        }
    }
    result = _run_workflow_script(
        WORKFLOW_DIR / "squad-issue-assign.yml",
        "Acknowledge approved member route",
        scenario,
        extra_env={
            "ROUTING_APPROVED": "true",
            "ROUTING_TARGET": target,
            "ASSIGNED_NAME": assigned_name,
            "ASSIGNED_ROLE": assigned_role,
        },
    )
    assert _calls(result, "issues.createComment") == [
        {
            "api": "issues.createComment",
            "payload": {
                "owner": "owner",
                "repo": "repo",
                "issue_number": 46,
                "body": "\n".join(
                    (
                        f"### 📋 Assigned to {assigned_name} ({assigned_role})",
                        "",
                        "**Issue:** #46 — Approved acknowledgment",
                        "",
                        f"{assigned_name} will pick this up in the next Copilot session.",
                        "",
                        "> **For Copilot coding agent:** If enabled, this issue will be worked automatically.",
                        "> Otherwise, start a Copilot session and say:",
                        f"> `{assigned_name}, work on issue #46`",
                    )
                ),
            },
        }
    ]

    for rejected_target in REJECTED_TARGET_IDS:
        rejected = _run_workflow_script(
            WORKFLOW_DIR / "squad-issue-assign.yml",
            "Acknowledge approved member route",
            scenario,
            extra_env={
                "ROUTING_APPROVED": "false",
                "ROUTING_TARGET": rejected_target,
                "ASSIGNED_NAME": _member_name(rejected_target),
                "ASSIGNED_ROLE": "Rejected fixture",
            },
        )
        assert not _calls(rejected, "issues.createComment"), rejected_target


def test_rejected_issue_path_only_routes_coordinator_triage() -> None:
    result = _run_workflow_script(
        WORKFLOW_DIR / "squad-issue-assign.yml",
        "Route rejected target to coordinator triage",
        {},
        extra_env={
            "COORDINATOR_LABEL": "squad:sung-jinwoo",
            "REJECTED_TARGET": "copilot",
        },
    )
    assert _calls(result, "issues.addLabels") == [
        {
            "api": "issues.addLabels",
            "payload": {
                "owner": "owner",
                "repo": "repo",
                "issue_number": 42,
                "labels": ["squad:sung-jinwoo"],
            },
        }
    ]
    assert not {
        call["api"] for call in result["calls"]
    } & {"issues.addAssignees", "github.request"}


@pytest.mark.parametrize("coordinator_label", ["squad:copilot", "squad:arbitrary"])
def test_rejected_issue_path_refuses_unauthorized_coordinator_label(
    coordinator_label: str,
) -> None:
    result = _run_workflow_script(
        WORKFLOW_DIR / "squad-issue-assign.yml",
        "Route rejected target to coordinator triage",
        {},
        extra_env={
            "COORDINATOR_LABEL": coordinator_label,
            "REJECTED_TARGET": "copilot",
        },
    )
    assert not _calls(result, "issues.addLabels")
    assert not {
        call["api"] for call in result["calls"]
    } & {"issues.addAssignees", "github.request"}


@pytest.mark.parametrize("routing_approved", ["false", "true"])
def test_issue_copilot_api_has_independent_fail_closed_gate(
    routing_approved: str,
) -> None:
    result = _run_workflow_script(
        WORKFLOW_DIR / "squad-issue-assign.yml",
        "Assign @copilot coding agent",
        {},
        extra_env={
            "ROUTING_APPROVED": routing_approved,
            "ROUTING_TARGET": "copilot",
        },
    )
    assert not {
        call["api"] for call in result["calls"]
    } & {"repos.get", "issues.addAssignees", "github.request"}


@pytest.mark.parametrize("target", sorted(ACTIVE_FABRIC_MEMBER_IDS))
def test_triage_calls_exact_label_apis_for_active_fabric_target(target: str) -> None:
    result = _run_workflow_script(
        WORKFLOW_DIR / "squad-triage.yml",
        "Triage issue via Lead agent",
        {
            "files": {".squad/team.md": _team_fixture([target])},
            "payload": {
                "label": {"name": "squad"},
                "issue": {"number": 44, "title": "Approved triage", "body": ""},
            },
        },
    )
    assert _calls(result, "issues.addLabels") == [
        {
            "api": "issues.addLabels",
            "payload": {
                "owner": "owner",
                "repo": "repo",
                "issue_number": 44,
                "labels": [f"squad:{target}"],
            },
        },
        {
            "api": "issues.addLabels",
            "payload": {
                "owner": "owner",
                "repo": "repo",
                "issue_number": 44,
                "labels": ["go:needs-research"],
            },
        },
    ]
    assert not {
        call["api"] for call in result["calls"]
    } & {"issues.addAssignees", "github.request"}


@pytest.mark.parametrize("target", REJECTED_TARGET_IDS)
def test_triage_never_calls_assignment_or_target_label_api_for_rejected_target(
    target: str,
) -> None:
    result = _run_workflow_script(
        WORKFLOW_DIR / "squad-triage.yml",
        "Triage issue via Lead agent",
        {
            "files": {
                ".squad/team.md": _team_fixture([target, "sung-jinwoo"]),
            },
            "payload": {
                "label": {"name": "squad"},
                "issue": {"number": 45, "title": "Rejected triage", "body": ""},
            },
        },
    )
    assert _calls(result, "issues.addLabels") == [
        {
            "api": "issues.addLabels",
            "payload": {
                "owner": "owner",
                "repo": "repo",
                "issue_number": 45,
                "labels": ["squad:sung-jinwoo"],
            },
        },
        {
            "api": "issues.addLabels",
            "payload": {
                "owner": "owner",
                "repo": "repo",
                "issue_number": 45,
                "labels": ["go:needs-research"],
            },
        },
    ]
    assert all(
        f"squad:{target}" not in call["payload"]["labels"]
        for call in _calls(result, "issues.addLabels")
    )
    assert not {
        call["api"] for call in result["calls"]
    } & {"issues.addAssignees", "github.request"}


def test_heartbeat_calls_exact_label_api_for_every_active_fabric_target() -> None:
    targets = sorted(ACTIVE_FABRIC_MEMBER_IDS)
    decisions = [
        {
            "issueNumber": index,
            "assignTo": target,
            "target": target,
            "label": f"squad:{target}",
            "reason": "fixture",
            "source": "fixture",
        }
        for index, target in enumerate(targets, start=101)
    ]
    result = _run_workflow_script(
        WORKFLOW_DIR / "squad-heartbeat.yml",
        "Ralph — Apply triage decisions",
        {"files": {"triage-results.json": json.dumps(decisions)}},
    )
    assert _calls(result, "issues.addLabels") == [
        {
            "api": "issues.addLabels",
            "payload": {
                "owner": "owner",
                "repo": "repo",
                "issue_number": index,
                "labels": [f"squad:{target}"],
            },
        }
        for index, target in enumerate(targets, start=101)
    ]
    assert not {
        call["api"] for call in result["calls"]
    } & {"issues.addAssignees", "github.request"}


def test_heartbeat_reauthorizes_rejected_decisions_to_coordinator() -> None:
    decisions = [
        {
            "issueNumber": index,
            "assignTo": target,
            "target": target,
            "label": f"squad:{target}",
            "reason": "fixture",
            "source": "fixture",
        }
        for index, target in enumerate(REJECTED_TARGET_IDS, start=1)
    ]
    result = _run_workflow_script(
        WORKFLOW_DIR / "squad-heartbeat.yml",
        "Ralph — Apply triage decisions",
        {"files": {"triage-results.json": json.dumps(decisions)}},
    )
    assert _calls(result, "issues.addLabels") == [
        {
            "api": "issues.addLabels",
            "payload": {
                "owner": "owner",
                "repo": "repo",
                "issue_number": index,
                "labels": ["squad:sung-jinwoo"],
            },
        }
        for index in range(1, len(REJECTED_TARGET_IDS) + 1)
    ]
    assert not {
        call["api"] for call in result["calls"]
    } & {"issues.addAssignees", "github.request"}


def test_heartbeat_copilot_assignment_never_uses_roster_as_authority() -> None:
    result = _run_workflow_script(
        WORKFLOW_DIR / "squad-heartbeat.yml",
        "Ralph — Assign @copilot issues",
        {
            "files": {
                ".squad/team.md": (
                    "🤖 Coding Agent @copilot\n<!-- copilot-auto-assign: true -->"
                )
            },
            "issues": [
                {
                    "number": 7,
                    "labels": [{"name": "squad:copilot"}],
                    "assignees": [],
                }
            ],
        },
    )
    assert not {
        call["api"] for call in result["calls"]
    } & {"issues.listForRepo", "repos.get", "issues.addAssignees", "github.request"}


@pytest.mark.parametrize(
    ("missing_active_labels", "write_api"),
    [(False, "issues.updateLabel"), (True, "issues.createLabel")],
)
def test_label_sync_writes_exact_active_routes_and_no_rejected_routes(
    missing_active_labels: bool,
    write_api: str,
) -> None:
    active_targets = sorted(ACTIVE_FABRIC_MEMBER_IDS)
    all_targets = [*active_targets, *REJECTED_TARGET_IDS]
    active_labels = [f"squad:{target}" for target in active_targets]
    result = _run_workflow_script(
        WORKFLOW_DIR / "sync-squad-labels.yml",
        "Parse roster and sync labels",
        {
            "files": {".squad/team.md": _team_fixture(all_targets)},
            "missingLabels": active_labels if missing_active_labels else [],
        },
    )
    expected_writes = [
        {
            "api": write_api,
            "payload": {
                "owner": "owner",
                "repo": "repo",
                "name": f"squad:{target}",
                "color": "9B8FCC",
                "description": f"Assigned to {_member_name(target)} (Lead)",
            },
        }
        for target in active_targets
    ]
    route_writes = [
        call
        for call in _calls(result, write_api)
        if call["payload"]["name"].startswith("squad:")
    ]
    assert route_writes == expected_writes
    rejected_labels = {f"squad:{target}" for target in REJECTED_TARGET_IDS}
    assert not any(
        call["payload"]["name"] in rejected_labels
        for api in ("issues.getLabel", "issues.updateLabel", "issues.createLabel")
        for call in _calls(result, api)
    )


def test_ralph_filters_roster_and_routes_rejected_targets_to_coordinator() -> None:
    result = _run_node(
        f"""
const fs = require('node:fs');
const ralph = require({json.dumps(str(RALPH_PATH))});
const routingMd = fs.readFileSync({json.dumps(str(ROUTING_PATH))}, 'utf8');
const teamMd = fs.readFileSync({json.dumps(str(TEAM_PATH))}, 'utf8');
const state = ralph.parseRoutingState(routingMd);
const roster = ralph.parseRoster(teamMd, state.activeMemberIds);
const rejected = {json.dumps(REJECTED_TARGET_IDS)}.map((target) => {{
  const decision = ralph.triageIssue(
    {{ title: 'trigger', body: '' }},
    [{{ workType: 'fixture', agentName: target, keywords: ['trigger'] }}],
    [],
    roster,
    state,
  );
  return {{ target, agent: decision.agent.id, source: decision.source }};
}});
console.log(JSON.stringify({{ roster: roster.map((member) => member.id), rejected }}));
"""
    )
    assert not set(REJECTED_TARGET_IDS) & set(result["roster"])
    assert all(item["agent"] == "sung-jinwoo" for item in result["rejected"])
    assert all(item["source"] == "routing-fallback" for item in result["rejected"])


def test_ralph_preserves_valid_active_fabric_role_routing() -> None:
    result = _run_node(
        f"""
const fs = require('node:fs');
const ralph = require({json.dumps(str(RALPH_PATH))});
const routingMd = fs.readFileSync({json.dumps(str(ROUTING_PATH))}, 'utf8');
const teamMd = fs.readFileSync({json.dumps(str(TEAM_PATH))}, 'utf8');
const state = ralph.parseRoutingState(routingMd);
const roster = ralph.parseRoster(teamMd, state.activeMemberIds);
const rules = ralph.parseRoutingRules(routingMd);
const fixtures = [
  ['historical-summary boundary', 'sung-jinwoo'],
  ['semantic model', 'go-gunhee'],
  ['run-level schema', 'woo-jinchul'],
  ['calibration CLI/schemas/runbook', 'yoo-jinho'],
  ['reproducibility', 'baek-yoonho'],
  ['secret handling', 'thomas-andre'],
  ['paused-capacity controls', 'igris'],
];
const decisions = fixtures.map(([title, expected]) => {{
  const decision = ralph.triageIssue(
    {{ title, body: '' }}, rules, [], roster, state
  );
  return {{ title, expected, actual: decision.agent.id }};
}});
console.log(JSON.stringify(decisions));
"""
    )
    assert all(item["actual"] == item["expected"] for item in result), result


def test_embedded_workflow_javascript_is_syntactically_valid() -> None:
    for workflow_path in (*ACTIVE_ROUTING_WORKFLOWS, *ROUTING_TEMPLATE_PATHS):
        workflow = workflow_path.read_text(encoding="utf-8")
        step_names = re.findall(r"^\s+- name: (.+)$", workflow, flags=re.MULTILINE)
        for step_name in step_names:
            try:
                script = _extract_step_script(workflow_path, step_name)
            except (AssertionError, StopIteration):
                continue
            completed = subprocess.run(
                ["node", "--check", "-"],
                input=f"(async () => {{\n{script}\n}})();\n",
                capture_output=True,
                text=True,
            )
            assert completed.returncode == 0, (
                f"{workflow_path}:{step_name}\n{completed.stderr}"
            )
