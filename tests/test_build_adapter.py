import contextlib
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
from tools.validate_skills import EXPECTED_SKILLS


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
            self.assertTrue((output / "commands" / "checkpoint-save.md").is_file())

    @staticmethod
    def _patched_sources(root: Path):
        """Point the builder at a throwaway copy of every single source tree.

        Since R5 the builder projects from skills/, commands/, and hooks/ rather
        than a per-host adapters/ template, so overlap protection must cover all
        of them plus the Python package.
        """
        return (
            mock.patch.object(build_adapter, "_SKILLS_ROOT", root / "skills"),
            mock.patch.object(build_adapter, "_COMMANDS_ROOT", root / "commands"),
            mock.patch.object(build_adapter, "_HOOKS_ROOT", root / "hooks"),
            mock.patch.object(
                build_adapter, "_SOURCE_PACKAGE", root / "agent_checkpoint"
            ),
        )

    @staticmethod
    def _make_sources(root: Path) -> Path:
        """Create a minimal stand-in for the single-source trees; return a sentinel."""
        (root / "skills" / "checkpoint").mkdir(parents=True)
        (root / "skills" / "checkpoint" / "SKILL.md").write_text(
            "---\nname: checkpoint\ndescription: x\n---\nbody\n", encoding="utf-8"
        )
        (root / "commands").mkdir(parents=True, exist_ok=True)
        (root / "hooks").mkdir(parents=True, exist_ok=True)
        (root / "agent_checkpoint").mkdir(parents=True, exist_ok=True)
        (root / "agent_checkpoint" / "__init__.py").write_text("", encoding="utf-8")
        sentinel = root / "skills" / "checkpoint" / "keep.md"
        sentinel.write_text("source", encoding="utf-8")
        return sentinel

    def test_build_rejects_output_equal_to_or_ancestor_of_sources(self):
        """Catches --force removing a canonical source tree itself."""
        for output_kind in ("source", "ancestor"):
            with self.subTest(output=output_kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "source-root"
                root.mkdir(parents=True)
                sentinel = self._make_sources(root)
                output = (root / "skills") if output_kind == "source" else root

                caught = None
                with contextlib.ExitStack() as stack:
                    for patch in self._patched_sources(root):
                        stack.enter_context(patch)
                    try:
                        build_adapter._build_bundle("codex", output, force=True)
                    except Exception as error:  # behavior under test
                        caught = error

                self.assertIsInstance(caught, build_adapter.BuildError)
                self.assertIn("overlap", str(caught))
                self.assertTrue(sentinel.is_file())
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "source")

    def test_build_rejects_output_nested_inside_a_source_tree(self):
        """Catches recursive self-copy when output is below a single source."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_sources(root)
            output = root / "skills" / "generated"

            caught = None
            with contextlib.ExitStack() as stack:
                for patch in self._patched_sources(root):
                    stack.enter_context(patch)
                stack.enter_context(
                    mock.patch.object(
                        build_adapter.shutil,
                        "copytree",
                        side_effect=AssertionError("copy must not start"),
                    )
                )
                try:
                    build_adapter._build_bundle("codex", output, force=False)
                except Exception as error:  # behavior under test
                    caught = error

            self.assertIsInstance(caught, build_adapter.BuildError)
            self.assertIn("overlap", str(caught))
            self.assertFalse(output.exists())

    def test_build_rejects_output_overlapping_a_sibling_source_tree(self):
        """Catches a build replacing a source tree it does not read from.

        codex ships no commands, so commands/ is untouched by its projection —
        it must still be protected from being used as the output directory.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_sources(root)
            sibling = root / "commands"
            sentinel = sibling / "keep.md"
            sentinel.write_text("source", encoding="utf-8")

            caught = None
            with contextlib.ExitStack() as stack:
                for patch in self._patched_sources(root):
                    stack.enter_context(patch)
                try:
                    build_adapter._build_bundle("codex", sibling, force=True)
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
        """Catches adapter capability labels drifting from the public contract.

        Since R6 the capability map is declared in hosts.toml rather than a
        hand-maintained adapters/capabilities.json, so this reads the builder's
        own accessor — the same path a bundle build takes.
        """
        self.assertEqual(
            build_adapter.capabilities(),
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


class SkillSuiteBuildTests(unittest.TestCase):
    """Every skill-shipping host must receive the whole canonical suite.

    The expected names are imported rather than restated: a local copy of the
    list silently skipped checkpoint-save when it was added, so these tests
    claimed to cover "all skills" while missing one.
    """

    def _assert_bundle_ships_every_skill(self, host: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / host

            result = run_tool("tools/build_adapter.py", host, "--output", str(output))

            self.assertEqual(result.returncode, 0, result.stderr)
            for name in EXPECTED_SKILLS:
                self.assertTrue(
                    (output / "skills" / name / "SKILL.md").is_file(),
                    f"missing skill: {name}",
                )

    def test_build_codex_bundle_installs_every_skill(self):
        """Catches build_adapter omitting skills beyond the router."""
        self._assert_bundle_ships_every_skill("codex")

    def test_build_opencode_bundle_installs_every_skill(self):
        """Catches build_adapter omitting skills from the OpenCode bundle."""
        self._assert_bundle_ships_every_skill("opencode")

    def test_build_claude_code_bundle_installs_every_skill(self):
        """Catches build_adapter omitting skills from the Claude Code bundle."""
        self._assert_bundle_ships_every_skill("claude-code")

    def test_skill_shipping_bundles_include_shared_routing_contract(self):
        """Catches the router's chain-v1.md reference dangling in a bundle."""
        canonical = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "_checkpoint-shared"
            / "chain-v1.md"
        ).read_bytes()
        for host in ("claude-code", "codex", "opencode"):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / host

                result = run_tool(
                    "tools/build_adapter.py", host, "--output", str(output)
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                shipped = output / "skills" / "_checkpoint-shared" / "chain-v1.md"
                self.assertTrue(shipped.is_file(), f"{host} bundle omits chain-v1.md")
                self.assertEqual(
                    shipped.read_bytes(),
                    canonical,
                    f"{host} bundle's chain-v1.md diverges from the canonical source",
                )


class ProjectionBaselineTests(unittest.TestCase):
    """Catches projected output drifting from the frozen R1 adapter baseline.

    R1 snapshotted the hand-maintained ``adapters/`` tree before any structural
    change; R5 verified that projection reproduces it byte-for-byte apart from
    two deliberate version-unification differences. ``adapters/`` itself is gone
    since R6, so this fixture is the only remaining record of the published
    output, and this test is what makes that R5 comparison durable.

    The fixture is frozen. A failure here means the generator changed what it
    emits — fix the generator, or make it a plan revision. Do not regenerate the
    fixture to match new output; that would defeat the check entirely.
    """

    _BASELINE = PROJECT_ROOT / "tests" / "fixtures" / "adapter-baseline"

    # Version is unified from package.json, so these two manifests legitimately
    # differ from the baseline. Every other projected file must match exactly.
    _PERMITTED_VERSION_DRIFT = {
        "codex/.codex-plugin/plugin.json",
        "gemini-cli/gemini-extension.json",
    }

    @staticmethod
    def _relative_files(root: Path) -> set[str]:
        return {
            str(path.relative_to(root))
            for path in root.rglob("*")
            if path.is_file()
        }

    def test_projection_matches_frozen_baseline(self):
        """Catches any generated file drifting from the published R1 output."""
        version = json.loads(
            (PROJECT_ROOT / "package.json").read_text(encoding="utf-8")
        )["version"]

        with tempfile.TemporaryDirectory() as directory:
            for host in ("claude-code", "codex", "gemini-cli", "opencode"):
                expected_root = self._BASELINE / host
                output = Path(directory) / host
                result = run_tool(
                    "tools/build_adapter.py", host, "--output", str(output)
                )
                self.assertEqual(result.returncode, 0, result.stderr)

                # lib/ and bin/ are bundle runtime, never part of the baseline.
                generated = {
                    name
                    for name in self._relative_files(output)
                    if not name.startswith(("lib/", "bin/"))
                }

                # Absence is contractual: codex ships no commands or hooks,
                # opencode no manifest, gemini-cli no skills. A missing file
                # must fail here rather than pass as an empty comparison.
                self.assertEqual(
                    generated,
                    self._relative_files(expected_root),
                    f"{host}: projected file set differs from the baseline",
                )

                for name in sorted(generated):
                    expected = (expected_root / name).read_text(encoding="utf-8")
                    actual = (output / name).read_text(encoding="utf-8")
                    if f"{host}/{name}" in self._PERMITTED_VERSION_DRIFT:
                        self.assertEqual(
                            actual,
                            expected.replace('"version": "0.1.0"', f'"version": "{version}"'),
                            f"{host}/{name} differs from the baseline beyond its version",
                        )
                    else:
                        self.assertEqual(
                            actual,
                            expected,
                            f"{host}/{name} drifted from the frozen baseline",
                        )
