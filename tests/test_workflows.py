"""Workflow-template materialization tests."""

from pathlib import Path
import tempfile
import unittest

from agent_checkpoint.work_manifest import load_manifest
from agent_checkpoint.workflows import initialize_workflow, render_final_workflow

_FAMILIES = (
    "project", "feature", "bugfix", "refactor", "upgrade",
    "migration", "performance", "integration", "release", "spike",
)


class WorkflowTests(unittest.TestCase):
    def test_initialize_feature_materializes_selected_template_and_pointer(self):
        """Catches a checkpoint workflow depending on the source sibling directory."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            result = initialize_workflow(root, "feature", "current")

            self.assertEqual(result.work_type, "feature")
            self.assertEqual(result.work_id, "current")
            self.assertTrue((result.path / "templates" / "CURRENT_TEMPLATE.md").is_file())
            self.assertTrue((result.path / "prompts" / "CONTINUE_PROMPT.md").is_file())
            self.assertTrue((result.path / "shared" / "EXECUTION_RULES.md").is_file())
            self.assertFalse((result.path / "bugfix").exists())
            self.assertIn("feature", result.progress_entry)
            self.assertIn(".agent-checkpoint/work/current", result.progress_entry)

    def test_initialize_project_materializes_missing_entrypoint_template(self):
        """Catches project type missing templates/CURRENT_TEMPLATE.md (OSError regression)."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            result = initialize_workflow(root, "project", "current")

            self.assertEqual(result.work_type, "project")
            self.assertEqual(result.work_id, "current")
            self.assertTrue((result.path / "templates" / "CURRENT_TEMPLATE.md").is_file())
            self.assertTrue((result.path / "CURRENT.md").is_file())
            self.assertTrue((result.path / "prompts" / "CONTINUE_PROMPT.md").is_file())
            self.assertTrue((result.path / "shared" / "EXECUTION_RULES.md").is_file())
            self.assertIn("project", result.progress_entry)


class RenderFinalWorkflowTests(unittest.TestCase):
    def test_render_final_workflow_produces_final_only_package_for_every_family(self):
        """Catches R5-I5's manifest-driven renderer diverging from workflows.py's entrypoint."""
        for work_type in _FAMILIES:
            with self.subTest(work_type=work_type):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)

                    result = render_final_workflow(root, work_type, "current")

                    self.assertEqual(result.work_type, work_type)
                    self.assertTrue((result.path / "RULES.md").is_file())
                    self.assertFalse((result.path / "templates").exists())
                    self.assertFalse((result.path / "prompts").exists())
                    self.assertFalse((result.path / "shared").exists())
                    manifest = load_manifest(work_type)
                    for name, policy in manifest.artifacts.items():
                        if policy != "omitted":
                            self.assertTrue((result.path / name).is_file(), name)

    def test_legacy_initialize_workflow_is_unaffected_by_the_new_renderer(self):
        """Catches the new renderer's import breaking the still-supported legacy copy path."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            legacy = initialize_workflow(root, "feature", "legacy")

            self.assertTrue((legacy.path / "templates" / "CURRENT_TEMPLATE.md").is_file())
            self.assertTrue((legacy.path / "shared" / "EXECUTION_RULES.md").is_file())
