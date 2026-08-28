import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
from types import SimpleNamespace
import unittest
from unittest import mock

from agent_checkpoint.config import ConfigError, ProjectConfig
from agent_checkpoint.progress import parse_progress
from agent_checkpoint import storage
from agent_checkpoint.storage import (
    CheckpointStore,
    LockTimeout,
    SecretDetected,
    ValidationError,
)
from tests.helpers import VALID_BODY


if os.name == "posix":
    import fcntl


def _body(label: str, padding: int = 0) -> str:
    return f"""## 1. Goal / Plan
- {label} goal

## 2. Progress
- {label} progress

## 3. Current Focus
- {label} focus

## 4. Next Actions / TODO
- {label} next

## 5. Decisions / Constraints / Notes
- {label} notes{'x' * padding}
"""


OTHER_VALID_BODY = _body("Other")
THIRD_VALID_BODY = _body("Third")


def _make_store(
    project_root: Path,
    *,
    max_live_chars: int = 12_000,
    lock_timeout_seconds: float = 2.0,
) -> CheckpointStore:
    return CheckpointStore(
        project_root,
        ProjectConfig(
            max_live_chars=max_live_chars,
            lock_timeout_seconds=lock_timeout_seconds,
        ),
    )


def _wait_for_path(path: Path, timeout_seconds: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while not path.exists():
        if time.monotonic() >= deadline:
            raise AssertionError(f"Timed out waiting for handshake file: {path.name}")
        time.sleep(0.01)


class StorageTests(unittest.TestCase):
    def test_store_resolves_safe_nested_paths_beneath_project(self):
        """Catches storage retaining ambiguous relative destination paths."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            config = ProjectConfig(
                progress_path=Path("state/PROGRESS.md"),
                archive_path=Path("state/PROGRESS_ARCHIVE.md"),
            )

            store = CheckpointStore(project_root, config)

            self.assertEqual(
                store.progress_path, (project_root / "state/PROGRESS.md").resolve()
            )
            self.assertEqual(
                store.archive_path,
                (project_root / "state/PROGRESS_ARCHIVE.md").resolve(),
            )

    def test_store_rejects_manually_constructed_escaping_config(self):
        """Catches callers bypassing load_config and escaping project containment."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory) / "project"
            project_root.mkdir()
            outside = project_root.parent / "outside.md"

            with self.assertRaises(ConfigError):
                CheckpointStore(
                    project_root,
                    ProjectConfig(progress_path=Path("../outside.md")),
                )

            self.assertFalse(outside.exists())

    def test_write_rejects_parent_replaced_by_symlink_after_store_creation(self):
        """Catches cached validation allowing a later parent-link escape."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project_root = base / "project"
            project_root.mkdir()
            safe_parent = project_root / "state"
            safe_parent.mkdir()
            external = base / "external"
            external.mkdir()
            config = ProjectConfig(
                progress_path=Path("state/PROGRESS.md"),
                archive_path=Path("state/PROGRESS_ARCHIVE.md"),
            )
            store = CheckpointStore(project_root, config)
            safe_parent.rmdir()
            try:
                safe_parent.symlink_to(external, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with self.assertRaisesRegex(ConfigError, "symlink"):
                store.write(VALID_BODY)

            self.assertEqual(list(external.iterdir()), [])

    def test_write_rejects_regular_file_parent_without_nameerror(self):
        """Catches safe-path errors raising NameError instead of ConfigError."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            (project_root / "state").write_text("not a directory\n", encoding="utf-8")
            store = CheckpointStore(
                project_root,
                ProjectConfig(progress_path=Path("state/PROGRESS.md")),
            )

            with self.assertRaisesRegex(ConfigError, "not a directory"):
                store.write(VALID_BODY)

            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_write_rejects_private_key_without_echoing_value(self):
        """Catches secret persistence and candidate-value leakage in diagnostics."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            store = _make_store(project_root)
            marker = "-----BEGIN " + "PRIVATE KEY-----"
            candidate_fragment = "sensi" + "tive-material"

            with self.assertRaisesRegex(SecretDetected, "private key") as raised:
                store.write(VALID_BODY + "\n" + marker + "\n" + candidate_fragment)

            self.assertNotIn(candidate_fragment, str(raised.exception))
            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_write_rejects_invalid_body_without_creating_progress(self):
        """Catches writing a checkpoint before required-section validation."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            with self.assertRaises(ValidationError):
                _make_store(project_root).write("## 1. Goal / Plan\n- incomplete\n")

            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_write_checks_explicit_verification_for_secrets(self):
        """Catches bypassing the guard through explicitly supplied verification text."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            candidate = "gh" + "p_" + ("v" * 24)

            with self.assertRaises(SecretDetected):
                _make_store(project_root).write(VALID_BODY, verification=(candidate,))

            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_write_rejects_sensitive_assignment_with_attached_hash_value(self):
        """Catches treating an attached hash-prefixed value as a comment."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            assignment = "password=" + "#" + "production-value"

            with self.assertRaises(SecretDetected):
                _make_store(project_root).write(VALID_BODY + "\n" + assignment)

            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_write_rejects_reserved_separator_before_persisting(self):
        """Catches successful writes that cannot be parsed back as one entry."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)

            with self.assertRaises(ValidationError):
                _make_store(project_root).write(VALID_BODY + "\n---\n")

            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_write_rejects_git_diff_shaped_body_before_persisting(self):
        """Catches a write path that stores patch content before resume screening."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            patch = "diff --git a/app.py b/app.py\n@@ -1 +1 @@\n-old\n+new\n"

            with self.assertRaisesRegex(ValidationError, "diff-shaped"):
                _make_store(project_root).write(VALID_BODY + "\n" + patch)

            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_write_rejects_indented_binary_diff_before_persisting(self):
        """Catches indented binary/metadata patches bypassing storage validation."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            patch = (
                "    diff --git a/logo.png b/logo.png\n"
                "    new file mode 100644\n"
                "    index 0000000..abcd123\n"
                "    Binary files /dev/null and b/logo.png differ\n"
            )

            with self.assertRaisesRegex(ValidationError, "diff-shaped"):
                _make_store(project_root).write(VALID_BODY + "\n" + patch)

            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_write_rejects_indented_git_metadata_only_blocks(self):
        """Catches metadata-only Git diff blocks being persisted."""
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

                with self.assertRaisesRegex(ValidationError, "diff-shaped"):
                    _make_store(project_root).write(VALID_BODY + "\n" + patch)

                self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_write_rejects_indented_git_headers_with_spaces(self):
        """Catches real Git diff headers with spaces being persisted."""
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

                with self.assertRaisesRegex(ValidationError, "diff-shaped"):
                    _make_store(project_root).write(VALID_BODY + "\n" + patch)

                self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_write_allows_indented_git_metadata_prose(self):
        """Catches prose mentioning Git metadata being rejected as a diff."""
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

                _make_store(project_root).write(VALID_BODY + "\n" + prose)

                progress = (project_root / "PROGRESS.md").read_text(encoding="utf-8")
                self.assertIn(prose, progress)

    def test_write_rejects_diff_shaped_existing_live_document(self):
        """Catches modifying an already unsafe live document."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            progress_path = project_root / "PROGRESS.md"
            progress_path.write_text(
                "# Project Checkpoints\n\ndiff --git a/file b/file\n",
                encoding="utf-8",
            )
            before = progress_path.read_bytes()

            with self.assertRaisesRegex(ValidationError, "diff-shaped"):
                _make_store(project_root).write(VALID_BODY)

            self.assertEqual(progress_path.read_bytes(), before)

    def test_rotation_rejects_diff_shaped_existing_archive(self):
        """Catches appending to an unsafe archive during live-file rotation."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            seed_store = _make_store(project_root)
            seed_store.write(_body("Existing", padding=300))
            progress_path = project_root / "PROGRESS.md"
            archive_path = project_root / "PROGRESS_ARCHIVE.md"
            archive_path.write_text(
                "# Project Checkpoint Archive\n\n--- old\n+++ new\n@@ -1 +1 @@\n",
                encoding="utf-8",
            )
            progress_before = progress_path.read_bytes()
            archive_before = archive_path.read_bytes()

            with self.assertRaisesRegex(ValidationError, "diff-shaped"):
                _make_store(project_root, max_live_chars=1_000).write(
                    _body("Incoming", padding=300)
                )

            self.assertEqual(progress_path.read_bytes(), progress_before)
            self.assertEqual(archive_path.read_bytes(), archive_before)

    def test_write_rejects_diff_shaped_archive_even_without_rotation(self):
        """Catches unsafe stored archives being ignored until the live budget fills."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            archive_path = project_root / "PROGRESS_ARCHIVE.md"
            archive_path.write_text(
                "# Project Checkpoint Archive\n\ndiff --git a/file b/file\n",
                encoding="utf-8",
            )
            before = archive_path.read_bytes()

            with self.assertRaisesRegex(ValidationError, "diff-shaped"):
                _make_store(project_root).write(VALID_BODY)

            self.assertEqual(archive_path.read_bytes(), before)
            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_invalid_existing_document_does_not_leak_parser_detail(self):
        """Catches value-bearing parser causes appearing in formatted tracebacks."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            marker = "private-input-marker"
            (project_root / "PROGRESS.md").write_text(
                "# Project Checkpoints\n\n## " + marker + "\n", encoding="utf-8"
            )

            with self.assertRaises(ValidationError) as raised:
                _make_store(project_root).write(VALID_BODY)

            formatted = "".join(
                traceback.format_exception(
                    type(raised.exception),
                    raised.exception,
                    raised.exception.__traceback__,
                )
            )
            self.assertNotIn(marker, formatted)

    def test_invalid_existing_encoding_raises_sanitized_validation_error(self):
        """Catches leaking decoder details or bypassing document validation."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            (project_root / "PROGRESS.md").write_bytes(b"\xff")

            with self.assertRaises(ValidationError) as raised:
                _make_store(project_root).write(VALID_BODY)

            self.assertTrue(raised.exception.__suppress_context__)

    def test_two_writer_processes_do_not_lose_entries(self):
        """Catches locking only the final replace instead of the read-modify-write cycle."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            first_read = project_root / "first-read"
            release_first = project_root / "release-first"
            second_attempt = project_root / "second-attempt"
            program = """
import sys
import time
from pathlib import Path
from agent_checkpoint.config import ProjectConfig
from agent_checkpoint import storage
from agent_checkpoint.storage import CheckpointStore
role = sys.argv[3]
first_read = Path(sys.argv[4])
release_first = Path(sys.argv[5])
second_attempt = Path(sys.argv[6])
real_read = CheckpointStore._read_document
real_acquire = storage._acquire_lock
def controlled_read(self, *args, **kwargs):
    document = real_read(self, *args, **kwargs)
    if role == "first":
        first_read.write_text("ready", encoding="utf-8")
        while not release_first.exists():
            time.sleep(0.01)
    return document
def announcing_acquire(lock_file, timeout_seconds):
    if role == "second":
        second_attempt.write_text("attempting", encoding="utf-8")
    return real_acquire(lock_file, timeout_seconds)
CheckpointStore._read_document = controlled_read
storage._acquire_lock = announcing_acquire
CheckpointStore(Path(sys.argv[1]), ProjectConfig()).write(sys.argv[2])
"""
            base_command = [sys.executable, "-c", program, str(project_root)]
            common_args = [str(first_read), str(release_first), str(second_attempt)]
            process_options = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "env": {**os.environ, "PYTHONPATH": "."},
                "cwd": Path(__file__).resolve().parents[1],
            }
            first_process = subprocess.Popen(
                [*base_command, VALID_BODY, "first", *common_args],
                **process_options,
            )
            _wait_for_path(first_read)
            second_process = subprocess.Popen(
                [*base_command, OTHER_VALID_BODY, "second", *common_args],
                **process_options,
            )
            _wait_for_path(second_attempt)
            release_first.write_text("release", encoding="utf-8")
            processes = [first_process, second_process]
            exit_codes = [process.wait(timeout=10) for process in processes]
            document = parse_progress(
                (project_root / "PROGRESS.md").read_text(encoding="utf-8")
            )

            self.assertEqual(exit_codes, [0, 0])
            self.assertEqual(len(document.entries), 2)
            self.assertEqual(
                {entry.body for entry in document.entries},
                {VALID_BODY, OTHER_VALID_BODY},
            )

    def test_rotation_keeps_pinned_and_archives_oldest_ordinary_entry(self):
        """Catches pin eviction or archiving the newest ordinary entry first."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            store = _make_store(project_root, max_live_chars=1_200)
            store.write(_body("Pinned", padding=260), pinned=True)
            store.write(_body("Oldest ordinary", padding=260))
            store.write(_body("Newest ordinary", padding=260))

            live_text = (project_root / "PROGRESS.md").read_text(encoding="utf-8")
            archive_text = (project_root / "PROGRESS_ARCHIVE.md").read_text(
                encoding="utf-8"
            )

            self.assertIn("[PINNED]", live_text)
            self.assertIn("Newest ordinary", live_text)
            self.assertNotIn("Oldest ordinary", live_text)
            self.assertIn("Oldest ordinary", archive_text)
            self.assertNotIn("Newest ordinary", archive_text)

            store.write(_body("Fourth ordinary", padding=260))
            appended_archive = (project_root / "PROGRESS_ARCHIVE.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Oldest ordinary", appended_archive)
            self.assertIn("Newest ordinary", appended_archive)

    def test_public_rotate_archives_an_over_budget_existing_document(self):
        """Catches a public rotate method that does not apply the live budget."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            progress_path = project_root / "PROGRESS.md"
            seed = _make_store(project_root, max_live_chars=12_000)
            seed.write(_body("Older", padding=300))
            seed.write(_body("Newer", padding=300))

            _make_store(project_root, max_live_chars=1_000).rotate()

            self.assertLessEqual(
                len(progress_path.read_text(encoding="utf-8")), 1_000
            )
            self.assertTrue((project_root / "PROGRESS_ARCHIVE.md").exists())

    @unittest.skipUnless(os.name == "posix", "POSIX flock behavior")
    def test_write_times_out_while_another_owner_holds_lock(self):
        """Catches blocking indefinitely or writing without owning the lock."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            lock_path = project_root / ".agent-checkpoint.lock"
            with lock_path.open("a+b") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                with self.assertRaises(LockTimeout):
                    _make_store(
                        project_root, lock_timeout_seconds=0.05
                    ).write(VALID_BODY)

            self.assertFalse((project_root / "PROGRESS.md").exists())

    def test_windows_backend_uses_one_byte_nonblocking_lock(self):
        """Catches an msvcrt branch that locks no byte or uses blocking mode."""
        calls = []
        fake_msvcrt = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2)

        def record_locking(file_descriptor, mode, byte_count):
            calls.append((file_descriptor, mode, byte_count))

        fake_msvcrt.locking = record_locking
        with tempfile.TemporaryFile(mode="w+b") as lock_file:
            with mock.patch.object(storage.os, "name", "nt"), mock.patch.object(
                storage, "msvcrt", fake_msvcrt, create=True
            ):
                storage._ensure_lock_byte(lock_file)
                storage._acquire_lock(lock_file, 0.0)
                storage._release_lock(lock_file)
                lock_file.seek(0, os.SEEK_END)
                size = lock_file.tell()

        self.assertEqual(size, 1)
        self.assertEqual([call[1:] for call in calls], [(1, 1), (2, 1)])

    def test_failed_replace_preserves_previous_progress(self):
        """Catches truncating or deleting the destination before atomic replacement."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            store = _make_store(project_root)
            store.write(VALID_BODY)
            progress_path = project_root / "PROGRESS.md"
            before = progress_path.read_bytes()

            with mock.patch.object(
                storage.os, "replace", side_effect=OSError("replace failed")
            ):
                with self.assertRaises(OSError):
                    store.write(OTHER_VALID_BODY)

            self.assertEqual(progress_path.read_bytes(), before)
            self.assertEqual(
                list(project_root.glob(".agent-checkpoint-*.tmp")), []
            )

    def test_second_replace_failure_restores_progress_and_archive(self):
        """Catches partial rotation when progress replacement fails after archival."""
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            store = _make_store(project_root, max_live_chars=1_200)
            store.write(_body("Pinned", padding=260), pinned=True)
            store.write(_body("First ordinary", padding=260))
            store.write(_body("Second ordinary", padding=260))
            progress_path = project_root / "PROGRESS.md"
            archive_path = project_root / "PROGRESS_ARCHIVE.md"
            progress_before = progress_path.read_bytes()
            archive_before = archive_path.read_bytes()
            real_replace = os.replace
            replace_calls = 0

            def fail_second_replace(source, destination, *args, **kwargs):
                nonlocal replace_calls
                replace_calls += 1
                if replace_calls == 2:
                    raise OSError("replace failed")
                return real_replace(source, destination, *args, **kwargs)

            with mock.patch.object(storage.os, "replace", fail_second_replace):
                with self.assertRaises(OSError):
                    store.write(_body("Third ordinary", padding=260))

            self.assertEqual(progress_path.read_bytes(), progress_before)
            self.assertEqual(archive_path.read_bytes(), archive_before)
            self.assertEqual(
                list(project_root.glob(".agent-checkpoint-*.tmp")), []
            )

            store.write(_body("Third ordinary", padding=260))
            archive_after_retry = parse_progress(
                archive_path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                sum(
                    "Second ordinary" in entry.body
                    for entry in archive_after_retry.entries
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
