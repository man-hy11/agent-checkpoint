"""package.json is a version source, not an npm distribution manifest.

npm publishing is retired: the published package is deprecated, and the
supported install paths are the Claude Code plugin bundle and the community
``skills`` CLI (``npx skills add``), which clones the repository. package.json
survives only because ``hosts.toml`` names it as ``version_source`` and
``tools/build_adapter.py`` reads every generated manifest's version from it.
"""

import json
from pathlib import Path
import unittest

from tests.helpers import PROJECT_ROOT


class PackageManifestTests(unittest.TestCase):
    def _package(self) -> dict:
        return json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))

    def test_manifest_supplies_the_version_host_bundles_project(self):
        """Catches a package.json that no longer satisfies build_adapter's version read."""
        version = self._package().get("version")
        self.assertIsInstance(version, str, "package.json must declare a string version")
        self.assertTrue(version, "package.json must declare a non-empty version")

    def test_manifest_stays_unpublishable(self):
        """Catches npm distribution being revived by accident.

        ``private`` is what makes ``npm publish`` refuse outright; the
        distribution fields are what a publish would act on. Neither belongs
        here while the plugin bundle and ``npx skills add`` are the supported
        install paths.
        """
        package = self._package()
        self.assertIs(
            package.get("private"), True,
            "package.json must set private:true so npm publish refuses",
        )
        for field in ("files", "bin", "scripts"):
            self.assertNotIn(
                field, package,
                f"package.json must not declare {field!r}: npm distribution is retired",
            )

    def test_npm_only_launchers_stay_removed(self):
        """Catches the npm bin wrapper or postinstall helper coming back.

        Host bundles ship the Python launcher (bin/agent-checkpoint) directly;
        the .cjs wrappers existed solely to serve `npm install`'s bin field.
        """
        for name in ("agent-checkpoint.cjs", "postinstall-skill-install.cjs"):
            self.assertFalse(
                (PROJECT_ROOT / "bin" / name).exists(),
                f"bin/{name} is an npm-only artifact and must stay removed",
            )
        self.assertFalse(
            (PROJECT_ROOT / ".npmignore").exists(),
            ".npmignore is an npm-only artifact and must stay removed",
        )

    def test_python_launcher_remains_the_shipped_entry_point(self):
        """Catches the launcher every install path depends on going missing."""
        launcher = PROJECT_ROOT / "bin" / "agent-checkpoint"
        self.assertTrue(launcher.is_file(), "bin/agent-checkpoint must exist")


if __name__ == "__main__":
    unittest.main()
