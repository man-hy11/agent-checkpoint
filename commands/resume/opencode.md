---
description: Manually render the current checkpoint context.
---

Render the current checkpoint context with the installed CLI:

```bash
agent-checkpoint resume
```

Use `--root PATH` or `--max-chars NUMBER` when needed. Follow the rendered
`Language:` instruction. If `agent-checkpoint` is unavailable, reinstall the
CLI and retry:

```bash
npm install -g agent-checkpoint
```

For an installed CLI that reports an error, run:

```bash
agent-checkpoint doctor --adapter opencode
```
