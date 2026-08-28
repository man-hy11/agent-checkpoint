# tests/test_lifecycle.py
"""Lifecycle scenario tests for the work-status CLI routing (R5-I9)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import PROJECT_ROOT

from agent_checkpoint.work_state import BLOCK_BEGIN, BLOCK_END, parse_state


def _make_current(state_dict: dict) -> str:
    block = json.dumps(state_dict, indent=2)
    return f"# CURRENT.md\n\n{BLOCK_BEGIN}\n{block}\n{BLOCK_END}\n"


def _run_work_status_json(project_root: Path) -> dict:
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    result = subprocess.run(
        [sys.executable, "-m", "agent_checkpoint.cli", "work", "status", "--json",
         "--root", str(project_root)],
        capture_output=True, text=True, env=env,
    )
    return json.loads(result.stdout)


_BASE: dict = {
    "schema_version": 1, "work_id": "pkg", "work_type": "feature",
    "plan_revision": 1, "brief_confirmed": True, "current_unit": "I1",
    "max_attempts": 3, "attempt_override": None,
    "units": [{"id": "I1", "group": None, "kind": "step", "state": "ready", "attempt": 0}],
    "attempts": [],
}


class LifecycleCLITests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.pkg = self.root / ".agent-checkpoint" / "work" / "pkg"
        self.pkg.mkdir(parents=True)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write(self, state_dict: dict) -> None:
        (self.pkg / "CURRENT.md").write_text(_make_current(state_dict), encoding="utf-8")

    def _status(self) -> dict:
        return _run_work_status_json(self.root)

    def test_work_status_json_ready_unit(self):
        """Catches work status --json not reflecting a ready unit's state and next_skill."""
        self._write(_BASE)
        data = self._status()
        self.assertEqual(data["state"], "ready")
        self.assertEqual(data["next_skill"], "checkpoint-claim")
        self.assertIn("start", data["allowed_events"])

    def test_work_status_json_failed_no_fingerprint_routes_diagnose(self):
        """Catches next_skill not routing a failed unit without fingerprint to checkpoint-diagnose."""
        state = {**_BASE,
                 "units": [{"id": "I1", "group": None, "kind": "step", "state": "failed", "attempt": 1}],
                 "attempts": [{"unit": "I1", "n": 1, "result": "failed",
                                "root_cause_fingerprint": None, "evidence_ref": None}]}
        self._write(state)
        data = self._status()
        self.assertEqual(data["next_skill"], "checkpoint-diagnose")

    def test_work_status_json_failed_with_fingerprint_routes_recover(self):
        """Catches next_skill routing a diagnosed failure to diagnose again instead of recover."""
        state = {**_BASE,
                 "units": [{"id": "I1", "group": None, "kind": "step", "state": "failed", "attempt": 1}],
                 "attempts": [{"unit": "I1", "n": 1, "result": "failed",
                                "root_cause_fingerprint": "test-env-missing", "evidence_ref": None}]}
        self._write(state)
        data = self._status()
        self.assertEqual(data["next_skill"], "checkpoint-recover")
        self.assertIn("retry", data["allowed_events"])

    def test_work_status_json_duplicate_fingerprint_removes_retry(self):
        """Catches retry_permitted not blocking a repeated fingerprint across two attempts."""
        state = {**_BASE, "max_attempts": 3,
                 "units": [{"id": "I1", "group": None, "kind": "step", "state": "failed", "attempt": 2}],
                 "attempts": [
                     {"unit": "I1", "n": 1, "result": "failed",
                      "root_cause_fingerprint": "same-cause", "evidence_ref": None},
                     {"unit": "I1", "n": 2, "result": "failed",
                      "root_cause_fingerprint": "same-cause", "evidence_ref": None},
                 ]}
        self._write(state)
        data = self._status()
        self.assertNotIn("retry", data["allowed_events"])
        for event in ("replan", "supersede", "block"):
            self.assertIn(event, data["allowed_events"])

    def test_work_status_json_attempt_ceiling_removes_retry(self):
        """Catches attempt ceiling not blocking retry when max_attempts is exhausted."""
        state = {**_BASE, "max_attempts": 2,
                 "units": [{"id": "I1", "group": None, "kind": "step", "state": "failed", "attempt": 2}],
                 "attempts": [
                     {"unit": "I1", "n": 1, "result": "failed",
                      "root_cause_fingerprint": "cause-a", "evidence_ref": None},
                     {"unit": "I1", "n": 2, "result": "failed",
                      "root_cause_fingerprint": "cause-b", "evidence_ref": None},
                 ]}
        self._write(state)
        data = self._status()
        self.assertNotIn("retry", data["allowed_events"])

    def test_work_status_json_blocked_routes_recover(self):
        """Catches next_skill not routing a blocked unit to checkpoint-recover."""
        state = {**_BASE,
                 "units": [{"id": "I1", "group": None, "kind": "step", "state": "blocked", "attempt": 1}],
                 "attempts": [{"unit": "I1", "n": 1, "result": "failed",
                                "root_cause_fingerprint": "blocker", "evidence_ref": None}]}
        self._write(state)
        data = self._status()
        self.assertEqual(data["next_skill"], "checkpoint-recover")
        self.assertIn("unblock", data["allowed_events"])

    def test_work_status_json_all_passed_routes_handoff(self):
        """Catches next_skill not routing a completed work package to checkpoint-handoff."""
        state = {**_BASE,
                 "units": [{"id": "I1", "group": None, "kind": "step", "state": "passed", "attempt": 1}],
                 "attempts": [{"unit": "I1", "n": 1, "result": "passed",
                                "root_cause_fingerprint": None, "evidence_ref": None}]}
        self._write(state)
        data = self._status()
        self.assertEqual(data["next_skill"], "checkpoint-handoff")
        self.assertEqual(data["allowed_events"], [])

    def test_work_status_json_gate_unit_running_routes_verify_gate(self):
        """Catches next_skill routing a running gate unit to execute instead of verify-gate."""
        state = {**_BASE, "current_unit": "G1",
                 "units": [{"id": "G1", "group": None, "kind": "gate", "state": "running", "attempt": 1}],
                 "attempts": []}
        self._write(state)
        data = self._status()
        self.assertEqual(data["next_skill"], "checkpoint-verify-gate")
