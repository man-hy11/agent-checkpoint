---
description: Manually create a checkpoint handoff summary for the next agent.
---

Create a handoff summary with the installed CLI:

```bash
agent-checkpoint handoff
```

Use `--root PATH` or `--max-chars NUMBER` when needed. Keep verification
results separate from recent decisions and follow the rendered `Language:`
instruction. If `agent-checkpoint` is unavailable, reinstall the CLI and
retry:

```bash
npm install -g agent-checkpoint
```

For an installed CLI that reports an error, run:

```bash
agent-checkpoint doctor --adapter opencode
```
