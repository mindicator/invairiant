# Liskov Lens — Abstraction and Substitutability

**Pack:** implementation · **ID:** `liskov`

## Purpose

This lens protects against abstractions that are true in the type system
and false at runtime: implementations that satisfy an interface's signature
while violating the behavior callers rely on, adapters with divergent error
semantics, backends that were "replaceable" until someone tried, and
special cases that bend a generic API around one implementation.

An abstraction is only real if substitution is safe: **any implementation
can be swapped in without callers noticing, or the interface is a
costume.**

## Scope

**Use when:**

- the system declares interfaces with more than one implementation —
  drivers, providers, storage backends, model vendors, channels;
- test doubles (mocks, fakes, in-memory versions) stand in for production
  implementations;
- a backend or vendor swap is planned, promised, or marketed;
- adapters were added by different authors (or AI sessions) over time.

**Skip when:**

- an interface has exactly one implementation, no test double, and no
  second one planned — evaluate its depth under Ousterhout instead;
- the question is what an interface hides rather than whether its
  implementations agree — that is Parnas territory.

## Core Questions

- For each interface: is the behavioral contract written down — ordering,
  atomicity, idempotency, error semantics, blocking behavior — or only the
  method signatures?
- Is there a conformance test suite, and does it run against every
  implementation, including the in-memory fake used by unit tests?
- Do callers branch on the concrete type behind an abstraction
  (instanceof, type switches, config-keyed special cases)?
- Which implementation-specific behaviors have callers silently absorbed —
  retry quirks, pagination sizes, error-string matching, ordering luck?
- Does any implementation stub out a required method (silent no-op, "not
  supported" error) while still claiming the interface?
- Has a special case pushed a flag, mode, or vendor-shaped parameter into
  the generic API?
- When was a real substitution last performed or rehearsed, and what did
  it actually take?
- Do errors cross the abstraction in a normalized form, or does each
  adapter leak its vendor's exception types upward?

## Good-State Examples

- The object-store contract documents atomic `Put` and `ErrNotFound` on
  missing keys; one conformance suite covers S3, GCS, and the in-memory fake.
- The notification dispatcher consumes only the `Channel` interface; the
  fourth provider was a new adapter package and zero dispatcher changes.
- Vendor exceptions are normalized at the adapter boundary into the
  interface's typed errors; no caller matches on vendor error strings.
- The in-memory fake fails the same conformance suite when its semantics
  drift — which is how a divergence was caught before any unit test lied.
- A `forceSyncMode` flag needed by one backend was rejected from the
  generic interface and expressed inside that backend's adapter instead.

## Red Flags

- An implementation satisfies the signature but violates the contract:
  returns nil where an error is promised, or no-ops a required method.
- Callers type-check or switch on the concrete implementation behind an
  interface.
- Adapters disagree on error semantics, ordering, or atomicity, and no
  document or test says which behavior is contractual.
- A conformance suite exists for one implementation only — or for none.
- Test fakes embody friendlier semantics than production, so unit tests
  pass against behavior no real backend has.
- Interface documentation specifies types but never behavior: no ordering,
  idempotency, or failure clauses.
- "Not supported" errors thrown from methods the interface requires.
- A vendor-shaped parameter or mode flag has leaked into the generic API.

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

Typical for this lens: the adapter method contradicting the interface's
documented contract (both files + lines — a doc/code contradiction); the
caller's type switch on a concrete implementation (file + lines); a
conformance suite bound to one backend (missing test for the others); a
runtime log from the incident where a swap surfaced unpinned semantics.

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

Claim: The S3 adapter violates the object-store contract: `Get` on a
missing key returns `(nil, nil)` where the interface documents
`ErrNotFound`, and only the in-memory implementation is conformance-tested.

Evidence: `pkg/objstore/store.go:22-31` — interface comment: "Get returns
ErrNotFound if the key does not exist";
`pkg/objstore/s3/adapter.go:88-104` maps `NoSuchKey` to `nil, nil`
(doc/code contradiction); `pkg/objstore/conformance_test.go:12`
instantiates only `memstore.New()` (missing test).

Risk: Callers that correctly handle `ErrNotFound` dereference nil in
production while passing every unit test against the fake; each new caller
must rediscover the divergence; the abstraction actively teaches wrong
code.

Recommended fix: Normalize `NoSuchKey` to `ErrNotFound` in the adapter;
parameterize the conformance suite over all registered implementations and
run it in CI against real or containerized backends.

### S2 Example

Claim: The dispatcher branches on concrete channel types to compensate for
divergent adapter semantics, so the `Channel` abstraction no longer
substitutes.

Evidence: `notify/dispatch.ts:71-93` — `instanceof SlackChannel` batches
messages and `instanceof SmsChannel` re-orders sends; staging log
`logs/notify-2026-06-08.log` shows out-of-order delivery when the new
`PushChannel` hit the generic branch (runtime log).

Risk: Every new channel must be threaded through the dispatcher's special
cases; substitutability is gone, and each provider integration inherits an
undocumented behavioral matrix instead of a contract.

Recommended fix: Define batching and ordering in the `Channel` contract —
capabilities the adapter declares, defaults the interface guarantees; move
per-vendor compensation into the adapters; delete the type switch and add
an ordering case to the conformance suite.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Liskov Lens (id: liskov) from the invAIriant audit
protocol: abstraction and substitutability.

Examine the provided code/diff/docs for:
- behavioral contracts: are ordering, atomicity, idempotency, and error
  semantics documented per interface, or only the type signatures;
- implementations that satisfy the signature but break the contract
  (silent no-ops, "not supported" errors, divergent error values);
- callers branching on concrete types or matching vendor error strings
  behind an abstraction;
- conformance suites: whether they exist and whether they run against
  every implementation, including test fakes;
- special cases leaking vendor-shaped flags or modes into generic APIs.

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
   Liskov Lens: N / 10
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
