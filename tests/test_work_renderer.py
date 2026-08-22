"""Final-package renderer and RULES.md generation tests."""

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from agent_checkpoint.work_chain import next_skill
from agent_checkpoint.work_manifest import load_manifest
from agent_checkpoint.work_renderer import (
    CHAIN_TABLE,
    RenderError,
    render_final_package,
    render_rules,
)
from agent_checkpoint.work_state import Attempt, Unit, WorkState

_FAMILIES = (
    "project", "feature", "bugfix", "refactor", "upgrade",
    "migration", "performance", "integration", "release", "spike",
)

_BASE_STATE = WorkState(
    schema_version=1,
    work_id="demo",
    work_type="feature",
    plan_revision=1,
    brief_confirmed=True,
    current_unit="F1",
    max_attempts=3,
    attempt_override=None,
    units=(Unit(id="F1", group=None, kind="step", state="ready", attempt=0),),
    attempts=(),
)


class RenderFinalPackageTests(unittest.TestCase):
    def test_all_ten_families_render_final_only_packages(self):
        """Catches any family leaking templates/prompts/shared into the final package."""
        for work_type in _FAMILIES:
            with self.subTest(work_type=work_type):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    result = render_final_package(root, work_type, "current")

                    self.assertEqual(result.work_type, work_type)
                    self.assertTrue((result.path / "RULES.md").is_file())
                    self.assertTrue((result.path / "CURRENT.md").is_file())
                    self.assertFalse((result.path / "templates").exists())
                    self.assertFalse((result.path / "prompts").exists())
                    self.assertFalse((result.path / "shared").exists())

                    manifest = load_manifest(work_type)
                    for name, policy in manifest.artifacts.items():
                        artifact_path = result.path / name
                        if policy == "omitted":
                            self.assertFalse(artifact_path.exists())
                        else:
                            self.assertTrue(artifact_path.is_file(), f"{name} missing")

    def test_render_twice_refuses_existing_package(self):
        """Catches a second render silently overwriting an existing work package."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            render_final_package(root, "feature", "current")
            with self.assertRaises(RenderError):
                render_final_package(root, "feature", "current")

    def test_invalid_work_id_is_refused(self):
        """Catches an uppercase or space-containing work id reaching the filesystem."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(RenderError):
                render_final_package(root, "feature", "Not Valid")

    def test_symlinked_work_root_is_refused_without_writing(self):
        """Catches a symlinked .agent-checkpoint/work directory bypassing the safe-path guard."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            real_root = base / "real-project"
            real_root.mkdir()
            (real_root / ".agent-checkpoint").mkdir()
            real_work = base / "elsewhere"
            real_work.mkdir()
            (real_root / ".agent-checkpoint" / "work").symlink_to(real_work, target_is_directory=True)

            with self.assertRaises(RenderError):
                render_final_package(real_root, "feature", "current")

            self.assertEqual(list(real_work.iterdir()), [])


class RenderRulesTests(unittest.TestCase):
    def test_render_rules_includes_hard_rules_and_evidence_and_chain_table(self):
        """Catches RULES.md omitting hard rules, evidence keys, or the chain table."""
        manifest = load_manifest("performance")
        text = render_rules(manifest)
        for rule in manifest.hard_rules:
            self.assertIn(rule, text)
        for key in manifest.evidence_required["step"]:
            self.assertIn(f"`{key}`", text)
        for key in manifest.evidence_required["gate"]:
            self.assertIn(f"`{key}`", text)
        self.assertIn("checkpoint-execute", text)
        self.assertIn("checkpoint-handoff", text)

    def test_render_rules_has_no_unresolved_placeholders(self):
        """Catches a template substitution being skipped and leaking {{ }} markers."""
        for work_type in _FAMILIES:
            manifest = load_manifest(work_type)
            text = render_rules(manifest)
            self.assertNotIn("{{", text)
            self.assertNotIn("}}", text)


class ChainTableEquivalenceTests(unittest.TestCase):
    """Proves CHAIN_TABLE (rendered into RULES.md) matches work_chain.next_skill,
    row for row, for a constructed state satisfying each row's condition."""

    def test_no_state_block_exists(self):
        """Catches row 1 (no state block) drifting from next_skill(None)."""
        self.assertEqual(next_skill(None), CHAIN_TABLE[0][1])

    def test_brief_not_confirmed(self):
        """Catches row 2 drifting from the engine's brief_confirmed check."""
        state = replace(_BASE_STATE, brief_confirmed=False)
        self.assertEqual(next_skill(state), CHAIN_TABLE[1][1])

    def test_units_empty(self):
        """Catches row 3 drifting from the engine's empty-units check."""
        state = replace(_BASE_STATE, units=(), current_unit=None)
        self.assertEqual(next_skill(state), CHAIN_TABLE[2][1])

    def test_every_unit_passed(self):
        """Catches row 4 drifting from the engine's all-passed check."""
        state = replace(
            _BASE_STATE,
            units=(Unit(id="F1", group=None, kind="step", state="passed", attempt=1),),
        )
        self.assertEqual(next_skill(state), CHAIN_TABLE[3][1])

    def test_current_unit_names_no_member(self):
        """Catches row 5 drifting from the engine's unknown-current-unit check."""
        state = replace(_BASE_STATE, current_unit="F9")
        self.assertEqual(next_skill(state), CHAIN_TABLE[4][1])

    def test_current_unit_passed_but_not_all_passed(self):
        """Catches row 6 drifting from the engine's stale-passed-tracker check."""
        state = replace(
            _BASE_STATE,
            current_unit="F1",
            units=(
                Unit(id="F1", group=None, kind="step", state="passed", attempt=1),
                Unit(id="F2", group=None, kind="step", state="pending", attempt=1),
            ),
        )
        self.assertEqual(next_skill(state), CHAIN_TABLE[5][1])

    def test_current_unit_superseded(self):
        """Catches row 7 drifting from the engine's superseded check."""
        state = replace(
            _BASE_STATE,
            units=(Unit(id="F1", group=None, kind="step", state="superseded", attempt=1),),
        )
        self.assertEqual(next_skill(state), CHAIN_TABLE[6][1])

    def test_current_unit_blocked(self):
        """Catches row 8 drifting from the engine's blocked check."""
        state = replace(
            _BASE_STATE,
            units=(Unit(id="F1", group=None, kind="step", state="blocked", attempt=1),),
        )
        self.assertEqual(next_skill(state), CHAIN_TABLE[7][1])

    def test_failed_without_diagnosis(self):
        """Catches row 9 drifting from the engine's no-fingerprint failed check."""
        state = replace(
            _BASE_STATE,
            units=(Unit(id="F1", group=None, kind="step", state="failed", attempt=1),),
        )
        self.assertEqual(next_skill(state), CHAIN_TABLE[8][1])

    def test_failed_with_diagnosis(self):
        """Catches row 10 drifting from the engine's diagnosed-failed check."""
        state = replace(
            _BASE_STATE,
            units=(Unit(id="F1", group=None, kind="step", state="failed", attempt=1),),
            attempts=(
                Attempt(
                    unit="F1", n=1, result="failed",
                    root_cause_fingerprint="abc", evidence_ref=None,
                ),
            ),
        )
        self.assertEqual(next_skill(state), CHAIN_TABLE[9][1])

    def test_current_unit_pending_or_ready(self):
        """Catches row 11 drifting from the engine's ready-unit check."""
        self.assertEqual(next_skill(_BASE_STATE), CHAIN_TABLE[10][1])

    def test_current_unit_running_gate(self):
        """Catches row 12 drifting from the engine's running-gate check."""
        state = replace(
            _BASE_STATE,
            units=(Unit(id="F1", group=None, kind="gate", state="running", attempt=1),),
        )
        self.assertEqual(next_skill(state), CHAIN_TABLE[11][1])

    def test_current_unit_running_step(self):
        """Catches row 13 drifting from the engine's running-step check."""
        state = replace(
            _BASE_STATE,
            units=(Unit(id="F1", group=None, kind="step", state="running", attempt=1),),
        )
        self.assertEqual(next_skill(state), CHAIN_TABLE[12][1])


if __name__ == "__main__":
    unittest.main()
