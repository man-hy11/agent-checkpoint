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
