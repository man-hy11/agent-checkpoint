"""npm wrapper package tests."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.helpers import PROJECT_ROOT


class NpmPackageTests(unittest.TestCase):
    def test_package_excludes_python_cache_artifacts(self):
        """Catches an npm allowlist leaking ignored Python bytecode."""
        packed = subprocess.run(
            ["npm", "pack", "--dry-run", "--json"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(packed.returncode, 0, packed.stderr)
        names = [item["path"] for item in json.loads(packed.stdout)[0]["files"]]
        self.assertFalse(any("/__pycache__/" in name for name in names))
        self.assertFalse(any(name.endswith((".pyc", ".pyo", ".pyd")) for name in names))

    def test_package_exposes_cli_wrapper_and_bundles_python_core(self):
        """Catches an npx package that cannot run outside the repository checkout."""
        package = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))

        self.assertEqual(package["name"], "agent-checkpoint")
        self.assertEqual(package["bin"]["agent-checkpoint"], "bin/agent-checkpoint.cjs")
        result = subprocess.run(
            ["node", PROJECT_ROOT / package["bin"]["agent-checkpoint"], "--help"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("workflow", result.stdout)

    def test_packed_tarball_runs_through_npx_outside_checkout(self):
        """Catches package file-list omissions that source-tree wrapper tests miss."""
        with tempfile.TemporaryDirectory() as temporary:
            packed = subprocess.run(
                ["npm", "pack", "--pack-destination", temporary, "--json"],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(packed.returncode, 0, packed.stderr)
            tarball = Path(temporary) / json.loads(packed.stdout)[0]["filename"]
            result = subprocess.run(
                ["npx", "--yes", "--package", str(tarball), "agent-checkpoint", "--help"],
                cwd=temporary,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("skill-install", result.stdout)

    def test_package_declares_postinstall_skill_install(self):
        """Catches npm installs that do not auto-link the global skill directory."""
        package = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))
        scripts = package.get("scripts", {})
        self.assertIn("postinstall", scripts, "package.json missing scripts.postinstall")
        self.assertIn("postinstall-skill-install.cjs", scripts["postinstall"])
        files = package.get("files", [])
        self.assertIn("bin/postinstall-skill-install.cjs", files)

    def test_postinstall_skill_install_handles_existing_skill(self):
        """Catches postinstall that fails when ~/.agent/skills/checkpoint already exists."""
        import os
        with tempfile.TemporaryDirectory() as fake_home:
            skill_path = Path(fake_home) / ".agent" / "skills" / "checkpoint"
            skill_path.mkdir(parents=True)
            sentinel = skill_path / "sentinel.txt"
            sentinel.write_text("do-not-overwrite", encoding="utf-8")
            env = os.environ.copy()
            env["HOME"] = fake_home
            completed = subprocess.run(
                ["node", str(PROJECT_ROOT / "bin" / "postinstall-skill-install.cjs")],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                completed.returncode, 0,
                f"postinstall failed for existing skill: {completed.stderr}",
            )
            self.assertTrue(skill_path.is_dir())
            self.assertTrue(sentinel.exists(), "existing skill contents must be preserved")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "do-not-overwrite")
