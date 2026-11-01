"""Grader-only bridge to the existing independent Decimal oracle (not runtime).

Emits expected summaries for frontend tests; never writes/loads runtime fixtures.
"""

import importlib.util
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location("offset_oracle", ROOT / "tests/test_offset_analysis.py")
oracle_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle_module)
oracle = oracle_module.OffsetOracle(oracle_module.load_archive("v1.1.0"))
cases = []
for target in oracle.tables["planned_targets"]:
    profiles = [
        {"radiusFt": "10000", "formationMatch": formation, "holeSizeMatch": hole, "mdOverlap": md}
        for formation, hole, md in itertools.product((False, True), repeat=3)
    ] + [
        {"radiusFt": "0", "formationMatch": False, "holeSizeMatch": False, "mdOverlap": False},
        {"radiusFt": "3000000", "formationMatch": False, "holeSizeMatch": False, "mdOverlap": False},
    ]
    for criteria in profiles:
        rows, exclusions = oracle.candidates(target["target_id"], criteria)
        cases.append({"targetId": target["target_id"], "criteria": criteria, "rows": rows,
                      "excludedCount": len(exclusions)})
print(json.dumps(cases, separators=(",", ":")))
