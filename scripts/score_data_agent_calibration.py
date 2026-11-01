#!/usr/bin/env python3
"""CLI entry point for separate offline calibration scoring."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calibration.scoring import main


if __name__ == "__main__":
    main()
