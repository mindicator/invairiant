# Distributed Systems Lens — Membership, Partitions, and Convergence

**Pack:** domain · **ID:** `distributed-systems`

## Purpose

This lens protects multi-node systems against undefined behavior at the
membership and topology layer: joins and evictions that corrupt state,
partitions handled by assumption rather than design, coordinator failovers
nobody has rehearsed, gossip and DHT layers open to amplification,
poisoning, or eclipse, and state that is claimed to converge after healing
with no evidence that it does. The recurring question: for every failure
the network can produce, is the system's response defined, tested, and
owned — or folklore?

## Scope

**Use when:**

- more than one node cooperates: clusters, meshes, replicated stores,
  distributed work queues;
- the system has membership, discovery, gossip, a DHT, or leader election;
- partitions are expected in normal operation (multi-region, unreliable
  links, mobile peers).

**Skip when:**

- the deployment is single-node, or distribution is fully delegated to a
  managed store with documented semantics — audit the delegation
  assumptions instead of applying this lens.

Where the systems-pack `lamport` lens audits reasoning about event
ordering, this lens audits the operational surface of a distributed
system: membership, partitions, and convergence in the running cluster.

## Core Questions

- Is join/leave/eviction defined precisely: what state a joining node
  must sync before serving, who decides eviction, and on what signal?
- Can a wrongly evicted or re-joining node cause split-brain or resurrect
  deleted state — and what (fencing tokens, epochs) prevents it?
- For each subsystem, what happens during a partition — pause, degrade,
  serve stale — and is that written down and tested, or assumed?
- How is coordinator/leader failure detected, how long does takeover
  take, and what happens to in-flight work? When was failover last
  exercised?
- What bounds gossip/DHT amplification, and what prevents poisoning and
  eclipse attacks (validation, signatures, diverse peer selection)?
- Does routing stay correct under churn: stale entries expire, and
  in-flight requests to departed nodes have defined outcomes?
- After a partition heals, by what mechanism does state converge (CRDTs,
  anti-entropy, reconciliation) — and what evidence shows it actually
  converges (fault-injection tests, chaos runs)?
- Are timeouts and heartbeats tuned with evidence, or copied defaults
  that flap membership under load or GC pauses?

## Good-State Examples

- Membership transitions follow a documented state machine (joining →
  syncing → serving → leaving), and each transition — including a crash
  mid-transition — has a test.
- Partition behavior is a table per subsystem (reads, writes, queues,
  timers), and fault-injection tests in CI exercise every row.
- Coordinator failover is drilled on a schedule; takeover time is
  measured against a target, and in-flight work is reconciled through
  idempotent handoff verified by test.
- Gossip messages are signed and rate-bounded; peer selection mixes
  independent seeds to resist eclipse; a poisoning attempt appears in
  the test suite.
- A convergence harness splits and heals the cluster nightly and asserts
  replicas reach identical digests within a deadline.

## Red Flags

- Eviction on heartbeat timeout alone, with no fencing — a paused node
  can wake up and keep writing.
- "We retry" presented as the complete partition strategy.
- Failover documented but never rehearsed; runbooks name retired tooling.
- Unbounded gossip fanout; membership messages accepted unauthenticated.
- Routing entries without TTLs; no test exercises churn.
- Post-heal reconciliation called "eventual" with no test ever proving it.
- Timeout values copied from defaults; membership flaps under GC pauses.

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

Typical for this lens: eviction or takeover code missing fencing (file +
lines); the absent partition, churn, or convergence test (missing test);
an incident report of split-brain or duplicate ownership; a design doc or
runbook the code contradicts (doc/code contradiction); membership flap
traces (runtime log).

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

Claim: Shard ownership is reassigned on heartbeat timeout without
fencing, so a paused-but-alive node can keep writing to a shard it no
longer owns.

Evidence: `cluster/membership/evictor.go:141-178` evicts after three
missed heartbeats and reassigns shards immediately, with no fencing token
or epoch check on subsequent writes; incident report INC-2031
(2026-03-12) records two nodes accepting writes for shard 14 for six
minutes (incident report).

Risk: Split-brain writes corrupt shard state under exactly the conditions
(GC pause, network blip) that trigger eviction; the incident has already
happened once and nothing structural has changed.

Recommended fix: Introduce epoch-fenced writes rejected by storage when
the epoch is stale; delay reassignment until the old owner is fenced; add
a fault-injection test reproducing INC-2031.

### S2 Example

Claim: Post-partition convergence is asserted in the design docs but
exercised by no test: anti-entropy runs only on manual trigger.

Evidence: `replication/antientropy.py:60-97` — the repair loop is invoked
only from an operator CLI; `docs/design/replication.md:31` states
"replicas converge automatically after partitions heal" (doc/code
contradiction); no split/heal test exists under `tests/replication/`
(missing test).

Risk: After real partitions, replicas silently diverge until an operator
remembers the CLI; read results depend on which replica answers, and the
documented guarantee is not real.

Recommended fix: Schedule anti-entropy automatically with backpressure;
add a nightly split/heal convergence test asserting digest equality
within a deadline; correct the design doc until then.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Distributed Systems Lens (id: distributed-systems)
from the invAIriant audit protocol: membership, partitions, and
convergence.

Examine the provided code/diff/docs for:
- membership correctness: join/leave/eviction, fencing, re-join
  semantics;
- partition behavior per subsystem: defined and tested, not assumed;
- coordinator/leader failure: detection, takeover, and in-flight work;
- gossip/DHT exposure: amplification, poisoning, eclipse resistance;
- routing correctness under churn;
- state convergence after healing, with evidence that it converges.

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
   Distributed Systems Lens: N / 10
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
