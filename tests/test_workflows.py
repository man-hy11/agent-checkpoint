"""Workflow-template materialization tests."""

from pathlib import Path
import tempfile
import unittest

from agent_checkpoint.workflows import initialize_workflow


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
