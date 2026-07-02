# Lamport Lens — Time, Ordering, and Distributed State

**Pack:** systems · **ID:** `lamport`

## Purpose

This lens protects against code that assumes a single, well-ordered world:
events processed as if they arrive in the order they were produced,
retries that assume the first attempt never landed, timestamps treated as
causality, readers that assume their copy of state is current, and
partition behavior that exists only as an unhandled exception.

Two communicating processes are already a distributed system. This lens
checks whether its ordering assumptions are **written down and defended**,
or merely hoped.

## Scope

**Use when:**

- more than one process, node, replica, or client communicates over a
  network or queue;
- there are retries, at-least-once delivery, webhooks, or message
  consumers;
- state is replicated, cached, or read by parties other than its writer;
- timestamps, TTLs, leases, or clocks participate in decisions.

**Skip when:**

- the system is genuinely single-process and single-writer, with
  synchronous, un-retried calls — the von Neumann lens covers its state;
  note that explicitly instead of scoring.

## Core Questions

- Where does the code assume events arrive in the order they were
  produced? What enforces that ordering — sequence numbers, a single
  partition, a version check — or is it hope?
- Any network effect can be duplicated by a retry: which writes are
  idempotent, which are guarded by keys or versions, which double-apply?
- Which reads can be stale, and does downstream logic tolerate that — or
  can a decision made on stale state be applied to fresh state?
- What happens during a partition: does each side keep accepting writes,
  and what merges the results on reconnect — design or accident?
- Are wall-clock timestamps used to order events across machines? What
  justifies treating clock order as causal order (bounded skew, hybrid
  clocks, a single writer)?
- For every check-then-act over shared state: what prevents the state
  changing between check and act (lease, transaction, compare-and-swap)?
- Where the design claims consensus, leader election, or distributed
  locking: a proven component, or handwritten timeout-and-hope logic?
- Where "eventually consistent" is claimed: is convergence specified —
  what converges, by what mechanism, observable how?

## Good-State Examples

- Consumers treat delivery as at-least-once: every handler is idempotent
  via a processed-message table keyed by message id, and a
  duplicate-delivery test exists.
- Cross-entity ordering uses explicit sequence numbers or versions;
  out-of-order arrivals are buffered or rejected, never silently applied.
- Writes carry compare-and-swap version guards; a stale writer receives a
  typed conflict, not a lost update.
- Partition behavior is written down per subsystem — which side accepts
  writes, what happens to the other side's on reconnect — and a
  fault-injection test disconnects a node and asserts that outcome.
- Leases and TTLs carry explicit skew margins, and expiry is decided on
  the resource owner's clock, not the client's.

## Red Flags

- The system assumes events arrive in natural order: no sequence numbers,
  no version checks, one concurrent consumer away from corruption.
- A retry can double-apply a side effect (payment, email, counter, state
  transition).
- Timestamp order is treated as causal order across machines without
  justification.
- Partition/reconnect behavior is undefined: no design note, no test, only
  a connection-error branch.
- "Eventually consistent" is used as a handwave, with no statement of what
  converges or how.
- Check-then-act sequences over shared state with no lease, transaction,
  or version guard.
- Handwritten leader election or distributed locking where a proven
  primitive was available.

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

Typical for this lens: the handler that applies a message with no
idempotency guard (file + lines); a runtime log showing the same event id
applied twice; a missing test for duplicate or out-of-order delivery; a
doc/code contradiction where the design claims exactly-once but the
transport is at-least-once; cross-host timestamp comparison with no bound.

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

Claim: The payment webhook handler is not idempotent: a provider retry
re-applies the event and increments the customer balance twice.

Evidence: `billing/webhooks/payment.go:88-117` — `UPDATE balances SET
amount = amount + $1` keyed only on customer id, with no processed-event
table; the service log from 2026-06-03 shows event `evt_9f27c1` delivered
twice, 30 seconds apart, and applied both times (runtime log).

Risk: Any provider retry, network flap, or manual redelivery corrupts
balances, and the books can no longer be reconciled from the event stream.

Recommended fix: Record processed event ids in the same transaction as the
balance update; make the handler a no-op on duplicates; add a
duplicate-delivery test.

### S2 Example

Claim: Cross-node conflict resolution orders edits by wall-clock
timestamps from different hosts, treating clock order as causal order with
no skew bound.

Evidence: `sync/src/merge.rs:61-97` — sorts by `event.recorded_at`
(producer-local clocks) and applies last-write-wins;
`docs/design/replication.md:54` claims "conflicting edits are resolved
causally" (doc/code contradiction); nothing under `deploy/` configures or
asserts clock synchronization.

Risk: A node with a fast clock silently wins every conflict; edits are
dropped in an order no user observed; the documented causal guarantee is
false.

Recommended fix: Order conflicting edits with logical clocks or
per-entity version vectors, keeping wall time for display only; correct
the design doc; add a merge test with deliberately skewed clocks.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Lamport Lens (id: lamport) from the invAIriant audit
protocol: time, ordering, and distributed state.

Examine the provided code/diff/docs for:
- ordering assumptions: events applied as if arrival order equals
  production order, with no sequence or version enforcement;
- retry and duplicate behavior: idempotency of every network-facing write;
- stale reads and check-then-act races over shared or replicated state;
- partition and reconnect behavior: designed, documented, and tested — or
  emergent;
- clock usage: wall-clock timestamps treated as causal order, and lease or
  TTL logic without skew margins;
- claims of consensus, exactly-once, or eventual consistency without a
  mechanism behind them.

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
   Lamport Lens: N / 10
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
