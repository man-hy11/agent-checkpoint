from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
workflows = ["project","feature","bugfix","refactor","upgrade","migration","performance","integration","release","spike"]
missing = []

for w in workflows:
    p = root / w / "prompts"
    if not p.exists():
        missing.append(str(p))
        continue
    if len(list(p.glob("PLAN_*_PROMPT.md"))) != 1:
        missing.append(f"{w}: PLAN prompt")
    for name in ["FIRST_RUN_PROMPT_TEMPLATE.md","CONTINUE_PROMPT.md","QUICK_REQUEST.txt"]:
        if not (p/name).exists():
            missing.append(f"{w}: {name}")

for rel in [
    "shared/EXECUTION_RULES.md",
    "shared/EVIDENCE_STANDARD.md",
    "shared/GATE_STANDARD.md",
    "shared/CHANGE_SCOPE_RULES.md",
    "shared/TEMPLATE_SELECTOR.md",
    "shared/WORK_TYPE_HARD_RULES.md",
]:
    if not (root/rel).exists():
        missing.append(rel)

if missing:
    print("FAIL")
    for x in missing:
        print("-", x)
    sys.exit(1)

print("PASS")
print("Workflows:", len(workflows))
