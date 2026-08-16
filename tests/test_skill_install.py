"""Tests for installing the portable generic checkpoint skill."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_checkpoint.skill_install import agent_skill_roots, global_skill_destination
from tests.helpers import run_cli


class SkillInstallTests(unittest.TestCase):
    def test_installs_canonical_skill_and_creates_requested_links(self):
        """One .agent source must be reusable from agent-specific skill paths."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / ".agent" / "skills"
            claude = root / ".claude" / "skills"
            codex = root / ".codex" / "skills"
            result = run_cli(
                "skill-install",
                "--destination",
                str(source),
                "--link",
                str(claude),
                "--link",
                str(codex),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            installed = source / "checkpoint" / "SKILL.md"
            self.assertTrue(installed.is_file())
            self.assertIn("agent-checkpoint workflow", installed.read_text(encoding="utf-8"))
            for linked_root in (claude, codex):
                linked = linked_root / "checkpoint"
                self.assertTrue(linked.is_symlink())
                self.assertEqual(linked.resolve(), installed.parent.resolve())

    def test_global_mode_requires_a_selected_agent_for_each_link(self):
        """Catches a global installer silently linking every runtime by default."""
        result = run_cli("skill-install", "--global", "--agent", "gemini-cli")

        self.assertEqual(result.returncode, 2)
        self.assertIn("native extension", result.stderr)

    def test_global_agent_paths_are_selected_without_implicit_links(self):
        """Catches a global installation using undocumented or all-agent paths."""
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            with patch("agent_checkpoint.skill_install.Path.home", return_value=home):
                self.assertEqual(global_skill_destination(), home / ".agent" / "skills")
                self.assertEqual(
                    agent_skill_roots(("claude-code", "opencode", "agent-compatible")),
                    (
                        home / ".claude" / "skills",
                        home / ".config" / "opencode" / "skills",
                        home / ".agents" / "skills",
                    ),
                )

    def test_refuses_to_replace_existing_skill_or_link(self):
        """A pre-existing target must never be overwritten by an install rerun."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / ".agent" / "skills"
            first = run_cli("skill-install", "--destination", str(destination))
            self.assertEqual(first.returncode, 0, first.stderr)

            second = run_cli("skill-install", "--destination", str(destination))
            self.assertEqual(second.returncode, 2)
            self.assertIn("already exists", second.stderr)


class MultiSkillInstallTests(unittest.TestCase):
    def test_install_skill_suite_copies_all_twelve_skills(self):
        """Catches install_skill_suite leaving any of the twelve skills absent."""
        from agent_checkpoint.skill_install import install_skill_suite, SKILL_NAMES
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / ".agent" / "skills"
            result = install_skill_suite(destination, link_roots=())
            for name in SKILL_NAMES:
                self.assertTrue(
                    (destination / name / "SKILL.md").is_file(),
                    f"missing installed skill: {name}",
                )
            self.assertEqual(len(result.skills), len(SKILL_NAMES))

    def test_install_skill_suite_refuses_if_any_skill_already_exists(self):
        """Catches install_skill_suite overwriting an existing skill directory."""
        from agent_checkpoint.skill_install import install_skill_suite
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / ".agent" / "skills"
            destination.mkdir(parents=True)
            # Pre-create the checkpoint dir to trigger the guard
            (destination / "checkpoint").mkdir()
            from agent_checkpoint.config import ConfigError
            with self.assertRaises(ConfigError):
                install_skill_suite(destination, link_roots=())

    def test_install_skill_suite_creates_links_for_all_skills(self):
        """Catches install_skill_suite not creating links for every installed skill."""
        from agent_checkpoint.skill_install import install_skill_suite, SKILL_NAMES
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / ".agent" / "skills"
            claude_root = root / ".claude" / "skills"
            result = install_skill_suite(destination, link_roots=(claude_root,))
            for name in SKILL_NAMES:
                link = claude_root / name
                self.assertTrue(link.is_symlink(), f"missing link for {name}")
                self.assertEqual(link.resolve(), (destination / name).resolve())
            # Total links = len(SKILL_NAMES) * len(link_roots)
            self.assertEqual(len(result.links), len(SKILL_NAMES))

    def test_install_skill_suite_is_atomic_on_partial_failure(self):
        """Catches install_skill_suite leaving partial state on error."""
        import shutil as _shutil
        import unittest.mock as mock
        from agent_checkpoint.skill_install import install_skill_suite
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / ".agent" / "skills"
            # Simulate failure mid-install by patching shutil.copytree to fail
            # on the third call (first two skill copies succeed, then error)
            call_count = {"n": 0}
            real_copytree = _shutil.copytree
            def failing_copytree(src, dst, **kw):
                call_count["n"] += 1
                if call_count["n"] >= 3:
                    raise OSError("simulated disk full")
                return real_copytree(src, dst, **kw)
            with mock.patch("agent_checkpoint.skill_install.shutil.copytree", failing_copytree):
                try:
                    install_skill_suite(destination, link_roots=())
                except (OSError, Exception):
                    pass
            # After failure: destination should be absent or empty (no partial install)
            if destination.exists():
                installed = list(destination.iterdir())
                self.assertEqual(
                    len(installed), 0,
                    f"partial install left {len(installed)} items: {installed}",
                )
