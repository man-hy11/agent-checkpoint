from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from agent_checkpoint.config import ConfigError, read_active_work_id, write_active_work_id
from agent_checkpoint.work_state import parse_state
from agent_checkpoint.workflows import write_root_continue_prompt
from tests.helpers import CORE_ROOT, VALID_BODY, run_cli


if os.name == "posix":
    import fcntl


ALL_COMMANDS = (
    "init",
    "write",
    "validate",
    "status",
    "resume",
    "handoff",
    "doctor",
    "dry-run",
    "workflow",
    "skill-install",
)


def _activate_work_package(project_root: Path, work_id: str = "current") -> Path:
    """Create a work package directory and point the active pointer at it.

    R3 made ``write`` resolve its target through the active pointer, so tests
    that exercise the write path must first establish an active work package.
    """
    package = project_root / ".agent-checkpoint" / "work" / work_id
    package.mkdir(parents=True)
    (project_root / ".agent-checkpoint" / "active").write_text(
        work_id + "\n", encoding="utf-8"
    )
    return package


def _scoped_progress(project_root: Path, work_id: str = "current") -> Path:
    return project_root / ".agent-checkpoint" / "work" / work_id / "PROGRESS.md"


def _make_work_package_with_all_units_passed(
    project_root: Path, work_id: str = "current"
) -> Path:
    """Create a work package whose sole unit is ``passed`` -- a completed package."""
    pkg = project_root / ".agent-checkpoint" / "work" / work_id
    pkg.mkdir(parents=True)
    state_json = f"""{{
  "schema_version": 1,
  "work_id": "{work_id}",
  "work_type": "feature",
  "plan_revision": 1,
  "brief_confirmed": true,
  "current_unit": "U1",
  "max_attempts": 3,
  "attempt_override": null,
  "units": [{{"id": "U1", "group": null, "kind": "step", "state": "passed", "attempt": 1}}],
  "attempts": []
}}"""
    current_text = (
        "# CURRENT.md\n\n"
        "<!-- agent-checkpoint:state v1 -->\n"
        + state_json
        + "\n<!-- /agent-checkpoint:state -->\n"
    )
    (pkg / "CURRENT.md").write_text(current_text, encoding="utf-8")
    (pkg / "EVIDENCE.md").write_text("# Evidence\n", encoding="utf-8")
    (project_root / ".agent-checkpoint" / "active").write_text(
        work_id + "\n", encoding="utf-8"
    )
    return pkg


class CliTests(unittest.TestCase):
    def test_help_lists_all_public_subcommands(self):
        """Catches a public command being omitted from the stable parser."""
        result = run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ALL_COMMANDS:
            self.assertIn(command, result.stdout)
        self.assertEqual(result.stderr, "")

    def test_workflow_initializes_template_and_writes_progress_pointer(self):
        """Catches skills scaffolding templates without a durable session entrypoint."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            result = run_cli(
                "workflow",
                "--root",
                str(project_root),
                "--type",
                "feature",
                "--id",
                "current",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(
                (project_root / ".agent-checkpoint/work/current/CURRENT.md").is_file()
            )
            self.assertEqual(
                (project_root / ".agent-checkpoint/active").read_text(encoding="utf-8"),
                "current\n",
            )
            progress = (
                project_root / ".agent-checkpoint/work/current/PROGRESS.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Workflow type: feature", progress)
            self.assertIn(".agent-checkpoint/work/current/CURRENT.md", progress)
            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_workflow_without_type_lists_required_choice(self):
        """Catches a first workflow invocation silently guessing its template type."""
        result = run_cli("workflow")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Workflow type is required", result.stderr)
        self.assertIn("feature", result.stderr)
        self.assertIn("bugfix", result.stderr)

    def test_init_ignores_progress_files_and_status_reports_empty_project(self):
        """Catches init mutating more than ignore state or status requiring a checkpoint."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            result = run_cli("init", "--root", str(project_root))
            status = run_cli("status", "--root", str(project_root), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertIn("PROGRESS.md", (project_root / ".gitignore").read_text())
            self.assertFalse((project_root / "PROGRESS.md").exists())
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertEqual(status.stderr, "")
            self.assertFalse(json.loads(status.stdout)["checkpoint_exists"])

    def test_dry_run_validates_stdin_without_writing(self):
        """Catches dry-run persisting input or skipping real entry validation."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            result = run_cli(
                "dry-run",
                "--root",
                str(project_root),
                "--entry",
                "-",
                input_text=VALID_BODY,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertIn("valid", result.stderr.lower())
            self.assertFalse((project_root / "PROGRESS.md").exists())
            self.assertFalse((project_root / ".agent-checkpoint.lock").exists())

    def test_write_validate_and_dry_run_reject_diff_shaped_entries(self):
        """Catches public ingestion commands accepting Git patch content."""
        patch = "diff --git a/app.py b/app.py\n@@ -1 +1 @@\n-old\n+new\n"
        for command in ("write", "validate", "dry-run"):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as directory:
                project_root = Path(directory)
                _activate_work_package(project_root)

                result = run_cli(
                    command,
                    "--root",
                    str(project_root),
                    "--entry",
                    "-",
                    input_text=VALID_BODY + "\n" + patch,
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn("diff-shaped", result.stderr)
                self.assertFalse(_scoped_progress(project_root).exists())

    def test_write_regular_file_parent_exits_two_without_traceback(self):
        """Catches handled storage path errors escaping as NameError tracebacks."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            package = _activate_work_package(project_root)
            (package / "state").write_text("not a directory\n", encoding="utf-8")
            (project_root / ".agent-checkpoint.toml").write_text(
                'progress_path = "state/PROGRESS.md"\n',
                encoding="utf-8",
            )

            result = run_cli(
                "write",
                "--root",
                str(project_root),
                "--entry",
                "-",
                input_text=VALID_BODY,
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("not a directory", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertNotIn("NameError", result.stderr)
            self.assertFalse((package / "state" / "PROGRESS.md").exists())

    def test_write_rejects_indented_git_metadata_only_blocks(self):
        """Catches CLI writes persisting metadata-only Git diff blocks."""
        cases = {
            "mode_only": (
                "    diff --git a/script.sh b/script.sh\n"
                "    old mode 100644\n"
                "    new mode 100755\n"
            ),
            "rename": (
                "    diff --git a/old.txt b/new.txt\n"
                "    similarity index 100%\n"
                "    rename from old.txt\n"
                "    rename to new.txt\n"
            ),
            "git_binary_patch": (
                "    diff --git a/logo.png b/logo.png\n"
                "    index abcd123..fffffff 100644\n"
                "    GIT binary patch\n"
                "    literal 0\n"
            ),
        }
        for name, patch in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                project_root = Path(directory)
                _activate_work_package(project_root)

                result = run_cli(
                    "write",
                    "--root",
                    str(project_root),
                    "--entry",
                    "-",
                    input_text=VALID_BODY + "\n" + patch,
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn("diff-shaped", result.stderr)
                self.assertFalse(_scoped_progress(project_root).exists())

    def test_write_rejects_indented_git_headers_with_spaces(self):
        """Catches CLI writes persisting real Git headers with spaces."""
        cases = {
            "mode_only": (
                "    diff --git a/script name.sh b/script name.sh\n"
                "    old mode 100644\n"
                "    new mode 100755\n"
            ),
            "rename": (
                "    diff --git a/old name.txt b/new name.txt\n"
                "    similarity index 100%\n"
                "    rename from old name.txt\n"
                "    rename to new name.txt\n"
            ),
            "git_binary_patch": (
                "    diff --git a/logo name.bin b/logo name.bin\n"
                "    index abcd123..fffffff 100644\n"
                "    GIT binary patch\n"
                "    literal 0\n"
            ),
        }
        for name, patch in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                project_root = Path(directory)
                _activate_work_package(project_root)

                result = run_cli(
                    "write",
                    "--root",
                    str(project_root),
                    "--entry",
                    "-",
                    input_text=VALID_BODY + "\n" + patch,
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn("diff-shaped", result.stderr)
                self.assertFalse(_scoped_progress(project_root).exists())

    def test_write_allows_indented_git_metadata_prose(self):
        """Catches CLI prose mentioning Git metadata being rejected as a diff."""
        cases = {
            "rename_words": (
                "    diff --git is the command name in docs.\n"
                "    rename from describes the original path in prose.\n"
            ),
            "mode_words": (
                "    diff --git may appear in a tutorial sentence.\n"
                "    new mode 100755 may be cited as an example permission.\n"
            ),
            "binary_words": (
                "    diff --git can be discussed without a patch header.\n"
                "    Binary files old and new differ may be quoted in prose.\n"
            ),
        }
        for name, prose in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                project_root = Path(directory)
                _activate_work_package(project_root)

                result = run_cli(
                    "write",
                    "--root",
                    str(project_root),
                    "--entry",
                    "-",
                    input_text=VALID_BODY + "\n" + prose,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                progress = _scoped_progress(project_root).read_text(encoding="utf-8")
                self.assertIn(prose, progress)

    def test_write_validate_resume_handoff_status_and_doctor_streams(self):
        """Catches command routing, flags, or stdout/stderr contracts drifting."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _activate_work_package(project_root)
            entry_path = project_root / "entry.md"
            entry_path.write_text(VALID_BODY, encoding="utf-8")

            validation = run_cli(
                "validate", "--root", str(project_root), "--entry", str(entry_path)
            )
            write = run_cli(
                "write",
                "--root",
                str(project_root),
                "--entry",
                "-",
                "--pin",
                "--verification",
                "48 tests passed",
                input_text=VALID_BODY,
            )
            resume = run_cli(
                "resume", "--root", str(project_root), "--max-chars", "96"
            )
            handoff = run_cli(
                "handoff", "--root", str(project_root), "--max-chars", "120"
            )
            status = run_cli("status", "--root", str(project_root))
            doctor = run_cli(
                "doctor",
                "--root",
                str(project_root),
                "--adapter",
                "codex",
                "--json",
            )

            self.assertEqual(validation.returncode, 0, validation.stderr)
            self.assertEqual(validation.stdout, "")
            self.assertIn("valid", validation.stderr.lower())
            self.assertEqual(write.returncode, 0, write.stderr)
            self.assertEqual(write.stdout, "")
            progress = _scoped_progress(project_root).read_text(encoding="utf-8")
            self.assertIn("[PINNED]", progress)
            self.assertIn("48 tests passed", progress)
            self.assertEqual(resume.returncode, 0, resume.stderr)
            self.assertEqual(resume.stderr, "")
            self.assertLessEqual(len(resume.stdout), 96)
            self.assertIn("Checkpoint", resume.stdout)
            self.assertEqual(handoff.returncode, 0, handoff.stderr)
            self.assertEqual(handoff.stderr, "")
            self.assertLessEqual(len(handoff.stdout), 120)
            self.assertIn("Handoff", handoff.stdout)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertEqual(status.stdout, "")
            self.assertIn("checkpoint", status.stderr.lower())
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            self.assertEqual(doctor.stderr, "")
            doctor_payload = json.loads(doctor.stdout)
            self.assertEqual(doctor_payload["adapter"], "codex")
            self.assertEqual(doctor_payload["capability"], "manual")

    def test_handoff_resolve_removes_report_end_to_end(self):
        """Catches the CLI resolve surface failing to reach handoff.py's primitive."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            handoff_dir = project_root / ".agent-checkpoint" / "handoff"
            handoff_dir.mkdir(parents=True)
            report_path = handoff_dir / "current-R9-scratch-report.md"
            report_path.write_text("# Scratch Report\n\nBody.\n", encoding="utf-8")

            resolve = run_cli(
                "handoff",
                "resolve",
                "--root",
                str(project_root),
                "--name",
                "current-R9-scratch-report",
            )

            self.assertEqual(resolve.returncode, 0, resolve.stderr)
            self.assertIn("resolved", resolve.stderr.lower())
            self.assertFalse(report_path.exists())

    def test_handoff_resolve_nonexistent_report_exits_invalid(self):
        """Catches a bad --name silently succeeding instead of surfacing exit code 2."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            resolve = run_cli(
                "handoff",
                "resolve",
                "--root",
                str(project_root),
                "--name",
                "never-written",
            )

            self.assertEqual(resolve.returncode, 2, resolve.stderr)

    def test_handoff_auto_commits_when_opted_in(self):
        """Catches the opt-in auto-commit flag failing to reach the CLI handoff path."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            subprocess.run(
                ["git", "init", "-q"], cwd=project_root, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.email", "tests@example.invalid"],
                cwd=project_root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Checkpoint Tests"],
                cwd=project_root,
                check=True,
                capture_output=True,
            )
            (project_root / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "README.md"], cwd=project_root, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-qm", "fixture"],
                cwd=project_root,
                check=True,
                capture_output=True,
            )
            (project_root / ".agent-checkpoint.toml").write_text(
                "auto_commit_on_handoff = true\n", encoding="utf-8"
            )
            _make_work_package_with_all_units_passed(project_root)
            (project_root / "work.txt").write_text("changed", encoding="utf-8")

            handoff = run_cli("handoff", "--root", str(project_root))

            self.assertEqual(handoff.returncode, 0, handoff.stderr)
            self.assertIn("Auto-committed handoff", handoff.stderr)
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_root,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(status.stdout, "")

    def test_handoff_skips_auto_commit_by_default(self):
        """Catches auto-commit running without an explicit opt-in."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            subprocess.run(
                ["git", "init", "-q"], cwd=project_root, check=True, capture_output=True
            )
            (project_root / "work.txt").write_text("changed", encoding="utf-8")

            handoff = run_cli("handoff", "--root", str(project_root))

            self.assertEqual(handoff.returncode, 0, handoff.stderr)
            self.assertEqual(handoff.stderr, "")

    def test_invalid_input_and_config_exit_two_without_json_stdout(self):
        """Catches invalid user/configuration data escaping the code-2 boundary."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            invalid = run_cli(
                "validate",
                "--root",
                str(project_root),
                "--entry",
                "-",
                input_text="## 1. Goal / Plan\n- incomplete\n",
            )
            (project_root / ".agent-checkpoint.toml").write_text(
                "max_live_chars = 999\n", encoding="utf-8"
            )
            invalid_config = run_cli(
                "status", "--root", str(project_root), "--json"
            )

            self.assertEqual(invalid.returncode, 2)
            self.assertEqual(invalid.stdout, "")
            self.assertIn("missing", invalid.stderr.lower())
            self.assertEqual(invalid_config.returncode, 2)
            self.assertEqual(invalid_config.stdout, "")
            self.assertNotEqual(invalid_config.stderr, "")

    def test_argparse_and_config_errors_redact_credential_shaped_values(self):
        """Catches parser and handled-config diagnostics echoing user credentials."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            candidate = "gh" + "p_" + ("a" * 24)

            argument_error = run_cli("status", "--" + candidate)
            (project_root / ".agent-checkpoint.toml").write_text(
                f"{candidate} = true\n", encoding="utf-8"
            )
            config_error = run_cli("status", "--root", str(project_root), "--json")

            self.assertEqual(argument_error.returncode, 2)
            self.assertEqual(argument_error.stdout, "")
            self.assertNotIn(candidate, argument_error.stderr)
            self.assertEqual(config_error.returncode, 2)
            self.assertEqual(config_error.stdout, "")
            self.assertNotIn(candidate, config_error.stderr)

    def test_argparse_error_redacts_sensitive_option_assignment(self):
        """Catches argparse reflecting an unknown --password=value credential."""
        candidate = "production-value"

        result = run_cli("status", "--password=" + candidate)

        self.assertEqual(result.returncode, 2)
        self.assertNotIn(candidate, result.stderr)
        self.assertIn("invalid arguments", result.stderr)

    def test_argparse_error_redacts_sensitive_option_separate_value(self):
        """Catches argparse reflecting credential next-token forms."""
        for option in ("--api-key", "--api_key", "--token", "--secret", "--password"):
            with self.subTest(option=option):
                candidate = "production-separate-value"

                result = run_cli("status", option, candidate)

                self.assertEqual(result.returncode, 2)
                self.assertNotIn(candidate, result.stderr)
                self.assertIn("invalid arguments", result.stderr)

    def test_written_verification_is_handed_off_outside_recent_decisions(self):
        """Catches persisted verification disappearing or being labeled a decision."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _activate_work_package(project_root)
            existing_verification = "manual smoke test: passed"
            verification = "python -m unittest: 123 passed"
            written = run_cli(
                "write",
                "--root",
                str(project_root),
                "--entry",
                "-",
                "--verification",
                verification,
                input_text=(
                    VALID_BODY
                    + "\n## 6. Verification\n- "
                    + existing_verification
                    + "\n"
                ),
            )
            handoff = run_cli(
                "handoff", "--root", str(project_root), "--max-chars", "4000"
            )

            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertEqual(handoff.returncode, 0, handoff.stderr)
            verification_block = handoff.stdout.partition("Verification results:")[2]
            verification_block = verification_block.partition("Current Focus:")[0]
            decisions_block = handoff.stdout.partition("Recent Decisions:")[2]
            progress = _scoped_progress(project_root).read_text(encoding="utf-8")
            self.assertEqual(progress.count("## 6. Verification"), 1)
            self.assertIn(existing_verification, verification_block)
            self.assertIn(verification, verification_block)
            self.assertNotIn(existing_verification, decisions_block)
            self.assertNotIn(verification, decisions_block)

    def test_write_rejects_multiline_verification_heading_injection(self):
        """Catches every Unicode/Python line boundary creating hidden content."""
        for separator in ("\n", "\r", "\x0b", "\x0c", "\x85", "\u2028", "\u2029"):
            with self.subTest(separator=repr(separator)), tempfile.TemporaryDirectory() as directory:
                project_root = Path(directory)
                _activate_work_package(project_root)
                injected = f"tests passed{separator}## 6. Verification - hidden result"

                result = run_cli(
                    "write",
                    "--root",
                    str(project_root),
                    "--entry",
                    "-",
                    "--verification",
                    injected,
                    input_text=VALID_BODY,
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn("single line", result.stderr)
                self.assertFalse(_scoped_progress(project_root).exists())

    def test_config_filesystem_failure_exits_five(self):
        """Catches a wrapped configuration read failure being labeled invalid input."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            (project_root / ".agent-checkpoint.toml").mkdir()

            result = run_cli("status", "--root", str(project_root), "--json")

            self.assertEqual(result.returncode, 5)
            self.assertEqual(result.stdout, "")
            self.assertIn("i/o", result.stderr.lower())

    def test_secret_detection_exits_three_without_echoing_candidate(self):
        """Catches credential input using a generic exit or leaking its value."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            candidate = "gh" + "p_" + ("z" * 24)

            result = run_cli(
                "dry-run",
                "--root",
                str(project_root),
                "--entry",
                "-",
                input_text=VALID_BODY + "\n" + candidate,
            )

            self.assertEqual(result.returncode, 3)
            self.assertEqual(result.stdout, "")
            self.assertNotIn(candidate, result.stderr)
            self.assertIn("probable", result.stderr.lower())
            self.assertFalse((project_root / "PROGRESS.md").exists())

            doctor = run_cli(
                "doctor",
                "--root",
                str(project_root),
                "--adapter",
                candidate,
                "--json",
            )
            self.assertEqual(doctor.returncode, 3)
            self.assertEqual(doctor.stdout, "")
            self.assertNotIn(candidate, doctor.stderr)

    def test_write_summary_does_not_echo_credential_shaped_root_metadata(self):
        """Catches a successful human summary leaking unsafe project metadata."""
        with tempfile.TemporaryDirectory() as directory:
            candidate = "gh" + "p_" + ("r" * 24)
            project_root = Path(directory) / candidate
            project_root.mkdir()
            _activate_work_package(project_root)

            result = run_cli(
                "write",
                "--root",
                str(project_root),
                "--entry",
                "-",
                input_text=VALID_BODY,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertNotIn(candidate, result.stderr)
            self.assertTrue(_scoped_progress(project_root).is_file())

    @unittest.skipUnless(os.name == "posix", "POSIX flock behavior")
    def test_lock_timeout_exits_four_without_writing(self):
        """Catches lock contention being flattened into invalid input or I/O."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            package = _activate_work_package(project_root)
            (project_root / ".agent-checkpoint.toml").write_text(
                "lock_timeout_seconds = 0\n", encoding="utf-8"
            )
            lock_path = package / ".agent-checkpoint.lock"
            with lock_path.open("a+b") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = run_cli(
                    "write",
                    "--root",
                    str(project_root),
                    "--entry",
                    "-",
                    input_text=VALID_BODY,
                )

            self.assertEqual(result.returncode, 4)
            self.assertEqual(result.stdout, "")
            self.assertIn("lock", result.stderr.lower())
            self.assertFalse(_scoped_progress(project_root).exists())

    def test_entry_read_failure_exits_five(self):
        """Catches filesystem failures being mislabeled as validation failures."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            missing_entry = project_root / "missing-entry.md"

            result = run_cli(
                "write",
                "--root",
                str(project_root),
                "--entry",
                str(missing_entry),
            )

            self.assertEqual(result.returncode, 5)
            self.assertEqual(result.stdout, "")
            self.assertNotEqual(result.stderr, "")
            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_source_launcher_finds_core_without_pythonpath(self):
        """Catches the launcher depending on its caller's environment or cwd."""
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)

        result = subprocess.run(
            [sys.executable, str(CORE_ROOT / "bin" / "agent-checkpoint"), "--help"],
            cwd=CORE_ROOT.parent,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ALL_COMMANDS:
            self.assertIn(command, result.stdout)

    def test_skill_install_places_all_twelve_skills(self):
        """Catches skill-install regressing to installing only the router skill."""
        from agent_checkpoint.skill_install import SKILL_NAMES

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "skills"

            result = run_cli("skill-install", "--destination", str(destination))

            self.assertEqual(result.returncode, 0, result.stderr)
            for name in SKILL_NAMES:
                self.assertTrue(
                    (destination / name / "SKILL.md").is_file(),
                    f"missing {name}/SKILL.md",
                )


MINIMAL_STATE = """{
  "schema_version": 1,
  "work_id": "test-work",
  "work_type": "feature",
  "plan_revision": 1,
  "brief_confirmed": true,
  "current_unit": "U1",
  "max_attempts": 3,
  "attempt_override": null,
  "units": [{"id": "U1", "group": null, "kind": "step", "state": "ready", "attempt": 0}],
  "attempts": []
}"""

MINIMAL_EVIDENCE = (
    "## Unit: U1\n"
    "## Attempt: 1\n"
    "### command\npython -m pytest\n"
    "### pass_fail\npassed\n"
    "### observed_output\nAll tests pass.\n"
)


def _make_work_package(
    project_root: Path, state_json: str | None = None, work_id: str = "test-work"
) -> Path:
    pkg = project_root / ".agent-checkpoint" / "work" / work_id
    pkg.mkdir(parents=True)
    current_text = (
        "# CURRENT.md\n\n"
        "<!-- agent-checkpoint:state v1 -->\n"
        + (state_json or MINIMAL_STATE).replace('"test-work"', f'"{work_id}"')
        + "\n<!-- /agent-checkpoint:state -->\n"
    )
    (pkg / "CURRENT.md").write_text(current_text, encoding="utf-8")
    (pkg / "EVIDENCE.md").write_text("# Evidence\n", encoding="utf-8")
    return pkg


class WorkCliTests(unittest.TestCase):
    def test_work_status_json_includes_work_fields(self):
        """Catches work status omitting next_skill, allowed_events, hard_rules."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root)

            result = run_cli("work", "status", "--root", str(project_root), "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("next_skill", payload)
        self.assertIn("allowed_events", payload)
        self.assertIn("evidence_required", payload)
        self.assertIn("hard_rules", payload)
        self.assertIn("work_id", payload)
        self.assertIn("work_type", payload)
        self.assertIn("current_unit", payload)
        self.assertIn("state", payload)
        self.assertIn("plan_revision", payload)
        self.assertEqual(payload["work_id"], "test-work")
        self.assertEqual(payload["work_type"], "feature")
        self.assertEqual(payload["current_unit"], "U1")
        self.assertEqual(payload["state"], "ready")
        self.assertEqual(payload["plan_revision"], 1)
        self.assertEqual(payload["next_skill"], "checkpoint-claim")
        self.assertIn("start", payload["allowed_events"])

    def test_work_status_with_id_selects_named_package(self):
        """Catches --id being ignored and always resolving candidates[0]."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root, work_id="current")
            _make_work_package(project_root, work_id="fix-next-skill-routing")

            result = run_cli(
                "work", "status", "--id", "fix-next-skill-routing",
                "--root", str(project_root), "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["work_id"], "fix-next-skill-routing")

    def test_work_status_without_id_and_multiple_candidates_is_refused(self):
        """Catches BUG.md Bug 2: silently picking candidates[0] instead of
        refusing an ambiguous multi-package selection."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root, work_id="current")
            _make_work_package(project_root, work_id="fix-next-skill-routing")

            result = run_cli("work", "status", "--root", str(project_root), "--json")

        self.assertEqual(result.returncode, 2)
        self.assertIn("current", result.stderr)
        self.assertIn("fix-next-skill-routing", result.stderr)
        self.assertIn("--id", result.stderr)

    def test_work_status_without_id_and_single_candidate_is_unchanged(self):
        """Regression guard: the common single-package case must keep
        working with zero --id required."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root)

            result = run_cli("work", "status", "--root", str(project_root), "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["work_id"], "test-work")

    def test_work_status_with_id_naming_nonexistent_package_is_refused(self):
        """Catches --id silently falling back to another candidate instead
        of refusing a nonexistent package name."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root)

            result = run_cli(
                "work", "status", "--id", "does-not-exist",
                "--root", str(project_root), "--json",
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("does-not-exist", result.stderr)

    def test_work_status_with_malformed_id_is_refused(self):
        """Catches --id being used as an unvalidated path component."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root)

            result = run_cli(
                "work", "status", "--id", "../../etc",
                "--root", str(project_root), "--json",
            )

        self.assertEqual(result.returncode, 2)

    def test_work_status_human_without_json_flag(self):
        """Catches work status --json being required for structured output."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root)

            result = run_cli("work", "status", "--root", str(project_root))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("test-work", result.stderr)

    def test_work_start_transitions_unit_to_running(self):
        """Catches start not applying the ready->running transition."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            pkg = _make_work_package(project_root)

            result = run_cli(
                "work", "start",
                "--unit", "U1",
                "--plan-revision", "1",
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            current = (pkg / "CURRENT.md").read_text(encoding="utf-8")
            self.assertIn('"running"', current)

    def test_work_start_with_id_selects_named_package_among_multiple(self):
        """Catches start ignoring --id and operating on candidates[0]."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root, work_id="current")
            target = _make_work_package(project_root, work_id="fix-next-skill-routing")

            result = run_cli(
                "work", "start",
                "--id", "fix-next-skill-routing",
                "--unit", "U1",
                "--plan-revision", "1",
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            current = (target / "CURRENT.md").read_text(encoding="utf-8")
            self.assertIn('"running"', current)

    def test_work_start_without_id_and_multiple_candidates_is_refused(self):
        """Catches start silently guessing candidates[0] among many packages."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root, work_id="current")
            _make_work_package(project_root, work_id="fix-next-skill-routing")

            result = run_cli(
                "work", "start",
                "--unit", "U1",
                "--plan-revision", "1",
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("--id", result.stderr)

    def test_work_start_requires_no_evidence_file(self):
        """Catches start demanding an evidence file it should not need."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root)

            result = run_cli(
                "work", "start",
                "--unit", "U1",
                "--plan-revision", "1",
                "--root", str(project_root),
            )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_work_pass_requires_evidence_file(self):
        """Catches pass accepting a transition without evidence."""
        result = run_cli("work", "pass", "--unit", "U1", "--plan-revision", "1")
        self.assertEqual(result.returncode, 2)

    def test_work_pass_transitions_running_unit_to_passed(self):
        """Catches pass not applying the running->passed transition.

        Uses a second, still-pending unit (U2) so this U1 pass is
        non-terminal and the package is not archived out from under the
        assertions below — archive-on-terminal-pass is covered separately by
        ``ArchiveOnCompleteTests``.
        """
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            running_state = (
                MINIMAL_STATE
                .replace('"ready"', '"running"')
                .replace('"attempt": 0', '"attempt": 1')
                .replace(
                    '"units": [{"id": "U1", "group": null, "kind": "step", '
                    '"state": "running", "attempt": 1}]',
                    '"units": ['
                    '{"id": "U1", "group": null, "kind": "step", "state": "running", "attempt": 1}, '
                    '{"id": "U2", "group": null, "kind": "step", "state": "pending", "attempt": 0}'
                    ']',
                )
            )
            pkg = _make_work_package(project_root, running_state)
            evidence_file = Path(directory) / "ev.md"
            evidence_file.write_text(MINIMAL_EVIDENCE, encoding="utf-8")

            result = run_cli(
                "work", "pass",
                "--unit", "U1",
                "--plan-revision", "1",
                "--evidence-file", str(evidence_file),
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            current = (pkg / "CURRENT.md").read_text(encoding="utf-8")
            self.assertIn('"passed"', current)
            evidence = (pkg / "EVIDENCE.md").read_text(encoding="utf-8")
            self.assertIn("## Unit: U1", evidence)

    def test_work_pass_with_id_selects_named_package_among_multiple(self):
        """Catches pass ignoring --id and operating on candidates[0] (shared
        resolution path with start/fail/recover/revise).

        Uses a second, still-pending unit (U2) so this U1 pass is
        non-terminal and the target package is not archived out from under
        the assertions below.
        """
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            running_state = (
                MINIMAL_STATE
                .replace('"ready"', '"running"')
                .replace('"attempt": 0', '"attempt": 1')
                .replace(
                    '"units": [{"id": "U1", "group": null, "kind": "step", '
                    '"state": "running", "attempt": 1}]',
                    '"units": ['
                    '{"id": "U1", "group": null, "kind": "step", "state": "running", "attempt": 1}, '
                    '{"id": "U2", "group": null, "kind": "step", "state": "pending", "attempt": 0}'
                    ']',
                )
            )
            _make_work_package(project_root, work_id="current")
            target = _make_work_package(project_root, running_state, work_id="fix-next-skill-routing")
            evidence_file = Path(directory) / "ev.md"
            evidence_file.write_text(MINIMAL_EVIDENCE, encoding="utf-8")

            result = run_cli(
                "work", "pass",
                "--id", "fix-next-skill-routing",
                "--unit", "U1",
                "--plan-revision", "1",
                "--evidence-file", str(evidence_file),
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            current = (target / "CURRENT.md").read_text(encoding="utf-8")
            self.assertIn('"passed"', current)

    def test_work_fail_requires_evidence_file(self):
        """Catches fail accepting a transition without evidence."""
        result = run_cli("work", "fail", "--unit", "U1", "--plan-revision", "1")
        self.assertEqual(result.returncode, 2)

    def test_work_fail_transitions_running_unit_to_failed(self):
        """Catches fail not applying the running->failed transition."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            running_state = (
                MINIMAL_STATE
                .replace('"ready"', '"running"')
                .replace('"attempt": 0', '"attempt": 1')
            )
            pkg = _make_work_package(project_root, running_state)
            fail_evidence = (
                "## Unit: U1\n"
                "## Attempt: 1\n"
                "### command\npython -m pytest\n"
                "### pass_fail\nfailed\n"
                "### observed_output\nErrors found.\n"
                "### root_cause\nBug in parser.\n"
            )
            evidence_file = Path(directory) / "ev.md"
            evidence_file.write_text(fail_evidence, encoding="utf-8")

            result = run_cli(
                "work", "fail",
                "--unit", "U1",
                "--plan-revision", "1",
                "--evidence-file", str(evidence_file),
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            current = (pkg / "CURRENT.md").read_text(encoding="utf-8")
            self.assertIn('"failed"', current)

    def test_work_recover_requires_evidence_file(self):
        """Catches recover accepting a transition without evidence."""
        result = run_cli(
            "work", "recover",
            "--unit", "U1",
            "--plan-revision", "1",
            "--event", "retry",
        )
        self.assertEqual(result.returncode, 2)

    def test_work_recover_retry_transitions_failed_unit_to_ready(self):
        """Catches recover not applying the failed->retry->ready transition."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            failed_state = (
                MINIMAL_STATE
                .replace('"ready"', '"failed"')
                .replace('"attempt": 0', '"attempt": 1')
                .replace(
                    '"attempts": []',
                    '"attempts": [{"unit": "U1", "n": 1, "result": "failed",'
                    ' "root_cause_fingerprint": "bug-in-parser", "evidence_ref": null}]',
                )
            )
            pkg = _make_work_package(project_root, failed_state)
            recover_evidence = (
                "## Unit: U1\n"
                "## Attempt: 1\n"
                "### command\npython -m pytest\n"
                "### pass_fail\nfailed\n"
                "### observed_output\nErrors found.\n"
                "### root_cause\nFixed bug.\n"
            )
            evidence_file = Path(directory) / "ev.md"
            evidence_file.write_text(recover_evidence, encoding="utf-8")

            result = run_cli(
                "work", "recover",
                "--unit", "U1",
                "--plan-revision", "1",
                "--event", "retry",
                "--evidence-file", str(evidence_file),
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            current = (pkg / "CURRENT.md").read_text(encoding="utf-8")
            self.assertIn('"ready"', current)

    def test_work_revise_requires_evidence_file(self):
        """Catches revise accepting a plan revision without evidence."""
        result = run_cli("work", "revise", "--plan-revision", "2")
        self.assertEqual(result.returncode, 2)

    def test_work_revise_increments_plan_revision(self):
        """Catches revise not updating plan_revision in the state block."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            pkg = _make_work_package(project_root)
            evidence_file = Path(directory) / "ev.md"
            evidence_file.write_text(
                "## Unit: test-work\n## Attempt: 1\n### command\nreplan\n### pass_fail\npassed\n### observed_output\nOK\n",
                encoding="utf-8",
            )

            result = run_cli(
                "work", "revise",
                "--plan-revision", "2",
                "--evidence-file", str(evidence_file),
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            current = (pkg / "CURRENT.md").read_text(encoding="utf-8")
            import re as _re
            block = _re.search(
                r"<!-- agent-checkpoint:state v1 -->\n(.*?)\n<!-- /agent-checkpoint:state -->",
                current,
                _re.S,
            )
            self.assertIsNotNone(block)
            payload = json.loads(block.group(1))
            self.assertEqual(payload["plan_revision"], 2)

    def test_work_revise_with_id_selects_named_package_among_multiple(self):
        """Catches revise ignoring --id and operating on candidates[0]."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root, work_id="current")
            target = _make_work_package(project_root, work_id="fix-next-skill-routing")
            evidence_file = Path(directory) / "ev.md"
            evidence_file.write_text(
                "## Unit: fix-next-skill-routing\n## Attempt: 1\n### command\nreplan\n"
                "### pass_fail\npassed\n### observed_output\nOK\n",
                encoding="utf-8",
            )

            result = run_cli(
                "work", "revise",
                "--id", "fix-next-skill-routing",
                "--plan-revision", "2",
                "--evidence-file", str(evidence_file),
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            current = (target / "CURRENT.md").read_text(encoding="utf-8")
            self.assertIn('"plan_revision": 2', current)

    def test_work_revise_refuses_wrong_revision(self):
        """Catches revise accepting a non-stored-plus-one revision number."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root)
            evidence_file = Path(directory) / "ev.md"
            evidence_file.write_text(
                "## Unit: test-work\n## Attempt: 1\n### command\nreplan\n### pass_fail\npassed\n### observed_output\nOK\n",
                encoding="utf-8",
            )

            result = run_cli(
                "work", "revise",
                "--plan-revision", "5",
                "--evidence-file", str(evidence_file),
                "--root", str(project_root),
            )

        self.assertEqual(result.returncode, 2)

    def test_work_revise_refuses_while_unit_running(self):
        """Catches revise proceeding while an in-flight session holds state."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            running_state = (
                MINIMAL_STATE
                .replace('"ready"', '"running"')
                .replace('"attempt": 0', '"attempt": 1')
            )
            _make_work_package(project_root, running_state)
            evidence_file = Path(directory) / "ev.md"
            evidence_file.write_text(
                "## Unit: test-work\n## Attempt: 1\n### command\nreplan\n### pass_fail\npassed\n### observed_output\nOK\n",
                encoding="utf-8",
            )

            result = run_cli(
                "work", "revise",
                "--plan-revision", "2",
                "--evidence-file", str(evidence_file),
                "--root", str(project_root),
            )

        self.assertEqual(result.returncode, 2)

    def test_work_pass_stale_revision_exits_two_and_leaves_files_unchanged(self):
        """Regression: stale plan_revision refuses pass and leaves durable files unchanged."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            running_state = (
                MINIMAL_STATE
                .replace('"ready"', '"running"')
                .replace('"attempt": 0', '"attempt": 1')
            )
            pkg = _make_work_package(project_root, running_state)
            before = (pkg / "CURRENT.md").read_bytes()
            evidence_file = Path(directory) / "ev.md"
            evidence_file.write_text(MINIMAL_EVIDENCE, encoding="utf-8")

            result = run_cli(
                "work", "pass",
                "--unit", "U1",
                "--plan-revision", "99",  # stale
                "--evidence-file", str(evidence_file),
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual((pkg / "CURRENT.md").read_bytes(), before)

    def test_work_revise_stale_session_refused_on_next_pass(self):
        """Regression: after revise the old revision is refused on next pass."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root)
            evidence_file = Path(directory) / "ev.md"
            evidence_file.write_text(
                "## Unit: test-work\n## Attempt: 1\n### command\nreplan\n### pass_fail\npassed\n### observed_output\nOK\n",
                encoding="utf-8",
            )
            # First revise: increment plan_revision to 2
            revise = run_cli(
                "work", "revise",
                "--plan-revision", "2",
                "--evidence-file", str(evidence_file),
                "--root", str(project_root),
            )
            self.assertEqual(revise.returncode, 0, revise.stderr)

            # Now start U1 with new revision
            start = run_cli(
                "work", "start",
                "--unit", "U1",
                "--plan-revision", "2",
                "--root", str(project_root),
            )
            self.assertEqual(start.returncode, 0, start.stderr)

            # Stale session uses old revision 1 to pass
            stale_ev = Path(directory) / "stale_ev.md"
            stale_ev.write_text(MINIMAL_EVIDENCE, encoding="utf-8")
            stale_pass = run_cli(
                "work", "pass",
                "--unit", "U1",
                "--plan-revision", "1",  # old revision
                "--evidence-file", str(stale_ev),
                "--root", str(project_root),
            )

            self.assertEqual(stale_pass.returncode, 2)
            self.assertIn("stale", stale_pass.stderr.lower())

    def test_work_migrate_dry_run_exits_zero(self):
        """Catches migrate default blocking instead of running dry-run."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            result = run_cli("work", "migrate", "--root", str(project_root))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dry", result.stderr.lower())

    def test_work_refusal_mentions_checkpoint_evidence(self):
        """Catches missing-evidence refusals not naming checkpoint-evidence."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            running_state = (
                MINIMAL_STATE
                .replace('"ready"', '"running"')
                .replace('"attempt": 0', '"attempt": 1')
            )
            _make_work_package(project_root, running_state)
            # Provide an evidence file with missing sections
            bad_evidence = Path(directory) / "bad.md"
            bad_evidence.write_text("## Unit: U1\n## Attempt: 1\n", encoding="utf-8")

            result = run_cli(
                "work", "pass",
                "--unit", "U1",
                "--plan-revision", "1",
                "--evidence-file", str(bad_evidence),
                "--root", str(project_root),
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("checkpoint-evidence", result.stderr)

    def test_work_status_json_keys_are_sorted(self):
        """Catches work status --json emitting keys in arbitrary order."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            _make_work_package(project_root)

            result = run_cli("work", "status", "--root", str(project_root), "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        raw = result.stdout
        # Extract top-level keys from the JSON output
        payload = json.loads(raw)
        keys = list(payload.keys())
        self.assertEqual(keys, sorted(keys))


class ReviseAtomicWriteTests(unittest.TestCase):
    """Catches work revise bypassing the lock-guarded atomic-write path (R5-I11)."""

    @staticmethod
    def _write_evidence(directory):
        evidence_file = Path(directory) / "ev.md"
        evidence_file.write_text(
            "## Unit: test-work\n## Attempt: 1\n### command\nreplan\n"
            "### pass_fail\npassed\n### observed_output\nOK\n",
            encoding="utf-8",
        )
        return evidence_file

    def test_revise_refuses_symlinked_current_md(self):
        """Catches revise following a symlinked CURRENT.md instead of refusing it."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            pkg = _make_work_package(project_root)
            real_target = project_root / "real-current.md"
            current_path = pkg / "CURRENT.md"
            original = current_path.read_text(encoding="utf-8")
            real_target.write_text(original, encoding="utf-8")
            current_path.unlink()
            try:
                current_path.symlink_to(real_target)
            except OSError as error:
                self.skipTest(f"symlinks unavailable: {error}")
            evidence = self._write_evidence(directory)

            result = run_cli(
                "work", "revise",
                "--plan-revision", "2",
                "--evidence-file", str(evidence),
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(real_target.read_text(encoding="utf-8"), original)

    def test_revise_leaves_current_md_unchanged_on_replace_failure(self):
        """Catches a crash mid-write corrupting or truncating CURRENT.md."""
        from agent_checkpoint import storage as storage_module
        from agent_checkpoint.work_store import revise_plan

        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            pkg = _make_work_package(project_root)
            current_path = pkg / "CURRENT.md"
            original = current_path.read_text(encoding="utf-8")

            with mock.patch.object(
                storage_module.os, "replace", side_effect=OSError("simulated crash")
            ):
                with self.assertRaises(OSError):
                    revise_plan(project_root, current_path, plan_revision=2)

            self.assertEqual(current_path.read_text(encoding="utf-8"), original)
            leaked = [
                p for p in current_path.parent.iterdir()
                if p.name.startswith(".") and p.name != ".agent-checkpoint.lock"
            ]
            self.assertEqual(leaked, [], f"leaked temp files: {leaked}")

    def test_revise_still_increments_plan_revision_end_to_end(self):
        """Regression: the atomic rewrite still performs the same logical update."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            pkg = _make_work_package(project_root)
            evidence = self._write_evidence(directory)

            result = run_cli(
                "work", "revise",
                "--plan-revision", "2",
                "--evidence-file", str(evidence),
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"plan_revision": 2', (pkg / "CURRENT.md").read_text(encoding="utf-8"))

    def test_concurrent_revise_serializes_without_corruption(self):
        """Catches two concurrent revise calls racing past the lock and tearing CURRENT.md."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            pkg = _make_work_package(project_root)
            evidence = self._write_evidence(directory)

            def run_once():
                return run_cli(
                    "work", "revise",
                    "--plan-revision", "2",
                    "--evidence-file", str(evidence),
                    "--root", str(project_root),
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                first, second = [
                    future.result()
                    for future in [pool.submit(run_once), pool.submit(run_once)]
                ]

            codes = sorted([first.returncode, second.returncode])
            self.assertEqual(codes[0], 0, "exactly one revise should succeed")
            self.assertNotEqual(codes[1], 0, "the losing revise should be refused, not corrupt")
            parse_state((pkg / "CURRENT.md").read_text(encoding="utf-8"))


class ArchiveOnCompleteTests(unittest.TestCase):
    """Catches `work pass` failing to auto-archive a terminally-complete package
    (F1: WorkState.is_complete() + archive_completed_package)."""

    def _terminal_package(self, project_root, work_id="test-work"):
        """A single-unit package whose only unit is `running`, so a `pass`
        on it is terminal per WorkState.is_complete()."""
        running_state = (
            MINIMAL_STATE
            .replace('"ready"', '"running"')
            .replace('"attempt": 0', '"attempt": 1')
        )
        return _make_work_package(project_root, running_state, work_id=work_id)

    def _pass(self, project_root, work_id=None, unit="U1"):
        args = ["work", "pass", "--unit", unit, "--plan-revision", "1",
                "--evidence-file", str(project_root / "ev.md"), "--root", str(project_root)]
        if work_id is not None:
            args[2:2] = ["--id", work_id]
        return run_cli(*args)

    def test_terminal_pass_archives_the_package(self):
        """Catches a terminal pass leaving the package at its old work/<id>/ path."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            self._terminal_package(project_root)
            (project_root / "ev.md").write_text(MINIMAL_EVIDENCE, encoding="utf-8")

            result = self._pass(project_root)

            self.assertEqual(result.returncode, 0, result.stderr)
            old_path = project_root / ".agent-checkpoint" / "work" / "test-work"
            self.assertFalse(old_path.exists(), "package left at its pre-archive path")
            archive_dir = project_root / ".agent-checkpoint" / "work" / "archive"
            matches = list(archive_dir.glob("test-work-*"))
            self.assertEqual(len(matches), 1, f"expected exactly one archive dir, got {matches}")
            current = (matches[0] / "CURRENT.md").read_text(encoding="utf-8")
            self.assertIn('"passed"', current)
            evidence = (matches[0] / "EVIDENCE.md").read_text(encoding="utf-8")
            self.assertIn("## Unit: U1", evidence)

    def test_non_terminal_pass_does_not_archive(self):
        """Catches a non-terminal pass (other units still pending) being archived anyway."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            running_state = (
                MINIMAL_STATE
                .replace('"ready"', '"running"')
                .replace('"attempt": 0', '"attempt": 1')
                .replace(
                    '"units": [{"id": "U1", "group": null, "kind": "step", '
                    '"state": "running", "attempt": 1}]',
                    '"units": ['
                    '{"id": "U1", "group": null, "kind": "step", "state": "running", "attempt": 1}, '
                    '{"id": "U2", "group": null, "kind": "step", "state": "pending", "attempt": 0}'
                    ']',
                )
            )
            pkg = _make_work_package(project_root, running_state)
            (project_root / "ev.md").write_text(MINIMAL_EVIDENCE, encoding="utf-8")

            result = self._pass(project_root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(pkg.is_dir(), "non-terminal pass must not archive the package")
            archive_dir = project_root / ".agent-checkpoint" / "work" / "archive"
            self.assertFalse(archive_dir.exists())

    def test_fail_on_would_be_final_unit_does_not_archive(self):
        """Catches a fail event on the last unit being treated as terminal."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            pkg = self._terminal_package(project_root)
            evidence_file = project_root / "ev.md"
            evidence_file.write_text(MINIMAL_EVIDENCE, encoding="utf-8")

            result = run_cli(
                "work", "fail",
                "--unit", "U1",
                "--plan-revision", "1",
                "--evidence-file", str(evidence_file),
                "--root", str(project_root),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(pkg.is_dir(), "fail must never trigger an archive move")
            archive_dir = project_root / ".agent-checkpoint" / "work" / "archive"
            self.assertFalse(archive_dir.exists())

    def test_multi_package_coexistence_only_completed_one_moves(self):
        """Catches a terminal pass on one package sweeping up an unrelated coexisting one."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            self._terminal_package(project_root, work_id="finishing")
            other = _make_work_package(project_root, work_id="other-package")
            (project_root / "ev.md").write_text(MINIMAL_EVIDENCE, encoding="utf-8")

            result = self._pass(project_root, work_id="finishing")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(other.is_dir(), "untouched package must not move")
            archive_dir = project_root / ".agent-checkpoint" / "work" / "archive"
            self.assertEqual(
                [p.name for p in archive_dir.iterdir() if p.is_dir()],
                [p.name for p in archive_dir.iterdir() if p.is_dir() and p.name.startswith("finishing-")],
            )

    def test_destination_collision_is_refused_and_source_left_intact(self):
        """Catches a same-day retried pass merging into or overwriting an existing archive dir."""
        from agent_checkpoint.workflows import archive_completed_package

        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            pkg = self._terminal_package(project_root)
            archive_dir = project_root / ".agent-checkpoint" / "work" / "archive"
            colliding = archive_dir / "test-work-20260822"
            colliding.mkdir(parents=True)
            (colliding / "sentinel.txt").write_text("pre-existing", encoding="utf-8")

            with self.assertRaises(ConfigError):
                archive_completed_package(
                    project_root, "test-work", pkg, date_str="20260822"
                )

            self.assertTrue(pkg.is_dir(), "source must be untouched when the destination collides")
            self.assertEqual(
                (colliding / "sentinel.txt").read_text(encoding="utf-8"), "pre-existing"
            )
            # The un-moved package is still fully functional.
            status = run_cli(
                "work", "status", "--id", "test-work", "--root", str(project_root), "--json",
            )
            self.assertEqual(status.returncode, 0, status.stderr)

    def test_active_pointer_naming_archived_package_is_cleared(self):
        """Catches the active pointer/root CONTINUE_PROMPT.md dangling after archive."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            self._terminal_package(project_root)
            (project_root / "ev.md").write_text(MINIMAL_EVIDENCE, encoding="utf-8")
            write_active_work_id(project_root, "test-work")
            write_root_continue_prompt(project_root, "test-work")

            result = self._pass(project_root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsNone(read_active_work_id(project_root))
            self.assertFalse((project_root / "CONTINUE_PROMPT.md").exists())

    def test_active_pointer_naming_a_different_package_is_untouched(self):
        """Catches an archive move clearing a pointer that names another active package."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            self._terminal_package(project_root, work_id="finishing")
            _make_work_package(project_root, work_id="other-active")
            (project_root / "ev.md").write_text(MINIMAL_EVIDENCE, encoding="utf-8")
            write_active_work_id(project_root, "other-active")
            write_root_continue_prompt(project_root, "other-active")

            result = self._pass(project_root, work_id="finishing")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(read_active_work_id(project_root), "other-active")
            prompt_text = (project_root / "CONTINUE_PROMPT.md").read_text(encoding="utf-8")
            self.assertIn("other-active", prompt_text)


if __name__ == "__main__":
    unittest.main()
