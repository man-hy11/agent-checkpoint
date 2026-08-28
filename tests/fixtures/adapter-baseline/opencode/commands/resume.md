---
description: Manually render the current checkpoint context.
---

Render the current checkpoint context with the installed CLI:

```bash
agent-checkpoint resume
```

Use `--root PATH` or `--max-chars NUMBER` when needed. Follow the rendered
`Language:` instruction. If `agent-checkpoint` is unavailable, put its
launcher on `PATH` and retry:

```bash
ln -s /absolute/path/to/agent-checkpoint/bin/agent-checkpoint /usr/local/bin/agent-checkpoint
```

For an installed CLI that reports an error, run:

```bash
agent-checkpoint doctor --adapter opencode
```
