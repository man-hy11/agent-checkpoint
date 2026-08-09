# GATE_STANDARD.md

## Purpose

A Gate verifies an integrated milestone.

A Gate is an independent execution unit.

It is not a place to casually implement missing features.

## Gate Preconditions

All Steps belonging to the Gate must already be verified complete unless the plan explicitly defines otherwise.

## Gate Verification

A Gate should verify relevant combinations of:

- functional behavior;
- data/state invariants;
- security;
- failure/recovery;
- upgrade/migration;
- end-to-end workflow;
- quality/performance;
- backward compatibility;
- observability.

## Gate Failure

If the Gate reveals a defect:

1. do not mark the Gate complete;
2. do not patch large unrelated code inside the Gate unless the Gate explicitly permits tiny verification-only corrections;
3. create/remand the required fix work;
4. record evidence;
5. STOP.

## Gate PASS

If every Gate criterion passes:

1. mark Gate complete;
2. update Current Target;
3. write Gate report;
4. STOP.
