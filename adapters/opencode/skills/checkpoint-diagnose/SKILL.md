---
name: checkpoint-diagnose
description: "Use when the current unit is failed and has no root_cause_fingerprint \u2014 analyzes the failure to produce a fingerprint before any recovery decision."
---

# Checkpoint — Diagnose

The current unit is `failed` and no `root_cause_fingerprint` has been recorded. Diagnosis must precede recovery.

## Analyze the failure

Read the last entry in `EVIDENCE.md` for this unit. Identify the root cause. Produce a short fingerprint string (e.g., `"import-error-missing-module"`) that uniquely identifies this failure mode.

Record the fingerprint in the evidence document. The fingerprint is required before `checkpoint-recover` may propose a recovery action.

## Do not propose recovery events here

This skill produces a diagnosis. Recovery events (`replan`, `supersede`, `block`) are selected by `checkpoint-recover` after the fingerprint is set. Do not call `work recover` here.

## Why this skill and not checkpoint-recover?

`checkpoint-diagnose` fires when the unit is `failed` with no fingerprint. `checkpoint-recover` fires after a fingerprint exists and selects the recovery action.
