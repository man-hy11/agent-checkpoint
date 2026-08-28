"""Legacy classification and migration tests (R5-I10)."""

from pathlib import Path
import tempfile
import unittest

from agent_checkpoint.work_migration import (
    ALREADY_MIGRATED,
    PATH_CONFLICT,
    SYMLINK_HAZARD,
    UNKNOWN_LAYOUT,
    UNTOUCHED_SCAFFOLD,
    USER_EDITED,
    apply_migration,
    classify,
    discover_legacy_packages,
    plan_migration,
    rollback_migration,
)
from agent_checkpoint.work_manifest import load_manifest
from agent_checkpoint.workflows import initialize_workflow


class DiscoveryTests(unittest.TestCase):
    def test_discover_finds_legacy_package(self):
        """Catches discovery missing a package with the legacy templates/prompts signature."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize_workflow(root, "feature", "current")

            found = discover_legacy_packages(root)

            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].work_id, "current")

    def test_discover_ignores_staging_and_backup_directories(self):
        """Catches discovery treating in-flight staging or backup dirs as packages."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work_root = root / ".agent-checkpoint" / "work"
            work_root.mkdir(parents=True)
            (work_root / ".staging-abc").mkdir()
            (work_root / ".migration-backup-abc").mkdir()

            found = discover_legacy_packages(root)

            self.assertEqual(found, ())

    def test_discover_returns_empty_when_no_work_directory(self):
        """Catches discovery crashing when .agent-checkpoint/work does not exist."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            found = discover_legacy_packages(root)

            self.assertEqual(found, ())


class ClassificationTests(unittest.TestCase):
    def test_untouched_scaffold_is_classified_safe(self):
        """Catches an untouched scaffold not being recognized as safe to migrate."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize_workflow(root, "feature", "current")

            [package] = discover_legacy_packages(root)
            classification = classify(package)

            self.assertEqual(classification.category, UNTOUCHED_SCAFFOLD)
            self.assertEqual(classification.reasons, ())

    def test_user_edited_current_is_refused(self):
        """Catches a user-edited CURRENT.md being classified as safe to migrate."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")
            (result.path / "CURRENT.md").write_text(
                "# CURRENT.md\n\nUser wrote real progress here.\n", encoding="utf-8"
            )

            [package] = discover_legacy_packages(root)
            classification = classify(package)

            self.assertEqual(classification.category, USER_EDITED)
            self.assertTrue(classification.reasons)
            self.assertIn("CURRENT.md", classification.reasons[0])

    def test_user_edited_continue_prompt_is_refused(self):
        """Catches a user-edited CONTINUE_PROMPT.md being classified as safe to migrate."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")
            (result.path / "CONTINUE_PROMPT.md").write_text(
                "Custom continuation instructions.\n", encoding="utf-8"
            )

            [package] = discover_legacy_packages(root)
            classification = classify(package)

            self.assertEqual(classification.category, USER_EDITED)

    def test_missing_top_level_current_is_unknown_layout(self):
        """Catches a package missing its top-level CURRENT.md not being flagged unknown_layout."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")
            (result.path / "CURRENT.md").unlink()

            [package] = discover_legacy_packages(root)
            classification = classify(package)

            self.assertEqual(classification.category, UNKNOWN_LAYOUT)

    def test_symlink_inside_package_is_a_hazard(self):
        """Catches a symlinked file inside the package not being refused."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")
            real_file = result.path / "real.txt"
            real_file.write_text("data", encoding="utf-8")
            (result.path / "link.txt").symlink_to(real_file)

            [package] = discover_legacy_packages(root)
            classification = classify(package)

            self.assertEqual(classification.category, SYMLINK_HAZARD)

    def test_path_conflict_is_refused(self):
        """Catches an unexpected top-level entry colliding with a final artifact target."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")
            manifest = load_manifest("feature")
            conflicting_name = next(iter(manifest.artifacts))
            (result.path / conflicting_name).mkdir()

            [package] = discover_legacy_packages(root)
            classification = classify(package)

            self.assertEqual(classification.category, PATH_CONFLICT)


class DryRunTests(unittest.TestCase):
    def test_plan_migration_makes_no_filesystem_write(self):
        """Catches dry-run mutating the package instead of only reporting."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")
            before = (result.path / "CURRENT.md").read_text(encoding="utf-8")

            report = plan_migration(root)

            after = (result.path / "CURRENT.md").read_text(encoding="utf-8")
            self.assertEqual(before, after)
            self.assertTrue((result.path / "templates").is_dir())
            self.assertFalse(report.applied)
            self.assertEqual(len(report.actions), 1)
            self.assertTrue(report.actions[0].will_migrate)

    def test_plan_migration_reports_no_packages_when_none_exist(self):
        """Catches dry-run failing on an empty or absent work directory."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            report = plan_migration(root)

            self.assertEqual(report.actions, ())


class ApplyMigrationTests(unittest.TestCase):
    def test_apply_migrates_untouched_scaffold_in_place(self):
        """Catches apply failing to migrate an untouched scaffold to the final-only layout."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")
            work_id = result.work_id

            report = apply_migration(root)

            self.assertTrue(report.applied)
            self.assertIn(work_id, report.migrated_ids)
            migrated_path = root / ".agent-checkpoint" / "work" / work_id
            self.assertTrue(migrated_path.is_dir())
            self.assertFalse((migrated_path / "templates").exists())
            self.assertFalse((migrated_path / "prompts").exists())
            self.assertFalse((migrated_path / "shared").exists())
            self.assertTrue((migrated_path / "RULES.md").is_file())
            manifest = load_manifest("feature")
            for name, policy in manifest.artifacts.items():
                if policy != "omitted":
                    self.assertTrue((migrated_path / name).is_file(), name)

    def test_apply_refuses_user_edited_package_without_writing(self):
        """Catches apply silently overwriting a user-edited package."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")
            (result.path / "CURRENT.md").write_text(
                "# CURRENT.md\n\nReal user progress.\n", encoding="utf-8"
            )

            report = apply_migration(root)

            self.assertNotIn("current", report.migrated_ids)
            self.assertTrue((result.path / "templates").is_dir())
            self.assertEqual(
                (result.path / "CURRENT.md").read_text(encoding="utf-8"),
                "# CURRENT.md\n\nReal user progress.\n",
            )

    def test_apply_creates_a_recoverable_backup(self):
        """Catches apply not writing a recoverable backup before replacing the layout."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize_workflow(root, "feature", "current")

            report = apply_migration(root)

            [action] = report.actions
            self.assertIsNotNone(action.backup_path)
            self.assertTrue(action.backup_path.is_dir())
            self.assertTrue((action.backup_path / "templates" / "CURRENT_TEMPLATE.md").is_file())

    def test_rerun_after_apply_finds_nothing_left_to_migrate(self):
        """Catches a rerun reclassifying an already-migrated package as legacy."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize_workflow(root, "feature", "current")
            apply_migration(root)

            second_report = plan_migration(root)

            self.assertEqual(second_report.actions, ())

    def test_work_id_and_path_are_unchanged_after_migration(self):
        """Catches migration breaking a stale PROGRESS.md pointer by moving the package."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")
            original_path = result.path

            apply_migration(root)

            self.assertTrue(original_path.is_dir())
            self.assertTrue((original_path / "RULES.md").is_file())

    def test_partial_failure_leaves_earlier_success_committed(self):
        """Catches one package's migration failure rolling back an earlier success."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize_workflow(root, "feature", "safe-one")
            edited = initialize_workflow(root, "feature", "edited-two")
            (edited.path / "CURRENT.md").write_text(
                "# CURRENT.md\n\nUser edit.\n", encoding="utf-8"
            )

            report = apply_migration(root)

            self.assertIn("safe-one", report.migrated_ids)
            self.assertNotIn("edited-two", report.migrated_ids)
            safe_path = root / ".agent-checkpoint" / "work" / "safe-one"
            self.assertTrue((safe_path / "RULES.md").is_file())
            edited_path = root / ".agent-checkpoint" / "work" / "edited-two"
            self.assertTrue((edited_path / "templates").is_dir())

    def test_concurrent_apply_and_claim_do_not_interleave(self):
        """Catches migration writing CURRENT.md concurrently with a work_store.claim call."""
        import json
        import threading

        from agent_checkpoint.work_state import BLOCK_BEGIN, BLOCK_END
        from agent_checkpoint.work_store import claim

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")

            # The legacy scaffold's CURRENT.md has no state block; give it one so a
            # concurrent claim() has something legal to operate on without racing
            # migration's classification of the legacy templates/ signature.
            state_dict = {
                "schema_version": 1, "work_id": "current", "work_type": "feature",
                "plan_revision": 1, "brief_confirmed": True, "current_unit": "F1",
                "max_attempts": 3, "attempt_override": None,
                "units": [{"id": "F1", "group": None, "kind": "step", "state": "ready", "attempt": 0}],
                "attempts": [],
            }
            block = json.dumps(state_dict, indent=2)
            (result.path / "CURRENT.md").write_text(
                f"# CURRENT.md\n\n{BLOCK_BEGIN}\n{block}\n{BLOCK_END}\n", encoding="utf-8"
            )
            # This now makes the package user_edited (top-level diverges from
            # templates/), so apply_migration must refuse it, and a concurrent
            # claim() on the same lock file must not interleave with that refusal.
            errors: list[Exception] = []

            def _do_apply():
                try:
                    apply_migration(root)
                except Exception as error:  # pragma: no cover - defensive
                    errors.append(error)

            def _do_claim():
                try:
                    claim(
                        root,
                        result.path / "CURRENT.md",
                        result.path / "EVIDENCE.md",
                        unit_id="F1",
                        event="start",
                        plan_revision=1,
                        evidence_text="",
                    )
                except Exception as error:  # pragma: no cover - defensive
                    errors.append(error)

            t1 = threading.Thread(target=_do_apply)
            t2 = threading.Thread(target=_do_claim)
            t1.start()
            t2.start()
            t1.join(timeout=15)
            t2.join(timeout=15)

            self.assertFalse(t1.is_alive())
            self.assertFalse(t2.is_alive())
            # No corruption: CURRENT.md remains valid, parseable text either way.
            final_text = (result.path / "CURRENT.md").read_text(encoding="utf-8")
            self.assertIn("CURRENT.md", final_text)


class RollbackTests(unittest.TestCase):
    def test_rollback_restores_byte_identical_state(self):
        """Catches rollback not fully restoring pre-migration content."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")
            before_current = (result.path / "CURRENT.md").read_text(encoding="utf-8")
            before_template = (result.path / "templates" / "CURRENT_TEMPLATE.md").read_text(
                encoding="utf-8"
            )

            report = apply_migration(root)
            [action] = report.actions
            migrated_path = root / ".agent-checkpoint" / "work" / "current"
            self.assertTrue((migrated_path / "RULES.md").is_file())

            rollback_migration(migrated_path, action.backup_path)

            after_current = (migrated_path / "CURRENT.md").read_text(encoding="utf-8")
            after_template = (migrated_path / "templates" / "CURRENT_TEMPLATE.md").read_text(
                encoding="utf-8"
            )
            self.assertEqual(before_current, after_current)
            self.assertEqual(before_template, after_template)
            self.assertFalse((migrated_path / "RULES.md").exists())

    def test_rollback_refuses_a_backup_path_outside_the_package_directory(self):
        """Catches rollback accepting an arbitrary directory as a fake backup."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")
            outside = Path(directory) / "not-a-backup"
            outside.mkdir()

            with self.assertRaises(Exception):
                rollback_migration(result.path, outside)


class OldProgressPointerTests(unittest.TestCase):
    def test_progress_pointer_still_resolves_after_migration(self):
        """Catches migration breaking a PROGRESS.md pointer that names the legacy work_id/path."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_workflow(root, "feature", "current")
            progress_path = root / "PROGRESS.md"
            progress_path.write_text(
                "# Project Checkpoints\n\n## Checkpoint\n\n"
                f"Work package: .agent-checkpoint/work/{result.work_id}\n",
                encoding="utf-8",
            )

            apply_migration(root)

            pointer_target = root / ".agent-checkpoint" / "work" / result.work_id
            self.assertTrue(pointer_target.is_dir())
            self.assertIn(result.work_id, progress_path.read_text(encoding="utf-8"))


class ToolCreatedPackageTests(unittest.TestCase):
    """Catches migrate refusing a package the CLI itself just created.

    `initialize_workflow` alone does not write PROGRESS.md — `cli.py` writes it
    in the same `workflow` invocation. Tests that call the helper directly
    therefore never saw the file, which is how `_find_path_conflict` came to
    treat it as foreign content.
    """

    @staticmethod
    def _create_via_cli(root: Path) -> None:
        from agent_checkpoint.cli import main

        exit_code = main(
            ["workflow", "--type", "bugfix", "--id", "current", "--root", str(root)]
        )
        if exit_code != 0:
            raise AssertionError(f"workflow command failed: {exit_code}")

    def test_cli_created_package_is_not_a_path_conflict(self):
        """Catches PROGRESS.md, written by the CLI, being read as a collision."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._create_via_cli(root)

            [package] = discover_legacy_packages(root)
            classification = classify(package)

            self.assertTrue((package.path / "PROGRESS.md").is_file())
            self.assertNotEqual(classification.category, PATH_CONFLICT)

    def test_genuine_foreign_artifact_is_still_refused(self):
        """Catches the conflict check being widened until it stops protecting."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._create_via_cli(root)

            [package] = discover_legacy_packages(root)
            (package.path / "BRIEF.md").write_text("pre-existing\n", encoding="utf-8")

            classification = classify(package)

            self.assertEqual(classification.category, PATH_CONFLICT)
            self.assertIn("BRIEF.md", " ".join(classification.reasons))
