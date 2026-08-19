# Spike / Research / POC Gate — <TITLE>

## Preconditions

All planned Spike / Research / POC Steps are verified complete in
`CURRENT.md`, and `DECISION_RECORD.md` is filled in, not left with
placeholder sections.

## Gate Focus

Verify that the original question was actually answered with evidence, that
realistic alternatives were genuinely compared (not one option investigated
and the rest assumed), and that a recommendation/decision record exists and
is well-supported. **Gate PASS here means "the decision is well-supported,"
not "code works."** Passing prototype code is not sufficient evidence and
is not itself a Gate criterion.

## Verify

> See `shared/GATE_STANDARD.md`. Include only sections relevant to what this
> spike actually investigated; do not leave a relevant section as `...`.

### Question Answered With Evidence
- the Question recorded in `DECISION_RECORD.md` is answered — or explicitly
  recorded as unanswerable within scope/time, with why — not left implicit;
- every claim in the Findings section traces back to a specific experiment
  and its captured evidence (raw output, benchmark numbers, reproducible
  steps), not an unsupported assertion;
- if a Step's finding was negative (an approach failed/was infeasible), that
  finding is present in the record with the same rigor as positive
  findings — a spike that only reports what worked is incomplete.

### Alternatives Genuinely Compared
- every alternative listed in `DECISION_RECORD.md`'s Alternatives
  Considered has actual investigation behind it (an experiment, a
  documented reason it was ruled out without full experimentation, or clear
  evidence it was infeasible) — not a placeholder entry with no
  investigation;
- the Decision Criteria used are the ones that actually matter for this
  decision (correctness, feasibility, latency, maintainability, ecosystem
  maturity, security, cost, effort, portability, licensing, team
  familiarity — as relevant), and each alternative is scored/discussed
  against them, not only the winning option;
- rejected alternatives have a stated, specific reason for rejection tied
  to the criteria — not "we didn't like it."

### Uncertainty Recorded
- `DECISION_RECORD.md`'s Uncertainty/Unknowns section names concrete
  unknowns that remain, not a vague disclaimer;
- the record names what evidence would change the decision later, so a
  future re-evaluation has a concrete trigger.

### Recommendation / Decision Record Exists
- `DECISION_RECORD.md`'s Recommendation and Decision sections are filled in
  with an accepted option, explicitly rejected options, and the reasoning
  — not left blank or deferred;
- the Next Work Type is named (PROJECT / FEATURE / INTEGRATION / REFACTOR /
  PERFORMANCE / UPGRADE / MIGRATION / no further work) so the decision has
  an actionable next step, not a dead end.

### Productionization Boundary Respected
- every prototype artifact produced during this spike is marked
  `DISPOSABLE` or `CANDIDATE_FOR_REIMPLEMENTATION` in
  `DECISION_RECORD.md` — confirm none of it was silently wired into
  production paths (check for imports/references from real application
  code into any `spikes/`/`experiments/` location);
- per `WORK_TYPE_HARD_RULES.md` (SPIKE): if a prototype is selected as the
  path forward, confirm the record states that productionizing it requires
  a normal PROJECT/FEATURE/REFACTOR/INTEGRATION plan — the spike itself
  does not authorize shipping the prototype as-is.

### Cross-Step Consistency
- findings across Steps do not contradict each other without the
  contradiction being explicitly resolved or noted as remaining
  uncertainty;
- ...

## Representative End-to-End

```text
Question / Decision Criteria (S1)
-> Alternatives identified (S2)
-> Bounded experiments actually run, evidence captured (S3)
-> Findings and tradeoffs documented, including negative results (S4)
-> Recommendation and Decision recorded, with Next Work Type named (S5)
```

## Required Evidence

- exact experiments run and their raw captured output/results;
- `DECISION_RECORD.md` reviewed section-by-section for completeness (no
  placeholder `...` left in a section that should be filled);
- confirmation that no prototype code was silently referenced from
  production paths;
- unresolved issues/uncertainty, explicitly named.

## Gate Failure

If the Gate reveals a defect:

1. do not mark the Gate complete;
2. do not run large new experiments inside the Gate — only tiny
   verification-only checks are permitted (e.g. re-running an existing
   experiment to confirm reproducibility), and only if this Gate explicitly
   allows them;
3. identify the required remediation as a new/reopened Step (e.g. an
   alternative needs actual investigation, a finding needs stronger
   evidence);
4. record evidence;
5. STOP.

## Gate PASS

1. mark the Spike / Research / POC Gate complete in `CURRENT.md`;
2. write the final work summary (per `shared/EXECUTION_RULES.md`),
   including the accepted Decision and Next Work Type;
3. STOP.

Do not start the Next Work Type's plan in this invocation — that is a
separate work package.
