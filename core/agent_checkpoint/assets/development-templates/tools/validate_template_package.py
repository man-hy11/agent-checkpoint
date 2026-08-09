from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]

required = [
    "README.md",
    "USAGE_CHEATSHEET.md",
    "shared/EXECUTION_RULES.md",
    "shared/EVIDENCE_STANDARD.md",
    "shared/GATE_STANDARD.md",
    "project/prompts/PLAN_NEW_PROJECT_PROMPT.md",
    "project/prompts/FIRST_RUN_PROMPT_TEMPLATE.md",
    "project/prompts/CONTINUE_PROMPT.md",
    "feature/prompts/PLAN_FEATURE_CHANGE_PROMPT.md",
    "feature/prompts/FIRST_RUN_PROMPT_TEMPLATE.md",
    "feature/prompts/CONTINUE_PROMPT.md",
    "bugfix/prompts/PLAN_BUGFIX_PROMPT.md",
    "bugfix/prompts/FIRST_RUN_PROMPT_TEMPLATE.md",
    "bugfix/prompts/CONTINUE_PROMPT.md",
]

missing = [p for p in required if not (root / p).exists()]

checks = {
    "project_continue_one_unit": "one Step or one Phase Gate" in (root/"project/prompts/CONTINUE_PROMPT.md").read_text(),
    "feature_continue_one_unit": "one Feature Step or one Feature Gate" in (root/"feature/prompts/CONTINUE_PROMPT.md").read_text(),
    "bugfix_continue_one_unit": "one Bugfix Step or one Bug Gate" in (root/"bugfix/prompts/CONTINUE_PROMPT.md").read_text(),
    "bugfix_root_cause_rule": "do not enter Fix before Root Cause is evidence-backed" in (root/"bugfix/prompts/PLAN_BUGFIX_PROMPT.md").read_text(),
}

print("Missing:", missing)
print("Checks:", checks)

if missing or not all(checks.values()):
    sys.exit(1)

print("PASS")
