#!/usr/bin/env python3
"""Validate the twelve-skill progressive-disclosure suite structure.

Usage:
    python3 tools/validate_skills.py skills
"""

import sys
from pathlib import Path

EXPECTED_SKILLS = (
    "checkpoint",
    "checkpoint-brainstorm",
    "checkpoint-claim",
    "checkpoint-diagnose",
    "checkpoint-evidence",
    "checkpoint-execute",
    "checkpoint-handoff",
    "checkpoint-inspect",
    "checkpoint-plan",
    "checkpoint-recover",
    "checkpoint-save",
    "checkpoint-select-workflow",
    "checkpoint-verify-gate",
)


def validate(skills_root: Path) -> list[str]:
    errors: list[str] = []
    for name in EXPECTED_SKILLS:
        skill_dir = skills_root / name
        if not skill_dir.is_dir():
            errors.append(f"MISSING directory: {skill_dir}")
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"MISSING SKILL.md: {skill_md}")
            continue
        text = skill_md.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            errors.append(f"{name}: SKILL.md missing frontmatter")
            continue
        try:
            end = text.index("\n---\n", 4)
        except ValueError:
            errors.append(f"{name}: SKILL.md frontmatter not closed")
            continue
        block = text[4:end]
        fm: dict[str, str] = {}
        for line in block.splitlines():
            if ": " in line:
                k, _, v = line.partition(": ")
                fm[k.strip()] = v.strip()
        if fm.get("name") != name:
            errors.append(f"{name}: frontmatter name mismatch: got {fm.get('name')!r}")
        if "description" not in fm or len(fm["description"]) < 10:
            errors.append(f"{name}: missing or too-short description")
        extra = set(fm.keys()) - {"name", "description"}
        if extra:
            errors.append(f"{name}: unexpected frontmatter keys: {extra}")

    shared = skills_root / "_checkpoint-shared"
    if not shared.is_dir():
        errors.append("MISSING _checkpoint-shared directory")
    elif not (shared / "chain-v1.md").is_file():
        errors.append("MISSING _checkpoint-shared/chain-v1.md")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} SKILLS_ROOT", file=sys.stderr)
        return 2
    skills_root = Path(sys.argv[1])
    if not skills_root.is_dir():
        print(f"Not a directory: {skills_root}", file=sys.stderr)
        return 2
    errors = validate(skills_root)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print(f"OK — {len(EXPECTED_SKILLS)} skills valid, _checkpoint-shared present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
