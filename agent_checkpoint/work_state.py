"""Parse, validate, render, and transition the CURRENT.md work-state block."""

from dataclasses import dataclass, replace
import json
import re

from .storage import ValidationError

BLOCK_BEGIN = "<!-- agent-checkpoint:state v1 -->"
BLOCK_END = "<!-- /agent-checkpoint:state -->"
SCHEMA_VERSION = 1
DEFAULT_MAX_ATTEMPTS = 3

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
    ("pending", "start"): "running",
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

    def is_complete(self) -> bool:
        """Return True iff the package has finished all its work (chain-v1.md Row 4).

        Every unit must be ``passed`` or ``superseded``, and at least one unit
        must be ``passed`` — a package that superseded all of its own units
        without ever passing one has not finished any work. An empty
        ``units`` tuple returns False rather than raising: no units passed
        means the "at least one passed" clause is unmet.
        """
        if not self.units:
            return False
        if any(unit.state not in ("passed", "superseded") for unit in self.units):
            return False
        return any(unit.state == "passed" for unit in self.units)


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
    """Replace the state block in text, then resync the tracker's prose.

    The state block is machine-read; the "Current Target" heading and the step
    checkboxes below it are what a person reads after a compaction. They are two
    halves of one file and must not disagree, so both are written together here
    rather than left to the agent.
    """
    body = json.dumps(_to_payload(state), indent=2, sort_keys=True)
    replacement = f"{BLOCK_BEGIN}\n{body}\n{BLOCK_END}"
    rendered, count = _BLOCK.subn(lambda _: replacement, text, count=1)
    if count != 1:
        raise StateError("CURRENT.md must contain exactly one state block")
    return _render_tracker_prose(rendered, state)


# `- [x] R2 Unwrap core/ (step)` -> marker, id, and the title that follows it.
_STEP_LINE = re.compile(r"(?m)^- \[(?P<marker>.)\] (?P<id>\S+)(?P<rest>.*)$")

_STATE_MARKERS = {
    "passed": "x",
    "superseded": "x",   # terminal and resolved, like passed
    "running": "-",
    "blocked": "!",
}


def _render_tracker_prose(text: str, state: WorkState) -> str:
    """Resync the Current Target heading and step checkboxes with the state block.

    Both are rewritten from the step list already in the file, so unit titles
    survive without being duplicated into the state block. A tracker whose prose
    does not follow the documented shape is left alone rather than guessed at.
    """
    titles: dict[str, str] = {}

    def _remark(match: re.Match[str]) -> str:
        unit = state.unit(match.group("id"))
        if unit is None:
            return match.group(0)
        titles[unit.id] = match.group("rest").strip()
        marker = _STATE_MARKERS.get(unit.state, " ")
        return f"- [{marker}] {unit.id}{match.group('rest')}"

    rendered = _STEP_LINE.sub(_remark, text)

    current = state.unit(state.current_unit) if state.current_unit else None
    if current is None or current.id not in titles:
        return rendered
    title = titles[current.id].removesuffix(f"({current.kind})").strip()
    heading = f"**{current.id} — {title}**" if title else f"**{current.id}**"
    # Anchored to the "## Current Target" heading rather than to the first bold
    # line in the file, so a tracker with bold text elsewhere is not rewritten.
    return re.sub(
        r"(?ms)(^## Current Target\s*\n\n)\*\*.+?\*\*",
        lambda match: match.group(1) + heading,
        rendered,
        count=1,
    )


def initial_state(work_id: str, work_type: str) -> WorkState:
    """Return the state a brand-new work package starts from.

    No plan exists yet, so ``units`` is empty and ``current_unit`` is None —
    chain-v1 then routes the package to checkpoint-brainstorm (Row 2, the brief
    is unconfirmed) and on to checkpoint-plan (Row 3, no units).
    """
    return WorkState(
        schema_version=SCHEMA_VERSION,
        work_id=work_id,
        work_type=work_type,
        plan_revision=1,
        brief_confirmed=False,
        current_unit=None,
        max_attempts=DEFAULT_MAX_ATTEMPTS,
        attempt_override=None,
        units=(),
        attempts=(),
    )


def render_initial_block(work_id: str, work_type: str) -> str:
    """Serialize a new package's state block, delimiters included.

    Package creation writes this rather than carrying a block in each of the ten
    bundled CURRENT_TEMPLATE.md files: one generator cannot drift from the
    parser, ten hand-maintained copies can, and the templates' prose belongs to
    the work type rather than to the schema.
    """
    body = json.dumps(_to_payload(initial_state(work_id, work_type)), indent=2, sort_keys=True)
    return f"{BLOCK_BEGIN}\n{body}\n{BLOCK_END}"


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
    if event == "pass":
        return replace(state, units=units, current_unit=_next_unit(units, state.current_unit))
    return replace(state, units=units)


def _next_unit(units: tuple[Unit, ...], current: str | None) -> str | None:
    """Return the unit the tracker should point at once one has passed.

    Only ``pass`` advances: ``fail`` must leave the pointer on the unit that
    still needs recovery, and ``start`` must not move it either, since a unit is
    started only after the pointer already names it. That split is the contract
    generated packages already state — "update CURRENT.md only after verified
    PASS", "FAIL does not advance", and "Advancing Current Target does not
    authorize beginning it in this invocation" (``work_renderer``).

    The next unit is the first in declaration order that is neither ``passed``
    nor ``superseded`` — both are terminal, so neither can be returned to. When
    every unit is resolved the pointer is left alone: chain-v1 Row 4 precedes
    the current-unit rows, so a finished package routes to checkpoint-handoff
    regardless of what current_unit still names.
    """
    for unit in units:
        if unit.state not in ("passed", "superseded"):
            return unit.id
    return current


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
