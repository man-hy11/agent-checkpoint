"""Command-line interface for portable project checkpoints."""

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Sequence

from .config import ConfigError, ensure_gitignore, load_config
from .diagnostics import build_doctor, build_handoff, build_resume, build_status, build_work_status
from .progress import contains_diff_content, validate_entry
from .secrets import find_secret_kind
from .storage import (
    CheckpointStore,
    LockTimeout,
    SecretDetected,
    ValidationError,
)
from .skill_install import agent_skill_roots, global_skill_destination, install_skill_suite
from .work_evidence import validate_evidence
from .work_manifest import ManifestError, load_manifest
from .work_migration import apply_migration, plan_migration
from .work_state import StateError, parse_state
from .work_store import claim as _work_claim
from .work_store import revise_plan as _work_revise
from .workflows import discard_workflow, initialize_workflow, workflow_types


EXIT_SUCCESS = 0
EXIT_INVALID = 2
EXIT_SECRET = 3
EXIT_LOCK_TIMEOUT = 4
EXIT_IO = 5

_RESERVED_SEPARATOR = re.compile(r"(?m)^---\s*$")


class _SafeArgumentParser(argparse.ArgumentParser):
    """Argument parser that never echoes credential-shaped input."""

    def error(self, message: str) -> None:
        if find_secret_kind(message) is not None:
            message = "invalid arguments"
        super().error(message)


def build_parser() -> argparse.ArgumentParser:
    """Build the stable public argument parser."""
    parser = _SafeArgumentParser(prog="agent-checkpoint")
    commands = parser.add_subparsers(dest="command", required=True)

    init_parser = commands.add_parser("init", help="initialize checkpoint ignores")
    _add_root(init_parser)

    write_parser = commands.add_parser("write", help="write a checkpoint entry")
    _add_root(write_parser)
    _add_entry(write_parser)
    write_parser.add_argument("--pin", action="store_true", help="retain as a milestone")
    write_parser.add_argument(
        "--verification",
        action="append",
        default=[],
        help="append an explicit verification result (repeatable)",
    )

    validate_parser = commands.add_parser("validate", help="validate an entry")
    _add_root(validate_parser)
    _add_entry(validate_parser)

    status_parser = commands.add_parser("status", help="show checkpoint status")
    _add_root(status_parser)
    status_parser.add_argument("--json", action="store_true", dest="json_output")

    resume_parser = commands.add_parser("resume", help="render resume context")
    _add_root(resume_parser)
    _add_max_chars(resume_parser)

    handoff_parser = commands.add_parser("handoff", help="render handoff context")
    _add_root(handoff_parser)
    _add_max_chars(handoff_parser)

    doctor_parser = commands.add_parser("doctor", help="diagnose checkpoint setup")
    _add_root(doctor_parser)
    doctor_parser.add_argument("--json", action="store_true", dest="json_output")
    doctor_parser.add_argument(
        "--adapter", default="manual", help="adapter name used for capability reporting"
    )

    dry_run_parser = commands.add_parser(
        "dry-run", help="validate an entry without writing"
    )
    _add_root(dry_run_parser)
    _add_entry(dry_run_parser)

    workflow_parser = commands.add_parser(
        "workflow", help="materialize a template-backed checkpoint work package"
    )
    _add_root(workflow_parser)
    workflow_parser.add_argument("--type", choices=workflow_types())
    workflow_parser.add_argument("--id", default="current", help="work package id")

    work_parser = commands.add_parser("work", help="manage workflow state transitions")
    work_sub = work_parser.add_subparsers(dest="work_command", required=True)

    work_status_p = work_sub.add_parser("status", help="show work package status")
    _add_root(work_status_p)
    work_status_p.add_argument("--json", action="store_true", dest="json_output")

    work_start_p = work_sub.add_parser("start", help="start a unit")
    _add_root(work_start_p)
    work_start_p.add_argument("--unit", required=True)
    work_start_p.add_argument("--plan-revision", type=int, required=True)

    work_pass_p = work_sub.add_parser("pass", help="mark a unit passed")
    _add_root(work_pass_p)
    work_pass_p.add_argument("--unit", required=True)
    work_pass_p.add_argument("--plan-revision", type=int, required=True)
    work_pass_p.add_argument("--evidence-file", required=True)

    work_fail_p = work_sub.add_parser("fail", help="mark a unit failed")
    _add_root(work_fail_p)
    work_fail_p.add_argument("--unit", required=True)
    work_fail_p.add_argument("--plan-revision", type=int, required=True)
    work_fail_p.add_argument("--evidence-file", required=True)

    work_recover_p = work_sub.add_parser("recover", help="apply a recovery event")
    _add_root(work_recover_p)
    work_recover_p.add_argument("--unit", required=True)
    work_recover_p.add_argument("--plan-revision", type=int, required=True)
    work_recover_p.add_argument(
        "--event", required=True,
        choices=("retry", "replan", "supersede", "block", "unblock"),
    )
    work_recover_p.add_argument("--evidence-file", required=True)

    work_revise_p = work_sub.add_parser("revise", help="increment plan_revision")
    _add_root(work_revise_p)
    work_revise_p.add_argument("--plan-revision", type=int, required=True)
    work_revise_p.add_argument("--evidence-file", required=True)

    work_migrate_p = work_sub.add_parser("migrate", help="migrate legacy work packages")
    _add_root(work_migrate_p)
    work_migrate_p.add_argument("--apply", action="store_true")
    work_migrate_p.add_argument("--json", action="store_true", dest="json_output")

    skill_install_parser = commands.add_parser(
        "skill-install", help="install the generic skill and optional directory links"
    )
    target = skill_install_parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--destination", help="canonical skill directory, such as .agent/skills"
    )
    target.add_argument(
        "--global", action="store_true", dest="global_install", help="install under ~/.agent/skills"
    )
    skill_install_parser.add_argument(
        "--link",
        action="append",
        default=[],
        help="agent-specific skill directory to link to the canonical skill (repeatable)",
    )
    skill_install_parser.add_argument(
        "--agent",
        action="append",
        choices=("claude-code", "codex", "opencode", "agent-compatible", "gemini-cli"),
        default=[],
        help="global agent skill path to link (repeatable; requires --global)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command and return its stable process exit code."""
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        return _dispatch(arguments)
    except SecretDetected as error:
        _print_error(error)
        return EXIT_SECRET
    except LockTimeout as error:
        _print_error(error)
        return EXIT_LOCK_TIMEOUT
    except ConfigError as error:
        if isinstance(error.__cause__, OSError):
            _print_io_error()
            return EXIT_IO
        _print_error(error)
        return EXIT_INVALID
    except (ValidationError, ValueError) as error:
        _print_error(error)
        return EXIT_INVALID
    except (OSError, UnicodeError):
        _print_io_error()
        return EXIT_IO


def _dispatch(arguments: argparse.Namespace) -> int:
    if arguments.command == "skill-install":
        if arguments.agent and not arguments.global_install:
            raise ValidationError("--agent requires --global")
        destination = (
            global_skill_destination()
            if arguments.global_install
            else Path(arguments.destination)
        )
        result = install_skill_suite(
            destination,
            tuple(Path(link) for link in arguments.link) + agent_skill_roots(tuple(arguments.agent)),
        )
        for skill in result.skills:
            print(f"Skill installed: {skill}", file=sys.stderr)
        for link in result.links:
            print(f"Skill link created: {link}", file=sys.stderr)
        return EXIT_SUCCESS

    root = Path(arguments.root)
    config = load_config(root)

    if arguments.command == "init":
        result = ensure_gitignore(root, config)
        action = "updated" if result.changed else "already configured"
        print(f"Checkpoint ignore rules {action}.", file=sys.stderr)
    elif arguments.command == "write":
        body = _read_entry(arguments.entry)
        CheckpointStore(root, config).write(
            body,
            pinned=arguments.pin,
            verification=arguments.verification,
        )
        print("Checkpoint written.", file=sys.stderr)
    elif arguments.command == "workflow":
        if arguments.type is None:
            choices = ", ".join(workflow_types())
            raise ValidationError(f"Workflow type is required. Choose one of: {choices}")
        ensure_gitignore(root, config)
        workflow = initialize_workflow(root, arguments.type, arguments.id)
        try:
            CheckpointStore(root, config).write(workflow.progress_entry)
        except BaseException:
            discard_workflow(workflow)
            raise
        print(f"Workflow package created: {workflow.path}", file=sys.stderr)
    elif arguments.command in ("validate", "dry-run"):
        _validate_body(_read_entry(arguments.entry))
        label = "Dry-run valid" if arguments.command == "dry-run" else "Entry valid"
        print(f"{label}.", file=sys.stderr)
    elif arguments.command == "status":
        status = build_status(root, config)
        if arguments.json_output:
            _print_json(status)
        else:
            existence = "present" if status["checkpoint_exists"] else "absent"
            print(
                f"Checkpoint {existence}; {status['checkpoint_entries']} entries.",
                file=sys.stderr,
            )
    elif arguments.command == "resume":
        sys.stdout.write(build_resume(root, config, arguments.max_chars))
    elif arguments.command == "handoff":
        sys.stdout.write(build_handoff(root, config, max_chars=arguments.max_chars))
    elif arguments.command == "doctor":
        _reject_secret_text(arguments.adapter)
        report = build_doctor(root, config, arguments.adapter)
        if arguments.json_output:
            _print_json(report)
        else:
            warnings = report["warnings"] or "No warnings."
            print(
                f"Adapter {report['adapter']} ({report['capability']}).\n{warnings}",
                file=sys.stderr,
            )
    elif arguments.command == "work":
        return _dispatch_work(arguments)
    else:  # pragma: no cover - argparse restricts command values
        raise ValueError(f"Unsupported command: {arguments.command}")
    return EXIT_SUCCESS


def _dispatch_work(arguments: argparse.Namespace) -> int:
    """Dispatch a `work` subcommand. Errors surface via the main exception handler."""
    root = Path(arguments.root)
    config = load_config(root)
    work_command = arguments.work_command

    if work_command == "status":
        report = build_work_status(root, config)
        if report is None:
            print("No active work package found.", file=sys.stderr)
            return EXIT_SUCCESS
        if arguments.json_output:
            _print_json(report)
        else:
            print(
                f"Work package {report['work_id']} ({report['work_type']}); "
                f"unit {report['current_unit']} is {report['state']}.",
                file=sys.stderr,
            )
        return EXIT_SUCCESS

    if work_command == "migrate":
        report = apply_migration(root) if arguments.apply else plan_migration(root)
        mode = "apply" if arguments.apply else "dry-run"
        payload = {
            "applied": report.applied,
            "mode": mode,
            "actions": [
                {
                    "work_id": action.work_id,
                    "category": action.classification.category,
                    "reasons": list(action.classification.reasons),
                    "will_migrate": action.will_migrate,
                    "backup_path": (
                        str(action.backup_path) if action.backup_path is not None else None
                    ),
                }
                for action in report.actions
            ],
        }
        verb = "Apply" if arguments.apply else "Dry run"
        if arguments.json_output:
            _print_json(payload)
        elif not report.actions:
            print(f"{verb}: no legacy packages found.", file=sys.stderr)
        else:
            for action in report.actions:
                status = "migrated" if action.will_migrate else "refused"
                print(
                    f"{verb}: {action.work_id} -> {action.classification.category} ({status}).",
                    file=sys.stderr,
                )
        return EXIT_SUCCESS

    # Locate the active work package for all other subcommands.
    work_root = root / ".agent-checkpoint" / "work"
    candidates = (
        sorted(
            p for p in work_root.iterdir()
            if p.is_dir() and not p.name.startswith(".staging-") and (p / "CURRENT.md").is_file()
        )
        if work_root.is_dir()
        else []
    )
    if not candidates:
        raise ValidationError("No active work package found")
    package_path = candidates[0]
    current_path = package_path / "CURRENT.md"
    evidence_path = package_path / "EVIDENCE.md"

    if work_command == "revise":
        evidence_text = Path(arguments.evidence_file).read_text(encoding="utf-8")
        _reject_secret_text(evidence_text)
        _work_revise(
            root,
            current_path,
            plan_revision=arguments.plan_revision,
        )
        print(f"Plan revision updated to {arguments.plan_revision}.", file=sys.stderr)
        return EXIT_SUCCESS

    # start / pass / fail / recover — all go through work_store.claim
    if work_command == "start":
        event = "start"
        evidence_text = ""
    else:
        event = {
            "pass": "pass",
            "fail": "fail",
            "recover": getattr(arguments, "event", None),
        }[work_command]
        evidence_text = Path(arguments.evidence_file).read_text(encoding="utf-8")
        _reject_secret_text(evidence_text)

        # Validate evidence against the manifest before claiming.
        text = current_path.read_text(encoding="utf-8")
        state = parse_state(text)
        unit = state.unit(arguments.unit)
        if unit is None:
            raise ValidationError(f"unknown unit: {arguments.unit}")
        try:
            manifest = load_manifest(state.work_type)
            required = manifest.evidence_required.get(unit.kind, ())
        except ManifestError:
            required = ()
        unmet = validate_evidence(evidence_text, unit_id=arguments.unit, required=required)
        if unmet:
            raise ValidationError(
                f"checkpoint-evidence is inadequate: missing {', '.join(sorted(unmet))}. "
                "Provide a checkpoint-evidence document with all required sections."
            )

    _work_claim(
        root,
        current_path,
        evidence_path,
        unit_id=arguments.unit,
        event=event,
        plan_revision=arguments.plan_revision,
        evidence_text=evidence_text,
    )
    label = {"start": "started", "pass": "passed", "fail": "failed"}.get(
        work_command, work_command
    )
    print(f"Unit {arguments.unit} {label}.", file=sys.stderr)
    return EXIT_SUCCESS


def _add_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=".", help="project root (default: current directory)")


def _add_entry(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--entry",
        default="-",
        help="entry file path, or - to read standard input (default: -)",
    )


def _add_max_chars(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-chars", type=int, help="maximum rendered characters")


def _read_entry(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def _validate_body(body: str) -> None:
    _reject_secret_text(body)
    if contains_diff_content(body):
        raise ValidationError("Checkpoint contains diff-shaped content")
    missing_sections = validate_entry(body)
    if missing_sections:
        raise ValidationError(
            "Checkpoint is missing required section(s): " + ", ".join(missing_sections)
        )
    if _RESERVED_SEPARATOR.search(body):
        raise ValidationError("Checkpoint body contains a reserved separator line")


def _reject_secret_text(value: str) -> None:
    secret_kind = find_secret_kind(value)
    if secret_kind is not None:
        raise SecretDetected(f"Probable {secret_kind} detected; input was not accepted")


def _print_json(value: dict) -> None:
    json.dump(value, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")


def _print_error(error: Exception) -> None:
    message = str(error)
    if find_secret_kind(message) is not None:
        message = "Invalid input or configuration"
    print(message, file=sys.stderr)


def _print_io_error() -> None:
    print("I/O error: unable to complete checkpoint command", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
