---
name: checkpoint-brainstorm
description: Use when a work package exists but brief_confirmed is false — gathers the goal, scope, success criteria, constraints, and affected area before any planning step.
---

# Checkpoint — Brainstorm

A state block exists but `brief_confirmed` is false. The work package brief must be confirmed before planning.

## Confirm planning fields

Check `.agent-checkpoint/work/current/CURRENT.md` for the state block. If `brief_confirmed` is false, ask the user for any missing fields:

- **Goal:** what outcome does the work achieve?
- **Scope:** what is explicitly in and out of scope?
- **Success criteria:** how will you know the work is done?
- **Constraints:** time, people, technology, or policy limits.
- **Affected area:** files, systems, teams, or surfaces touched.

Do not fabricate or default any field. Record only confirmed answers in `BRIEF.md` and `PROJECT_CONTEXT.md`.

## Set brief_confirmed

When all fields are confirmed, update `CURRENT.md` with `brief_confirmed: true` before running `checkpoint-plan`.

## Why this skill and not checkpoint-select-workflow?

`checkpoint-brainstorm` fires when `brief_confirmed` is false inside an existing state block. `checkpoint-select-workflow` fires when no state block exists at all.
