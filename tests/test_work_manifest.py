"""Workflow manifest loading and validation tests."""

import unittest

from agent_checkpoint.work_manifest import (
    ManifestError,
    WorkflowManifest,
    load_manifest,
    parse_manifest,
)

VALID = """{
  "schema_version": 1,
  "type": "feature",
  "unit_prefix": "F",
  "grouped": false,
  "max_attempts": 3,
  "hard_rules": ["Understand the system before changing it"],
  "artifacts": {
    "BRIEF.md": "required", "PROJECT_CONTEXT.md": "required",
    "DESIGN.md": "required", "PLAN.md": "required",
    "CURRENT.md": "required", "CONTINUE_PROMPT.md": "required",
    "EVIDENCE.md": "required", "RULES.md": "generated"
  },
  "evidence_required": {
    "step": ["command", "pass_fail", "observed_output"],
    "gate": ["acceptance_criteria", "regression_check", "sign_off"]
  },
  "default_units": ["F1 Foundation", "Feature Gate"]
}
"""


class ParseManifestTests(unittest.TestCase):
    def test_valid_manifest_parses_into_frozen_dataclass(self):
        """Catches a valid manifest being rejected or silently coerced to plain dicts."""
        manifest = parse_manifest(VALID)
        self.assertIsInstance(manifest, WorkflowManifest)
        self.assertEqual(manifest.type, "feature")
        self.assertEqual(manifest.unit_prefix, "F")
        self.assertFalse(manifest.grouped)
        self.assertEqual(manifest.max_attempts, 3)
        self.assertEqual(manifest.artifacts["RULES.md"], "generated")
        self.assertEqual(
            manifest.evidence_required["step"],
            ("command", "pass_fail", "observed_output"),
        )
        self.assertEqual(manifest.default_units, ("F1 Foundation", "Feature Gate"))
        with self.assertRaises(AttributeError):
            manifest.type = "bugfix"  # frozen dataclass

    def test_not_json_raises_manifest_error(self):
        """Catches malformed JSON producing an unhandled JSONDecodeError."""
        with self.assertRaises(ManifestError):
            parse_manifest("{not json")

    def test_missing_required_key_raises_manifest_error(self):
        """Catches a manifest silently missing a required top-level key."""
        text = VALID.replace('"max_attempts": 3,', "")
        with self.assertRaises(ManifestError):
            parse_manifest(text)

    def test_rules_md_must_be_generated(self):
        """Catches RULES.md being declared required/optional instead of generated."""
        text = VALID.replace('"RULES.md": "generated"', '"RULES.md": "required"')
        with self.assertRaises(ManifestError):
            parse_manifest(text)

    def test_always_required_artifact_cannot_be_downgraded(self):
        """Catches CURRENT.md being declared optional, breaking the state authority."""
        text = VALID.replace('"CURRENT.md": "required"', '"CURRENT.md": "optional"')
        with self.assertRaises(ManifestError):
            parse_manifest(text)

    def test_unknown_artifact_policy_raises_manifest_error(self):
        """Catches an invented fifth artifact policy value slipping through."""
        text = VALID.replace('"DESIGN.md": "required"', '"DESIGN.md": "sometimes"')
        with self.assertRaises(ManifestError):
            parse_manifest(text)

    def test_evidence_required_missing_gate_kind_raises(self):
        """Catches a manifest that only declares step evidence, never gate evidence."""
        text = VALID.replace(
            '"gate": ["acceptance_criteria", "regression_check", "sign_off"]', '"gate": []'
        )
        with self.assertRaises(ManifestError):
            parse_manifest(text)

    def test_empty_default_units_raises(self):
        """Catches a manifest declaring zero default units."""
        text = VALID.replace(
            '"default_units": ["F1 Foundation", "Feature Gate"]', '"default_units": []'
        )
        with self.assertRaises(ManifestError):
            parse_manifest(text)


class LoadManifestTests(unittest.TestCase):
    def test_load_manifest_reads_every_bundled_family(self):
        """Catches any one of the ten bundled workflow.json files failing to parse."""
        families = (
            "project", "feature", "bugfix", "refactor", "upgrade",
            "migration", "performance", "integration", "release", "spike",
        )
        for work_type in families:
            with self.subTest(work_type=work_type):
                manifest = load_manifest(work_type)
                self.assertEqual(manifest.type, work_type)
                self.assertEqual(manifest.artifacts["RULES.md"], "generated")

    def test_load_manifest_unknown_type_raises_manifest_error(self):
        """Catches an unbundled work type producing an unhandled FileNotFoundError."""
        with self.assertRaises(ManifestError):
            load_manifest("not-a-real-type")

    def test_project_manifest_matches_family_override_table(self):
        """Catches project losing its AGENTS.md requirement or grouped/PH override."""
        manifest = load_manifest("project")
        self.assertTrue(manifest.grouped)
        self.assertEqual(manifest.unit_prefix, "PH")
        self.assertEqual(manifest.artifacts["AGENTS.md"], "required")

    def test_bugfix_manifest_matches_family_override_table(self):
        """Catches bugfix losing its BUG.md requirement or DESIGN.md downgrade."""
        manifest = load_manifest("bugfix")
        self.assertEqual(manifest.artifacts["BUG.md"], "required")
        self.assertEqual(manifest.artifacts["DESIGN.md"], "optional")

    def test_spike_manifest_matches_family_override_table(self):
        """Catches spike losing its DECISION_RECORD.md requirement or DESIGN.md omission."""
        manifest = load_manifest("spike")
        self.assertEqual(manifest.artifacts["DECISION_RECORD.md"], "required")
        self.assertEqual(manifest.artifacts["DESIGN.md"], "omitted")

    def test_performance_manifest_matches_spec_gate_evidence(self):
        """Catches performance's gate evidence drifting from the design-spec example."""
        manifest = load_manifest("performance")
        self.assertEqual(
            manifest.evidence_required["gate"],
            ("before_measurement", "after_measurement", "correctness_regression"),
        )


if __name__ == "__main__":
    unittest.main()
