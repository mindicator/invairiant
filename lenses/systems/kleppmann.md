# Kleppmann Lens — Data Systems, Consistency, and Evolution

**Pack:** systems · **ID:** `kleppmann`

## Purpose

This lens protects against data layers that work only for today's schema
and yesterday's traffic: migrations that cannot run against live readers,
derived views with no rebuild path, two stores both claiming to be the
truth, pipelines that assume an exactly-once delivery no layer actually
provides, and history destroyed by updates in place.

Data outlives code. This lens checks whether the data layer can **evolve
without a stop-the-world rewrite or a silent loss of meaning.**

## Scope

**Use when:**

- the system stores data that outlives a single process run: databases,
  event logs, queues, files, search indexes;
- schemas, message formats, or APIs evolve while old readers and writers
  are still running;
- derived or materialized state exists (indexes, caches, projections,
  aggregates, warehouse tables);
- migrations or backfills are performed, or consistency across replicas
  and stores is assumed.

**Skip when:**

- the system is stateless or its only persistence is ephemeral scratch
  data — the von Neumann lens covers state ownership, the Lamport lens
  pure ordering concerns; note that explicitly instead of scoring.

## Core Questions

- For every schema and message format: can version-N readers handle N+1
  data and vice versa (forward/backward compatibility), and does a test
  prove it for the rolling-deploy window?
- What is the source of truth for each dataset — the log, a table, an
  upstream system — and is everything else formally derived from it?
- For every materialized view, index, cache, or projection: is there a
  rebuild path from the source of truth, exercised at production scale?
- Are writes idempotent under redelivery, or does the pipeline assume an
  exactly-once delivery that no layer actually provides?
- What consistency does each read path actually get (read-your-writes,
  monotonic reads), and does logic depend on more than is guaranteed?
- Are migrations safe against live traffic: staged expand/contract,
  rollback-able, tested on production-shaped data, bounded in lock time?
- Are backfills idempotent and resumable, so a crash mid-backfill leaves a
  known state rather than an unknown mixture?
- When current state is updated in place, is required history preserved
  somewhere (audit log, event stream), or is the past silently destroyed?

## Good-State Examples

- Schema changes ship in expand/contract phases; CI replays version-N
  fixtures through version-N+1 readers and vice versa before deploy.
- Every derived store (search index, cache, reporting projection) declares
  its source of truth and has a tested `rebuild` command; the runbook
  records the last full rebuild.
- Consumers are idempotent by key and version; the design doc claims
  at-least-once delivery and the code matches the claim.
- Every migration `up` has a tested `down` or an explicit forward-fix
  plan; long migrations run online in batches with bounded lock time.
- Financially significant tables are append-only events plus a materialized
  current view; "what did the balance say on June 3" is answerable by replay.

## Red Flags

- Schema changes deployed in lockstep with code, with no compatibility
  window — a rolling deploy makes old readers crash on new data.
- A materialized view, cache, or index with no rebuild path: the
  derivation logic is lost or was never written.
- Two sources of truth for the same fact (a table and a log, two services'
  databases) with no declared winner and no reconciliation.
- Pipeline correctness depends on exactly-once delivery from a transport
  that provides at-least-once.
- Destructive in-place updates on data with audit or history requirements.
- Backfill scripts that are neither idempotent nor resumable.
- Read paths that require read-your-writes but are served by lagging
  replicas.
- Migration rollbacks never tested against production-shaped data.

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

Typical for this lens: the schema change and the reader that cannot parse
the old shape (two file references or a diff hunk); a missing rebuild path
or compatibility test; a config/schema mismatch between the declared
message contract and what producers emit; an incident report from a
migration or replica-lag event; doc/code contradiction on guarantees.

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

Claim: The v3 order event schema removed `amount_cents` in favor of
`amount` with no compatibility window; consumers still on v2 crash on new
events during any rolling deploy.

Evidence: `schemas/orders/order_placed.json` — the diff between rev
`8c41d0e` and HEAD removes `amount_cents` and rewrites `required` in place
(diff hunk); `pipelines/settlement/consumer.py:74-88` still reads
`event["amount_cents"]`; no fixture-replay contract test (missing test).

Risk: Any deploy overlap between producer and consumer versions poisons
the settlement queue; poison messages block the partition and settlement
halts until manual intervention.

Recommended fix: Re-add `amount_cents` as deprecated-but-populated; stage
the removal as expand/contract; add a bidirectional fixture-replay
compatibility test to CI.

### S2 Example

Claim: The `daily_revenue` reporting projection is updated incrementally
but has no rebuild path from the order log; drift is already observed and
is unrepairable by any tracked mechanism.

Evidence: `reporting/src/projector.rs:41-77` applies increments only, with
no replay entry point in the crate or in `ops/runbooks/reporting.md`;
incident report `ops/incidents/2026-04-22-revenue-drift.md` records a 0.4%
discrepancy "corrected by manual SQL" (incident report).

Risk: The projection is a cache promoted to truth: after any consumer bug,
redelivery, or partial outage, the only correction mechanism is untracked
manual SQL, and discrepancies compound silently between incidents.

Recommended fix: Implement replay-from-log rebuild keyed by event offsets;
schedule periodic reconciliation against the source of truth; document the
procedure in the runbook.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Kleppmann Lens (id: kleppmann) from the invAIriant
audit protocol: data systems, consistency, and evolution.

Examine the provided code/diff/docs for:
- schema and format evolution: forward/backward compatibility across
  rolling deploys, proven by tests with old and new fixtures;
- a declared source of truth per dataset, and rebuild paths for every
  materialized view, cache, index, or projection;
- delivery assumptions: idempotent writes versus exactly-once illusions on
  at-least-once transports;
- replication and staleness: read paths that need read-your-writes or
  monotonic reads, and whether the store guarantees them;
- migration and backfill safety: expand/contract staging, tested
  rollbacks, bounded lock time, idempotent resumable backfills;
- history vs current state: in-place destruction of audit-relevant data.

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
   Kleppmann Lens: N / 10
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
