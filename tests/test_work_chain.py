"""Chain routing and no-progress guard tests."""

import unittest

from agent_checkpoint.work_chain import (
    SKILLS,
    allowed_events,
    next_skill,
    retry_permitted,
)
from agent_checkpoint.work_state import Attempt, Unit, WorkState


def state(**overrides) -> WorkState:
    base = dict(
        schema_version=1,
        work_id="demo",
        work_type="performance",
        plan_revision=5,
        brief_confirmed=True,
        current_unit="P3",
        max_attempts=3,
        attempt_override=None,
        units=(Unit("P3", None, "step", "ready", 0),),
        attempts=(),
    )
    base.update(overrides)
    return WorkState(**base)


def unit(unit_state: str, kind: str = "step", attempt: int = 0) -> tuple[Unit, ...]:
    return (Unit("P3", None, kind, unit_state, attempt),)


def failure(n: int, fingerprint: str | None) -> Attempt:
    return Attempt("P3", n, "failed", fingerprint, f"EVIDENCE.md#p3-a{n}")


class NextSkillTests(unittest.TestCase):
    def test_absent_state_routes_to_workflow_selection(self):
        """Catches a fresh project being routed into planning before type choice."""
        self.assertEqual(next_skill(None), "checkpoint-select-workflow")

    def test_unconfirmed_brief_routes_to_brainstorm(self):
        """Catches planning starting before goal and scope are confirmed."""
        self.assertEqual(
            next_skill(state(brief_confirmed=False)), "checkpoint-brainstorm"
        )

    def test_empty_units_route_to_plan(self):
        """Catches a confirmed brief stalling with no decomposition step."""
        self.assertEqual(
            next_skill(state(units=(), current_unit=None)), "checkpoint-plan"
        )

    def test_ready_unit_routes_to_claim(self):
        """Catches execution beginning without claiming the unit first."""
        self.assertEqual(next_skill(state(units=unit("ready"))), "checkpoint-claim")

    def test_running_step_routes_to_execute(self):
        """Catches a claimed step failing to reach the execution skill."""
        self.assertEqual(next_skill(state(units=unit("running", attempt=1))), "checkpoint-execute")

    def test_running_gate_routes_to_verify_gate(self):
        """Catches a gate being implemented rather than verified."""
        self.assertEqual(
            next_skill(state(units=unit("running", kind="gate", attempt=1))),
            "checkpoint-verify-gate",
        )

    def test_failed_without_diagnosis_routes_to_diagnose(self):
        """Catches a recovery decision being made before root-cause analysis."""
        result = next_skill(
            state(units=unit("failed", attempt=1), attempts=(failure(1, None),))
        )

        self.assertEqual(result, "checkpoint-diagnose")

    def test_failed_with_diagnosis_routes_to_recover(self):
        """Catches diagnosis looping forever instead of forcing a decision."""
        result = next_skill(
            state(units=unit("failed", attempt=1), attempts=(failure(1, "a3f9"),))
        )

        self.assertEqual(result, "checkpoint-recover")

    def test_blocked_routes_to_recover(self):
        """Catches a blocked unit having no route back into the workflow."""
        self.assertEqual(next_skill(state(units=unit("blocked", attempt=1))), "checkpoint-recover")

    def test_superseded_routes_to_plan(self):
        """Catches a superseded unit leaving the package without a next action."""
        self.assertEqual(next_skill(state(units=unit("superseded", attempt=1))), "checkpoint-plan")

    def test_all_passed_routes_to_handoff(self):
        """Catches completed work failing to terminate at a handoff."""
        self.assertEqual(next_skill(state(units=unit("passed", attempt=1))), "checkpoint-handoff")

    def test_passed_and_superseded_mix_routes_to_handoff(self):
        """Catches BUG.md Bug 4: a package with a superseded unit (a normal,
        resolved re-planning outcome, not a failure) must still reach
        checkpoint-handoff once every other unit is passed — superseded
        must not block completion forever."""
        current = state(
            units=(
                Unit("P1", None, "step", "passed", 1),
                Unit("P2", None, "step", "superseded", 1),
                Unit("P3", None, "step", "passed", 2),
                Unit("Gate", None, "gate", "passed", 2),
            ),
            current_unit="Gate",
        )
        self.assertEqual(next_skill(current), "checkpoint-handoff")

    def test_all_superseded_does_not_route_to_handoff(self):
        """Catches the completion check treating superseded as sufficient on
        its own: a package where every unit was superseded and nothing was
        ever passed has not actually finished any work and must not be
        reported complete."""
        current = state(
            units=(
                Unit("P1", None, "step", "superseded", 1),
                Unit("P2", None, "step", "superseded", 1),
            ),
            current_unit="P1",
        )
        self.assertNotEqual(next_skill(current), "checkpoint-handoff")

    def test_passed_current_unit_with_pending_sibling_routes_to_plan(self):
        """Catches BUG.md Bug 1: a stale current_unit pointing at an
        already-passed unit while a sibling is still pending must not fall
        through to checkpoint-handoff (which would falsely signal the whole
        package is complete)."""
        current = state(
            units=(
                Unit("P1", None, "step", "passed", 1),
                Unit("P2", None, "step", "pending", 0),
            ),
            current_unit="P1",
        )
        self.assertEqual(next_skill(current), "checkpoint-plan")

    def test_all_passed_still_wins_over_passed_current_unit_row(self):
        """Catches the new row 6 (passed-but-stale) shadowing row 4
        (uniformly passed) when both could otherwise match — row 4 must be
        checked first and terminate at handoff."""
        current = state(units=unit("passed", attempt=1), current_unit="P3")
        self.assertEqual(next_skill(current), "checkpoint-handoff")

    def test_evidence_and_inspect_are_never_routed_to(self):
        """Catches the chain advertising skills that must be reached another way."""
        combinations = [
            state(units=unit(value, kind=kind, attempt=1))
            for value in ("pending", "ready", "running", "passed", "failed", "blocked", "superseded")
            for kind in ("step", "gate")
        ]

        results = {next_skill(item) for item in combinations}

        self.assertNotIn("checkpoint-evidence", results)
        self.assertNotIn("checkpoint-inspect", results)

    def test_every_routed_skill_is_a_declared_skill(self):
        """Catches a typo producing a skill name no runtime installs."""
        combinations = [None] + [
            state(units=unit(value, kind=kind, attempt=1))
            for value in ("pending", "ready", "running", "passed", "failed", "blocked", "superseded")
            for kind in ("step", "gate")
        ]

        for item in combinations:
            with self.subTest(item=item):
                self.assertIn(next_skill(item), SKILLS)


class NoProgressTests(unittest.TestCase):
    def test_retry_permitted_after_a_single_distinct_failure(self):
        """Catches the guard blocking a legitimate first retry."""
        current = state(units=unit("failed", attempt=1), attempts=(failure(1, "a3f9"),))

        self.assertTrue(retry_permitted(current, "P3"))

    def test_repeated_fingerprint_refuses_retry(self):
        """Catches an agent looping on the same root cause indefinitely."""
        current = state(
            units=unit("failed", attempt=2),
            attempts=(failure(1, "a3f9"), failure(2, "a3f9")),
        )

        self.assertFalse(retry_permitted(current, "P3"))

    def test_max_attempts_refuses_retry(self):
        """Catches the attempt ceiling being ignored when causes differ."""
        current = state(
            units=unit("failed", attempt=3),
            attempts=(failure(1, "a"), failure(2, "b"), failure(3, "c")),
        )

        self.assertFalse(retry_permitted(current, "P3"))

    def test_override_raises_the_ceiling(self):
        """Catches a recorded user authority being silently ignored."""
        current = state(
            units=unit("failed", attempt=3),
            attempt_override=5,
            attempts=(failure(1, "a"), failure(2, "b"), failure(3, "c")),
        )

        self.assertTrue(retry_permitted(current, "P3"))

    def test_refused_retry_still_allows_replan_block_and_supersede(self):
        """Catches the guard stranding a unit with no legal event at all."""
        current = state(
            units=unit("failed", attempt=2),
            attempts=(failure(1, "a3f9"), failure(2, "a3f9")),
        )

        events = allowed_events(current)

        self.assertNotIn("retry", events)
        self.assertIn("replan", events)
        self.assertIn("supersede", events)
        self.assertIn("block", events)


if __name__ == "__main__":
    unittest.main()
