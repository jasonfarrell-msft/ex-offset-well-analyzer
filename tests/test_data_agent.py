"""Static validation for the source-controlled Fabric Data Agent definition."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "fabric" / "da_drillrun_summary.DataAgent"
CONFIG = AGENT / "Files" / "Config"
DRAFT = CONFIG / "draft"
SOURCE = DRAFT / "semantic-model-sm_drillrun_summary" / "datasource.json"
PUBLISHED = CONFIG / "published"
PUBLISHED_SOURCE = (
    PUBLISHED / "semantic-model-sm_drillrun_summary" / "datasource.json"
)
PUBLISH_INFO = CONFIG / "publish_info.json"
SYNTHETIC_LABEL = (
    "SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY"
)
DATA_AGENT_VERSION = "v1.0.1"

PLATFORM_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/"
    "gitIntegration/platformProperties/2.0.0/schema.json"
)
AGENT_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/"
    "definition/dataAgent/2.1.0/schema.json"
)
STAGE_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/"
    "definition/stageConfiguration/1.0.0/schema.json"
)
SOURCE_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/"
    "definition/dataSource/1.0.0/schema.json"
)
PUBLISH_INFO_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/"
    "definition/publishInfo/1.0.0/schema.json"
)
EXPECTED_TABLES = {"Wells", "Dataset Metadata", "Data Quality", "Categories"}


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    assert isinstance(value, dict)
    return value


def test_required_definition_parts_and_official_schemas() -> None:
    expected = {
        ".platform",
        "Files/Config/data_agent.json",
        "Files/Config/draft/stage_config.json",
        "Files/Config/draft/semantic-model-sm_drillrun_summary/datasource.json",
        "Files/Config/publish_info.json",
        "Files/Config/published/stage_config.json",
        "Files/Config/published/semantic-model-sm_drillrun_summary/datasource.json",
    }
    actual = {
        path.relative_to(AGENT).as_posix()
        for path in AGENT.rglob("*")
        if path.is_file()
    }
    assert actual == expected

    platform = _load(AGENT / ".platform")
    agent = _load(CONFIG / "data_agent.json")
    stage = _load(DRAFT / "stage_config.json")
    source = _load(SOURCE)
    published_stage = _load(PUBLISHED / "stage_config.json")
    published_source = _load(PUBLISHED_SOURCE)
    publish_info = _load(PUBLISH_INFO)

    assert platform["$schema"] == PLATFORM_SCHEMA
    assert agent == {"$schema": AGENT_SCHEMA}
    assert stage["$schema"] == STAGE_SCHEMA
    assert isinstance(stage["aiInstructions"], str) and stage["aiInstructions"].strip()
    assert source["$schema"] == SOURCE_SCHEMA
    assert published_stage["$schema"] == STAGE_SCHEMA
    assert published_source["$schema"] == SOURCE_SCHEMA
    assert publish_info["$schema"] == PUBLISH_INFO_SCHEMA
    assert set(publish_info) == {"$schema", "description"}
    assert "calibration-only" in publish_info["description"].casefold()
    assert "unshared" in publish_info["description"].casefold()
    assert DATA_AGENT_VERSION in publish_info["description"]

    assert {"$schema", "metadata", "config"} <= platform.keys()
    assert {"type", "displayName"} <= platform["metadata"].keys()
    assert {"version", "logicalId"} <= platform["config"].keys()
    platform_description = platform["metadata"]["description"].casefold()
    assert DATA_AGENT_VERSION in platform_description
    assert "calibration-only" in platform_description
    assert "draft" in platform_description
    assert "published" in platform_description
    assert "unshared" in platform_description
    assert "draft-only" not in platform_description
    assert "production" not in platform_description
    assert "general sharing" not in platform_description
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        platform["config"]["logicalId"],
    )
    assert {
        "$schema",
        "artifactId",
        "workspaceId",
        "displayName",
        "type",
    } <= source.keys()


def test_exact_item_source_and_table_selection() -> None:
    platform = _load(AGENT / ".platform")
    source_files = list(DRAFT.glob("*/datasource.json"))
    published_source_files = list(PUBLISHED.glob("*/datasource.json"))
    assert platform["metadata"]["type"] == "DataAgent"
    assert platform["metadata"]["displayName"] == "da_drillrun_summary"
    assert len(source_files) == 1
    assert len(published_source_files) == 1

    source = _load(source_files[0])
    assert source["artifactId"] == "ee7583b6-5be7-4802-83a8-530ce7dd8351"
    assert source["workspaceId"] == "4e1977a8-d7ff-487e-b42d-c4b3bc118f3d"
    assert source["displayName"] == "sm_drillrun_summary"
    assert source["type"] == "semantic_model"
    assert source["metadata"]["selectionMode"] == "explicit"
    assert source["metadata"]["datasetVersion"] == "v1.0.0"

    elements = source["elements"]
    assert len(elements) == 4
    assert {element["display_name"] for element in elements} == EXPECTED_TABLES
    assert all(element["type"] == "semantic_model.table" for element in elements)
    assert all(element["is_selected"] is True for element in elements)
    assert len({element["id"] for element in elements}) == 4
    assert all("children" not in element for element in elements)


def test_agent_instructions_enforce_required_behavior() -> None:
    raw_instructions = _load(DRAFT / "stage_config.json")["aiInstructions"]
    instructions = raw_instructions.casefold()
    source_instructions = _load(SOURCE)["dataSourceInstructions"].casefold()
    combined = f"{instructions}\n{source_instructions}"

    required_phrases = {
        "historical-summary",
        "sm_drillrun_summary",
        "synthetic data • v1.0.0 • development / historical summary only",
        "explicit semantic-model measures",
        "do not invent calculations",
        "source-history summaries",
        "may include quarantined source runs",
        "clarify ambiguous",
        "exact raw records",
        "individual run detail",
        "deep provenance",
        "prediction",
        "similarity",
        "operational prioritization",
        "operational recommendations",
        "real-data",
        "secrets",
        "credentials",
        "write actions",
        "administrative actions",
        "destructive actions",
        "outside the selected semantic-model scope",
        "questions or data",
        "governance files",
        "grader expected answers",
        "sql views",
        "raw tables",
        "data agent output supports it",
        "dataset version v1.0.0",
        "never fabricate a citation",
        "clean-conversation",
        "do not assume memory",
    }
    missing = sorted(phrase for phrase in required_phrases if phrase not in combined)
    assert not missing, f"Missing instruction controls: {missing}"
    exact_first_line_instruction = (
        f"Begin EVERY response with exactly this first line: {SYNTHETIC_LABEL}"
    )
    assert exact_first_line_instruction in raw_instructions
    assert "The exact line must appear before any other text." in raw_instructions
    assert (
        "normal answers, clarifications, refusals, tool or query errors, "
        "partial answers"
    ) in raw_instructions
    assert "never condition it on a successful query" in instructions
    assert "or equivalent" not in instructions
    assert "semantically equivalent" not in instructions
    assert raw_instructions.endswith(
        "replace or prepend the first line so the response starts exactly with: "
        + SYNTHETIC_LABEL
    )

    for table in EXPECTED_TABLES:
        assert table.casefold() in combined


def test_published_definition_matches_draft_without_fewshots_or_actions() -> None:
    paths = [path.relative_to(AGENT).as_posix().casefold() for path in AGENT.rglob("*")]
    assert _load(PUBLISHED / "stage_config.json") == _load(DRAFT / "stage_config.json")
    assert _load(PUBLISHED_SOURCE) == _load(SOURCE)
    assert not any(path.endswith("fewshots.json") for path in paths)

    documents = [
        _load(AGENT / ".platform"),
        _load(CONFIG / "data_agent.json"),
        _load(DRAFT / "stage_config.json"),
        _load(SOURCE),
        _load(PUBLISH_INFO),
        _load(PUBLISHED / "stage_config.json"),
        _load(PUBLISHED_SOURCE),
    ]
    serialized = json.dumps(documents).casefold()
    prohibited_keys = {
        "actions",
        "tools",
        "writeback",
        "connectionstring",
        "password",
        "secret",
        "token",
    }
    for document in documents:
        stack = [document]
        discovered_keys: set[str] = set()
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                discovered_keys.update(str(key).casefold() for key in value)
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
        assert prohibited_keys.isdisjoint(discovered_keys)

    assert '"type": "lakehouse' not in serialized
    assert '"type": "data_warehouse"' not in serialized
    assert '"type": "kusto"' not in serialized
    assert '"type": "graph"' not in serialized


def test_definition_makes_no_prohibited_access_or_capability_claims() -> None:
    stage = _load(DRAFT / "stage_config.json")["aiInstructions"]
    source = _load(SOURCE)
    controlled_text = "\n".join(
        [
            stage,
            source["dataSourceInstructions"],
            source["userDescription"],
            *(element["description"] for element in source["elements"]),
        ]
    ).casefold()

    prohibited_claims = {
        "i can access raw",
        "i have access to raw",
        "has access to governance files",
        "has access to grader expected answers",
        "has access to sql views",
        "can directly query raw",
        "can directly query curated",
        "uses real data",
        "production data source",
        "can update",
        "can delete",
        "can publish",
        "can deploy",
        "will recommend operations",
    }
    present = sorted(claim for claim in prohibited_claims if claim in controlled_text)
    assert not present, f"Prohibited capability claims found: {present}"
