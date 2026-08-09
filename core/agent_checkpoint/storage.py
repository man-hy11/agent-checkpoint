"""Locked, atomic persistence and rotation for checkpoint documents."""

from collections.abc import Callable, Iterable
from contextlib import contextmanager
from datetime import datetime, timezone
import errno
import os
from pathlib import Path
import re
import time
from typing import BinaryIO, Iterator, NamedTuple
import uuid

from .config import ConfigError, ProjectConfig, resolve_checkpoint_paths
from .models import CheckpointEntry, ProgressDocument
from .progress import (
    contains_diff_content,
    contains_line_boundary,
    parse_progress,
    render_entry,
    validate_entry,
)
from .secrets import find_secret_kind


if os.name == "nt":  # pragma: no cover - exercised on Windows
    import msvcrt
else:  # pragma: no branch - exactly one platform implementation is imported
    import fcntl


class SecretDetected(ValueError):
    """Raised when input contains a probable credential."""


class ValidationError(ValueError):
    """Raised when checkpoint input or an existing document is invalid."""


class LockTimeout(TimeoutError):
    """Raised when the checkpoint lock cannot be acquired before its deadline."""


_VERIFICATION_HEADING = re.compile(r"(?m)^## 6\. Verification\s*$")


class CheckpointStore:
    """Persist checkpoint entries beneath one configured project root."""

    def __init__(
        self,
        project_root: Path,
        config: ProjectConfig | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config or ProjectConfig()
        (
            self.project_root,
            self.progress_path,
            self.archive_path,
        ) = resolve_checkpoint_paths(project_root, self.config)
        self.lock_path = self.progress_path.parent / ".agent-checkpoint.lock"
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def write(
        self,
        body: str,
        pinned: bool = False,
        verification: Iterable[str] = (),
    ) -> Path:
        """Validate and prepend an entry, rotating old ordinary entries as needed."""
        self._revalidate_paths()
        prepared_body = _prepare_body(body, verification)
        secret_kind = find_secret_kind(prepared_body)
        if secret_kind is not None:
            raise SecretDetected(
                f"Probable {secret_kind} detected; checkpoint was not written"
            )
        if contains_diff_content(prepared_body):
            raise ValidationError("Checkpoint contains diff-shaped content")
        missing_sections = validate_entry(prepared_body)
        if missing_sections:
            raise ValidationError(
                "Checkpoint is missing required section(s): "
                + ", ".join(missing_sections)
            )
        if re.search(r"(?m)^---\s*$", prepared_body):
            raise ValidationError("Checkpoint body contains a reserved separator line")

        with self._lock():
            document = self._read_document(self.progress_path)
            self._reject_existing_secret(document)
            created_at = self._clock()
            entry = CheckpointEntry(
                heading=_entry_heading(created_at, pinned),
                body=prepared_body,
                pinned=pinned,
                created_at=created_at,
            )
            updated = ProgressDocument(
                entries=[entry, *document.entries], header=document.header
            )
            self._persist_rotated(updated)
        return self.progress_path

    def rotate(self) -> None:
        """Move over-budget ordinary entries to the configured archive."""
        self._revalidate_paths()
        with self._lock():
            document = self._read_document(self.progress_path)
            self._reject_existing_secret(document)
            self._persist_rotated(document)

    def _persist_rotated(self, document: ProgressDocument) -> None:
        self._revalidate_paths()
        retained, evicted = _partition_for_live_budget(
            document, self.config.max_live_chars
        )
        archive = self._read_document(
            self.archive_path, default_header="# Project Checkpoint Archive"
        )
        self._reject_existing_secret(archive)
        if evicted:
            archived = ProgressDocument(
                entries=[*archive.entries, *evicted], header=archive.header
            )
            self._atomic_write_pair(
                self.archive_path,
                _render_document(archived),
                self.progress_path,
                _render_document(retained),
            )
        else:
            self._atomic_write(self.progress_path, _render_document(retained))

    def _read_document(
        self, path: Path, *, default_header: str = "# Project Checkpoints"
    ) -> ProgressDocument:
        self._revalidate_paths()
        try:
            text = _read_text_no_follow(self.project_root, path)
        except FileNotFoundError:
            return ProgressDocument(entries=[], header=default_header)
        except UnicodeError:
            raise ValidationError("Existing checkpoint document is invalid") from None
        secret_kind = find_secret_kind(text)
        if secret_kind is not None:
            raise SecretDetected(
                f"Probable {secret_kind} detected; checkpoint was not written"
            )
        if contains_diff_content(text):
            raise ValidationError(
                "Existing checkpoint document contains diff-shaped content"
            )
        try:
            return parse_progress(text)
        except ValueError:
            raise ValidationError("Existing checkpoint document is invalid") from None

    @staticmethod
    def _reject_existing_secret(document: ProgressDocument) -> None:
        for entry in document.entries:
            secret_kind = find_secret_kind(entry.body)
            if secret_kind is not None:
                raise SecretDetected(
                    f"Probable {secret_kind} detected; checkpoint was not written"
                )

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self._revalidate_paths()
        with _open_safe_parent(
            self.project_root, self.lock_path, create=True
        ) as lock_parent:
            descriptor = _open_at(
                lock_parent,
                self.lock_path.name,
                os.O_RDWR | os.O_CREAT | os.O_APPEND,
                0o600,
            )
            with os.fdopen(descriptor, "a+b") as lock_file:
                _ensure_lock_byte(lock_file)
                _acquire_lock(lock_file, self.config.lock_timeout_seconds)
                try:
                    self._revalidate_paths()
                    yield
                finally:
                    _release_lock(lock_file)

    def _revalidate_paths(self) -> None:
        """Reject path swaps made after construction before each filesystem step."""
        root, progress_path, archive_path = resolve_checkpoint_paths(
            self.project_root, self.config
        )
        if (
            root != self.project_root
            or progress_path != self.progress_path
            or archive_path != self.archive_path
        ):
            raise ValidationError("Checkpoint paths changed after initialization")

    def _atomic_write(self, path: Path, text: str) -> None:
        self._revalidate_paths()
        _atomic_write(self.project_root, path, text)

    def _atomic_write_pair(
        self,
        first_path: Path,
        first_text: str,
        second_path: Path,
        second_text: str,
    ) -> None:
        self._revalidate_paths()
        _atomic_write_pair(
            self.project_root,
            first_path,
            first_text,
            second_path,
            second_text,
        )


def _prepare_body(body: str, verification: Iterable[str]) -> str:
    if not isinstance(body, str):
        raise ValidationError("Checkpoint body must be text")
    if isinstance(verification, str):
        raise ValidationError("Verification results must be a sequence of text values")
    try:
        results = tuple(verification)
    except TypeError as error:
        raise ValidationError(
            "Verification results must be a sequence of text values"
        ) from error
    if any(not isinstance(result, str) for result in results):
        raise ValidationError("Verification results must be text values")
    if any(contains_line_boundary(result) for result in results):
        raise ValidationError("Verification results must each be a single line")
    verification_headings = list(_VERIFICATION_HEADING.finditer(body))
    if len(verification_headings) > 1:
        raise ValidationError("Checkpoint contains duplicate verification sections")
    if not results:
        return body
    rendered_results = "".join(f"- {result}\n" for result in results)
    if verification_headings:
        section_start = verification_headings[0].end()
        next_heading = re.search(r"(?m)^##\s", body[section_start:])
        insertion = (
            len(body)
            if next_heading is None
            else section_start + next_heading.start()
        )
        prefix = body[:insertion].rstrip("\n")
        suffix = body[insertion:].lstrip("\n")
        separator = "\n" if suffix else ""
        return f"{prefix}\n{rendered_results}{separator}{suffix}"
    body_with_newline = body if body.endswith("\n") else body + "\n"
    return f"{body_with_newline}\n## 6. Verification\n{rendered_results}"


def _entry_heading(created_at: datetime, pinned: bool) -> str:
    pin_marker = " [PINNED]" if pinned else ""
    return f"## Checkpoint{pin_marker} {created_at.isoformat()}"


def _render_document(document: ProgressDocument) -> str:
    if not document.entries:
        return document.header + "\n"
    entries = "".join(
        render_entry(entry.body, entry.created_at, entry.pinned)
        for entry in document.entries
    )
    return f"{document.header}\n\n{entries}"


def _partition_for_live_budget(
    document: ProgressDocument, max_live_chars: int
) -> tuple[ProgressDocument, list[CheckpointEntry]]:
    if len(_render_document(document)) <= max_live_chars:
        return document, []

    retained_ids = {id(entry) for entry in document.entries if entry.pinned}
    ordinary_entries = [entry for entry in document.entries if not entry.pinned]
    evicted: list[CheckpointEntry] = []
    for index, entry in enumerate(ordinary_entries):
        candidate_ids = retained_ids | {id(entry)}
        candidate = ProgressDocument(
            entries=[
                item for item in document.entries if id(item) in candidate_ids
            ],
            header=document.header,
        )
        if len(_render_document(candidate)) <= max_live_chars:
            retained_ids.add(id(entry))
            continue
        evicted.extend(ordinary_entries[index:])
        break

    retained = ProgressDocument(
        entries=[entry for entry in document.entries if id(entry) in retained_ids],
        header=document.header,
    )
    return retained, evicted


def _atomic_write(root: Path, path: Path, text: str) -> None:
    with _open_safe_parent(root, path, create=True) as parent:
        temporary_name = _stage_text_at(parent, text)
        try:
            _replace_at(parent, temporary_name, parent.name)
            temporary_name = None
        finally:
            if temporary_name is not None:
                _unlink_if_exists_at(parent, temporary_name)


def _atomic_write_pair(
    root: Path,
    first_path: Path,
    first_text: str,
    second_path: Path,
    second_text: str,
) -> None:
    with _open_safe_parent(root, first_path, create=True) as first_parent:
        with _open_safe_parent(root, second_path, create=True) as second_parent:
            _atomic_write_pair_at(
                first_parent,
                first_text,
                second_parent,
                second_text,
            )


def _atomic_write_pair_at(
    first_parent: "_SafeParent",
    first_text: str,
    second_parent: "_SafeParent",
    second_text: str,
) -> None:
    first_temporary = _stage_text_at(first_parent, first_text)
    second_temporary: str | None = None
    backup_temporary: str | None = None
    first_existed = _exists_at(first_parent, first_parent.name)
    try:
        second_temporary = _stage_text_at(second_parent, second_text)
        if first_existed:
            backup_temporary = _stage_bytes_at(
                first_parent, _read_bytes_at(first_parent, first_parent.name)
            )
        _replace_at(first_parent, first_temporary, first_parent.name)
        first_temporary = None
        try:
            _replace_at(second_parent, second_temporary, second_parent.name)
            second_temporary = None
        except OSError:
            try:
                if first_existed:
                    _replace_at(first_parent, backup_temporary, first_parent.name)
                    backup_temporary = None
                else:
                    _unlink_if_exists_at(first_parent, first_parent.name)
            except OSError as rollback_error:
                raise OSError("Checkpoint rollback failed") from rollback_error
            raise
    finally:
        for parent, temporary_name in (
            (first_parent, first_temporary),
            (second_parent, second_temporary),
            (first_parent, backup_temporary),
        ):
            if temporary_name is not None:
                _unlink_if_exists_at(parent, temporary_name)


def _read_text_no_follow(root: Path, path: Path) -> str:
    with _open_safe_parent(root, path, create=False) as parent:
        descriptor = _open_at(parent, parent.name, os.O_RDONLY)
        with os.fdopen(descriptor, "r", encoding="utf-8") as file:
            return file.read()


class _SafeParent(NamedTuple):
    fd: int | None
    directory: Path
    name: str


@contextmanager
def _open_safe_parent(
    root: Path, path: Path, *, create: bool
) -> Iterator[_SafeParent]:
    if not _supports_dir_fd():
        if create:
            path.parent.mkdir(parents=True, exist_ok=True)
        yield _SafeParent(None, path.parent, path.name)
        return

    try:
        relative_path = path.relative_to(root)
    except ValueError:
        raise ConfigError("Checkpoint path must remain within the project") from None

    opened_fds: list[int] = []
    try:
        current_fd = _open_directory_no_follow(root)
        opened_fds.append(current_fd)
        current_path = root
        for component in relative_path.parent.parts:
            if component in ("", "."):
                continue
            try:
                next_fd = os.open(
                    component,
                    _directory_open_flags(),
                    dir_fd=current_fd,
                )
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(component, 0o700, dir_fd=current_fd)
                next_fd = os.open(
                    component,
                    _directory_open_flags(),
                    dir_fd=current_fd,
                )
            except NotADirectoryError:
                raise ConfigError(
                    "Checkpoint path parent is not a directory"
                ) from None
            except OSError as error:
                if error.errno == errno.ELOOP:
                    raise ConfigError(
                        "Checkpoint path contains a symlinked path component"
                    ) from None
                raise
            opened_fds.append(next_fd)
            current_fd = next_fd
            current_path /= component
        yield _SafeParent(current_fd, current_path, path.name)
    finally:
        for descriptor in reversed(opened_fds):
            os.close(descriptor)


def _supports_dir_fd() -> bool:
    return (
        os.name != "nt"
        and os.open in os.supports_dir_fd
        and os.mkdir in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
        and os.unlink in os.supports_dir_fd
        and os.rename in os.supports_dir_fd
    )


def _directory_open_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _file_open_flags(flags: int) -> int:
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _open_directory_no_follow(path: Path) -> int:
    try:
        return os.open(path, _directory_open_flags())
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise ConfigError(
                "Checkpoint path contains a symlinked path component"
            ) from None
        raise


def _open_at(parent: _SafeParent, name: str, flags: int, mode: int = 0o600) -> int:
    try:
        if parent.fd is None:
            return os.open(parent.directory / name, _file_open_flags(flags), mode)
        return os.open(name, _file_open_flags(flags), mode, dir_fd=parent.fd)
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise ConfigError("Checkpoint file must not be a symlink") from None
        raise


def _stage_text_at(parent: _SafeParent, text: str) -> str:
    return _stage_bytes_at(parent, text.encode("utf-8"))


def _stage_bytes_at(parent: _SafeParent, content: bytes) -> str:
    temporary_name = ""
    for _ in range(100):
        candidate = f".agent-checkpoint-{uuid.uuid4().hex}.tmp"
        try:
            descriptor = _open_at(
                parent,
                candidate,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            continue
        temporary_name = candidate
        break
    if not temporary_name:
        raise OSError("Could not allocate checkpoint temporary file")
    try:
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
    except BaseException:
        _unlink_if_exists_at(parent, temporary_name)
        raise
    return temporary_name


def _read_bytes_at(parent: _SafeParent, name: str) -> bytes:
    descriptor = _open_at(parent, name, os.O_RDONLY)
    with os.fdopen(descriptor, "rb") as file:
        return file.read()


def _exists_at(parent: _SafeParent, name: str) -> bool:
    try:
        if parent.fd is None:
            (parent.directory / name).lstat()
        else:
            os.stat(name, dir_fd=parent.fd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False


def _replace_at(parent: _SafeParent, source: str | None, destination: str) -> None:
    if source is None:
        raise OSError("Missing checkpoint rollback file")
    if parent.fd is None:
        os.replace(parent.directory / source, parent.directory / destination)
    else:
        os.replace(source, destination, src_dir_fd=parent.fd, dst_dir_fd=parent.fd)


def _unlink_if_exists_at(parent: _SafeParent, name: str) -> None:
    try:
        if parent.fd is None:
            (parent.directory / name).unlink()
        else:
            os.unlink(name, dir_fd=parent.fd)
    except FileNotFoundError:
        pass


def _ensure_lock_byte(lock_file: BinaryIO) -> None:
    if os.name != "nt":
        return
    lock_file.seek(0, os.SEEK_END)
    if lock_file.tell() == 0:
        lock_file.write(b"\0")
        lock_file.flush()


def _acquire_lock(lock_file: BinaryIO, timeout_seconds: float) -> None:
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while True:
        try:
            if os.name == "nt":  # pragma: no cover - exercised on Windows
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except OSError as error:
            if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise
            if time.monotonic() >= deadline:
                raise LockTimeout("Timed out waiting for checkpoint lock") from None
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))


def _release_lock(lock_file: BinaryIO) -> None:
    if os.name == "nt":  # pragma: no cover - exercised on Windows
        lock_file.seek(0)
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
