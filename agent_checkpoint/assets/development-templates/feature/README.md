# Feature Change Template

Use this template for adding/changing functionality in an existing project.

The target project already has architecture and behavior that must be understood before implementation.

Recommended change package:

```text
changes/
└── FEATURE-YYYY-NNN-<slug>/
    ├── CHANGE.md
    ├── CURRENT.md
    ├── IMPACT.md
    ├── step-F1.md
    ├── step-F2.md
    ├── ...
    ├── gate.md
    ├── FIRST_RUN_PROMPT.md
    └── CONTINUE_PROMPT.md
```

The existing project's own `AGENTS.md`, architecture docs, tests, and conventions remain authoritative unless the change explicitly updates them.
