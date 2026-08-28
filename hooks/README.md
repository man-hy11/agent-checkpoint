# hooks/ — single-source hook implementations

Three hook scripts, held once each:

| Script | Host | Registered as |
|---|---|---|
| `pre_compact.py` | claude-code | `PreCompact` |
| `session_start.py` | claude-code | `SessionStart` |
| `pre_compress.py` | gemini-cli | `PreCompress` |

`hosts.toml` declares the registration facts — event names, matchers, the path
variable (`${CLAUDE_PLUGIN_ROOT}` vs `${extensionPath}`), timeout values and
their units, and the command shape. `tools/build_adapter.py` (R5) generates
each host's `hooks/hooks.json` from those declarations and copies the scripts
it needs.

codex and opencode ship no hooks at all.

## Why the scripts are not de-duplicated further

The plan called for de-duplicating "where the logic is shared". Measured with
an AST comparison across all three scripts, that turns out to be one function:

| Function | Present in | Identical? |
|---|---|---|
| `_read_payload` | all 3 | **yes** |
| `_project_root` | all 3 | no |
| `_checkpoint_status` | 2 | no |
| `main` | all 3 | no |

`pre_compact.py` and `pre_compress.py` differ by 126 lines and implement
genuinely different behaviors, matching their capability levels: claude-code's
hook *writes* a bootstrap checkpoint (`automatic`), while gemini-cli's only
*emits an advisory message* (`advisory`). They are not two copies of one thing.

Extracting the single shared function into a module is also blocked by how
bundles work: `build_adapter.py` copies hook scripts verbatim into the bundle,
where they run standalone with no import path back to a shared module. A hook
that imported one would break at runtime on every host.

So the honest de-duplication here is at the **file** level — each script exists
once in this tree instead of once per host tree — not at the function level.
Extracting `_read_payload` would change every hook's bytes for a ~8-line saving
and break R5's empty-diff requirement, while introducing a runtime import the
bundle format cannot satisfy.
