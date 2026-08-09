---
description: Manually create a checkpoint handoff summary for the next agent.
---

Create a handoff summary with the installed CLI:

```bash
agent-checkpoint handoff
```

Use `--root PATH` or `--max-chars NUMBER` when needed. If `agent-checkpoint`
is unavailable, run the following from this project's source directory. Keep
verification results separate from recent decisions and follow the rendered
`Language:` instruction. Ensure
the prefix's `bin` directory is on `PATH`, and retry:

```bash
python3 tools/install.py --prefix "$HOME/.local"
```

For an installed CLI that reports an error, run:

```bash
agent-checkpoint doctor --adapter opencode
```
