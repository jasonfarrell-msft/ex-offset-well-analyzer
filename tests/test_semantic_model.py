"""Static validation for the source-controlled historical-summary semantic model."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "fabric" / "sm_drillrun_summary.SemanticModel"
DEFINITION = MODEL / "definition"
TABLES = DEFINITION / "tables"

APPROVED_VIEWS = {
    ("serving", "well_summary"),
    ("serving", "dataset_summary"),
    ("serving", "quality_summary"),
    ("serving", "category_summary"),
}
REQUIRED_TABLES = {"Wells", "Dataset Metadata", "Data Quality", "Categories"}
REQUIRED_MEASURES = {
    "Well Count",
    "Total Section Count",
    "Total Source Run Count",
    "Total Accepted Run Count",
    "Total Quarantined Run Count",
    "Total Footage",
    "Average Footage per Run",
    "Total Quarantined Footage",
    "Total Duration",
    "Average Duration per Run",
    "Total Quarantined Duration",
    "Data Quality Issue Count",
    "Selected Group Affected Well Count",
    "Selected Group Affected Section Count",
    "Selected Group Affected Run Count",
    "Total Rejected Record Count",
    "Selected Category Record Count",
    "Synthetic Dataset Label",
}
PROHIBITED_MODEL_TERMS = {
    "prediction",
    "similarity",
    "recommendation",
    "forecast",
    "confidence",
    "operational advice",
}
TECHNICAL_SOURCE_COLUMNS = {
    "generation_run_id",
    "deterministic_seed",
    "manifest_sha256",
    "_transformation_contract_version",
    "well_id",
}
EXPECTED_RELATIONSHIPS = {
    "7818cc74-a18b-581e-9e5d-3f3f29285338": (
        "Wells.'Dataset Version'",
        "'Dataset Metadata'.'Dataset Version'",
    ),
    "77f296d9-35c8-5ff4-91b3-872edcfbde38": (
        "'Data Quality'.'Dataset Version'",
        "'Dataset Metadata'.'Dataset Version'",
    ),
    "2707238b-f951-5a36-ac5a-9e4d8445c49d": (
        "Categories.'Dataset Version'",
        "'Dataset Metadata'.'Dataset Version'",
    ),
}


def _table_files() -> list[Path]:
    return sorted(TABLES.glob("*.tmdl"))


def _text_files() -> list[Path]:
    return sorted(MODEL.rglob("*.tmdl"))


def _entity_blocks(text: str, kind: str) -> dict[str, str]:
    """Return top-level TMDL column or measure blocks from one table file."""
    declaration = r"([^=\n]+?)\s*=[^\n]*" if kind == "measure" else r"([^\n]+?)"
    pattern = re.compile(
        rf"(?ms)^\t{kind} {declaration}\n"
        rf"(.*?)(?=^\t(?:measure|column|partition|annotation) |\Z)"
    )
    return {
        raw_name.strip().strip("'"): body
        for raw_name, body in pattern.findall(text)
    }


def _entity_descriptions(text: str, kind: str) -> dict[str, str]:
    """Return TMDL triple-slash descriptions attached to table child objects."""
    descriptions: dict[str, str] = {}
    lines = text.splitlines()
    for index, line in enumerate(lines):
        prefix = f"\t{kind} "
        if not line.startswith(prefix):
            continue
        declaration = line.removeprefix(prefix)
        name = (
            re.split(r"\s*=\s*", declaration, maxsplit=1)[0]
            if kind == "measure"
            else declaration
        ).strip().strip("'")
        comment_lines: list[str] = []
        cursor = index - 1
        while cursor >= 0 and lines[cursor].startswith("\t/// "):
            comment_lines.append(lines[cursor].removeprefix("\t/// "))
            cursor -= 1
        descriptions[name] = "\n".join(reversed(comment_lines))
    return descriptions


def test_item_uses_current_source_control_structure() -> None:
    platform = json.loads((MODEL / ".platform").read_text())
    pbism = json.loads((MODEL / "definition.pbism").read_text())

    assert platform["metadata"]["type"] == "SemanticModel"
    assert platform["metadata"]["displayName"] == "Drill Run Historical Summary"
    assert platform["config"]["version"] == "2.0"
    assert re.fullmatch(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
        platform["config"]["logicalId"],
    )
    assert pbism["version"] == "4.0"
    assert (DEFINITION / "database.tmdl").is_file()
    assert (DEFINITION / "model.tmdl").is_file()
    assert (DEFINITION / "relationships.tmdl").is_file()
    assert (DEFINITION / "expressions.tmdl").is_file()
    assert (DEFINITION / "cultures" / "en-US.tmdl").is_file()


def test_model_table_inventory_and_references_match() -> None:
    table_names: set[str] = set()
    for path in _table_files():
        match = re.search(r"(?m)^table (.+)$", path.read_text())
        assert match, f"{path} has no table declaration"
        table_names.add(match.group(1).strip().strip("'"))

    model = (DEFINITION / "model.tmdl").read_text()
    refs = {
        value.strip().strip("'")
        for value in re.findall(r"(?m)^ref table (.+)$", model)
    }
    assert table_names == REQUIRED_TABLES
    assert refs == table_names
    assert "discourageImplicitMeasures" in model


def test_every_table_column_and_measure_has_a_description() -> None:
    for path in _table_files():
        text = path.read_text()
        assert re.match(r"(?s)^/// \S.*\ntable .+$", text.split("\n\n", 1)[0]), path

        for kind in ("measure", "column"):
            blocks = _entity_blocks(text, kind)
            descriptions = _entity_descriptions(text, kind)
            assert blocks, f"{path} has no {kind}s"
            assert descriptions.keys() == blocks.keys()
            for name, description in descriptions.items():
                assert description, (
                    f"{path.name} {kind} {name!r} needs a description"
                )


def test_descriptions_use_parser_supported_triple_slash_syntax() -> None:
    """Description is special TMDL syntax, not a colon-delimited TOM property."""
    for path in _text_files():
        text = path.read_text()
        assert not re.search(r"(?m)^\s*description\s*:", text), (
            f"{path} uses unsupported description: property syntax"
        )
        assert not re.search(r"(?m)^(\t*)/// .+\n\s*\n\1(?:table|measure|column) ", text), (
            f"{path} separates a description from its object declaration"
        )


def test_required_explicit_measures_exist() -> None:
    measures: set[str] = set()
    for path in _table_files():
        measures.update(_entity_blocks(path.read_text(), "measure"))
    assert REQUIRED_MEASURES <= measures

    wells = (TABLES / "Wells.tmdl").read_text()
    synthetic = _entity_blocks(wells, "measure")["Synthetic Dataset Label"]
    assert "SYNTHETIC DATA" in synthetic
    assert "Dataset Version" in synthetic


def test_synthetic_label_reads_the_single_nonblank_active_release() -> None:
    wells = (TABLES / "Wells.tmdl").read_text()
    synthetic = _entity_blocks(wells, "measure")["Synthetic Dataset Label"]

    # A DirectQuery relationship can expose its unknown blank member alongside
    # the one metadata row, so SELECTEDVALUE must not classify that as multiple
    # releases. The model contract publishes exactly one active nonblank row.
    assert "SELECTEDVALUE" not in synthetic
    assert "Multiple versions" not in synthetic
    assert "MAXX(" in synthetic
    assert "FILTER(" in synthetic
    assert "ALL('Dataset Metadata'[Dataset Version])" in synthetic
    assert "NOT ISBLANK('Dataset Metadata'[Dataset Version])" in synthetic
    assert 'COALESCE(VersionLabel, "METADATA MISSING")' in synthetic
    assert (
        '"SYNTHETIC DATA • " & DisplayVersion '
        '& " • DEVELOPMENT / HISTORICAL SUMMARY ONLY"'
    ) in synthetic


def test_table_object_names_are_unique_across_columns_and_measures() -> None:
    for path in _table_files():
        text = path.read_text()
        names = [
            *_entity_blocks(text, "column"),
            *_entity_blocks(text, "measure"),
        ]
        normalized_names = [name.casefold() for name in names]
        duplicates = sorted(
            name for name in set(normalized_names)
            if normalized_names.count(name) > 1
        )
        assert not duplicates, (
            f"{path.name} has case-insensitive object-name collisions: "
            f"{duplicates}"
        )


def test_numeric_columns_do_not_invite_implicit_aggregation() -> None:
    for path in _table_files():
        for name, block in _entity_blocks(path.read_text(), "column").items():
            assert "\t\tsummarizeBy: none" in block, (
                f"{path.name} column {name!r} must use summarizeBy none"
            )


def test_all_partitions_are_directquery_over_only_approved_serving_views() -> None:
    found_views: set[tuple[str, str]] = set()
    for path in _table_files():
        text = path.read_text()
        assert len(re.findall(r"(?m)^\tpartition ", text)) == 1, path
        assert re.search(r"(?m)^\t\tmode: directQuery$", text), path
        assert "Sql.Database(SqlEndpointHost, SqlEndpointDatabase)" in text

        refs = {
            (schema, item)
            for schema, item in re.findall(
                r'Schema="([^"]+)", Item="([^"]+)"', text
            )
        }
        assert len(refs) == 1, path
        assert refs <= APPROVED_VIEWS, f"{path} references an unapproved object"
        found_views.update(refs)

    assert found_views == APPROVED_VIEWS


def test_endpoint_parameters_target_the_expected_database() -> None:
    expressions = (DEFINITION / "expressions.tmdl").read_text()
    expected_parameters = {
        "SqlEndpointHost": "SET-BY-DEPLOYMENT",
        "SqlEndpointDatabase": "lh_drillrun_summary",
    }
    parameter_pattern = re.compile(
        r'^expression (\w+) = "([^"]+)" meta '
        r'\[IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true\]$',
        re.MULTILINE,
    )
    assert dict(parameter_pattern.findall(expressions)) == expected_parameters
    assert "annotation IsParameterQuery" not in expressions

    for path in _table_files():
        text = path.read_text()
        assert text.count(
            "Sql.Database(SqlEndpointHost, SqlEndpointDatabase)"
        ) == 1
        assert "SET-BY-DEPLOYMENT" not in text
        assert "lh_drillrun_summary" not in text
    # Host binding is intentionally environment-specific and must not be a secret.
    assert "password" not in expressions.lower()
    assert "token" not in expressions.lower()


def test_category_measure_never_aggregates_mixed_family_grains() -> None:
    text = (TABLES / "Categories.tmdl").read_text()
    measures = _entity_blocks(text, "measure")

    assert "Category Record Count" not in measures
    selected = measures["Selected Category Record Count"]
    declaration = re.search(
        r"(?m)^\tmeasure 'Selected Category Record Count' = (.+)$", text
    )
    assert declaration
    expression = declaration.group(1)
    assert "HASONEVALUE(Categories[Category Name])" in expression
    assert "SUM(Categories[Record Count])" in expression
    assert "BLANK()" in expression
    assert "accepted historical" not in text.lower()
    assert "mud" not in text.lower()
    assert "trajectory" not in text.lower()
    assert "raw sections" in text.lower()
    assert "raw runs" in text.lower()
    assert "may include quarantined runs" in text.lower()
    assert "it is not Total Accepted Run Count" in text


def test_affected_entity_measures_are_safe_for_overlapping_groups() -> None:
    text = (TABLES / "Data Quality.tmdl").read_text()
    measures = _entity_blocks(text, "measure")

    for entity in ("Well", "Section", "Run"):
        name = f"Selected Group Affected {entity} Count"
        source_name = f"Affected {entity} Count"
        block = measures[name]
        declaration = re.search(
            rf"(?m)^\tmeasure '{re.escape(name)}' = (.+)$", text
        )
        assert declaration
        expression = declaration.group(1)
        assert "COUNTROWS('Data Quality') = 1" in expression
        assert f"MAX('Data Quality'[{source_name}])" in expression
        assert "BLANK()" in expression
        assert f"SUM('Data Quality'[{source_name}])" not in expression
        description = _entity_descriptions(text, "measure")[name]
        assert "returns blank across multiple groups" in description

    assert "Affected Entity Count" not in measures
    assert not re.search(
        r"Affected Well Count\]\s*\+\s*.*Affected Section Count\]",
        text,
    )


def test_category_scope_documentation_is_accurate() -> None:
    text = (ROOT / "docs" / "semantic-model-design.md").read_text()
    lower = text.lower()

    assert "source-history summaries" in lower
    assert "may include quarantined records" in lower
    assert "accepted run count" in lower
    assert "source-category record count" in lower
    assert "does not fabricate accepted-only category measures" in lower
    assert "mud type" not in lower
    assert "trajectory profile" not in lower


def test_semantic_model_documentation_records_deployed_status_without_overclaiming() -> None:
    text = (ROOT / "docs" / "semantic-model-design.md").read_text()
    lower = text.lower()

    assert "ee7583b6-5be7-4802-83a8-530ce7dd8351" in text
    assert "ws-welladvisor-drillrunhistory-poc-dev" in text
    assert "directquery" in lower
    assert "live dax results were reconciled" in lower
    assert "answer-quality evaluation has been executed or approved" in lower
    assert "sole analytical source for the fabric data agent definition" in lower
    assert "no report, custom user interface" in lower
    assert "report, custom user interface" in lower
    assert "checked-in portable definition intentionally retains" in lower
    assert 'SqlEndpointHost = "SET-BY-DEPLOYMENT"' in text
    assert "it is local only" not in lower
    assert "no deployment was attempted" not in lower
    assert "before a later deployment" not in lower


def test_technical_audit_columns_are_hidden_but_retained() -> None:
    found: set[str] = set()
    for path in _table_files():
        for _, block in _entity_blocks(path.read_text(), "column").items():
            source_match = re.search(r"(?m)^\t\tsourceColumn: (.+)$", block)
            assert source_match
            source = source_match.group(1).strip()
            if source in TECHNICAL_SOURCE_COLUMNS:
                found.add(source)
                assert re.search(r"(?m)^\t\tisHidden$", block), (
                    f"{path.name} technical column {source} must be hidden"
                )
    assert found == TECHNICAL_SOURCE_COLUMNS


def test_relationships_are_single_direction_one_to_many() -> None:
    text = (DEFINITION / "relationships.tmdl").read_text()
    blocks = re.split(r"(?m)(?=^relationship )", text)
    relationships = [block for block in blocks if block.startswith("relationship ")]
    assert len(relationships) == 3

    actual: dict[str, dict[str, str]] = {}
    for block in relationships:
        declaration, *property_lines = block.strip().splitlines()
        relationship_id = declaration.removeprefix("relationship ")
        properties = dict(
            line.strip().split(": ", 1)
            for line in property_lines
            if ": " in line
        )
        assert set(properties) == {
            "fromCardinality",
            "toCardinality",
            "crossFilteringBehavior",
            "fromColumn",
            "toColumn",
        }
        actual[relationship_id] = properties

    assert set(actual) == set(EXPECTED_RELATIONSHIPS)
    for relationship_id, (from_column, to_column) in EXPECTED_RELATIONSHIPS.items():
        properties = actual[relationship_id]
        # TOM defines From as the many/child end and To as the one/parent end.
        # OneDirection propagates filters from To to From. These endpoint
        # assertions intentionally reject the inverse spelling rejected by AS.
        assert properties["fromCardinality"] == "many"
        assert properties["toCardinality"] == "one"
        assert properties["crossFilteringBehavior"] == "oneDirection"
        assert properties["fromColumn"] == from_column
        assert properties["toColumn"] == to_column
        assert not properties["fromColumn"].startswith("'Dataset Metadata'.")
        assert properties["toColumn"].startswith("'Dataset Metadata'.")


def test_model_contains_no_out_of_scope_analytical_terms() -> None:
    text = "\n".join(path.read_text().lower() for path in _text_files())
    for term in PROHIBITED_MODEL_TERMS:
        assert term not in text


def test_no_report_item_was_created() -> None:
    assert not list((ROOT / "fabric").glob("*.Report"))
