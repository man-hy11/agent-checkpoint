# Bugfix Template

Use this template for diagnosing and fixing a bug in an existing project.

The default lifecycle is:

```text
B1 Reproduce
-> B2 Root Cause
-> B3 Fix
-> B4 Regression / Related Behavior
-> Bug Gate
```

For more complex bugs, add Steps.

## Hard Rule

When reproduction/evidence is reasonably obtainable:

```text
Do not enter the Fix Step before Root Cause is supported by evidence.
```

A plausible explanation is not enough.

If the issue cannot be reproduced, document why and use the strongest available evidence before proposing a bounded fix.
