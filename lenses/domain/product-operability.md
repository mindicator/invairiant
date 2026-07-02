# Product Operability Lens — Deployability and Supportability

**Pack:** domain · **ID:** `product-operability`

## Purpose

This lens protects a product from the gap between "works in staging" and
"operable by real teams for real users". It detects deploys only one
person can perform, rollbacks and migrations that were never rehearsed,
user-facing errors that are stack traces in disguise, support teams that
must escalate everything to engineering, runbooks that describe a retired
system, and dashboards that stay green while users fail.

## Scope

**Use when:**

- the system is a SaaS or product with real users and a support
  function;
- deploys and schema migrations happen regularly;
- features roll out to cohorts, or should;
- support load, escalation rate, or operational toil is under
  discussion.

**Skip when:**

- the system is a research prototype or throwaway internal tool with no
  support surface — note that explicitly instead of scoring;
- the audit target is library or infrastructure code with no user-facing
  operation.

## Core Questions

- Can anyone on the team run a deploy through one documented pipeline,
  or is deployment tribal knowledge?
- Can the last release be rolled back safely, and when was a rollback
  last actually performed — in anger or in rehearsal?
- Do migrations proceed in backward-compatible steps (expand, migrate,
  contract), with gates that stop a deploy when a step is unsafe, and a
  rehearsed down-path per step?
- Do user-facing errors tell the user what happened and what to do next,
  with a stable code support can look up — or are they stack traces and
  "something went wrong"?
- Can support staff perform the common actions (refund, reset, unlock,
  reassign) in admin tooling with audit logging, without engineering
  escalation?
- Do runbooks match reality: commands exist, dashboards are linked, and
  steps carry a verified-on date?
- Do the metrics answer "is it working for users" — journey success
  rates, per-feature error rates — or only CPU and uptime?
- Can a support engineer trace a user report (account, timestamp) to a
  cause through request ids, correlated logs, and an audit trail?
- Are risky features behind flags with staged rollout and a kill switch?

## Good-State Examples

- Deploy is one pipeline any engineer can run; rollback is a single
  action, rehearsed monthly, completing in minutes.
- Migrations ship expand/contract in separate releases; a gate blocks
  deploy until backfill is verified, and the down-path is tested against
  a production-sized snapshot.
- Errors carry stable codes and user-actionable text; the support tool
  maps code → cause → next step, and the top codes are reviewed
  quarterly.
- The admin console covers the top ten support actions with audit
  logging; the escalation rate is tracked and trending down.
- Support can paste a request id and get the correlated trace, logs, and
  audit events in one view.

## Red Flags

- Deploys performed by one person, from a laptop, from memory.
- A rollback procedure that exists on paper and has never been executed.
- Irreversible migrations shipped without a rehearsed recovery plan.
- Raw stack traces or bare "something went wrong" shown to users, with
  no code for support to search.
- The support tool is a Slack channel into the engineering team.
- Runbook steps referencing dashboards or commands that no longer exist.
- Dashboards all green during a user-visible outage.
- Feature flags without kill-switch semantics, or staged rollout skipped
  under deadline pressure.

## Required Evidence

Findings under this lens must cite one or more of:

- file path + line range
- diff hunk
- test failure
- missing test
- doc/code contradiction
- runtime log
- incident report
- CI output
- configuration/schema mismatch

Typical for this lens: the migration without a down-path (file + lines);
a runbook step naming a retired command or dashboard (doc/code
contradiction); a production response body carrying a stack trace
(runtime log); a rollout or flag configuration contradicting the stated
policy (configuration/schema mismatch); a rollback path with no test or
drill record (missing test).

## Scoring Rubric

| Score | Meaning |
|---:|---|
| 0–2 | Dangerous / uncontrolled |
| 3–4 | Prototype with serious architectural risk |
| 5–6 | Meaningful but debt-heavy |
| 7 | Strong prototype |
| 8 | Strong engineering, not yet boring |
| 9 | Near-reference, survives growth |
| 10 | Mature, boring, repeatedly proven |

## Finding Examples

### S1 Example

Claim: A destructive migration drops columns that live code still reads,
and no gate or rehearsed rollback protects the deploy.

Evidence: `db/migrations/0042_drop_legacy_orders.sql:1-18` drops
`orders.legacy_status` and `orders.legacy_total`;
`api/handlers/orders.ts:88-115` still reads both fields on the refund
path; `docs/runbooks/deploy.md:57` requires expand/contract migrations
with a verified down-path (doc/code contradiction).

Risk: The next deploy breaks refunds in production with no rollback
story: the down-path does not exist, and the data is gone once the
columns are dropped.

Recommended fix: Split into expand/contract steps and remove the code
reads first; add a migration gate that blocks deploys when a dropped
column is still referenced; rehearse the down-path on a snapshot.

### S2 Example

Claim: Users receive raw exception details on payment failures, and
support cannot trace reports because responses carry no stable error code
or request id.

Evidence: `web/src/checkout/ErrorPanel.tsx:20-41` renders
`error.message` directly; a production log sample from 2026-06-18 shows a
500 response body containing a database driver stack trace (runtime
log); no error-code catalog exists under `docs/support/`.

Risk: Users see internals (a mild information leak) and get no actionable
next step; every payment complaint becomes an engineering escalation
because support has nothing to look up.

Recommended fix: Introduce stable error codes with user-facing text and a
support catalog; attach request ids to responses and logs; strip
internals from all user-visible errors; measure the escalation rate
before and after.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Product Operability Lens (id: product-operability)
from the invAIriant audit protocol: deployability and supportability.

Examine the provided code/diff/docs for:
- deployability: repeatable deploys, rehearsed rollback, migration
  gates;
- migration safety: backward-compatible steps and tested down-paths;
- user-facing errors: actionable, coded, traceable by support;
- admin and support tooling covering common actions without engineering
  escalation, and runbooks that match reality;
- metrics that answer "is it working for users";
- traceability from user report to cause; flags and staged rollout.

Rules:
- No evidence, no finding. Every finding must cite file+lines, a diff hunk,
  a test (failing or missing), a doc/code contradiction, a log, CI output,
  or a config/schema mismatch.
- If you cannot cite evidence, record the item as an Observation,
  Hypothesis, or Open question — never as a finding.
- Do not average away critical risks.
- Do not produce confident claims from vibes.

Output:
1. A score block:
   Product Operability Lens: N / 10
   Strengths:
   - ...
   Concerns:
   - ...
   Candidate findings:
   - ...
2. Candidate findings as JSON conforming to schemas/finding.schema.json
   (severity is provisional; the severity classifier assigns the final one).
3. Observations / hypotheses / open questions, clearly separated.
```
