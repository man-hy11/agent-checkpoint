---
description: Manually create a checkpoint handoff summary for the next agent.
---

Create a handoff summary with the installed CLI:

```bash
agent-checkpoint handoff
```

Use `--root PATH` or `--max-chars NUMBER` when needed. Keep verification
results separate from recent decisions and follow the rendered `Language:`
instruction. If `agent-checkpoint` is unavailable, put its launcher on
`PATH` and retry:

```bash
ln -s /absolute/path/to/agent-checkpoint/bin/agent-checkpoint /usr/local/bin/agent-checkpoint
```

For an installed CLI that reports an error, run:

```bash
agent-checkpoint doctor --adapter opencode
```
