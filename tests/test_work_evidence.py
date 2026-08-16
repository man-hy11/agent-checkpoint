"""Evidence adequacy tests."""

import unittest

from agent_checkpoint.work_evidence import (
    MAX_EVIDENCE_CHARS,
    parse_evidence,
    validate_evidence,
)

REQUIRED = ("command", "pass_fail", "observed_output")

ADEQUATE = """## Unit: P3
## Attempt: 2

### command
`PYTHONPATH=core python3 -m unittest tests.test_work_state -v`

### pass_fail
PASS

### observed_output
Ran 14 tests in 0.412s
OK
"""


class ParseTests(unittest.TestCase):
    def test_parse_reads_unit_attempt_and_sections(self):
        """Catches evidence being stored without unit or attempt attribution."""
        document = parse_evidence(ADEQUATE)

        self.assertEqual(document.unit, "P3")
        self.assertEqual(document.attempt, 2)
        self.assertIn("command", document.sections)
        self.assertIn("OK", document.sections["observed_output"])


class ValidateTests(unittest.TestCase):
    def test_adequate_evidence_returns_no_unmet_requirements(self):
        """Catches a validator rejecting evidence that satisfies the contract."""
        self.assertEqual(validate_evidence(ADEQUATE, unit_id="P3", required=REQUIRED), ())

    def test_missing_section_is_reported(self):
        """Catches a unit passing without recording what was actually run."""
        text = ADEQUATE.replace(
            "### command\n`PYTHONPATH=core python3 -m unittest tests.test_work_state -v`\n\n",
            "",
        )

        unmet = validate_evidence(text, unit_id="P3", required=REQUIRED)

        self.assertIn("command", unmet)

    def test_empty_section_is_reported(self):
        """Catches a heading being added with no observed result beneath it."""
        text = ADEQUATE.replace("Ran 14 tests in 0.412s\nOK\n", "\n")

        unmet = validate_evidence(text, unit_id="P3", required=REQUIRED)

        self.assertIn("observed_output", unmet)

    def test_wrong_unit_attribution_is_reported(self):
        """Catches evidence from one unit being used to pass another."""
        unmet = validate_evidence(ADEQUATE, unit_id="P4", required=REQUIRED)

        self.assertIn("unit_attribution", unmet)

    def test_credential_shaped_content_is_reported(self):
        """Catches a token pasted into evidence being persisted."""
        text = ADEQUATE + "\n### note\nghp_" + "a" * 36 + "\n"

        unmet = validate_evidence(text, unit_id="P3", required=REQUIRED)

        self.assertIn("secret_detected", unmet)

    def test_diff_shaped_content_is_reported(self):
        """Catches source diffs being smuggled into durable evidence."""
        text = ADEQUATE + "\n### note\n--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n"

        unmet = validate_evidence(text, unit_id="P3", required=REQUIRED)

        self.assertIn("diff_content", unmet)

    def test_oversized_evidence_is_reported(self):
        """Catches an unbounded transcript being written into EVIDENCE.md."""
        text = ADEQUATE + "\n### note\n" + ("x" * MAX_EVIDENCE_CHARS)

        unmet = validate_evidence(text, unit_id="P3", required=REQUIRED)

        self.assertIn("length", unmet)

    def test_gate_requirements_differ_from_step_requirements(self):
        """Catches gate evidence being accepted against step requirements."""
        gate_required = ("before_measurement", "after_measurement", "correctness_regression")

        unmet = validate_evidence(ADEQUATE, unit_id="P3", required=gate_required)

        self.assertEqual(
            set(unmet),
            {"before_measurement", "after_measurement", "correctness_regression"},
        )


if __name__ == "__main__":
    unittest.main()
