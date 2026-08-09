"""Data models for checkpoint progress documents."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CheckpointEntry:
    heading: str
    body: str
    pinned: bool
    created_at: datetime


@dataclass(frozen=True)
class ProgressDocument:
    entries: list[CheckpointEntry]
    header: str = "# Project Checkpoints"
