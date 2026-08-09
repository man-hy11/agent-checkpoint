---
description: Manually render the current checkpoint context.
---

Render the current checkpoint context with the installed CLI:

```bash
agent-checkpoint resume
```

Use `--root PATH` or `--max-chars NUMBER` when needed. If `agent-checkpoint`
is unavailable, run the following from this project's source directory. Follow
the rendered `Language:` instruction. Ensure
the prefix's `bin` directory is on `PATH`, and retry:

```bash
python3 tools/install.py --prefix "$HOME/.local"
```

For an installed CLI that reports an error, run:

```bash
agent-checkpoint doctor --adapter opencode
```
