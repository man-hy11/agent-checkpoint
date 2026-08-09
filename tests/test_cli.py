import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools import install as install_tool
from tests.helpers import CORE_ROOT, PROJECT_ROOT, VALID_BODY, run_cli


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
            progress = (project_root / "PROGRESS.md").read_text(encoding="utf-8")
            self.assertIn("Workflow type: feature", progress)
            self.assertIn(".agent-checkpoint/work/current/CURRENT.md", progress)

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
                self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_write_regular_file_parent_exits_two_without_traceback(self):
        """Catches handled storage path errors escaping as NameError tracebacks."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            (project_root / "state").write_text("not a directory\n", encoding="utf-8")
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
            self.assertFalse((project_root / "PROGRESS.md").exists())

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
                self.assertFalse((project_root / "PROGRESS.md").exists())

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
                self.assertFalse((project_root / "PROGRESS.md").exists())

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

                result = run_cli(
                    "write",
                    "--root",
                    str(project_root),
                    "--entry",
                    "-",
                    input_text=VALID_BODY + "\n" + prose,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                progress = (project_root / "PROGRESS.md").read_text(encoding="utf-8")
                self.assertIn(prose, progress)

    def test_write_validate_resume_handoff_status_and_doctor_streams(self):
        """Catches command routing, flags, or stdout/stderr contracts drifting."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
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
            progress = (project_root / "PROGRESS.md").read_text(encoding="utf-8")
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
            progress = (project_root / "PROGRESS.md").read_text(encoding="utf-8")
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
                self.assertFalse((project_root / "PROGRESS.md").exists())

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
            self.assertTrue((project_root / "PROGRESS.md").is_file())

    @unittest.skipUnless(os.name == "posix", "POSIX flock behavior")
    def test_lock_timeout_exits_four_without_writing(self):
        """Catches lock contention being flattened into invalid input or I/O."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            (project_root / ".agent-checkpoint.toml").write_text(
                "lock_timeout_seconds = 0\n", encoding="utf-8"
            )
            lock_path = project_root / ".agent-checkpoint.lock"
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
            self.assertFalse((project_root / "PROGRESS.md").exists())

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


class InstallerTests(unittest.TestCase):
    def _run_installer(self, *arguments: str, home: Path) -> subprocess.CompletedProcess:
        environment = os.environ.copy()
        environment["HOME"] = str(home)
        environment.pop("PYTHONPATH", None)
        return subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "tools" / "install.py"), *arguments],
            cwd=PROJECT_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def _make_owned_looking_symlink_destinations(self, base: Path):
        prefix = base / "prefix"
        external_package = base / "external-package"
        external_launcher = base / "external-launcher"
        external_payload = external_package / "agent_checkpoint" / "sentinel.txt"
        external_payload.parent.mkdir(parents=True)
        external_payload.write_text("external package", encoding="utf-8")
        (external_package / ".agent-checkpoint-install").write_text(
            "agent-checkpoint portable CLI\n", encoding="utf-8"
        )
        external_launcher.write_text(
            "#!/usr/bin/env python3\n# agent-checkpoint portable launcher\n"
            "print('external launcher')\n",
            encoding="utf-8",
        )
        package_destination = prefix / "share" / "agent-checkpoint"
        launcher_destination = prefix / "bin" / "agent-checkpoint"
        package_destination.parent.mkdir(parents=True)
        launcher_destination.parent.mkdir(parents=True)
        try:
            package_destination.symlink_to(external_package, target_is_directory=True)
            launcher_destination.symlink_to(external_launcher)
        except (NotImplementedError, OSError) as error:
            self.skipTest(f"symlinks unavailable: {error}")
        return (
            prefix,
            package_destination,
            launcher_destination,
            external_payload,
            external_launcher,
        )

    def test_no_prefix_only_recommends_user_paths_and_never_edits_shell_rc(self):
        """Catches the no-prefix path silently installing or editing shell startup."""
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            result = self._run_installer(home=home)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(home / ".local" / "share" / "agent-checkpoint"), result.stdout)
            self.assertIn(str(home / ".local" / "bin"), result.stdout)
            self.assertFalse((home / ".bashrc").exists())
            self.assertFalse((home / ".zshrc").exists())
            self.assertFalse((home / ".local").exists())

    def test_prefix_install_is_runnable_and_agent_owned_destination_is_updatable(self):
        """Catches a non-relocatable install or refusal to refresh its own marker."""
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            prefix = Path(directory) / "prefix"

            first = self._run_installer("--prefix", str(prefix), home=home)
            second = self._run_installer("--prefix", str(prefix), home=home)
            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)
            launched = subprocess.run(
                [sys.executable, str(prefix / "bin" / "agent-checkpoint"), "--help"],
                cwd=home.parent,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertTrue(
                (prefix / "share" / "agent-checkpoint" / "agent_checkpoint" / "cli.py").is_file()
            )
            self.assertTrue((prefix / "share" / "agent-checkpoint" / ".agent-checkpoint-install").is_file())
            self.assertTrue((prefix / "bin" / "agent-checkpoint").is_file())
            self.assertEqual(launched.returncode, 0, launched.stderr)
            for command in ALL_COMMANDS:
                self.assertIn(command, launched.stdout)

    def test_failed_owned_refresh_preserves_previous_installation(self):
        """Catches deleting the installed package before replacement is staged."""
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "prefix"
            install_tool._install(prefix, force=False)
            package = prefix / "share" / "agent-checkpoint" / "agent_checkpoint"
            marker = prefix / "share" / "agent-checkpoint" / ".agent-checkpoint-install"
            launcher = prefix / "bin" / "agent-checkpoint"
            package_before = sorted(path.relative_to(package) for path in package.rglob("*"))
            marker_before = marker.read_text(encoding="utf-8")
            launcher_before = launcher.read_bytes()

            with mock.patch.object(
                install_tool.shutil,
                "copytree",
                side_effect=OSError("copy failed"),
            ):
                with self.assertRaises(OSError):
                    install_tool._install(prefix, force=False)

            self.assertTrue(package.is_dir())
            self.assertEqual(
                sorted(path.relative_to(package) for path in package.rglob("*")),
                package_before,
            )
            self.assertEqual(marker.read_text(encoding="utf-8"), marker_before)
            self.assertEqual(launcher.read_bytes(), launcher_before)
            self.assertEqual(
                list((prefix / "share").glob(".agent-checkpoint-package-*")),
                [],
            )

    def test_prefix_refuses_foreign_destination_unless_force_is_explicit(self):
        """Catches the installer overwriting unrelated files without authorization."""
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            prefix = Path(directory) / "prefix"
            package_destination = prefix / "share" / "agent-checkpoint"
            package_destination.mkdir(parents=True)
            foreign_file = package_destination / "keep.txt"
            foreign_file.write_text("foreign", encoding="utf-8")

            refused = self._run_installer("--prefix", str(prefix), home=home)
            preserved_after_refusal = foreign_file.read_text(encoding="utf-8")
            forced = self._run_installer(
                "--prefix", str(prefix), "--force", home=home
            )

            self.assertEqual(refused.returncode, 2)
            self.assertEqual(preserved_after_refusal, "foreign")
            self.assertIn("refus", refused.stderr.lower())
            self.assertEqual(forced.returncode, 0, forced.stderr)
            self.assertFalse(foreign_file.exists())
            self.assertTrue((package_destination / ".agent-checkpoint-install").is_file())

    def test_symlink_destinations_are_refused_without_touching_external_targets(self):
        """Catches owned-looking symlinks bypassing refusal and mutating their targets."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home = base / "home"
            (
                prefix,
                package_destination,
                launcher_destination,
                external_payload,
                external_launcher,
            ) = self._make_owned_looking_symlink_destinations(base)
            launcher_before = external_launcher.read_bytes()

            result = self._run_installer("--prefix", str(prefix), home=home)

            self.assertEqual(result.returncode, 2)
            self.assertTrue(package_destination.is_symlink())
            self.assertTrue(launcher_destination.is_symlink())
            self.assertEqual(
                external_payload.read_text(encoding="utf-8"), "external package"
            )
            self.assertEqual(external_launcher.read_bytes(), launcher_before)

    def test_installer_rejects_symlinked_prefix_share_and_bin_ancestors(self):
        """Catches installation escaping through a linked destination ancestor."""
        for linked_component in ("prefix", "share", "bin"):
            with self.subTest(component=linked_component), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                home = base / "home"
                external = base / f"external-{linked_component}"
                external.mkdir()
                sentinel = external / "preserve-me"
                sentinel.write_text("unchanged", encoding="utf-8")
                prefix = base / "prefix"
                try:
                    if linked_component == "prefix":
                        prefix.symlink_to(external, target_is_directory=True)
                    else:
                        prefix.mkdir()
                        (prefix / linked_component).symlink_to(
                            external, target_is_directory=True
                        )
                except (NotImplementedError, OSError) as error:
                    self.skipTest(f"symlinks unavailable: {error}")

                result = self._run_installer(
                    "--prefix", str(prefix), "--force", home=home
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn("symlink", result.stderr.lower())
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged")
                self.assertFalse((external / "agent-checkpoint").exists())

    def test_force_unlinks_destination_symlinks_without_touching_external_targets(self):
        """Catches force following links instead of replacing the links themselves."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home = base / "home"
            (
                prefix,
                package_destination,
                launcher_destination,
                external_payload,
                external_launcher,
            ) = self._make_owned_looking_symlink_destinations(base)
            launcher_before = external_launcher.read_bytes()

            result = self._run_installer(
                "--prefix", str(prefix), "--force", home=home
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(package_destination.is_symlink())
            self.assertTrue(package_destination.is_dir())
            self.assertFalse(launcher_destination.is_symlink())
            self.assertTrue(launcher_destination.is_file())
            self.assertEqual(
                external_payload.read_text(encoding="utf-8"), "external package"
            )
            self.assertEqual(external_launcher.read_bytes(), launcher_before)

    def test_refusal_does_not_echo_credential_shaped_prefix(self):
        """Catches a safe refusal leaking credential-shaped destination metadata."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home = base / "home"
            candidate = "gh" + "p_" + ("p" * 24)
            prefix = base / candidate
            package_destination = prefix / "share" / "agent-checkpoint"
            package_destination.mkdir(parents=True)
            (package_destination / "foreign.txt").write_text(
                "foreign", encoding="utf-8"
            )

            result = self._run_installer("--prefix", str(prefix), home=home)

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertNotIn(candidate, result.stderr)
            self.assertIn("refus", result.stderr.lower())

    def test_installed_launcher_prefers_share_package_over_prefix_shadow(self):
        """Catches a foreign prefix package shadowing the installed share package."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home = base / "home"
            prefix = base / "prefix"
            installed = self._run_installer("--prefix", str(prefix), home=home)
            shadow_package = prefix / "agent_checkpoint"
            shadow_package.mkdir()
            (shadow_package / "__init__.py").write_text("", encoding="utf-8")
            (shadow_package / "cli.py").write_text(
                "def main():\n    print('foreign-shadow')\n    return 91\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)

            launched = subprocess.run(
                [sys.executable, str(prefix / "bin" / "agent-checkpoint"), "--help"],
                cwd=base,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(installed.returncode, 0, installed.stderr)
            self.assertEqual(launched.returncode, 0, launched.stderr)
            self.assertNotIn("foreign-shadow", launched.stdout)
            for command in ALL_COMMANDS:
                self.assertIn(command, launched.stdout)

    def test_force_replaces_foreign_launcher_directory_at_exact_target(self):
        """Catches force copying inside a foreign launcher directory instead of replacing it."""
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            prefix = Path(directory) / "prefix"
            launcher_destination = prefix / "bin" / "agent-checkpoint"
            launcher_destination.mkdir(parents=True)
            foreign_file = launcher_destination / "keep.txt"
            foreign_file.write_text("foreign", encoding="utf-8")

            refused = self._run_installer("--prefix", str(prefix), home=home)
            preserved_after_refusal = foreign_file.read_text(encoding="utf-8")
            forced = self._run_installer(
                "--prefix", str(prefix), "--force", home=home
            )

            self.assertEqual(refused.returncode, 2)
            self.assertEqual(preserved_after_refusal, "foreign")
            self.assertEqual(forced.returncode, 0, forced.stderr)
            self.assertTrue(launcher_destination.is_file())
            self.assertFalse(foreign_file.exists())


if __name__ == "__main__":
    unittest.main()
