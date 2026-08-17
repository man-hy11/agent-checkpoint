# tests/test_runners.py
"""Stub runner tests: runner uses work status --json, never agent prose (R5-I9)."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import PROJECT_ROOT

_RUNNER_PATH = PROJECT_ROOT / "examples" / "runners" / "run_once.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_once", _RUNNER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_status(state: str, next_skill: str, allowed: list | None = None) -> dict:
    return {
        "current_unit": "I1",
        "state": state,
        "next_skill": next_skill,
        "allowed_events": allowed or [],
        "work_id": "pkg",
        "work_type": "feature",
    }


class StubRunnerTests(unittest.TestCase):
    def setUp(self):
        self.runner = _load_runner()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _run(self, status_return):
        with mock.patch.object(self.runner, "_work_status", return_value=status_return):
            return self.runner.run_once(self.root, ["agent-checkpoint"])

    def test_runner_exits_zero_on_ready_unit(self):
        """Catches runner exiting nonzero on a ready unit that still needs claiming."""
        code = self._run(_make_status("ready", "checkpoint-claim", ["start"]))
        self.assertEqual(code, 0)

    def test_runner_exits_zero_on_running_unit(self):
        """Catches runner exiting nonzero while a unit is actively running."""
        code = self._run(_make_status("running", "checkpoint-execute", ["pass", "fail"]))
        self.assertEqual(code, 0)

    def test_runner_exits_one_on_failed_unit(self):
        """Catches runner not stopping when a unit fails."""
        code = self._run(_make_status("failed", "checkpoint-recover", ["replan", "supersede", "block"]))
        self.assertEqual(code, 1)

    def test_runner_exits_one_on_blocked_unit(self):
        """Catches runner not stopping on a blocked unit requiring recovery."""
        code = self._run(_make_status("blocked", "checkpoint-recover", ["unblock"]))
        self.assertEqual(code, 1)

    def test_runner_exits_two_on_all_passed(self):
        """Catches runner not detecting a completed work package."""
        code = self._run(_make_status("passed", "checkpoint-handoff", []))
        self.assertEqual(code, 2)

    def test_runner_exits_one_when_no_package_found(self):
        """Catches runner not handling a missing work package gracefully."""
        code = self._run(None)
        self.assertEqual(code, 1)

    def test_runner_never_parses_stderr_prose(self):
        """Catches runner relying on stderr text rather than --json stdout."""
        status = _make_status("ready", "checkpoint-claim", ["start"])
        status["current_unit"] = "unit\twith\ttabs"
        code = self._run(status)
        self.assertEqual(code, 0)

    def test_runner_stops_on_failed_regardless_of_next_skill(self):
        """Catches runner not stopping when state=failed and next_skill=checkpoint-diagnose."""
        code = self._run(_make_status("failed", "checkpoint-diagnose", []))
        self.assertEqual(code, 1)
