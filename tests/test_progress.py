import json
import unittest

from agent_checkpoint.progress import (
    contains_diff_content,
    parse_progress,
    render_entry,
    validate_entry,
)
from tests.helpers import FIXED_TIME, PROJECT_ROOT, VALID_BODY


class ProgressTests(unittest.TestCase):
    def test_diff_detector_recognizes_indented_structure_not_isolated_prose(self):
        """Catches indentation bypasses without flagging one explanatory line."""
        indented_patch = (
            "    diff --git a/app.py b/app.py\n"
            "    --- a/app.py\n"
            "    +++ b/app.py\n"
            "    @@ -1 +1 @@\n"
            "    -old\n"
            "    +new\n"
        )
        indented_unified = (
            "  --- previous.txt\n"
            "  +++ current.txt\n"
            "  @@ -2 +2 @@\n"
            "  -before\n"
            "  +after\n"
        )

        self.assertTrue(contains_diff_content(indented_patch))
        self.assertTrue(contains_diff_content(indented_unified))
        self.assertFalse(
            contains_diff_content("Example:     diff --git is the command name.\n")
        )
        self.assertFalse(contains_diff_content("    --- a thematic break example\n"))

    def test_diff_detector_recognizes_indented_binary_metadata_sequence(self):
        """Catches indented Git binary diffs without flagging prose mentions."""
        indented_binary_patch = (
            "    diff --git a/logo.png b/logo.png\n"
            "    new file mode 100644\n"
            "    index 0000000..abcd123\n"
            "    Binary files /dev/null and b/logo.png differ\n"
        )
        prose = (
            "    The command name is diff --git.\n"
            "    The phrase 'Binary files old and new differ' can appear in docs.\n"
            "    A note may mention new file mode without being a patch.\n"
        )

        self.assertTrue(contains_diff_content(indented_binary_patch))
        self.assertFalse(contains_diff_content(prose))

    def test_diff_detector_recognizes_indented_git_metadata_only_blocks(self):
        """Catches indented Git metadata-only diffs without rejecting prose."""
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
        prose = (
            "    diff --git is a useful phrase to mention in documentation.\n"
            "    It may discuss mode-only, rename, or binary patch examples.\n"
        )

        for name, patch in cases.items():
            with self.subTest(name=name):
                self.assertTrue(contains_diff_content(patch))
        self.assertFalse(contains_diff_content(prose))

    def test_diff_detector_recognizes_indented_git_headers_with_spaces(self):
        """Catches real Git diff headers whose paths contain spaces."""
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
            "quoted_special_path": (
                '    diff --git "a/quote\\" name.txt" "b/quote\\" name.txt"\n'
                "    index abcd123..fffffff 100644\n"
            ),
        }

        for name, patch in cases.items():
            with self.subTest(name=name):
                self.assertTrue(contains_diff_content(patch))

    def test_diff_detector_allows_indented_git_metadata_prose(self):
        """Catches prose being mistaken for a real diff --git header block."""
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
            with self.subTest(name=name):
                self.assertFalse(contains_diff_content(prose))

    def test_validate_entry_requires_all_sections(self):
        """Catches a validator that accepts an incomplete checkpoint body."""
        body = "## 1. Goal / Plan\n- Build it\n"
        self.assertEqual(
            validate_entry(body),
            [
                "## 2. Progress",
                "## 3. Current Focus",
                "## 4. Next Actions / TODO",
                "## 5. Decisions / Constraints / Notes",
            ],
        )

    def test_parse_and_render_round_trip_preserves_pinned_entry(self):
        """Catches a renderer or parser that loses entry pinning or body text."""
        entry = render_entry(VALID_BODY, FIXED_TIME, pinned=True)
        document = parse_progress("# Project Checkpoints\n\n" + entry)
        self.assertTrue(document.entries[0].pinned)
        self.assertEqual(document.entries[0].body, VALID_BODY)

    def test_schema_requires_every_core_section_when_verification_is_present(self):
        """Catches optional verification weakening the five required headings."""
        schema = json.loads(
            (PROJECT_ROOT / "core/schemas/progress.schema.json").read_text(
                encoding="utf-8"
            )
        )
        sections_schema = schema["properties"]["sections"]
        required = (
            "## 1. Goal / Plan",
            "## 2. Progress",
            "## 3. Current Focus",
            "## 4. Next Actions / TODO",
            "## 5. Decisions / Constraints / Notes",
        )
        verification = "## 6. Verification"

        self.assertTrue(_satisfies_contains_constraints(sections_schema, required))
        self.assertTrue(
            _satisfies_contains_constraints(
                sections_schema, (*required, verification)
            )
        )
        for omitted in required:
            with self.subTest(omitted=omitted):
                candidate = tuple(
                    section for section in required if section != omitted
                ) + (verification,)
                self.assertFalse(
                    _satisfies_contains_constraints(sections_schema, candidate)
                )


def _satisfies_contains_constraints(schema: dict, sections: tuple[str, ...]) -> bool:
    return all(
        constraint.get("contains", {}).get("const") in sections
        for constraint in schema.get("allOf", ())
    )
