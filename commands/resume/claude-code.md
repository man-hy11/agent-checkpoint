---
description: Manually render the current project checkpoint for resuming work.
---

Load bounded checkpoint context with:

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/agent-checkpoint" resume
```

Use `--root PATH` when the project root is not the current directory and
`--max-chars NUMBER` when a smaller context budget is needed. Follow the
rendered `Language:` instruction. If the command fails, report its diagnostic
without claiming that checkpoint context was loaded.
