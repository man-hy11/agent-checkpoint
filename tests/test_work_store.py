"""Atomic work-package store tests."""

import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from agent_checkpoint import storage
from agent_checkpoint.config import ConfigError
from agent_checkpoint.work_chain import allowed_events, next_skill
from agent_checkpoint.work_state import StateError, parse_state
from agent_checkpoint.work_store import claim

BLOCK = """<!-- agent-checkpoint:state v1 -->
{
  "schema_version": 1,
  "work_id": "demo",
  "work_type": "feature",
  "plan_revision": 1,
  "brief_confirmed": true,
  "current_unit": "I4",
  "max_attempts": 3,
  "attempt_override": null,
  "units": [
    {"id": "I4", "group": null, "kind": "step", "state": "ready", "attempt": 0}
  ],
  "attempts": []
}
<!-- /agent-checkpoint:state -->
"""

CURRENT_TEXT = f"# CURRENT.md\n\n{BLOCK}\nHuman prose below.\n"

EVIDENCE_ENTRY = """## Unit: I4
## Attempt: 1

### command
`PYTHONPATH=. python3 -m unittest tests.test_work_store -v`

### pass_fail
PASS

### observed_output
Ran 1 test in 0.001s

OK
"""


def _seed(project_root: Path) -> tuple[Path, Path]:
    current_path = project_root / "CURRENT.md"
    evidence_path = project_root / "EVIDENCE.md"
    current_path.write_text(CURRENT_TEXT, encoding="utf-8")
    return current_path, evidence_path


class ClaimTests(unittest.TestCase):
    def test_claim_updates_state_and_appends_evidence_together(self):
        """Catches a transition landing in one file without the other."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            current_path, evidence_path = _seed(project_root)

            updated = claim(
                project_root,
                current_path,
                evidence_path,
                unit_id="I4",
                event="start",
                plan_revision=1,
                evidence_text=EVIDENCE_ENTRY,
            )

            self.assertEqual(updated.unit("I4").state, "running")
            reparsed = parse_state(current_path.read_text(encoding="utf-8"))
            self.assertEqual(reparsed.unit("I4").state, "running")
            self.assertIn("## Unit: I4", evidence_path.read_text(encoding="utf-8"))

    def test_stale_plan_revision_leaves_both_files_untouched(self):
        """Catches a stale-revision transition mutating durable files before refusal."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            current_path, evidence_path = _seed(project_root)
            before_current = current_path.read_bytes()

            with self.assertRaises(StateError):
                claim(
                    project_root,
                    current_path,
                    evidence_path,
                    unit_id="I4",
                    event="start",
                    plan_revision=2,
                    evidence_text=EVIDENCE_ENTRY,
                )

            self.assertEqual(current_path.read_bytes(), before_current)
            self.assertFalse(evidence_path.exists())

    def test_illegal_transition_leaves_both_files_untouched(self):
        """Catches an illegal event being partially applied before refusal."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            current_path, evidence_path = _seed(project_root)
            before_current = current_path.read_bytes()

            with self.assertRaises(StateError):
                claim(
                    project_root,
                    current_path,
                    evidence_path,
                    unit_id="I4",
                    event="pass",
                    plan_revision=1,
                    evidence_text=EVIDENCE_ENTRY,
                )

            self.assertEqual(current_path.read_bytes(), before_current)
            self.assertFalse(evidence_path.exists())

    def test_symlinked_parent_is_refused_without_writing(self):
        """Catches a symlinked package directory bypassing the safe-open guard."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            real_package = base / "real-package"
            real_package.mkdir()
            current_path, evidence_path = _seed(real_package)
            project_root = base / "project"
            project_root.mkdir()
            link = project_root / "package"
            try:
                link.symlink_to(real_package, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with self.assertRaises(ConfigError):
                claim(
                    project_root,
                    link / "CURRENT.md",
                    link / "EVIDENCE.md",
                    unit_id="I4",
                    event="start",
                    plan_revision=1,
                    evidence_text=EVIDENCE_ENTRY,
                )

            self.assertEqual(list(real_package.glob(".agent-checkpoint-*.tmp")), [])
            self.assertEqual(
                current_path.read_text(encoding="utf-8"), CURRENT_TEXT
            )
            self.assertFalse(evidence_path.exists())

    def test_partial_replacement_failure_restores_current(self):
        """Catches a failed second replace leaving CURRENT.md pointing at new state."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            current_path, evidence_path = _seed(project_root)
            before_current = current_path.read_bytes()

            with mock.patch.object(
                storage.os, "replace", side_effect=OSError("replace failed")
            ):
                with self.assertRaises(OSError):
                    claim(
                        project_root,
                        current_path,
                        evidence_path,
                        unit_id="I4",
                        event="start",
                        plan_revision=1,
                        evidence_text=EVIDENCE_ENTRY,
                    )

            self.assertEqual(current_path.read_bytes(), before_current)
            self.assertFalse(evidence_path.exists())

    def test_stray_temporary_file_does_not_block_recovery(self):
        """Catches a leftover interrupted-write temp file corrupting the next claim."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            current_path, evidence_path = _seed(project_root)
            stray = project_root / ".agent-checkpoint-deadbeefdeadbeefdeadbeefdeadbeef.tmp"
            stray.write_text("orphaned partial write", encoding="utf-8")

            updated = claim(
                project_root,
                current_path,
                evidence_path,
                unit_id="I4",
                event="start",
                plan_revision=1,
                evidence_text=EVIDENCE_ENTRY,
            )

            self.assertEqual(updated.unit("I4").state, "running")
            self.assertEqual(stray.read_text(encoding="utf-8"), "orphaned partial write")
            reparsed = parse_state(current_path.read_text(encoding="utf-8"))
            self.assertEqual(reparsed.unit("I4").state, "running")

    def test_concurrent_claims_let_exactly_one_transition_win(self):
        """Catches two overlapping claims both advancing the same ready unit."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            current_path, evidence_path = _seed(project_root)
            first_holds_lock = threading.Event()
            release_first = threading.Event()
            real_acquire = storage._acquire_lock

            def controlled_acquire(lock_file, timeout_seconds):
                real_acquire(lock_file, timeout_seconds)
                if not first_holds_lock.is_set():
                    first_holds_lock.set()
                    release_first.wait(timeout=5)

            results: dict[str, object] = {}

            def attempt(role: str) -> None:
                try:
                    results[role] = claim(
                        project_root,
                        current_path,
                        evidence_path,
                        unit_id="I4",
                        event="start",
                        plan_revision=1,
                        evidence_text=EVIDENCE_ENTRY,
                        lock_timeout_seconds=5.0,
                    )
                except StateError as error:
                    results[role] = error

            with mock.patch.object(storage, "_acquire_lock", controlled_acquire):
                first_thread = threading.Thread(target=attempt, args=("first",))
                first_thread.start()
                first_holds_lock.wait(timeout=5)
                second_thread = threading.Thread(target=attempt, args=("second",))
                second_thread.start()
                release_first.set()
                first_thread.join(timeout=10)
                second_thread.join(timeout=10)

            outcomes = [results["first"], results["second"]]
            successes = [item for item in outcomes if not isinstance(item, Exception)]
            failures = [item for item in outcomes if isinstance(item, Exception)]
            self.assertEqual(len(successes), 1)
            self.assertEqual(len(failures), 1)
            self.assertIsInstance(failures[0], StateError)
            self.assertEqual(successes[0].unit("I4").state, "running")


if __name__ == "__main__":
    unittest.main()


MULTI_UNIT_BLOCK = """<!-- agent-checkpoint:state v1 -->
{
  "schema_version": 1,
  "work_id": "demo",
  "work_type": "feature",
  "plan_revision": 1,
  "brief_confirmed": true,
  "current_unit": "I1",
  "max_attempts": 3,
  "attempt_override": null,
  "units": [
    {"id": "I1", "group": null, "kind": "step", "state": "running", "attempt": 1},
    {"id": "I2", "group": null, "kind": "step", "state": "pending", "attempt": 0},
    {"id": "I3", "group": null, "kind": "gate", "state": "pending", "attempt": 0}
  ],
  "attempts": []
}
<!-- /agent-checkpoint:state -->
"""

MULTI_UNIT_TEXT = (
    "# CURRENT.md\n\n"
    f"{MULTI_UNIT_BLOCK}\n"
    "## Current Target\n\n"
    "**I1 — First step**\n\n"
    "## Steps\n\n"
    "- [ ] I1 First step\n"
    "- [ ] I2 Second step\n"
    "- [ ] I3 Gate\n"
)

PASS_EVIDENCE = """## Unit: I1
## Attempt: 1

### command
`PYTHONPATH=. python3 -m unittest tests.test_work_store -v`

### pass_fail
PASS

### observed_output
Ran 1 test in 0.001s

OK
"""


def _seed_multi(project_root: Path) -> tuple[Path, Path]:
    current_path = project_root / "CURRENT.md"
    evidence_path = project_root / "EVIDENCE.md"
    current_path.write_text(MULTI_UNIT_TEXT, encoding="utf-8")
    return current_path, evidence_path


class PointerAdvanceTests(unittest.TestCase):
    """Catches current_unit staying on a finished unit while work remains.

    Nothing wrote current_unit after the state block was first authored, so the
    pointer froze at planning time. Everything derived from it then went stale:
    `work status` described a finished unit, and next_skill routed ordinary
    progress to checkpoint-plan via chain-v1 Row 6.
    """

    def _pass_first_unit(self, project_root: Path, current_path: Path, evidence_path: Path):
        return claim(
            project_root,
            current_path,
            evidence_path,
            unit_id="I1",
            event="pass",
            plan_revision=1,
            evidence_text=PASS_EVIDENCE,
        )

    def test_pass_advances_current_unit_to_next_unresolved(self):
        """Catches the pointer freezing on a passed unit while work remains."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            current_path, evidence_path = _seed_multi(project_root)

            updated = self._pass_first_unit(project_root, current_path, evidence_path)

            self.assertEqual(updated.unit("I1").state, "passed")
            self.assertEqual(updated.current_unit, "I2")
            reparsed = parse_state(current_path.read_text(encoding="utf-8"))
            self.assertEqual(reparsed.current_unit, "I2")

    def test_advance_makes_status_and_routing_describe_the_next_unit(self):
        """Catches the user-visible symptoms: empty events and a plan detour."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            current_path, evidence_path = _seed_multi(project_root)

            updated = self._pass_first_unit(project_root, current_path, evidence_path)

            self.assertEqual(next_skill(updated), "checkpoint-claim")
            self.assertIn("start", allowed_events(updated))

    def test_fail_does_not_advance_the_pointer(self):
        """Catches a failure skipping past the unit that still needs recovery."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            current_path, evidence_path = _seed_multi(project_root)

            updated = claim(
                project_root,
                current_path,
                evidence_path,
                unit_id="I1",
                event="fail",
                plan_revision=1,
                evidence_text=PASS_EVIDENCE.replace("PASS", "FAIL"),
            )

            self.assertEqual(updated.unit("I1").state, "failed")
            self.assertEqual(updated.current_unit, "I1")

    def test_final_pass_leaves_pointer_and_routes_to_handoff(self):
        """Catches an advance past the end breaking chain-v1 Row 4."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            current_path, evidence_path = _seed_multi(project_root)
            # Collapse to a single remaining unit so this pass is the last one.
            text = current_path.read_text(encoding="utf-8")
            text = text.replace(
                '{"id": "I2", "group": null, "kind": "step", "state": "pending", "attempt": 0},\n'
                '    {"id": "I3", "group": null, "kind": "gate", "state": "pending", "attempt": 0}',
                '{"id": "I2", "group": null, "kind": "step", "state": "passed", "attempt": 1},\n'
                '    {"id": "I3", "group": null, "kind": "gate", "state": "passed", "attempt": 1}',
            )
            current_path.write_text(text, encoding="utf-8")

            updated = self._pass_first_unit(project_root, current_path, evidence_path)

            self.assertTrue(updated.is_complete())
            self.assertEqual(next_skill(updated), "checkpoint-handoff")

    def test_tracker_prose_matches_the_state_block_after_a_transition(self):
        """Catches the human-readable half going stale against the state block."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            current_path, evidence_path = _seed_multi(project_root)

            self._pass_first_unit(project_root, current_path, evidence_path)

            rendered = current_path.read_text(encoding="utf-8")
            self.assertIn("**I2", rendered)
            self.assertNotIn("**I1 — First step**", rendered)
            self.assertIn("- [x] I1 First step", rendered)
            self.assertIn("- [ ] I2 Second step", rendered)
