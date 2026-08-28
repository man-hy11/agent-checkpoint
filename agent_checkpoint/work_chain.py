"""Derive the next skill and the legal events from work state. Pure functions."""

from .work_state import TRANSITIONS, WorkState

SKILLS: tuple[str, ...] = (
    "checkpoint",
    "checkpoint-select-workflow",
    "checkpoint-brainstorm",
    "checkpoint-plan",
    "checkpoint-claim",
    "checkpoint-execute",
    "checkpoint-verify-gate",
    "checkpoint-evidence",
    "checkpoint-diagnose",
    "checkpoint-recover",
    "checkpoint-handoff",
    "checkpoint-inspect",
)


def next_skill(state: WorkState | None) -> str:
    """Return the single skill permitted to act next, per contracts/chain-v1.md."""
    if state is None:
        return "checkpoint-select-workflow"
    if not state.brief_confirmed:
        return "checkpoint-brainstorm"
    if not state.units:
        return "checkpoint-plan"
    if all(unit.state in ("passed", "superseded") for unit in state.units) and any(
        unit.state == "passed" for unit in state.units
    ):
        return "checkpoint-handoff"

    unit = state.unit(state.current_unit) if state.current_unit else None
    if unit is None:
        return "checkpoint-plan"
    if unit.state == "passed":
        return "checkpoint-plan"
    if unit.state == "superseded":
        return "checkpoint-plan"
    if unit.state == "blocked":
        return "checkpoint-recover"
    if unit.state == "failed":
        if _diagnosis(state, unit.id, unit.attempt) is None:
            return "checkpoint-diagnose"
        return "checkpoint-recover"
    if unit.state in ("pending", "ready"):
        return "checkpoint-claim"
    if unit.state == "running":
        return "checkpoint-verify-gate" if unit.kind == "gate" else "checkpoint-execute"
    return "checkpoint-handoff"


def allowed_events(state: WorkState) -> tuple[str, ...]:
    """Return the legal events for the current unit, minus guard refusals."""
    unit = state.unit(state.current_unit) if state.current_unit else None
    if unit is None:
        return ()
    events = [
        event for (source, event) in TRANSITIONS if source == unit.state
    ]
    if "retry" in events and not retry_permitted(state, unit.id):
        events.remove("retry")
    return tuple(sorted(events))


def retry_permitted(state: WorkState, unit_id: str) -> bool:
    """Return False when retrying would repeat a failure without new information."""
    attempts = [item for item in state.attempts if item.unit == unit_id]
    if not attempts:
        return True
    limit = state.attempt_override or state.max_attempts
    if len(attempts) >= limit:
        return False
    latest = attempts[-1].root_cause_fingerprint
    if latest is None:
        return False
    if len(attempts) >= 2 and attempts[-2].root_cause_fingerprint == latest:
        return False
    return True


def _diagnosis(state: WorkState, unit_id: str, attempt: int) -> str | None:
    for item in state.attempts:
        if item.unit == unit_id and item.n == attempt:
            return item.root_cause_fingerprint
    return None
