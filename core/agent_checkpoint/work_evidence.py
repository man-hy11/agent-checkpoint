"""Parse evidence documents and judge them against manifest requirements."""

from dataclasses import dataclass
import re

from .progress import contains_diff_content
from .secrets import find_secret_kind
from .storage import ValidationError

MAX_EVIDENCE_CHARS = 8000

_UNIT = re.compile(r"(?m)^##\s*Unit:\s*(?P<unit>\S+)\s*$")
_ATTEMPT = re.compile(r"(?m)^##\s*Attempt:\s*(?P<attempt>\d+)\s*$")
_SECTION = re.compile(r"(?m)^###\s*(?P<key>[a-z0-9_]+)\s*$")


class EvidenceError(ValidationError):
    """An evidence document cannot be parsed at all."""


@dataclass(frozen=True)
class EvidenceDocument:
    unit: str
    attempt: int
    sections: dict[str, str]


def parse_evidence(text: str) -> EvidenceDocument:
    """Read unit attribution, attempt number, and H3 sections from evidence."""
    unit_match = _UNIT.search(text)
    attempt_match = _ATTEMPT.search(text)
    if unit_match is None:
        raise EvidenceError("evidence is missing a '## Unit:' line")
    if attempt_match is None:
        raise EvidenceError("evidence is missing an '## Attempt:' line")

    sections: dict[str, str] = {}
    matches = list(_SECTION.finditer(text))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group("key")] = text[start:end].strip()

    return EvidenceDocument(
        unit=unit_match.group("unit"),
        attempt=int(attempt_match.group("attempt")),
        sections=sections,
    )


def validate_evidence(
    text: str, *, unit_id: str, required: tuple[str, ...]
) -> tuple[str, ...]:
    """Return every unmet requirement; an empty tuple means the evidence is adequate."""
    unmet: list[str] = []

    if len(text) > MAX_EVIDENCE_CHARS:
        unmet.append("length")
    if find_secret_kind(text) is not None:
        unmet.append("secret_detected")
    if contains_diff_content(text):
        unmet.append("diff_content")

    try:
        document = parse_evidence(text)
    except EvidenceError:
        return tuple(sorted(set(unmet + ["unit_attribution"] + list(required))))

    if document.unit != unit_id:
        unmet.append("unit_attribution")
    for key in required:
        if not document.sections.get(key):
            unmet.append(key)

    return tuple(sorted(set(unmet)))
