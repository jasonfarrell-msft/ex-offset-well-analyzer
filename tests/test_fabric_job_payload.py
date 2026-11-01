import base64
import json
from pathlib import Path


NOTEBOOK_IPYNB_PATH = Path(
    "fabric/nb_10_build_drillrun_summary.Notebook/notebook-content.ipynb"
)
PLATFORM_PATH = Path("fabric/nb_10_build_drillrun_summary.Notebook/.platform")
PAYLOAD_PATH = Path(".azure/notebook-update-body-v120-py.json")
RUN_PAYLOAD_PATH = Path(".azure/notebook-run-v120-readiness.json")
RECOVERY_RUN_PAYLOAD_PATH = Path(".azure/notebook-run-v120-recovery.json")
ACTIVE_V120_UPDATE_BODIES = [
    Path(".azure/notebook-update-body-v120-py.json"),
    Path(".azure/notebook-update-body-v120.json"),
    Path(".azure/notebook-update-body-generated.json"),
]
EXPECTED_LAKEHOUSE_ID = "964afbf5-6a33-46dc-98c1-be726d0f4999"
EXPECTED_WORKSPACE_ID = "4e1977a8-d7ff-487e-b42d-c4b3bc118f3d"
EXPECTED_LAKEHOUSE_NAME = "lh_drillrun_summary"
EXPECTED_RELEASE_ID = "v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0"
EXPECTED_RECOVERY_ATTEMPT_ID = "75134ad8-4c93-494a-a215-5a7defe4233c"
EXPECTED_RECOVERY_APPLICATION_ID = "application_1793392911491_0001"
EXPECTED_RECOVERY_JOB_INSTANCE_ID = "edf4cc1c-a02a-4ade-82e2-31f4d926dfe2"
EXPECTED_RECOVERY_END_TIME_UTC = "2026-10-30T20:52:19.1351093"
RECOVERY_FIXTURE_PATH = Path(".azure/fabric-v1.2-recovery-job.json")


def _decode_notebook_payload_bytes(payload: dict) -> bytes:
    notebook_part = payload["definition"]["parts"][0]
    return base64.b64decode(notebook_part["payload"])


def _decode_platform_payload_bytes(payload: dict) -> bytes:
    platform_part = payload["definition"]["parts"][1]
    return base64.b64decode(platform_part["payload"])


def _decode_notebook_payload_json(payload: dict) -> dict:
    return json.loads(_decode_notebook_payload_bytes(payload).decode("utf-8"))


def _parameters_code_cells(notebook_payload_json: dict) -> list[dict]:
    return [
        cell
        for cell in notebook_payload_json["cells"]
        if cell.get("cell_type") == "code"
        and "parameters" in cell.get("metadata", {}).get("tags", [])
    ]


def _all_code_cell_source(notebook_payload_json: dict) -> str:
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook_payload_json["cells"]
        if cell.get("cell_type") == "code"
    )


def _canonical_recovery_summary(payload: dict) -> dict[str, str]:
    activity_details = (
        payload["properties"]["computeDetails"]["monitoringInfo"]["activityDetails"]
    )
    creator_item = activity_details["creatorItem"]
    status = str(payload["status"])
    spark_application_id = str(activity_details["sparkApplicationId"])
    workspace_id = str(creator_item["workspaceId"])
    item_id = str(creator_item["itemId"])
    job_item_id = str(payload["itemId"])
    end_time_utc = str(payload["endTimeUtc"])
    root_activity_id = str(payload["rootActivityId"])
    failure_error_code = str(payload["failureReason"]["errorCode"])

    assert status == "Failed"
    assert spark_application_id
    assert workspace_id
    assert item_id
    assert job_item_id == item_id
    assert end_time_utc
    assert root_activity_id

    return {
        "id": str(payload["id"]),
        "status": status,
        "workspace_id": workspace_id,
        "item_id": item_id,
        "job_item_id": job_item_id,
        "root_activity_id": root_activity_id,
        "end_time_utc": end_time_utc,
        "failure_error_code": failure_error_code,
        "spark_application_id": spark_application_id,
    }


def _assert_recovery_request_matches_expected(
    parameters: dict[str, dict], payload: dict, *, expected_release_id: str
) -> None:
    assert parameters["RECOVERY_EXPECTED_RELEASE_ID"]["value"] == expected_release_id
    summary = _canonical_recovery_summary(payload)
    assert summary["workspace_id"] == EXPECTED_WORKSPACE_ID
    assert summary["item_id"] == "e7883ed6-638e-4131-9b8e-b6e86aa278b5"
    assert summary["spark_application_id"] == EXPECTED_RECOVERY_APPLICATION_ID
    assert summary["status"] == "Failed"


def test_v120_job_payload_includes_explicit_default_lakehouse_binding() -> None:
    payload = json.loads(RUN_PAYLOAD_PATH.read_text(encoding="utf-8"))

    execution_data = payload["executionData"]
    assert execution_data["compute"] == "Spark"
    assert execution_data["computeConfiguration"]["defaultLakehouse"] == {
        "referenceType": "ById",
        "itemId": EXPECTED_LAKEHOUSE_ID,
        "workspaceId": EXPECTED_WORKSPACE_ID,
    }

    parameters = payload["parameters"]
    assert parameters == [
        {"name": "RELEASE_VERSION", "type": "Text", "value": "v1.2.0"},
        {"name": "ACTIVATE_RELEASE_POINTER", "type": "Boolean", "value": True},
        {"name": "CONTROL_ONLY_PROMOTION", "type": "Boolean", "value": True},
    ]


def test_v120_recovery_payload_is_explicitly_bounded_to_failed_tuple_and_job_proof() -> None:
    payload = json.loads(RECOVERY_RUN_PAYLOAD_PATH.read_text(encoding="utf-8"))

    execution_data = payload["executionData"]
    assert execution_data["compute"] == "Spark"
    assert execution_data["computeConfiguration"]["defaultLakehouse"] == {
        "referenceType": "ById",
        "itemId": EXPECTED_LAKEHOUSE_ID,
        "workspaceId": EXPECTED_WORKSPACE_ID,
    }

    parameters = {entry["name"]: entry for entry in payload["parameters"]}
    assert parameters["RELEASE_VERSION"]["value"] == "v1.2.0"
    assert parameters["ACTIVATE_RELEASE_POINTER"]["value"] is True
    assert parameters["CONTROL_ONLY_PROMOTION"]["value"] is True
    assert parameters["RECOVERY_MODE"] == {
        "name": "RECOVERY_MODE",
        "type": "Boolean",
        "value": True,
    }
    assert parameters["RECOVERY_EXPECTED_DATASET_NAME"]["value"] == "drill_run_history"
    assert parameters["RECOVERY_EXPECTED_RELEASE_ID"]["value"] == EXPECTED_RELEASE_ID
    assert parameters["RECOVERY_EXPECTED_ATTEMPT_ID"]["value"] == EXPECTED_RECOVERY_ATTEMPT_ID
    assert parameters["RECOVERY_EXPECTED_APPLICATION_ID"]["value"] == EXPECTED_RECOVERY_APPLICATION_ID
    assert parameters["RECOVERY_EXPECTED_JOB_INSTANCE_ID"]["value"] == EXPECTED_RECOVERY_JOB_INSTANCE_ID

    operator_job_payload = json.loads(
        parameters["RECOVERY_EXPECTED_JOB_RESPONSE_JSON"]["value"]
    )
    assert operator_job_payload["id"] == EXPECTED_RECOVERY_JOB_INSTANCE_ID
    assert operator_job_payload["status"] == "Failed"
    assert operator_job_payload["itemId"] == "e7883ed6-638e-4131-9b8e-b6e86aa278b5"
    assert "workspaceId" not in operator_job_payload
    assert operator_job_payload["endTimeUtc"] == EXPECTED_RECOVERY_END_TIME_UTC
    creator_item = (
        operator_job_payload["properties"]["computeDetails"]["monitoringInfo"]["activityDetails"]["creatorItem"]
    )
    assert creator_item["workspaceId"] == EXPECTED_WORKSPACE_ID
    assert creator_item["itemId"] == operator_job_payload["itemId"]
    assert (
        operator_job_payload["properties"]["computeDetails"]["monitoringInfo"]["activityDetails"]["sparkApplicationId"]
        == EXPECTED_RECOVERY_APPLICATION_ID
    )


def test_v120_recovery_payload_operator_artifact_matches_readonly_fixture() -> None:
    payload = json.loads(RECOVERY_RUN_PAYLOAD_PATH.read_text(encoding="utf-8"))
    parameters = {entry["name"]: entry for entry in payload["parameters"]}
    embedded_payload = json.loads(parameters["RECOVERY_EXPECTED_JOB_RESPONSE_JSON"]["value"])
    readonly_fixture = json.loads(RECOVERY_FIXTURE_PATH.read_text(encoding="utf-8"))

    assert embedded_payload == readonly_fixture
    assert _canonical_recovery_summary(embedded_payload) == {
        "id": EXPECTED_RECOVERY_JOB_INSTANCE_ID,
        "status": "Failed",
        "workspace_id": EXPECTED_WORKSPACE_ID,
        "item_id": "e7883ed6-638e-4131-9b8e-b6e86aa278b5",
        "job_item_id": "e7883ed6-638e-4131-9b8e-b6e86aa278b5",
        "root_activity_id": "1e0b154f-3945-431b-a18d-d0f6011f3cc3",
        "end_time_utc": EXPECTED_RECOVERY_END_TIME_UTC,
        "failure_error_code": "System_Cancelled_Session_Statements_Failed",
        "spark_application_id": EXPECTED_RECOVERY_APPLICATION_ID,
    }
    _assert_recovery_request_matches_expected(
        parameters,
        embedded_payload,
        expected_release_id=EXPECTED_RELEASE_ID,
    )


def test_v120_recovery_payload_minimal_core_shape_fails_closed_for_spark_proof() -> None:
    minimal_payload = {
        "id": EXPECTED_RECOVERY_JOB_INSTANCE_ID,
        "itemId": "e7883ed6-638e-4131-9b8e-b6e86aa278b5",
        "status": "Failed",
        "rootActivityId": "1e0b154f-3945-431b-a18d-d0f6011f3cc3",
        "failureReason": {"errorCode": "System_Cancelled_Session_Statements_Failed"},
        "workspaceId": EXPECTED_WORKSPACE_ID,
    }

    try:
        _canonical_recovery_summary(minimal_payload)
    except KeyError as missing_key_error:
        assert str(missing_key_error) in {"'properties'", "'computeDetails'", "'monitoringInfo'", "'activityDetails'", "'creatorItem'", "'sparkApplicationId'"}
    else:
        raise AssertionError("minimal core payload must fail closed without rich Spark proof")


def test_v120_recovery_payload_wrong_owner_or_status_fail_closed() -> None:
    payload = json.loads(RECOVERY_FIXTURE_PATH.read_text(encoding="utf-8"))

    wrong_owner = json.loads(json.dumps(payload))
    wrong_owner["properties"]["computeDetails"]["monitoringInfo"]["activityDetails"]["creatorItem"]["workspaceId"] = "00000000-0000-0000-0000-000000000000"
    wrong_owner_summary = _canonical_recovery_summary(wrong_owner)
    assert wrong_owner_summary["workspace_id"] != EXPECTED_WORKSPACE_ID

    recovery_parameters = {
        "RECOVERY_EXPECTED_RELEASE_ID": {"value": EXPECTED_RELEASE_ID},
    }
    wrong_release_parameters = {
        "RECOVERY_EXPECTED_RELEASE_ID": {"value": "v1.2.0:wrong"},
    }
    _assert_recovery_request_matches_expected(
        recovery_parameters,
        payload,
        expected_release_id=EXPECTED_RELEASE_ID,
    )
    try:
        _assert_recovery_request_matches_expected(
            wrong_release_parameters,
            payload,
            expected_release_id=EXPECTED_RELEASE_ID,
        )
    except AssertionError:
        pass
    else:
        raise AssertionError("wrong release tuple must fail closed")

    wrong_status = json.loads(json.dumps(payload))
    wrong_status["status"] = "Running"
    try:
        _canonical_recovery_summary(wrong_status)
    except AssertionError:
        pass
    else:
        raise AssertionError("non-terminal status must fail closed")


def test_v120_notebook_update_payload_matches_tracked_notebook_definition() -> None:
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    expected_notebook_bytes = NOTEBOOK_IPYNB_PATH.read_bytes()
    expected_platform_bytes = PLATFORM_PATH.read_bytes()

    definition = payload["definition"]
    assert definition["format"] == "ipynb"
    parts = definition["parts"]
    assert [part["path"] for part in parts] == ["notebook-content.ipynb", ".platform"]
    assert all(part["payloadType"] == "InlineBase64" for part in parts)

    assert _decode_notebook_payload_bytes(payload) == expected_notebook_bytes
    assert _decode_platform_payload_bytes(payload) == expected_platform_bytes


def test_v120_notebook_update_payload_preserves_v12_default_parameter_cell() -> None:
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    decoded_notebook_payload = _decode_notebook_payload_json(payload)
    parameter_cells = _parameters_code_cells(decoded_notebook_payload)

    assert len(parameter_cells) == 1

    parameters_cell_source = "".join(parameter_cells[0].get("source", []))
    assert 'RELEASE_VERSION = "v1.2.0"' in parameters_cell_source
    assert "ACTIVATE_RELEASE_POINTER = True" in parameters_cell_source
    assert "CONTROL_ONLY_PROMOTION = True" in parameters_cell_source
    assert "RECOVERY_MODE = False" in parameters_cell_source
    assert 'RECOVERY_EXPECTED_JOB_RESPONSE_JSON = ""' in parameters_cell_source


def test_v120_notebook_update_payload_runtime_recovery_parameters_are_not_reset_after_injection() -> None:
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    decoded_notebook_payload = _decode_notebook_payload_json(payload)
    decoded_notebook_source = _all_code_cell_source(decoded_notebook_payload)

    assert 'raw_recovery_mode = globals().get("RECOVERY_MODE", DEFAULT_RECOVERY_MODE)' in decoded_notebook_source
    assert 'RECOVERY_OPERATOR = optional_recovery_parameter("RECOVERY_OPERATOR")' in decoded_notebook_source
    assert (
        'RECOVERY_EXPECTED_JOB_RESPONSE_JSON = optional_recovery_parameter("RECOVERY_EXPECTED_JOB_RESPONSE_JSON")'
        in decoded_notebook_source
    )
    publication_block_start = decoded_notebook_source.index("ATTEMPT_ID = str(uuid.uuid4())")
    publication_block_end = decoded_notebook_source.index(
        'FABRIC_NOTEBOOK_ITEM_ID = "e7883ed6-638e-4131-9b8e-b6e86aa278b5"',
        publication_block_start,
    )
    publication_block = decoded_notebook_source[
        publication_block_start:publication_block_end
    ]
    assert "\nRECOVERY_MODE = False\n" not in publication_block


def test_v120_notebook_update_payload_parameters_tag_is_structural_and_singular() -> None:
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    decoded_notebook_payload = _decode_notebook_payload_json(payload)

    notebook_level_tags = decoded_notebook_payload.get("metadata", {}).get("tags")
    assert notebook_level_tags in (None, [])

    parameter_cells = _parameters_code_cells(decoded_notebook_payload)
    assert len(parameter_cells) == 1
    assert parameter_cells[0]["cell_type"] == "code"


def test_v120_fabric_source_metadata_preserves_default_lakehouse_dependency_mapping() -> None:
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    notebook = json.loads(NOTEBOOK_IPYNB_PATH.read_text(encoding="utf-8"))
    payload_notebook = _decode_notebook_payload_json(payload)

    fabric_metadata = payload_notebook["metadata"]
    lakehouse_dependency = fabric_metadata["dependencies"]["lakehouse"]
    assert lakehouse_dependency["default_lakehouse"] == EXPECTED_LAKEHOUSE_ID
    assert lakehouse_dependency["default_lakehouse_workspace_id"] == EXPECTED_WORKSPACE_ID
    assert lakehouse_dependency["default_lakehouse_name"] == EXPECTED_LAKEHOUSE_NAME
    assert lakehouse_dependency["known_lakehouses"] == [{"id": EXPECTED_LAKEHOUSE_ID}]

    native_ipynb_lakehouse = notebook["metadata"]["dependencies"]["lakehouse"]
    assert native_ipynb_lakehouse == lakehouse_dependency


def test_all_active_v120_notebook_update_bodies_are_byte_identical() -> None:
    baseline = ACTIVE_V120_UPDATE_BODIES[0].read_bytes()

    for payload_path in ACTIVE_V120_UPDATE_BODIES[1:]:
        assert payload_path.read_bytes() == baseline, (
            f"{payload_path} drifted from {ACTIVE_V120_UPDATE_BODIES[0]}; "
            "all active v120 notebook update bodies must remain byte-identical."
        )
