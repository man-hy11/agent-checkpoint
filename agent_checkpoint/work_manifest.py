"""Load and validate workflow.json manifests. Pure apart from bundled-asset reads."""

from dataclasses import dataclass
import json
from pathlib import Path

from .storage import ValidationError

_ASSET_ROOT = Path(__file__).with_name("assets") / "development-templates"

REQUIRED_KEYS = (
    "schema_version",
    "type",
    "unit_prefix",
    "grouped",
    "max_attempts",
    "hard_rules",
    "artifacts",
    "evidence_required",
    "default_units",
)
ARTIFACT_POLICIES = ("required", "optional", "omitted", "generated")
BASE_ARTIFACTS = (
    "BRIEF.md",
    "PROJECT_CONTEXT.md",
    "DESIGN.md",
    "PLAN.md",
    "CURRENT.md",
    "CONTINUE_PROMPT.md",
    "EVIDENCE.md",
    "RULES.md",
)
_ALWAYS_REQUIRED = (
    "BRIEF.md",
    "PLAN.md",
    "CURRENT.md",
    "CONTINUE_PROMPT.md",
    "EVIDENCE.md",
)
_EVIDENCE_KINDS = ("step", "gate")


class ManifestError(ValidationError):
    """A workflow.json manifest is missing a key or holds an invalid value."""


@dataclass(frozen=True)
class WorkflowManifest:
    schema_version: int
    type: str
    unit_prefix: str
    grouped: bool
    max_attempts: int
    hard_rules: tuple[str, ...]
    artifacts: dict
    evidence_required: dict
    default_units: tuple[str, ...]


def parse_manifest(text: str) -> WorkflowManifest:
    """Parse and validate manifest JSON text against contracts/manifest-v1.json."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ManifestError(f"manifest is not valid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ManifestError("manifest must be a JSON object")

    missing = [key for key in REQUIRED_KEYS if key not in payload]
    if missing:
        raise ManifestError(f"manifest is missing keys: {', '.join(sorted(missing))}")

    artifacts = payload["artifacts"]
    if not isinstance(artifacts, dict) or not artifacts:
        raise ManifestError("manifest 'artifacts' must be a non-empty object")
    missing_base = [name for name in _ALWAYS_REQUIRED if name not in artifacts]
    if missing_base:
        raise ManifestError(
            f"manifest 'artifacts' is missing always-required entries: "
            f"{', '.join(sorted(missing_base))}"
        )
    if artifacts.get("RULES.md") != "generated":
        raise ManifestError("manifest 'artifacts' must declare RULES.md as 'generated'")
    for name, policy in artifacts.items():
        if not isinstance(name, str) or not name:
            raise ManifestError("manifest 'artifacts' keys must be non-empty strings")
        if policy not in ARTIFACT_POLICIES:
            raise ManifestError(f"manifest artifact '{name}' has unknown policy '{policy}'")
    for name in _ALWAYS_REQUIRED:
        if artifacts[name] != "required":
            raise ManifestError(f"manifest artifact '{name}' must be 'required'")

    evidence_required = payload["evidence_required"]
    if not isinstance(evidence_required, dict):
        raise ManifestError("manifest 'evidence_required' must be an object")
    missing_kinds = [kind for kind in _EVIDENCE_KINDS if kind not in evidence_required]
    if missing_kinds:
        raise ManifestError(
            f"manifest 'evidence_required' is missing kinds: {', '.join(missing_kinds)}"
        )
    for kind in _EVIDENCE_KINDS:
        keys = evidence_required[kind]
        if not isinstance(keys, list) or not keys or not all(
            isinstance(key, str) and key for key in keys
        ):
            raise ManifestError(
                f"manifest 'evidence_required.{kind}' must be a non-empty list of strings"
            )

    default_units = payload["default_units"]
    if not isinstance(default_units, list) or not default_units or not all(
        isinstance(item, str) and item for item in default_units
    ):
        raise ManifestError("manifest 'default_units' must be a non-empty list of strings")

    unit_prefix = payload["unit_prefix"]
    if not isinstance(unit_prefix, str) or not unit_prefix:
        raise ManifestError("manifest 'unit_prefix' must be a non-empty string")

    hard_rules = payload["hard_rules"]
    if not isinstance(hard_rules, list) or not hard_rules or not all(
        isinstance(item, str) and item for item in hard_rules
    ):
        raise ManifestError("manifest 'hard_rules' must be a non-empty list of strings")

    max_attempts = payload["max_attempts"]
    if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or max_attempts < 1:
        raise ManifestError("manifest 'max_attempts' must be a positive integer")

    if not isinstance(payload["grouped"], bool):
        raise ManifestError("manifest 'grouped' must be a boolean")
    if not isinstance(payload["schema_version"], int) or isinstance(
        payload["schema_version"], bool
    ):
        raise ManifestError("manifest 'schema_version' must be an integer")
    if not isinstance(payload["type"], str) or not payload["type"]:
        raise ManifestError("manifest 'type' must be a non-empty string")

    return WorkflowManifest(
        schema_version=payload["schema_version"],
        type=payload["type"],
        unit_prefix=unit_prefix,
        grouped=payload["grouped"],
        max_attempts=max_attempts,
        hard_rules=tuple(hard_rules),
        artifacts=dict(artifacts),
        evidence_required={kind: tuple(evidence_required[kind]) for kind in _EVIDENCE_KINDS},
        default_units=tuple(default_units),
    )


def load_manifest(work_type: str) -> WorkflowManifest:
    """Load and validate the bundled workflow.json for one family."""
    manifest_path = _ASSET_ROOT / work_type / "workflow.json"
    try:
        text = manifest_path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ManifestError(f"no bundled manifest for work type '{work_type}'") from error
    manifest = parse_manifest(text)
    if manifest.type != work_type:
        raise ManifestError(
            f"manifest 'type' ({manifest.type!r}) does not match directory ({work_type!r})"
        )
    return manifest
