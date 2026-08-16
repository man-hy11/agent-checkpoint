"""Parse, validate, render, and transition the CURRENT.md work-state block."""

from dataclasses import dataclass, replace
import json
import re

from .storage import ValidationError

BLOCK_BEGIN = "<!-- agent-checkpoint:state v1 -->"
BLOCK_END = "<!-- /agent-checkpoint:state -->"
SCHEMA_VERSION = 1

UNIT_STATES = frozenset(
    {"pending", "ready", "running", "passed", "failed", "blocked", "superseded"}
)
UNIT_KINDS = frozenset({"step", "gate"})
WORK_TYPES = frozenset(
    {
        "project", "feature", "bugfix", "refactor", "upgrade",
        "migration", "performance", "integration", "release", "spike",
    }
)

TRANSITIONS: dict[tuple[str, str], str] = {
    ("ready", "start"): "running",
    ("running", "pass"): "passed",
    ("running", "fail"): "failed",
    ("failed", "retry"): "ready",
    ("failed", "replan"): "superseded",
    ("failed", "supersede"): "superseded",
    ("failed", "block"): "blocked",
    ("blocked", "unblock"): "ready",
}

_BLOCK = re.compile(
    re.escape(BLOCK_BEGIN) + r"\n(?P<body>.*?)\n" + re.escape(BLOCK_END),
    re.S,
)
_WORK_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")


class StateError(ValidationError):
    """A work-state document or transition violates the frozen contract."""


@dataclass(frozen=True)
class Unit:
    id: str
    group: str | None
    kind: str
    state: str
    attempt: int


@dataclass(frozen=True)
class Attempt:
    unit: str
    n: int
    result: str
    root_cause_fingerprint: str | None
    evidence_ref: str | None


@dataclass(frozen=True)
class WorkState:
    schema_version: int
    work_id: str
    work_type: str
    plan_revision: int
    brief_confirmed: bool
    current_unit: str | None
    max_attempts: int
    attempt_override: int | None
    units: tuple[Unit, ...]
    attempts: tuple[Attempt, ...]

    def unit(self, unit_id: str) -> Unit | None:
        """Return the named unit, or None when the plan does not contain it."""
        for candidate in self.units:
            if candidate.id == unit_id:
                return candidate
        return None


def parse_state(text: str) -> WorkState:
    """Read the single delimited state block and validate every invariant."""
    matches = _BLOCK.findall(text)
    if len(matches) != 1:
        raise StateError("CURRENT.md must contain exactly one state block")
    try:
        payload = json.loads(matches[0])
    except json.JSONDecodeError as error:
        raise StateError("state block is not valid JSON") from error
    if not isinstance(payload, dict):
        raise StateError("state block must be a JSON object")
    return _build(payload)


def render_state(text: str, state: WorkState) -> str:
    """Replace the state block in text, preserving every surrounding character."""
    body = json.dumps(_to_payload(state), indent=2, sort_keys=True)
    replacement = f"{BLOCK_BEGIN}\n{body}\n{BLOCK_END}"
    rendered, count = _BLOCK.subn(lambda _: replacement, text, count=1)
    if count != 1:
        raise StateError("CURRENT.md must contain exactly one state block")
    return rendered


def apply_event(
    state: WorkState, unit_id: str, event: str, plan_revision: int
) -> WorkState:
    """Return a new state with one legal transition applied, or raise."""
    if plan_revision != state.plan_revision:
        raise StateError(
            f"stale plan revision {plan_revision}; tracker holds {state.plan_revision}"
        )
    unit = state.unit(unit_id)
    if unit is None:
        raise StateError(f"unknown unit: {unit_id}")
    target = TRANSITIONS.get((unit.state, event))
    if target is None:
        raise StateError(f"illegal transition: {unit.state} --{event}--> ?")
    attempt = unit.attempt + 1 if event == "start" else unit.attempt
    updated = replace(unit, state=target, attempt=attempt)
    units = tuple(updated if item.id == unit_id else item for item in state.units)
    return replace(state, units=units)


def _build(payload: dict) -> WorkState:
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        raise StateError(f"unsupported state schema version: {version!r}")

    work_id = payload.get("work_id")
    if not isinstance(work_id, str) or not _WORK_ID.fullmatch(work_id):
        raise StateError("work_id must use lowercase letters, digits, and hyphens")

    work_type = payload.get("work_type")
    if work_type not in WORK_TYPES:
        raise StateError(f"unknown work type: {work_type!r}")

    plan_revision = _positive_int(payload.get("plan_revision"), "plan_revision")
    max_attempts = _positive_int(payload.get("max_attempts"), "max_attempts")

    brief_confirmed = payload.get("brief_confirmed")
    if not isinstance(brief_confirmed, bool):
        raise StateError("brief_confirmed must be a boolean")

    override = payload.get("attempt_override")
    if override is not None:
        override = _positive_int(override, "attempt_override")

    units = tuple(_unit(item) for item in _sequence(payload.get("units"), "units"))
    identifiers = [unit.id for unit in units]
    if len(set(identifiers)) != len(identifiers):
        raise StateError("unit ids must be unique")
    if sum(1 for unit in units if unit.state == "running") > 1:
        raise StateError("at most one unit may be running")

    current = payload.get("current_unit")
    if current is None:
        if units:
            raise StateError("current_unit is required while units exist")
    elif current not in identifiers:
        raise StateError(f"current_unit {current!r} is not a planned unit")

    attempts = tuple(
        _attempt(item, identifiers)
        for item in _sequence(payload.get("attempts"), "attempts")
    )

    return WorkState(
        schema_version=SCHEMA_VERSION,
        work_id=work_id,
        work_type=work_type,
        plan_revision=plan_revision,
        brief_confirmed=brief_confirmed,
        current_unit=current,
        max_attempts=max_attempts,
        attempt_override=override,
        units=units,
        attempts=attempts,
    )


def _unit(item: object) -> Unit:
    if not isinstance(item, dict):
        raise StateError("each unit must be a JSON object")
    identifier = item.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise StateError("unit id must be a non-empty string")
    group = item.get("group")
    if group is not None and (not isinstance(group, str) or not group):
        raise StateError("unit group must be null or a non-empty string")
    kind = item.get("kind")
    if kind not in UNIT_KINDS:
        raise StateError(f"unknown unit kind: {kind!r}")
    state = item.get("state")
    if state not in UNIT_STATES:
        raise StateError(f"unknown unit state: {state!r}")
    attempt = item.get("attempt")
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 0:
        raise StateError("unit attempt must be a non-negative integer")
    return Unit(id=identifier, group=group, kind=kind, state=state, attempt=attempt)


def _attempt(item: object, identifiers: list[str]) -> Attempt:
    if not isinstance(item, dict):
        raise StateError("each attempt must be a JSON object")
    unit = item.get("unit")
    if unit not in identifiers:
        raise StateError(f"attempt references unknown unit: {unit!r}")
    number = _positive_int(item.get("n"), "attempt n")
    result = item.get("result")
    if result not in ("passed", "failed"):
        raise StateError(f"unknown attempt result: {result!r}")
    fingerprint = item.get("root_cause_fingerprint")
    if fingerprint is not None and not isinstance(fingerprint, str):
        raise StateError("root_cause_fingerprint must be null or a string")
    reference = item.get("evidence_ref")
    if reference is not None and not isinstance(reference, str):
        raise StateError("evidence_ref must be null or a string")
    return Attempt(
        unit=unit,
        n=number,
        result=result,
        root_cause_fingerprint=fingerprint,
        evidence_ref=reference,
    )


def _sequence(value: object, label: str) -> list:
    if not isinstance(value, list):
        raise StateError(f"{label} must be a JSON array")
    return value


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise StateError(f"{label} must be an integer of at least 1")
    return value


def _to_payload(state: WorkState) -> dict:
    return {
        "schema_version": state.schema_version,
        "work_id": state.work_id,
        "work_type": state.work_type,
        "plan_revision": state.plan_revision,
        "brief_confirmed": state.brief_confirmed,
        "current_unit": state.current_unit,
        "max_attempts": state.max_attempts,
        "attempt_override": state.attempt_override,
        "units": [
            {
                "id": unit.id,
                "group": unit.group,
                "kind": unit.kind,
                "state": unit.state,
                "attempt": unit.attempt,
            }
            for unit in state.units
        ],
        "attempts": [
            {
                "unit": attempt.unit,
                "n": attempt.n,
                "result": attempt.result,
                "root_cause_fingerprint": attempt.root_cause_fingerprint,
                "evidence_ref": attempt.evidence_ref,
            }
            for attempt in state.attempts
        ],
    }
