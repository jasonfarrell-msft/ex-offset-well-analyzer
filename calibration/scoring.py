"""Offline scoring for captured calibration evidence."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from pathlib import Path
from typing import Any

from calibration.config import (
    EVALUATION_PATH,
    EXPECTED_ATTEMPTS_PER_CASE,
    EXPECTED_CASE_COUNT,
    RUNS_ROOT,
    SCORING_PATH,
    SYNTHETIC_LABEL,
)
from calibration.evidence import iso_utc, utc_now, validate_schema, write_json


RUN_ID_PATTERN = re.compile(r"\A\d{8}T\d{6}Z-[0-9a-f]{8}\Z")
EXACT_SYNTHETIC_LABEL_CONTRACT = {
    "required_text": SYNTHETIC_LABEL,
    "required_position": "first_line",
    "match": "exact",
    "normalization": "none",
    "applies_to": [
        "answer",
        "clarification",
        "refusal",
        "error",
        "partial_answer",
    ],
}


def _run_dir(run_id: str) -> Path:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("Run ID has an invalid format")
    path = (RUNS_ROOT / run_id).resolve()
    if path.parent != RUNS_ROOT.resolve():
        raise ValueError("Run directory must be inside calibration/runs")
    if not path.is_dir():
        raise FileNotFoundError(f"Run not found: {run_id}")
    manifest = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
    validate_schema(manifest, "run-manifest.schema.json")
    return path


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _evaluation() -> dict[str, dict[str, Any]]:
    cases = _jsonl(EVALUATION_PATH)
    if len(cases) != EXPECTED_CASE_COUNT:
        raise ValueError("Evaluation case count changed")
    return {case["id"]: case for case in cases}


def prepare_grading_template(run_id: str) -> Path:
    run_dir = _run_dir(run_id)
    attempts = _jsonl(run_dir / "attempts.jsonl")
    evaluation = _evaluation()
    records = []
    for attempt in attempts:
        if attempt.get("status") != "SUCCESS":
            continue
        case = evaluation[attempt["case_id"]]
        records.append(
            {
                "schema_version": "1.0.0",
                "case_id": attempt["case_id"],
                "attempt": attempt["attempt"],
                "grader_context": {
                    "category": case["category"],
                    "expected_behavior": case["expected_behavior"],
                    "expected_facts": case["expected_facts"],
                    "source_references": case["source_references"],
                    "required_citations": case["required_citations"],
                    "required_disclosures": case["required_disclosures"],
                    "forbidden_claims": case["forbidden_claims"],
                    "severity_if_failed": case["severity_if_failed"],
                },
                "judgment": {
                    "expected_behavior_correct": None,
                    "critical_factual_failure": None,
                    "scope_boundary_violation": None,
                    "unauthorized_disclosure_or_security_failure": None,
                    "normalized_semantics": None,
                    "citation_claims": [],
                },
                "review": {
                    "reviewer_type": None,
                    "reviewer_id_or_model": None,
                    "reviewed_at_utc": None,
                    "notes": None,
                },
            }
        )
    path = run_dir / "grading-template.json"
    validate_schema(
        {"schema_version": "1.0.0", "grades": records},
        "grading.schema.json",
    )
    write_json(path, {"schema_version": "1.0.0", "grades": records})
    return path


def _nearest_rank_p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def _threshold_pass(value: float | int | None, operator: str, threshold: Any) -> bool | None:
    if value is None:
        return None
    if operator == "equals":
        return value == threshold
    if operator == "greater_than_or_equal":
        return value >= threshold
    if operator == "less_than_or_equal":
        return value <= threshold
    if operator == "diagnostic_only":
        return None
    raise ValueError(f"Unsupported scoring operator: {operator}")


def _has_exact_synthetic_label_first_line(response: str) -> bool:
    return response == SYNTHETIC_LABEL or response.startswith(f"{SYNTHETIC_LABEL}\n")


def score_run(run_id: str, grades_path: Path) -> Path:
    run_dir = _run_dir(run_id)
    if grades_path.resolve().parent != run_dir:
        raise ValueError("Grades must be stored in the selected ignored run directory")
    attempts = _jsonl(run_dir / "attempts.jsonl")
    evaluation = _evaluation()
    contract = json.loads(SCORING_PATH.read_text(encoding="utf-8"))
    if contract.get("synthetic_label") != EXACT_SYNTHETIC_LABEL_CONTRACT:
        raise ValueError(
            "Scoring contract must require the exact synthetic label first"
        )
    os.chmod(grades_path, 0o600)
    grade_document = json.loads(grades_path.read_text(encoding="utf-8"))
    validate_schema(grade_document, "grading.schema.json")
    grades = grade_document.get("grades")
    if not isinstance(grades, list):
        raise ValueError("Grades document must contain a grades list")

    successful = [item for item in attempts if item.get("status") == "SUCCESS"]
    expected_attempt_count = EXPECTED_CASE_COUNT * EXPECTED_ATTEMPTS_PER_CASE
    grade_index: dict[tuple[str, int], dict[str, Any]] = {}
    duplicate_grades = False
    for grade in grades:
        key = (grade.get("case_id"), grade.get("attempt"))
        if key[0] not in evaluation or key[1] not in {
            1,
            2,
            EXPECTED_ATTEMPTS_PER_CASE,
        }:
            raise ValueError("Grades contain an unknown case or attempt")
        if key in grade_index:
            duplicate_grades = True
        grade_index[key] = grade

    missing_judgments: list[dict[str, Any]] = []
    hard_counts = {
        "critical_factual_failures": 0,
        "scope_boundary_violations": 0,
        "unauthorized_disclosure_or_security_failures": 0,
    }
    synthetic_count = 0
    clarify_refuse_values: list[bool] = []
    citation_valid: list[bool] = []
    citation_present: list[bool] = []
    semantics_by_case: dict[str, list[str]] = {}

    judgment_fields = (
        "expected_behavior_correct",
        "critical_factual_failure",
        "scope_boundary_violation",
        "unauthorized_disclosure_or_security_failure",
        "normalized_semantics",
    )
    for attempt in successful:
        case_id = attempt["case_id"]
        attempt_number = attempt["attempt"]
        response = attempt.get("response_text") or ""
        synthetic_count += int(_has_exact_synthetic_label_first_line(response))
        grade = grade_index.get((case_id, attempt_number))
        judgment = grade.get("judgment") if isinstance(grade, dict) else None
        review = grade.get("review") if isinstance(grade, dict) else None
        missing = []
        if not isinstance(judgment, dict):
            missing.extend(judgment_fields)
        else:
            for field in judgment_fields:
                value = judgment.get(field)
                if field == "normalized_semantics":
                    if not isinstance(value, str) or not value.strip():
                        missing.append(field)
                elif not isinstance(value, bool):
                    missing.append(field)
            claims = judgment.get("citation_claims")
            if not isinstance(claims, list) or not claims:
                missing.append("citation_claims")
            else:
                for index, claim in enumerate(claims):
                    if (
                        not isinstance(claim, dict)
                        or not isinstance(claim.get("claim"), str)
                        or not isinstance(claim.get("citation_present"), bool)
                        or not isinstance(claim.get("citation_valid"), bool)
                    ):
                        missing.append(f"citation_claims[{index}]")
        if (
            not isinstance(review, dict)
            or review.get("reviewer_type") not in {"human", "llm"}
            or not isinstance(review.get("reviewer_id_or_model"), str)
            or not review.get("reviewer_id_or_model")
            or not isinstance(review.get("reviewed_at_utc"), str)
        ):
            missing.append("review")
        if missing:
            missing_judgments.append(
                {
                    "case_id": case_id,
                    "attempt": attempt_number,
                    "fields": sorted(set(missing)),
                }
            )
            continue

        hard_counts["critical_factual_failures"] += int(
            judgment["critical_factual_failure"]
        )
        hard_counts["scope_boundary_violations"] += int(
            judgment["scope_boundary_violation"]
        )
        hard_counts["unauthorized_disclosure_or_security_failures"] += int(
            judgment["unauthorized_disclosure_or_security_failure"]
        )
        if evaluation[case_id]["category"] in {"clarify", "refuse_security"}:
            clarify_refuse_values.append(judgment["expected_behavior_correct"])
        semantics_by_case.setdefault(case_id, []).append(
            judgment["normalized_semantics"].strip()
        )
        for claim in judgment["citation_claims"]:
            citation_present.append(claim["citation_present"])
            citation_valid.append(claim["citation_valid"])

    complete = (
        len(successful) == expected_attempt_count
        and len(attempts) == expected_attempt_count
        and not missing_judgments
        and not duplicate_grades
        and not (run_dir / "STOP_REQUIRED.json").exists()
    )
    synthetic_rate = (
        synthetic_count / len(successful) if successful else None
    )
    citation_validity = (
        sum(citation_valid) / len(citation_valid) if citation_valid else None
    )
    citation_presence = (
        sum(citation_present) / len(citation_present) if citation_present else None
    )
    behavior_rate = (
        sum(clarify_refuse_values) / len(clarify_refuse_values)
        if clarify_refuse_values
        else None
    )
    repeat_consistency = None
    if complete:
        repeat_consistency = sum(
            len(values) == EXPECTED_ATTEMPTS_PER_CASE
            and len(set(values)) == 1
            for values in semantics_by_case.values()
        ) / EXPECTED_CASE_COUNT
    latencies = [
        float(attempt["latency_seconds"])
        for attempt in successful
        if isinstance(attempt.get("latency_seconds"), (int, float))
    ]
    p95 = _nearest_rank_p95(latencies)
    costs = [attempt.get("cost_usd") for attempt in successful]
    cost_known = (
        len(costs) == expected_attempt_count
        and all(isinstance(cost, (int, float)) for cost in costs)
    )

    metrics = {
        "critical_factual_failures": hard_counts["critical_factual_failures"]
        if complete
        else None,
        "scope_boundary_violations": hard_counts["scope_boundary_violations"]
        if complete
        else None,
        "unauthorized_disclosure_or_security_failures": hard_counts[
            "unauthorized_disclosure_or_security_failures"
        ]
        if complete
        else None,
        "synthetic_label_rate": synthetic_rate,
        "citation_validity": citation_validity if complete else None,
        "citation_presence": citation_presence if complete else None,
        "correct_clarify_or_refuse_behavior": behavior_rate if complete else None,
        "deterministic_repeat_consistency": repeat_consistency,
        "p95_response_time_seconds": p95,
    }
    gates: dict[str, bool | None] = {}
    for name, rule in contract["hard_gates"].items():
        gates[name] = _threshold_pass(
            metrics[name] if complete else None,
            rule["operator"],
            rule["threshold"],
        )
    for name, rule in contract["quality_thresholds"].items():
        gates[name] = _threshold_pass(
            metrics[name] if complete else None,
            rule["operator"],
            rule["threshold"],
        )
    decisive_gates = [
        value
        for name, value in gates.items()
        if contract["quality_thresholds"].get(name, {}).get("operator")
        != "diagnostic_only"
    ]
    overall = (
        "INCOMPLETE"
        if not complete or any(value is None for value in decisive_gates)
        else "PASS"
        if all(decisive_gates)
        else "FAIL_ROLLBACK_REQUIRED"
    )
    report = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "scored_at_utc": iso_utc(utc_now()),
        "status": overall,
        "complete": complete,
        "attempt_counts": {
            "expected": expected_attempt_count,
            "captured": len(attempts),
            "successful": len(successful),
        },
        "metrics": metrics,
        "gates": gates,
        "cost": {
            "status": "KNOWN" if cost_known else "UNKNOWN",
            "total_usd": sum(costs) if cost_known else None,
            "missing_cost_is_not_zero": True,
        },
        "judgment_provenance": {
            "source": grades_path.name,
            "human_or_llm_fields_are_separate": True,
            "missing_judgments": missing_judgments,
            "duplicate_grades": duplicate_grades,
        },
        "rollback_required": overall == "FAIL_ROLLBACK_REQUIRED",
    }
    validate_schema(report, "score-report.schema.json")
    output = run_dir / "score-report.json"
    write_json(output, report, replace=output.exists())
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare or score offline calibration evidence.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", help="Create a grader-only template.")
    prepare.add_argument("--run-id", required=True)
    score = subparsers.add_parser("score", help="Score completed grader judgments.")
    score.add_argument("--run-id", required=True)
    score.add_argument(
        "--grades-file",
        default="grading-template.json",
        help="File name inside calibration/runs/<run-id>/.",
    )
    args = parser.parse_args()
    if args.command == "prepare":
        output = prepare_grading_template(args.run_id)
    else:
        if Path(args.grades_file).name != args.grades_file:
            parser.error("--grades-file must be a file name, not a path")
        output = score_run(
            args.run_id,
            _run_dir(args.run_id) / args.grades_file,
        )
    print(output)


if __name__ == "__main__":
    main()
