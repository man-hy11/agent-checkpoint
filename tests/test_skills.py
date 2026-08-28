"""Tests for the twelve-skill progressive-disclosure suite."""

import re
import unittest
from pathlib import Path

_SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"
_SHARED_DIR = _SKILLS_ROOT / "_checkpoint-shared"

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
    "checkpoint-select-workflow",
    "checkpoint-verify-gate",
)

ADJACENT_PAIRS = (
    ("checkpoint-select-workflow", "checkpoint-brainstorm"),
    ("checkpoint-brainstorm", "checkpoint-plan"),
    ("checkpoint-execute", "checkpoint-verify-gate"),
    ("checkpoint-diagnose", "checkpoint-recover"),
    ("checkpoint-evidence", "checkpoint-handoff"),
)


class SkillDirectoryTests(unittest.TestCase):
    def test_all_expected_skill_directories_exist(self):
        """Catches any of the twelve skill directories being absent."""
        for name in EXPECTED_SKILLS:
            d = _SKILLS_ROOT / name
            self.assertTrue(d.is_dir(), f"missing skill directory: {name}")

    def test_each_skill_has_a_skill_md(self):
        """Catches a skill directory created without a SKILL.md file."""
        for name in EXPECTED_SKILLS:
            p = _SKILLS_ROOT / name / "SKILL.md"
            self.assertTrue(p.is_file(), f"missing SKILL.md for {name}")

    def test_shared_directory_exists(self):
        """Catches _checkpoint-shared directory not being created."""
        self.assertTrue(_SHARED_DIR.is_dir())

    def test_shared_directory_has_chain_contract(self):
        """Catches _checkpoint-shared missing the chain-v1.md contract."""
        self.assertTrue((_SHARED_DIR / "chain-v1.md").is_file())


class SkillFrontmatterTests(unittest.TestCase):
    def _parse_frontmatter(self, path: Path) -> dict:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            return {}
        end = text.index("\n---\n", 4)
        block = text[4:end]
        result = {}
        for line in block.splitlines():
            if ": " in line:
                k, _, v = line.partition(": ")
                result[k.strip()] = v.strip()
        return result

    def test_each_skill_has_name_in_frontmatter(self):
        """Catches a skill SKILL.md missing the 'name:' frontmatter key."""
        for name in EXPECTED_SKILLS:
            p = _SKILLS_ROOT / name / "SKILL.md"
            fm = self._parse_frontmatter(p)
            self.assertIn("name", fm, f"{name}: missing name in frontmatter")
            self.assertEqual(fm["name"], name, f"{name}: name mismatch")

    def test_each_skill_has_description_in_frontmatter(self):
        """Catches a skill SKILL.md missing the 'description:' frontmatter key."""
        for name in EXPECTED_SKILLS:
            p = _SKILLS_ROOT / name / "SKILL.md"
            fm = self._parse_frontmatter(p)
            self.assertIn("description", fm, f"{name}: missing description in frontmatter")
            self.assertGreater(len(fm["description"]), 10, f"{name}: description too short")

    def test_frontmatter_has_only_name_and_description(self):
        """Catches extra frontmatter keys beyond name and description."""
        for name in EXPECTED_SKILLS:
            p = _SKILLS_ROOT / name / "SKILL.md"
            fm = self._parse_frontmatter(p)
            extra = set(fm.keys()) - {"name", "description"}
            self.assertFalse(extra, f"{name}: unexpected frontmatter keys: {extra}")


class RouterSkillTests(unittest.TestCase):
    def test_router_skill_md_does_not_contain_handoff_prose(self):
        """Catches router description colliding with checkpoint-handoff content."""
        p = _SKILLS_ROOT / "checkpoint" / "SKILL.md"
        text = p.read_text(encoding="utf-8")
        self.assertNotIn("handoff", text.lower(), "router must not describe handoff behavior")

    def test_router_skill_routes_to_next_skill_command(self):
        """Catches router not referencing 'work status' for routing."""
        p = _SKILLS_ROOT / "checkpoint" / "SKILL.md"
        text = p.read_text(encoding="utf-8")
        self.assertIn("work status", text, "router must reference 'work status' for routing")

    def test_router_description_mentions_routing(self):
        """Catches router description not indicating it routes to another skill."""
        p = _SKILLS_ROOT / "checkpoint" / "SKILL.md"
        fm_text = p.read_text(encoding="utf-8")
        m = re.search(r"description: (.+)", fm_text)
        self.assertIsNotNone(m, "no description found in router frontmatter")
        desc = m.group(1).lower()
        self.assertTrue(
            "rout" in desc or "dispatch" in desc or "select" in desc or "determin" in desc,
            f"router description should mention routing/dispatching: {desc}",
        )


class TriggerSeparationTests(unittest.TestCase):
    """Catches adjacent skill descriptions being interchangeable (spec testing strategy)."""

    def _body(self, name: str) -> str:
        p = _SKILLS_ROOT / name / "SKILL.md"
        text = p.read_text(encoding="utf-8")
        # Strip frontmatter
        if text.startswith("---\n"):
            end = text.index("\n---\n", 4)
            return text[end + 5:]
        return text

    def test_select_workflow_does_not_mention_brief_confirmed(self):
        """Catches select-workflow and brainstorm being indistinguishable."""
        body = self._body("checkpoint-select-workflow")
        self.assertNotIn("brief_confirmed", body)

    def test_brainstorm_mentions_brief_confirmed(self):
        """Catches brainstorm not being triggered by missing brief_confirmed."""
        body = self._body("checkpoint-brainstorm")
        self.assertIn("brief_confirmed", body)

    def test_execute_does_not_mention_gate(self):
        """Catches execute and verify-gate being interchangeable."""
        body = self._body("checkpoint-execute")
        self.assertNotIn("gate", body.lower())

    def test_verify_gate_mentions_gate(self):
        """Catches verify-gate not being gate-specific."""
        body = self._body("checkpoint-verify-gate")
        self.assertIn("gate", body.lower())

    def test_diagnose_does_not_mention_recovery_event(self):
        """Catches diagnose and recover being indistinguishable."""
        body = self._body("checkpoint-diagnose")
        # diagnose should not list recovery events like retry/replan/supersede
        self.assertNotIn("retry", body.lower())

    def test_recover_mentions_retry(self):
        """Catches recover not covering the retry event."""
        body = self._body("checkpoint-recover")
        self.assertIn("retry", body.lower())

    def test_evidence_does_not_mention_handoff(self):
        """Catches evidence and handoff being interchangeable."""
        body = self._body("checkpoint-evidence")
        self.assertNotIn("handoff", body.lower())

    def test_handoff_mentions_handoff(self):
        """Catches handoff skill not mentioning handoff context."""
        body = self._body("checkpoint-handoff")
        self.assertIn("handoff", body.lower())

    def test_inspect_does_not_write(self):
        """Catches inspect writing state (it must be read-only)."""
        body = self._body("checkpoint-inspect")
        self.assertNotIn("work pass", body)
        self.assertNotIn("work fail", body)
        self.assertNotIn("work start", body)

    def test_claim_mentions_start_transition(self):
        """Catches claim not covering the ready->running start transition."""
        body = self._body("checkpoint-claim")
        self.assertIn("start", body.lower())


class SharedDirectoryTests(unittest.TestCase):
    def test_chain_contract_content_matches_contracts_directory(self):
        """Catches _checkpoint-shared/chain-v1.md diverging from contracts/chain-v1.md."""
        contracts_dir = (
            Path(__file__).resolve().parents[1]
            / ".agent-checkpoint" / "work" / "checkpoint-skill-expansion" / "contracts"
        )
        canonical = contracts_dir / "chain-v1.md"
        if not canonical.is_file():
            self.skipTest("canonical contracts/chain-v1.md not found")
        shared = _SHARED_DIR / "chain-v1.md"
        self.assertEqual(
            shared.read_bytes(),
            canonical.read_bytes(),
            "_checkpoint-shared/chain-v1.md must be byte-identical to contracts/chain-v1.md",
        )


if __name__ == "__main__":
    unittest.main()
