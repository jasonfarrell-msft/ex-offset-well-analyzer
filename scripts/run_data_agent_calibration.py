#!/usr/bin/env python3
"""CLI entry point for approval-bound local Fabric Data Agent calibration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calibration.invocation import main


if __name__ == "__main__":
    main()
