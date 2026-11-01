"""Focused tests for safe regeneration with a staged historical reference."""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path
import sys
import unittest
import uuid
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from drillrun_synth.config import GeneratorConfig
from drillrun_synth.generator import ReleaseResult, generate_release, regenerate_release
from drillrun_synth.validation import sha256, validate_release


class RegenerateReleaseTests(unittest.TestCase):
    def _create_synthetic_regeneration_fixture(self) -> tuple[GeneratorConfig, Path]:
        config = GeneratorConfig.load(
            PROJECT_ROOT / "config" / "generator_config_v1.2.0.json"
        )
        scratch_parent = PROJECT_ROOT / ".test-artifacts"
        scratch_parent.mkdir(exist_ok=True)
        output_root = scratch_parent / f"regenerate-failure-{uuid.uuid4().hex}"
        output_root.mkdir()
        self.addCleanup(shutil.rmtree, output_root)

        reference = output_root / "v1.0.0"
        reference.mkdir()
        (reference / "reference.txt").write_text("preserved reference", encoding="utf-8")
        existing_release = output_root / config.dataset_version
        existing_release.mkdir()
        (existing_release / "existing.txt").write_text("old release", encoding="utf-8")
        return config, output_root

    @staticmethod
    def _fake_generate_release(
        config: GeneratorConfig,
        output_root: Path,
        *,
        source_root: Path | None = None,
    ) -> ReleaseResult:
        release_path = output_root / config.dataset_version
        release_path.mkdir()
        (release_path / "generated.txt").write_text("new release", encoding="utf-8")
        return ReleaseResult(release_path, {}, {}, {})

    def test_explicit_regeneration_stages_reference_release(self) -> None:
        canonical_reference = PROJECT_ROOT / "data" / "releases" / "v1.0.0"
        if not canonical_reference.is_dir():
            self.skipTest(
                "Local v1.0.0 reference archive is required for release generation."
            )

        config = GeneratorConfig.load(
            PROJECT_ROOT / "config" / "generator_config_v1.2.0.json"
        )
        scratch_parent = PROJECT_ROOT / ".test-artifacts"
        scratch_parent.mkdir(exist_ok=True)
        output_root = scratch_parent / f"regenerate-{uuid.uuid4().hex}"
        output_root.mkdir()
        self.addCleanup(shutil.rmtree, output_root)

        canonical_hashes = {
            path.name: sha256(path)
            for path in canonical_reference.iterdir()
            if path.is_file()
        }
        shutil.copytree(canonical_reference, output_root / "v1.0.0")
        first = generate_release(config, output_root, source_root=PROJECT_ROOT)
        first_hashes = {
            path.name: sha256(path)
            for path in first.release_path.iterdir()
            if path.is_file()
        }

        regenerated = regenerate_release(config, output_root, source_root=PROJECT_ROOT)

        self.assertEqual(
            [],
            validate_release(regenerated.release_path, source_root=PROJECT_ROOT),
        )
        self.assertEqual(
            first_hashes,
            {
                path.name: sha256(path)
                for path in regenerated.release_path.iterdir()
                if path.is_file()
            },
        )
        regenerated_hashes = {
            path.name: sha256(path)
            for path in regenerated.release_path.iterdir()
            if path.is_file()
        }
        with self.assertRaisesRegex(ValueError, "must reference the preserved v1.0.0"):
            regenerate_release(
                replace(config, reference_dataset_version="invalid-reference"),
                output_root,
                source_root=PROJECT_ROOT,
            )
        self.assertEqual(
            regenerated_hashes,
            {
                path.name: sha256(path)
                for path in regenerated.release_path.iterdir()
                if path.is_file()
            },
        )
        self.assertEqual(
            canonical_hashes,
            {
                path.name: sha256(path)
                for path in canonical_reference.iterdir()
                if path.is_file()
            },
        )
        self.assertTrue((output_root / "v1.0.0").is_dir())
        self.assertFalse((output_root / ".v1.2.0.regeneration").exists())
        self.assertFalse((output_root / ".v1.2.0.backup").exists())

    def test_backup_cleanup_failure_reports_committed_release_and_retains_backup(self) -> None:
        config, output_root = self._create_synthetic_regeneration_fixture()
        release_path = output_root / config.dataset_version
        backup_path = output_root / f".{config.dataset_version}.backup"
        staging_root = output_root / f".{config.dataset_version}.regeneration"
        original_rmtree = shutil.rmtree

        def fail_backup_cleanup(path: str | Path, *args, **kwargs) -> None:
            if Path(path) == backup_path:
                raise RuntimeError("injected backup cleanup failure")
            original_rmtree(path, *args, **kwargs)

        with (
            patch(
                "drillrun_synth.generator.generate_release",
                side_effect=self._fake_generate_release,
            ),
            patch("drillrun_synth.validation.validate_release", return_value=[]),
            patch("drillrun_synth.generator.shutil.rmtree", side_effect=fail_backup_cleanup),
            self.assertLogs("drillrun_synth.generator", level="WARNING") as captured,
        ):
            result = regenerate_release(config, output_root, source_root=PROJECT_ROOT)

        self.assertEqual(release_path, result.release_path)
        self.assertEqual("new release", (release_path / "generated.txt").read_text())
        self.assertFalse((release_path / "existing.txt").exists())
        self.assertEqual(
            "old release", (backup_path / "existing.txt").read_text(encoding="utf-8")
        )
        self.assertFalse(staging_root.exists())
        self.assertTrue(any("promotion committed" in message for message in captured.output))
        self.assertTrue(any("no rollback was attempted" in message for message in captured.output))

    def test_staging_root_cleanup_failure_reports_committed_release(self) -> None:
        config, output_root = self._create_synthetic_regeneration_fixture()
        release_path = output_root / config.dataset_version
        backup_path = output_root / f".{config.dataset_version}.backup"
        staging_root = output_root / f".{config.dataset_version}.regeneration"
        original_rmdir = Path.rmdir

        def fail_staging_root_cleanup(path: Path) -> None:
            if path == staging_root:
                raise RuntimeError("injected staging cleanup failure")
            original_rmdir(path)

        with (
            patch(
                "drillrun_synth.generator.generate_release",
                side_effect=self._fake_generate_release,
            ),
            patch("drillrun_synth.validation.validate_release", return_value=[]),
            patch.object(Path, "rmdir", fail_staging_root_cleanup),
            self.assertLogs("drillrun_synth.generator", level="WARNING") as captured,
        ):
            result = regenerate_release(config, output_root, source_root=PROJECT_ROOT)

        self.assertEqual(release_path, result.release_path)
        self.assertEqual("new release", (release_path / "generated.txt").read_text())
        self.assertFalse((release_path / "existing.txt").exists())
        self.assertFalse(backup_path.exists())
        self.assertTrue(staging_root.is_dir())
        self.assertEqual([], list(staging_root.iterdir()))
        self.assertTrue(any("promotion committed" in message for message in captured.output))
        self.assertTrue(any("staging cleanup failed" in message for message in captured.output))

    def test_pre_promotion_failure_preserves_release_and_surfaces_cleanup_error(
        self,
    ) -> None:
        config, output_root = self._create_synthetic_regeneration_fixture()
        release_path = output_root / config.dataset_version
        reference_path = output_root / "v1.0.0" / "reference.txt"
        staging_root = output_root / f".{config.dataset_version}.regeneration"
        backup_path = output_root / f".{config.dataset_version}.backup"
        original_rmtree = shutil.rmtree

        def fail_staging_cleanup(path: str | Path, *args, **kwargs) -> None:
            if Path(path) == staging_root:
                raise OSError("injected staging cleanup failure")
            original_rmtree(path, *args, **kwargs)

        with (
            patch(
                "drillrun_synth.generator.generate_release",
                side_effect=ValueError("injected generation failure"),
            ),
            patch("drillrun_synth.generator.shutil.rmtree", side_effect=fail_staging_cleanup),
        ):
            with self.assertRaisesRegex(ValueError, "injected generation failure") as raised:
                regenerate_release(config, output_root, source_root=PROJECT_ROOT)

        self.assertEqual("old release", (release_path / "existing.txt").read_text())
        self.assertEqual("preserved reference", reference_path.read_text(encoding="utf-8"))
        self.assertTrue(staging_root.is_dir())
        self.assertFalse(backup_path.exists())
        self.assertTrue(
            any(
                "generated staging could not be removed" in note
                for note in raised.exception.__notes__
            )
        )


if __name__ == "__main__":
    unittest.main()
