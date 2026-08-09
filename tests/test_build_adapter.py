import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests.helpers import PROJECT_ROOT
from tools import build_adapter


def run_tool(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run an adapter tool through its public command-line interface."""
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


class BuildAdapterTests(unittest.TestCase):
    def test_build_bundle_contains_adapter_and_canonical_core(self):
        """Catches a bundle that omits its template or portable Python package."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "gemini"

            result = run_tool(
                "tools/build_adapter.py", "gemini-cli", "--output", str(output)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((output / "gemini-extension.json").is_file())
            self.assertTrue((output / "lib" / "agent_checkpoint" / "cli.py").is_file())
            self.assertTrue((output / "bin" / "agent-checkpoint").is_file())
            self.assertFalse(any(output.rglob("__pycache__")))
            launcher_environment = {
                key: value for key, value in os.environ.items() if key != "PYTHONPATH"
            }
            launcher = subprocess.run(
                [output / "bin" / "agent-checkpoint", "--help"],
                cwd=output,
                text=True,
                capture_output=True,
                check=False,
                env=launcher_environment,
            )
            self.assertEqual(launcher.returncode, 0, launcher.stderr)

    def test_build_refuses_nonempty_output_without_force(self):
        """Catches a build silently mixing generated files with prior contents."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            output.mkdir()
            (output / "prior-file").write_text("preserve me", encoding="utf-8")

            result = run_tool(
                "tools/build_adapter.py", "codex", "--output", str(output)
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("nonempty", result.stderr.lower())
            self.assertEqual((output / "prior-file").read_text(encoding="utf-8"), "preserve me")

    def test_force_replaces_nonempty_output_with_deterministic_bundle(self):
        """Catches --force retaining stale output that changes a bundle's contents."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            output.mkdir()
            (output / "stale").write_text("old", encoding="utf-8")

            result = run_tool(
                "tools/build_adapter.py",
                "opencode",
                "--output",
                str(output),
                "--force",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((output / "stale").exists())
            self.assertFalse((output / ".keep").exists())
            self.assertTrue((output / "commands" / "checkpoint.md").is_file())

    def test_build_rejects_output_equal_to_or_ancestor_of_sources(self):
        """Catches --force removing the canonical source tree itself."""
        for output_kind in ("template", "ancestor"):
            with self.subTest(output=output_kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "source-root"
                template = root / "adapters" / "codex"
                package = root / "core" / "agent_checkpoint"
                template.mkdir(parents=True)
                package.mkdir(parents=True)
                sentinel = template / "keep.md"
                sentinel.write_text("source", encoding="utf-8")
                (package / "__init__.py").write_text("", encoding="utf-8")
                output = template if output_kind == "template" else root

                caught = None
                with mock.patch.object(build_adapter, "_ADAPTERS_ROOT", root / "adapters"), \
                    mock.patch.object(build_adapter, "_SOURCE_PACKAGE", package):
                    try:
                        build_adapter._build_bundle("codex", output, force=True)
                    except Exception as error:  # behavior under test
                        caught = error

                self.assertIsInstance(caught, build_adapter.BuildError)
                self.assertIn("overlap", str(caught))
                self.assertTrue(sentinel.is_file())
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "source")

    def test_build_rejects_output_nested_inside_adapter_template(self):
        """Catches recursive self-copy when output is below the selected template."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "adapters" / "codex"
            package = root / "core" / "agent_checkpoint"
            template.mkdir(parents=True)
            package.mkdir(parents=True)
            (template / "skill.md").write_text("source", encoding="utf-8")
            (package / "__init__.py").write_text("", encoding="utf-8")
            output = template / "generated"

            caught = None
            with mock.patch.object(build_adapter, "_ADAPTERS_ROOT", root / "adapters"), \
                mock.patch.object(build_adapter, "_SOURCE_PACKAGE", package), \
                mock.patch.object(
                    build_adapter.shutil,
                    "copytree",
                    side_effect=AssertionError("copy must not start"),
                ):
                try:
                    build_adapter._build_bundle("codex", output, force=False)
                except Exception as error:  # behavior under test
                    caught = error

            self.assertIsInstance(caught, build_adapter.BuildError)
            self.assertIn("overlap", str(caught))
            self.assertFalse(output.exists())

    def test_build_rejects_output_overlapping_a_different_adapter_template(self):
        """Catches one adapter build replacing a sibling adapter's source tree."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "adapters" / "codex"
            sibling_template = root / "adapters" / "opencode"
            package = root / "core" / "agent_checkpoint"
            template.mkdir(parents=True)
            sibling_template.mkdir(parents=True)
            package.mkdir(parents=True)
            sentinel = sibling_template / "keep.md"
            sentinel.write_text("source", encoding="utf-8")
            (package / "__init__.py").write_text("", encoding="utf-8")

            caught = None
            with mock.patch.object(build_adapter, "_ADAPTERS_ROOT", root / "adapters"), \
                mock.patch.object(build_adapter, "_SOURCE_PACKAGE", package):
                try:
                    build_adapter._build_bundle(
                        "codex", sibling_template, force=True
                    )
                except Exception as error:  # behavior under test
                    caught = error

            self.assertIsInstance(caught, build_adapter.BuildError)
            self.assertIn("overlap", str(caught))
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "source")

    def test_failed_staged_build_preserves_existing_forced_output(self):
        """Catches deleting the previous bundle before the replacement is complete."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            output.mkdir()
            sentinel = output / "prior-file"
            sentinel.write_text("preserve me", encoding="utf-8")

            with mock.patch.object(
                build_adapter.shutil,
                "copytree",
                side_effect=OSError("copy failed"),
            ):
                with self.assertRaises(OSError):
                    build_adapter._build_bundle("codex", output, force=True)

            self.assertTrue(sentinel.is_file())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve me")

    def test_build_rejects_output_below_symlinked_parent_without_touching_target(self):
        """Catches --force deleting a directory reached through a parent symlink."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target_parent = root / "target-parent"
            target_parent.mkdir()
            output = target_parent / "bundle"
            output.mkdir()
            sentinel = output / "preserve-me"
            sentinel.write_text("unchanged", encoding="utf-8")
            linked_parent = root / "linked-parent"
            linked_parent.symlink_to(target_parent, target_is_directory=True)

            result = run_tool(
                "tools/build_adapter.py",
                "codex",
                "--output",
                str(linked_parent / "bundle"),
                "--force",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr.lower())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged")

    def test_build_rejects_absolute_dotdot_output_before_symlink_check(self):
        """Catches absolute traversal hiding a linked parent before --force deletes."""
        with tempfile.TemporaryDirectory() as directory:
            output, requested_output, sentinel = _dotdot_symlinked_output(Path(directory))

            result = run_tool(
                "tools/build_adapter.py",
                "codex",
                "--output",
                str(requested_output),
                "--force",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("..", result.stderr)
            self.assertEqual(output, sentinel.parent)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged")

    def test_build_rejects_relative_dotdot_output_before_symlink_check(self):
        """Catches relative traversal hiding a linked parent before --force deletes."""
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as directory:
            output, absolute_request, sentinel = _dotdot_symlinked_output(Path(directory))
            requested_output = absolute_request.relative_to(PROJECT_ROOT)

            result = run_tool(
                "tools/build_adapter.py",
                "codex",
                "--output",
                str(requested_output),
                "--force",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("..", result.stderr)
            self.assertEqual(output, sentinel.parent)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged")

    def test_capability_metadata_lists_declared_adapter_levels(self):
        """Catches adapter capability labels drifting from the public contract."""
        capabilities = json.loads(
            (PROJECT_ROOT / "adapters" / "capabilities.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            capabilities,
            {
                "claude-code": "automatic",
                "gemini-cli": "advisory",
                "codex": "manual",
                "opencode": "manual",
            },
        )


def _dotdot_symlinked_output(root: Path) -> tuple[Path, Path, Path]:
    target_parent = root / "target-parent"
    target_parent.mkdir()
    output = target_parent / "bundle"
    output.mkdir()
    sentinel = output / "preserve-me"
    sentinel.write_text("unchanged", encoding="utf-8")
    linked_parent = root / "linked-parent"
    linked_parent.symlink_to(target_parent, target_is_directory=True)
    return output, linked_parent / ".." / "target-parent" / "bundle", sentinel
