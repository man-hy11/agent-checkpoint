---
description: Manually render a bounded handoff summary for the next agent.
---

Create the handoff with:

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" handoff
```

Use `--root PATH` when the project root is not the current directory and
`--max-chars NUMBER` when a smaller output budget is needed. Preserve the
rendered language, verification, focus, next actions, decisions, and optional
Git hints. If the command fails, report its diagnostic without claiming that a
handoff was created.
