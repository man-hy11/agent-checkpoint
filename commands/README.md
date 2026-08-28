# commands/ — single-source command definitions

One directory per command (`checkpoint`, `resume`, `handoff`), holding one body
file per host that ships that command:

```
commands/<command>/<host>.<md|toml>
```

`hosts.toml` declares which hosts ship commands, in which format, and which
per-host variables apply (CLI invocation string, npm-reinstall hint,
`doctor --adapter` block). `tools/build_adapter.py` (R5) projects these into a
host bundle's `commands/` directory.

## Why per-host bodies and not one template with slots

The BRIEF assumed command bodies were "near-identical", differing only in the
CLI invocation string, an optional npm hint, the `doctor --adapter` value, and
the file format. R1 disproved that, and R4 confirmed it while building this
tree. The bodies differ in three ways a slot-substitution template cannot
express:

1. **`description` strings are authored per host, not derived.** For example
   `resume`: claude-code says "Manually render the current project checkpoint
   for resuming work.", opencode "Manually render the current checkpoint
   context.", gemini-cli "Render the current checkpoint context." gemini-cli
   matches claude-code for `checkpoint` but not for `handoff`/`resume`, so no
   single rule generates all nine.

2. **Prose and structure differ, not just values.** claude-code wraps CLI calls
   in fenced ```bash blocks and writes flowing paragraphs; gemini-cli's body is
   a TOML `prompt = """..."""` string with bare unfenced commands; opencode uses
   fenced blocks plus two trailing recovery sections no other host has.

3. **Host-specific content is additive, not substitutive.** The npm-reinstall
   hint and `doctor --adapter opencode` block exist only in opencode.

Forcing these into one template would require rewriting all nine bodies to a
common shape — changing published output for every host and breaking R5's
requirement that generated output diff empty against the frozen fixture. That
is a content change masquerading as a refactor, and this work package is
explicitly behavior-preserving.

**What is genuinely single-source here** is the location and the projection
rules: one place to find every command body, with `hosts.toml` declaring how
each is projected, instead of the same information scattered across four
parallel host trees. Unifying the prose itself is a separate, content-level
decision that would need its own work package and its own review of what each
host's users actually see.
