"""Work-state parsing, rendering, and transition tests."""

from dataclasses import replace
import unittest

from agent_checkpoint.work_state import (
    StateError,
    Unit,
    WorkState,
    apply_event,
    parse_state,
    render_state,
)


def document(block: str) -> str:
    return (
        "# CURRENT.md\n\nHuman prose above.\n\n"
        "<!-- agent-checkpoint:state v1 -->\n"
        f"{block}\n"
        "<!-- /agent-checkpoint:state -->\n\n"
        "Human prose below.\n"
    )


VALID_BLOCK = """{
  "schema_version": 1,
  "work_id": "demo",
  "work_type": "performance",
  "plan_revision": 5,
  "brief_confirmed": true,
  "current_unit": "P3",
  "max_attempts": 3,
  "attempt_override": null,
  "units": [
    {"id": "P3", "group": null, "kind": "step", "state": "ready", "attempt": 0},
    {"id": "PG", "group": null, "kind": "gate", "state": "pending", "attempt": 0}
  ],
  "attempts": []
}"""


class ParseTests(unittest.TestCase):
    def test_parse_reads_every_declared_field(self):
        """Catches a state parser silently dropping contract fields."""
        state = parse_state(document(VALID_BLOCK))

        self.assertEqual(state.work_id, "demo")
        self.assertEqual(state.work_type, "performance")
        self.assertEqual(state.plan_revision, 5)
        self.assertTrue(state.brief_confirmed)
        self.assertEqual(state.current_unit, "P3")
        self.assertEqual(state.max_attempts, 3)
        self.assertIsNone(state.attempt_override)
        self.assertEqual(len(state.units), 2)
        self.assertEqual(state.unit("PG").kind, "gate")

    def test_parse_rejects_missing_block(self):
        """Catches a parser treating a package without state as empty state."""
        with self.assertRaises(StateError):
            parse_state("# CURRENT.md\n\nNo state block here.\n")

    def test_parse_rejects_two_running_units(self):
        """Catches concurrent claims producing two simultaneous current units."""
        block = VALID_BLOCK.replace(
            '{"id": "P3", "group": null, "kind": "step", "state": "ready", "attempt": 0}',
            '{"id": "P3", "group": null, "kind": "step", "state": "running", "attempt": 1}',
        ).replace(
            '{"id": "PG", "group": null, "kind": "gate", "state": "pending", "attempt": 0}',
            '{"id": "PG", "group": null, "kind": "gate", "state": "running", "attempt": 1}',
        )

        with self.assertRaises(StateError):
            parse_state(document(block))

    def test_parse_rejects_unknown_schema_version(self):
        """Catches a future state block being read with v1 semantics."""
        block = VALID_BLOCK.replace('"schema_version": 1', '"schema_version": 2')

        with self.assertRaises(StateError):
            parse_state(document(block))

    def test_parse_rejects_current_unit_absent_from_units(self):
        """Catches a tracker pointing at a unit the plan does not contain."""
        block = VALID_BLOCK.replace('"current_unit": "P3"', '"current_unit": "P9"')

        with self.assertRaises(StateError):
            parse_state(document(block))

    def test_parse_rejects_duplicate_unit_ids(self):
        """Catches a replan appending a unit id that already exists."""
        block = VALID_BLOCK.replace('"id": "PG"', '"id": "P3"')

        with self.assertRaises(StateError):
            parse_state(document(block))


class RenderTests(unittest.TestCase):
    def test_render_preserves_prose_outside_the_block(self):
        """Catches a renderer discarding human-authored tracker sections."""
        source = document(VALID_BLOCK)

        rendered = render_state(source, parse_state(source))

        self.assertIn("Human prose above.", rendered)
        self.assertIn("Human prose below.", rendered)

    def test_render_round_trips_identically(self):
        """Catches nondeterministic rendering breaking byte-identical writes."""
        source = document(VALID_BLOCK)
        state = parse_state(source)

        once = render_state(source, state)
        twice = render_state(once, parse_state(once))

        self.assertEqual(once, twice)


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.state = parse_state(document(VALID_BLOCK))

    def test_start_moves_ready_to_running_and_increments_attempt(self):
        """Catches a claim that fails to record which attempt is executing."""
        result = apply_event(self.state, "P3", "start", plan_revision=5)

        self.assertEqual(result.unit("P3").state, "running")
        self.assertEqual(result.unit("P3").attempt, 1)

    def test_fail_then_direct_restart_is_rejected(self):
        """Catches a failed unit being rerun without an explicit recovery decision."""
        running = apply_event(self.state, "P3", "start", plan_revision=5)
        failed = apply_event(running, "P3", "fail", plan_revision=5)

        with self.assertRaises(StateError):
            apply_event(failed, "P3", "start", plan_revision=5)

    def test_retry_returns_failed_unit_to_ready(self):
        """Catches recovery losing the retry path back into execution."""
        running = apply_event(self.state, "P3", "start", plan_revision=5)
        failed = apply_event(running, "P3", "fail", plan_revision=5)

        retried = apply_event(failed, "P3", "retry", plan_revision=5)

        self.assertEqual(retried.unit("P3").state, "ready")

    def test_replan_supersedes_without_deleting_the_unit(self):
        """Catches a replan erasing audit history of the superseded unit."""
        running = apply_event(self.state, "P3", "start", plan_revision=5)
        failed = apply_event(running, "P3", "fail", plan_revision=5)

        replanned = apply_event(failed, "P3", "replan", plan_revision=5)

        self.assertEqual(replanned.unit("P3").state, "superseded")
        self.assertIsNotNone(replanned.unit("P3"))

    def test_start_moves_pending_to_running_and_increments_attempt(self):
        """Catches BUG.md Bug 3: a unit left `pending` by workflow
        initialization (the normal state for every non-first unit) must be
        startable directly, mirroring the existing `ready` -> `running`
        path, without requiring a manual state-block edit."""
        result = apply_event(self.state, "PG", "start", plan_revision=5)

        self.assertEqual(result.unit("PG").state, "running")
        self.assertEqual(result.unit("PG").attempt, 1)

    def test_ready_to_running_path_is_unaffected_by_the_pending_addition(self):
        """Regression guard: adding ("pending", "start") must not change
        the pre-existing ("ready", "start") behavior."""
        result = apply_event(self.state, "P3", "start", plan_revision=5)

        self.assertEqual(result.unit("P3").state, "running")
        self.assertEqual(result.unit("P3").attempt, 1)

    def test_running_unit_cannot_be_started_again(self):
        """Catches the new pending-start entry over-broadening start beyond
        pending/ready into an already-running unit."""
        running = apply_event(self.state, "P3", "start", plan_revision=5)

        with self.assertRaises(StateError):
            apply_event(running, "P3", "start", plan_revision=5)

    def test_stale_plan_revision_is_rejected(self):
        """Catches a session planned against a superseded graph passing work."""
        with self.assertRaises(StateError):
            apply_event(self.state, "P3", "start", plan_revision=4)

    def test_invalid_transition_leaves_state_object_unchanged(self):
        """Catches a rejected transition partially mutating state."""
        before = self.state

        with self.assertRaises(StateError):
            apply_event(before, "P3", "pass", plan_revision=5)

        self.assertEqual(before.unit("P3").state, "ready")
        self.assertEqual(before.unit("P3").attempt, 0)


def _state_with_units(*states: str) -> WorkState:
    units = tuple(
        Unit(id=f"U{index}", group=None, kind="step", state=state, attempt=0)
        for index, state in enumerate(states, start=1)
    )
    return WorkState(
        schema_version=1,
        work_id="demo",
        work_type="performance",
        plan_revision=1,
        brief_confirmed=True,
        current_unit=units[0].id if units else None,
        max_attempts=3,
        attempt_override=None,
        units=units,
        attempts=(),
    )


class IsCompleteTests(unittest.TestCase):
    def test_all_passed_is_complete(self):
        """Catches the common terminal case (every unit passed) reporting incomplete."""
        state = _state_with_units("passed", "passed")

        self.assertTrue(state.is_complete())

    def test_passed_and_superseded_mix_with_one_passed_is_complete(self):
        """Catches chain-v1.md Row 4's superseded-counts-as-resolved rule being dropped."""
        state = _state_with_units("passed", "superseded")

        self.assertTrue(state.is_complete())

    def test_all_superseded_with_none_passed_is_not_complete(self):
        """Catches a package that superseded every unit without ever passing one
        being treated as having finished work."""
        state = _state_with_units("superseded", "superseded")

        self.assertFalse(state.is_complete())

    def test_any_non_terminal_unit_is_not_complete(self):
        """Catches a still-pending/running/failed/blocked unit being ignored."""
        for state_name in ("pending", "ready", "running", "failed", "blocked"):
            with self.subTest(state=state_name):
                state = _state_with_units("passed", state_name)

                self.assertFalse(state.is_complete())

    def test_empty_units_is_not_complete(self):
        """Catches an empty unit list crashing or reporting complete."""
        state = replace(_state_with_units("passed"), units=(), current_unit=None)

        self.assertFalse(state.is_complete())


if __name__ == "__main__":
    unittest.main()
