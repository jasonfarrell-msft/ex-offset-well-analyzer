"""Command-line interface."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import GeneratorConfig
from .generator import generate_release, regenerate_release


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the deterministic fictional drill-run history release."
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to generator JSON configuration.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/releases"),
        help="Parent folder for the immutable dataset-version release.",
    )
    parser.add_argument(
        "--regenerate-existing",
        action="store_true",
        help=(
            "Explicitly replace an existing release through staged generation, "
            "validation, backup, and atomic directory renames."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = GeneratorConfig.load(args.config)
        if args.regenerate_existing:
            result = regenerate_release(config, args.output_root)
        else:
            result = generate_release(config, args.output_root)
    except (OSError, ValueError) as exc:
        print(f"Generation failed: {exc}", file=sys.stderr)
        return 2

    action = "Regenerated" if args.regenerate_existing else "Created"
    print(f"{action} release: {result.release_path}")
    for name, count in sorted(result.row_counts.items()):
        print(f"  {name}: {count} rows")
    print("Intentional issues:")
    for code, count in sorted(result.issue_counts.items()):
        print(f"  {code}: {count}")
    return 0
