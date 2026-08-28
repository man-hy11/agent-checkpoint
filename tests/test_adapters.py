import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

from tests.helpers import PROJECT_ROOT, VALID_BODY


def run_tool(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run an adapter tool through its public command-line interface."""
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def build_bundle(adapter: str, directory: Path) -> Path:
    output = directory / adapter
    result = run_tool("tools/build_adapter.py", adapter, "--output", str(output))
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return output


def run_hook(
    bundle: Path, hook: str, payload: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run a bundled hook without access to the repository's Python package."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "CLAUDE_PLUGIN_ROOT"}
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, bundle / "hooks" / hook],
        cwd=payload["cwd"],
        env=environment,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def activate_work_package(project: Path, work_id: str = "current") -> Path:
    """Create a work package and point the active pointer at it.

    Since R3, ``write`` (and the read commands) resolve the live checkpoint
    through ``.agent-checkpoint/active``; a valid checkpoint therefore lives at
    ``.agent-checkpoint/work/<id>/PROGRESS.md`` rather than the project root.
    """
    package = project / ".agent-checkpoint" / "work" / work_id
    package.mkdir(parents=True, exist_ok=True)
    (project / ".agent-checkpoint" / "active").write_text(
        work_id + "\n", encoding="utf-8"
    )
    return package


def scoped_progress(project: Path, work_id: str = "current") -> Path:
    return project / ".agent-checkpoint" / "work" / work_id / "PROGRESS.md"


def write_valid_checkpoint(
    bundle: Path, project: Path, body: str = VALID_BODY
) -> None:
    """Write one valid checkpoint through the bundle's public launcher."""
    activate_work_package(project)
    result = subprocess.run(
        [
            bundle / "bin" / "agent-checkpoint",
            "write",
            "--root",
            str(project),
            "--entry",
            "-",
        ],
        cwd=project,
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
        input=body,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)


class ClaudeAdapterTests(unittest.TestCase):
    def test_claude_bundle_exposes_manifest_command_and_native_hook_paths(self):
        """Catches a bundle whose Claude components are absent or undiscoverable."""
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle("claude-code", Path(directory))

            manifest = json.loads(
                (bundle / ".claude-plugin" / "plugin.json").read_text(
                    encoding="utf-8"
                )
            )
            command = (bundle / "commands" / "checkpoint.md").read_text(
                encoding="utf-8"
            )
            hook_config = json.loads(
                (bundle / "hooks" / "hooks.json").read_text(encoding="utf-8")
            )

            self.assertEqual(manifest["name"], "agent-checkpoint")
            self.assertIn(
                '"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" write --entry -',
                command,
            )
            resume_command = bundle / "commands" / "resume.md"
            handoff_command = bundle / "commands" / "handoff.md"
            self.assertTrue(resume_command.is_file())
            self.assertTrue(handoff_command.is_file())
            self.assertIn(
                '"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" resume',
                resume_command.read_text(encoding="utf-8"),
            )
            self.assertIn(
                '"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" handoff',
                handoff_command.read_text(encoding="utf-8"),
            )
            hooks = hook_config["hooks"]
            self.assertEqual(set(hooks), {"PreCompact", "SessionStart"})
            expected_paths = {
                "PreCompact": "hooks/pre_compact.py",
                "SessionStart": "hooks/session_start.py",
            }
            for event, relative_path in expected_paths.items():
                registration = hooks[event][0]["hooks"][0]
                self.assertEqual(registration["type"], "command")
                self.assertEqual(registration["command"], "python3")
                self.assertEqual(
                    registration["args"],
                    [f"${{CLAUDE_PLUGIN_ROOT}}/{relative_path}"],
                )
                self.assertTrue((bundle / relative_path).is_file())

    def test_claude_precompact_blocks_when_no_active_work_package(self):
        """R3: a bootstrap write needs an active work package; on a fresh project
        the hook can no longer silently persist to a project-root PROGRESS.md.

        Since R3 relocated PROGRESS.md into ``.agent-checkpoint/work/<id>/`` and
        made ``write`` refuse when no active pointer is set (no silent global
        fallback), the PreCompact bootstrap write fails and the hook blocks
        compaction — the same safety path as an ordinary initial-write failure.
        Teaching the hook to establish a default work package first is adapter
        runtime work outside R3's config/storage/cli scope; tracked for the
        adapter update pass after R4 (root pointer) and R6 (doc/adapter sweep).
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            bundle = build_bundle("claude-code", root)
            payload = {"cwd": str(project), "session_id": "s1"}

            first = run_hook(bundle, "pre_compact.py", payload)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stderr, "")
            output = json.loads(first.stdout)
            self.assertEqual(output["decision"], "block")
            self.assertIn("could not be written", output["reason"])
            self.assertFalse((project / "PROGRESS.md").exists())
            self.assertFalse((project / ".claude").exists())

    def test_claude_precompact_allows_when_checkpoint_exists(self):
        """Catches a hook blocking without consulting the bundled status command."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            bundle = build_bundle("claude-code", root)
            write_valid_checkpoint(bundle, project)

            result = run_hook(
                bundle,
                "pre_compact.py",
                {"cwd": str(project), "session_id": "checkpoint-present"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")
            # The active checkpoint lives inside the work package; the hook must
            # neither create a root-level PROGRESS.md nor a bootstrap entry.
            self.assertFalse((project / "PROGRESS.md").exists())

    def test_claude_precompact_keeps_existing_checkpoint_unchanged(self):
        """Catches bootstrap writes mutating an existing project checkpoint."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            bundle = build_bundle("claude-code", root)
            write_valid_checkpoint(bundle, project)
            progress_path = scoped_progress(project)
            before = progress_path.read_text(encoding="utf-8")

            result = run_hook(
                bundle,
                "pre_compact.py",
                {"cwd": str(project), "session_id": "checkpoint-stable"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")
            self.assertEqual(progress_path.read_text(encoding="utf-8"), before)

    def test_claude_precompact_blocks_when_initial_write_fails(self):
        """Catches compaction continuing after an automatic checkpoint write failure."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            bundle = build_bundle("claude-code", root)
            launcher = bundle / "bin" / "agent-checkpoint"
            launcher.write_text(
                "import json, sys\n"
                "if sys.argv[1] == 'status':\n"
                "    print(json.dumps({'checkpoint_exists': False}))\n"
                "    raise SystemExit(0)\n"
                "raise SystemExit(5)\n",
                encoding="utf-8",
            )

            result = run_hook(
                bundle,
                "pre_compact.py",
                {"cwd": str(project), "session_id": "write-failure"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(output["decision"], "block")
            self.assertIn("could not be written", output["reason"])
            self.assertFalse((project / "PROGRESS.md").exists())

    def test_claude_session_start_skips_clear_and_stays_silent_without_root_continue_prompt(
        self,
    ):
        """R6: session_start reads the repo-root CONTINUE_PROMPT.md, the current
        pointer contract (R4) established after R3 relocated checkpoints under
        ``.agent-checkpoint/work/<id>/``. With no root CONTINUE_PROMPT.md present
        (no active package), startup guidance is empty.

        ``clear``/``resume`` sources stay silent (unchanged guard). ``startup``
        only emits guidance once a root CONTINUE_PROMPT.md exists.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            bundle = build_bundle("claude-code", root)
            write_valid_checkpoint(bundle, project)

            clear = run_hook(
                bundle,
                "session_start.py",
                {"cwd": str(project), "source": "clear"},
            )
            resumed = run_hook(
                bundle,
                "session_start.py",
                {"cwd": str(project), "source": "resume"},
            )
            start = run_hook(
                bundle,
                "session_start.py",
                {"cwd": str(project), "source": "startup"},
            )

            self.assertEqual(clear.returncode, 0, clear.stderr)
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            self.assertEqual(start.returncode, 0, start.stderr)
            self.assertEqual(clear.stdout, "")
            self.assertEqual(resumed.stdout, "")
            self.assertEqual(clear.stderr, "")
            self.assertEqual(start.stderr, "")
            # No root CONTINUE_PROMPT.md exists (write_valid_checkpoint only sets
            # the active pointer and work-scoped PROGRESS.md, not the root file),
            # so no startup guidance is emitted.
            self.assertEqual(start.stdout, "")
            self.assertFalse((project / "CONTINUE_PROMPT.md").exists())

    def test_claude_session_start_emits_guidance_from_root_continue_prompt(self):
        """R6: once a root CONTINUE_PROMPT.md names the active package (the R4
        pointer contract), startup guidance points the session at that
        package's own CURRENT.md/CONTINUE_PROMPT.md.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            bundle = build_bundle("claude-code", root)
            write_valid_checkpoint(bundle, project)
            (project / "CONTINUE_PROMPT.md").write_text(
                "# Continue: current\n\n"
                "Active work package: `.agent-checkpoint/work/current`.\n",
                encoding="utf-8",
            )

            start = run_hook(
                bundle,
                "session_start.py",
                {"cwd": str(project), "source": "startup"},
            )

            self.assertEqual(start.returncode, 0, start.stderr)
            self.assertEqual(start.stderr, "")
            output = json.loads(start.stdout)
            guidance = output["hookSpecificOutput"]["additionalContext"]
            self.assertIn("root\nCONTINUE_PROMPT.md", guidance)
            self.assertIn(
                ".agent-checkpoint/work/current/CURRENT.md and "
                "CONTINUE_PROMPT.md",
                guidance,
            )


class CodexOpenCodeAdapterTests(unittest.TestCase):
    def test_codex_bundle_exposes_checkpoint_skill(self):
        """Catches a Codex bundle whose manual checkpoint skill is undiscoverable."""
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle("codex", Path(directory))

            manifest = json.loads(
                (bundle / ".codex-plugin" / "plugin.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(manifest["skills"], "./skills/")
            self.assertEqual(
                manifest["interface"]["defaultPrompt"],
                ["Save a checkpoint for the current project."],
            )
            self.assertTrue((bundle / "skills" / "checkpoint" / "SKILL.md").is_file())

    def test_opencode_command_has_cli_install_fallback(self):
        """Catches an OpenCode checkpoint command with no recovery for a missing CLI."""
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle("opencode", Path(directory))

            command = (bundle / "commands" / "checkpoint.md").read_text(
                encoding="utf-8"
            )

            self.assertIn("agent-checkpoint write --entry -", command)
            self.assertIn("bin/agent-checkpoint /usr/local/bin/agent-checkpoint", command)


class GeminiAdapterTests(unittest.TestCase):
    def test_gemini_bundle_exposes_manifest_commands_and_precompress_hook(self):
        """Catches Gemini extension components that are absent or undiscoverable."""
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle("gemini-cli", Path(directory))

            manifest = json.loads(
                (bundle / "gemini-extension.json").read_text(encoding="utf-8")
            )
            hook_config = json.loads(
                (bundle / "hooks" / "hooks.json").read_text(encoding="utf-8")
            )

            self.assertEqual(manifest["name"], "agent-checkpoint")
            expected_cli_actions = {
                "checkpoint": "agent-checkpoint write --entry -",
                "resume": "agent-checkpoint resume",
                "handoff": "agent-checkpoint handoff",
            }
            for command_name, cli_action in expected_cli_actions.items():
                command = tomllib.loads(
                    (bundle / "commands" / f"{command_name}.toml").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertIsInstance(command["description"], str)
                self.assertIn(cli_action, command["prompt"])

            hooks = hook_config["hooks"]
            self.assertEqual(set(hooks), {"PreCompress"})
            registration = hooks["PreCompress"][0]["hooks"][0]
            self.assertEqual(registration["type"], "command")
            self.assertEqual(
                registration["command"],
                'python3 "${extensionPath}/hooks/pre_compress.py"',
            )
            self.assertTrue((bundle / "hooks" / "pre_compress.py").is_file())

    def test_gemini_configured_hook_executes_from_shell_sensitive_extension_paths(self):
        """Catches the shell splitting or truncating the substituted hook path."""
        for prefix in ("gemini extension ", "gemini extension's "):
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory(
                prefix=prefix
            ) as directory:
                root = Path(directory)
                project = root / "project"
                project.mkdir()
                bundle = build_bundle("gemini-cli", root)
                hook_config = json.loads(
                    (bundle / "hooks" / "hooks.json").read_text(encoding="utf-8")
                )
                configured_command = hook_config["hooks"]["PreCompress"][0][
                    "hooks"
                ][0]["command"]
                command = configured_command.replace("${extensionPath}", str(bundle))
                payload = json.loads(
                    (PROJECT_ROOT / "tests" / "fixtures" / "gemini-precompress.json")
                    .read_text(encoding="utf-8")
                )
                payload["cwd"] = str(project)
                environment = {
                    key: value
                    for key, value in os.environ.items()
                    if key != "PYTHONPATH"
                }
                environment["PYTHONDONTWRITEBYTECODE"] = "1"

                result = subprocess.run(
                    command,
                    cwd=project,
                    env=environment,
                    input=json.dumps(payload),
                    text=True,
                    capture_output=True,
                    check=False,
                    shell=True,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(set(json.loads(result.stdout)), {"systemMessage"})

    def test_gemini_precompress_emits_only_advisory_for_stale_checkpoint(self):
        """Catches blocking or plain-text output for unreadable checkpoint state."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            (project / "PROGRESS.md").write_text("stale", encoding="utf-8")
            bundle = build_bundle("gemini-cli", root)
            payload = json.loads(
                (PROJECT_ROOT / "tests" / "fixtures" / "gemini-precompress.json")
                .read_text(encoding="utf-8")
            )
            payload["cwd"] = str(project)

            result = run_hook(bundle, "pre_compress.py", payload)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            output = json.loads(result.stdout)
            self.assertEqual(set(output), {"systemMessage"})
            self.assertIn("checkpoint", output["systemMessage"].lower())

    def test_gemini_precompress_advises_for_valid_checkpoint_older_than_seven_days(self):
        """Catches the hook ignoring the core's timestamp-based stale warning."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            bundle = build_bundle("gemini-cli", root)
            write_valid_checkpoint(bundle, project)
            progress_path = scoped_progress(project)
            progress = progress_path.read_text(encoding="utf-8")
            prefix, marker, remainder = progress.partition("## Checkpoint ")
            self.assertEqual(marker, "## Checkpoint ")
            _, newline, suffix = remainder.partition("\n")
            self.assertEqual(newline, "\n")
            progress_path.write_text(
                prefix
                + marker
                + "2000-01-01T00:00:00+00:00"
                + newline
                + suffix,
                encoding="utf-8",
            )
            payload = json.loads(
                (PROJECT_ROOT / "tests" / "fixtures" / "gemini-precompress.json")
                .read_text(encoding="utf-8")
            )
            payload["cwd"] = str(project)

            result = run_hook(bundle, "pre_compress.py", payload)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(set(json.loads(result.stdout)), {"systemMessage"})

    def test_gemini_precompress_advises_when_checkpoint_is_missing(self):
        """Catches a missing checkpoint being treated as current progress."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            bundle = build_bundle("gemini-cli", root)
            payload = json.loads(
                (PROJECT_ROOT / "tests" / "fixtures" / "gemini-precompress.json")
                .read_text(encoding="utf-8")
            )
            payload["cwd"] = str(project)

            result = run_hook(bundle, "pre_compress.py", payload)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(set(json.loads(result.stdout)), {"systemMessage"})

    def test_gemini_precompress_is_silent_for_valid_checkpoint(self):
        """Catches advisory output that ignores the bundled status command."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            bundle = build_bundle("gemini-cli", root)
            write_valid_checkpoint(bundle, project)
            payload = json.loads(
                (PROJECT_ROOT / "tests" / "fixtures" / "gemini-precompress.json")
                .read_text(encoding="utf-8")
            )
            payload["cwd"] = str(project)

            result = run_hook(bundle, "pre_compress.py", payload)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")


class RepositoryLayoutTests(unittest.TestCase):
    def test_repository_no_longer_has_claude_only_root_layout(self):
        """Catches legacy Claude-only sources competing with portable adapters.

        Since R6 no per-host tree is stored at all: claude-code's plugin
        manifest is projected into a bundle from hosts.toml, so the repository
        must hold neither the old Claude-only root layout nor a hand-maintained
        adapters/ tree.
        """
        self.assertFalse((PROJECT_ROOT / ".claude-plugin").exists())
        self.assertFalse((PROJECT_ROOT / "hooks" / "hooks.json").exists())
        self.assertFalse((PROJECT_ROOT / "adapters").exists())
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle("claude-code", Path(directory))
            self.assertTrue((bundle / ".claude-plugin" / "plugin.json").is_file())

    def test_readme_documents_every_target_and_tracked_file_warning(self):
        """Catches portable install guidance omitting a runtime or Git warning."""
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        for target in ("Claude Code", "Codex", "OpenCode", "Gemini CLI"):
            self.assertIn(target, readme)
        self.assertIn("already tracked", readme)


class AdapterValidationTests(unittest.TestCase):
    def test_validate_adapter_accepts_all_four_native_bundles(self):
        """Catches native checks that disagree with any supported adapter build."""
        for adapter in ("claude-code", "codex", "opencode", "gemini-cli"):
            with self.subTest(adapter=adapter), tempfile.TemporaryDirectory() as directory:
                output = build_bundle(adapter, Path(directory))

                result = run_tool("tools/validate_adapters.py", str(output))

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_validate_adapter_rejects_undeclared_skill_on_every_skill_host(self):
        """Catches a skill-shipping host whose skill manifest is never validated.

        Before R5, `_validate_claude` never called `_validate_skill_manifest`,
        so claude-code — the only automatic-capability host, shipping 12
        skills — passed validation by checking nothing. A host that validates
        nothing passes an accepts-valid-bundles test trivially, so this asserts
        the negative case for every host that ships skills.
        """
        for adapter in ("claude-code", "codex", "opencode"):
            with self.subTest(adapter=adapter), tempfile.TemporaryDirectory() as directory:
                output = build_bundle(adapter, Path(directory))
                undeclared = output / "skills" / "bogus-skill"
                undeclared.mkdir(parents=True)
                (undeclared / "SKILL.md").write_text(
                    "---\nname: bogus\n---\nbody\n", encoding="utf-8"
                )

                result = run_tool("tools/validate_adapters.py", str(output))

                self.assertEqual(result.returncode, 2)
                self.assertIn("undeclared skill directory", result.stderr)

    def test_validate_adapter_reports_stray_file_in_skills_as_a_file(self):
        """Catches a stray file being misreported as an undeclared directory."""
        with tempfile.TemporaryDirectory() as directory:
            output = build_bundle("claude-code", Path(directory))
            (output / "skills" / "AGENTS.md").write_text("notes\n", encoding="utf-8")

            result = run_tool("tools/validate_adapters.py", str(output))

            self.assertEqual(result.returncode, 2)
            self.assertIn("unexpected file in skills/", result.stderr)
            self.assertNotIn("undeclared skill directory", result.stderr)

    def test_validate_adapter_rejects_corrupt_claude_native_files(self):
        """Catches common-only validation of an incomplete Claude command set."""
        with tempfile.TemporaryDirectory() as directory:
            output = build_bundle("claude-code", Path(directory))
            (output / "commands" / "resume.md").unlink(missing_ok=True)

            result = run_tool("tools/validate_adapters.py", str(output))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("commands/resume.md", result.stderr)

    def test_validate_adapter_rejects_misspelled_claude_frontmatter(self):
        """Catches substring matching of a non-native frontmatter key."""
        with tempfile.TemporaryDirectory() as directory:
            output = build_bundle("claude-code", Path(directory))
            (output / "commands" / "resume.md").write_text(
                "---\nnotdescription: invalid\n---\n\nagent-checkpoint resume\n",
                encoding="utf-8",
            )

            result = run_tool("tools/validate_adapters.py", str(output))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("commands/resume.md", result.stderr)

    def test_validate_adapter_rejects_corrupt_codex_native_manifest(self):
        """Catches a Codex manifest with the wrong defaultPrompt schema type."""
        with tempfile.TemporaryDirectory() as directory:
            output = build_bundle("codex", Path(directory))
            manifest_path = output / ".codex-plugin" / "plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["interface"]["defaultPrompt"] = "invalid string"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_tool("tools/validate_adapters.py", str(output))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("defaultPrompt", result.stderr)

    def test_validate_adapter_rejects_corrupt_opencode_native_files(self):
        """Catches common-only validation of an incomplete OpenCode command set."""
        with tempfile.TemporaryDirectory() as directory:
            output = build_bundle("opencode", Path(directory))
            (output / "commands" / "resume.md").unlink()

            result = run_tool("tools/validate_adapters.py", str(output))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("commands/resume.md", result.stderr)

    def test_validate_adapter_rejects_non_string_opencode_skill_frontmatter(self):
        """Catches YAML-native values being accepted as string metadata."""
        for description in ("[]", "0x10", "0b10", "2026-08-09", ".nan", "yes", "on"):
            with self.subTest(description=description), tempfile.TemporaryDirectory() as directory:
                output = build_bundle("opencode", Path(directory))
                (output / "skills" / "checkpoint" / "SKILL.md").write_text(
                    f"---\nname: checkpoint\ndescription: {description}\n---\n\n# Checkpoint\n",
                    encoding="utf-8",
                )

                result = run_tool("tools/validate_adapters.py", str(output))

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("skills/checkpoint/SKILL.md", result.stderr)

    def test_validate_adapter_rejects_corrupt_gemini_native_files(self):
        """Catches common-only validation of malformed Gemini command TOML."""
        with tempfile.TemporaryDirectory() as directory:
            output = build_bundle("gemini-cli", Path(directory))
            (output / "commands" / "resume.toml").write_text(
                'description = "unterminated\n', encoding="utf-8"
            )

            result = run_tool("tools/validate_adapters.py", str(output))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("commands/resume.toml", result.stderr)

    def test_validate_adapter_rejects_missing_launcher(self):
        """Catches a validator accepting a bundle with no runnable entry point."""
        with tempfile.TemporaryDirectory() as directory:
            output = build_bundle("codex", Path(directory))
            (output / "bin" / "agent-checkpoint").unlink()

            result = run_tool("tools/validate_adapters.py", str(output))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("bin/agent-checkpoint", result.stderr)

    def test_validate_adapter_rejects_missing_bundled_core(self):
        """Catches a validator accepting a launcher with no portable CLI module."""
        with tempfile.TemporaryDirectory() as directory:
            output = build_bundle("gemini-cli", Path(directory))
            (output / "lib" / "agent_checkpoint" / "cli.py").unlink()

            result = run_tool("tools/validate_adapters.py", str(output))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lib/agent_checkpoint/cli.py", result.stderr)

    def test_validate_adapter_rejects_symlinked_bin_directory(self):
        """Catches validation following a bin directory link outside the bundle."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = build_bundle("codex", root)
            linked_bin_target = root / "external-bin"
            shutil.move(str(output / "bin"), linked_bin_target)
            (output / "bin").symlink_to(linked_bin_target, target_is_directory=True)

            result = run_tool("tools/validate_adapters.py", str(output))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("bin", result.stderr)
            self.assertIn("symlink", result.stderr.lower())

    def test_validate_adapter_rejects_symlinked_lib_directory(self):
        """Catches validation following a lib directory link outside the bundle."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = build_bundle("codex", root)
            linked_lib_target = root / "external-lib"
            shutil.move(str(output / "lib"), linked_lib_target)
            (output / "lib").symlink_to(linked_lib_target, target_is_directory=True)

            result = run_tool("tools/validate_adapters.py", str(output))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lib", result.stderr)
            self.assertIn("symlink", result.stderr.lower())

    def test_validate_adapter_rejects_missing_expected_core_module(self):
        """Catches validation accepting a CLI whose imported core module is absent."""
        with tempfile.TemporaryDirectory() as directory:
            output = build_bundle("gemini-cli", Path(directory))
            (output / "lib" / "agent_checkpoint" / "diagnostics.py").unlink()

            result = run_tool("tools/validate_adapters.py", str(output))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lib/agent_checkpoint/diagnostics.py", result.stderr)


SKILL_NAMES = (
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
    "checkpoint-select-workflow",
    "checkpoint-verify-gate",
)


class TwelveSkillCoverageTests(unittest.TestCase):
    def test_codex_bundle_exposes_all_twelve_skills(self):
        """Catches a Codex bundle that only packages the router skill."""
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle("codex", Path(directory))

            for name in SKILL_NAMES:
                skill_path = bundle / "skills" / name / "SKILL.md"
                self.assertTrue(skill_path.is_file(), f"missing Codex skill: {name}")

    def test_opencode_bundle_exposes_all_twelve_skills(self):
        """Catches an OpenCode bundle that only packages the router skill."""
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle("opencode", Path(directory))

            for name in SKILL_NAMES:
                skill_path = bundle / "skills" / name / "SKILL.md"
                self.assertTrue(skill_path.is_file(), f"missing OpenCode skill: {name}")

    def test_claude_bundle_skill_suite_directory_contains_all_twelve(self):
        """Catches the Claude bundle installing fewer than twelve skills."""
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle("claude-code", Path(directory))

            for name in SKILL_NAMES:
                skill_path = bundle / "skills" / name / "SKILL.md"
                self.assertTrue(skill_path.is_file(), f"missing Claude skill: {name}")

    def test_openai_agents_yaml_covers_all_twelve_skills(self):
        """Catches agents/openai.yaml omitting any skill or using a wrong name."""
        import importlib.util
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed; install pyyaml to run this test")
        yaml_path = PROJECT_ROOT / "agents" / "openai.yaml"
        self.assertTrue(yaml_path.is_file(), "missing agents/openai.yaml")
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        self.assertIn("functions", data, "agents/openai.yaml must have a 'functions' key")
        function_names = {fn["name"] for fn in data["functions"]}
        for name in SKILL_NAMES:
            expected_fn_name = name.replace("-", "_")
            self.assertIn(
                expected_fn_name,
                function_names,
                f"agents/openai.yaml missing function for skill: {name}",
            )
        self.assertEqual(
            len(data["functions"]),
            len(SKILL_NAMES),
            "agents/openai.yaml function count does not match SKILL_NAMES count",
        )

    def test_validate_adapter_rejects_codex_bundle_missing_non_router_skill(self):
        """Catches skill-manifest validation accepting a bundle with a missing skill."""
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle("codex", Path(directory))
            shutil.rmtree(bundle / "skills" / "checkpoint-brainstorm")

            result = run_tool("tools/validate_adapters.py", str(bundle))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checkpoint-brainstorm", result.stderr)

    def test_validate_adapter_rejects_opencode_bundle_missing_non_router_skill(self):
        """Catches skill-manifest validation accepting an OpenCode bundle with missing skill."""
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle("opencode", Path(directory))
            shutil.rmtree(bundle / "skills" / "checkpoint-claim")

            result = run_tool("tools/validate_adapters.py", str(bundle))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checkpoint-claim", result.stderr)

    def test_validate_adapter_rejects_codex_bundle_with_extra_skill_directory(self):
        """Catches skill-manifest validation accepting an undeclared skill directory."""
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle("codex", Path(directory))
            extra = bundle / "skills" / "checkpoint-unknown"
            extra.mkdir()
            (extra / "SKILL.md").write_text(
                "---\nname: checkpoint-unknown\ndescription: Extra.\n---\n\n# Extra\n",
                encoding="utf-8",
            )

            result = run_tool("tools/validate_adapters.py", str(bundle))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checkpoint-unknown", result.stderr)

    def test_validate_adapter_rejects_symlinked_skill_inside_codex_bundle(self):
        """Catches skill-manifest validation following a symlinked skill directory."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = build_bundle("codex", root)
            skill_dir = bundle / "skills" / "checkpoint-plan"
            external = root / "external-skill"
            shutil.move(str(skill_dir), external)
            skill_dir.symlink_to(external, target_is_directory=True)

            result = run_tool("tools/validate_adapters.py", str(bundle))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr.lower())


def _skill_body(path: Path) -> str:
    """Return everything after the frontmatter's closing '---' line."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return text
    _, separator, remainder = text[4:].partition("\n---\n")
    return remainder if separator else text


class SkillContentParityTests(unittest.TestCase):
    """Catches an adapter skill drifting from its skills/ source of truth (R5-I11)."""

    def test_all_twelve_skills_match_core_across_text_adapters(self):
        """Catches the codex/opencode router regressing to stale pre-R5 content.

        Since R6 no per-host skills tree is stored, so parity is checked against
        what a build actually projects rather than against a checked-in copy.
        """
        with tempfile.TemporaryDirectory() as directory:
            for adapter in ("codex", "opencode", "claude-code"):
                bundle = build_bundle(adapter, Path(directory))
                for name in SKILL_NAMES:
                    core_body = _skill_body(PROJECT_ROOT / "skills" / name / "SKILL.md")
                    self.assertEqual(
                        _skill_body(bundle / "skills" / name / "SKILL.md"),
                        core_body,
                        f"{adapter} projected skills/{name}/SKILL.md body drifted "
                        f"from skills/{name}/SKILL.md",
                    )

    def test_validate_adapter_rejects_skill_body_drifted_from_core(self):
        """Catches the exact class of drift R5-R1 found: an adapter skill silently
        diverging from its skills/ source with no validation failure."""
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle("codex", Path(directory))
            stale_skill = bundle / "skills" / "checkpoint" / "SKILL.md"
            stale_skill.write_text(
                "---\nname: checkpoint\ndescription: stale pre-R5 content\n---\n\nStale body.\n",
                encoding="utf-8",
            )

            result = run_tool("tools/validate_adapters.py", str(bundle))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("drifted", result.stderr.lower())
            self.assertIn("checkpoint", result.stderr)
