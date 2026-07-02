# Cormen Lens — Algorithmic Rigor and Invariants

**Pack:** core · **ID:** `cormen` · **Cross-listed in:** correctness

## Purpose

This lens protects against systems whose correctness is an accident of how
they happen to be called rather than a property of their design: critical
flows with no stated invariant, state transitions scattered across flags
instead of a finite phase table, commands that double-actuate when re-run,
versions that silently regress, and failure paths nobody can describe.

The question underneath every check: **can this flow's contract be written
on one page — states, transitions, invariants, failure outcomes — and does
anything enforce it?**

## Scope

**Use when:**

- a critical flow mutates shared or persistent state (apply, promote,
  rotate, migrate, provision, bill);
- the system contains state machines, staged pipelines, or multi-step
  actuation of any kind;
- commands can be retried, duplicated, or interrupted mid-flight;
- versioned specs or artifacts exist where regression or divergence would
  corrupt downstream state.

**Skip when:**

- the code is stateless transformation or presentation with no transitions
  and no persistence — McConnell covers construction quality there;
- the correctness concern is termination or oracle output — the Turing
  lens owns loops and model boundaries (avoid double-charging the risk).

## Core Questions

- For each critical flow: can the invariant be stated in one sentence, and
  which test or gate enforces it?
- Can every state transition be written as a table — a finite set of
  phases — or does state live implicitly in flags, nulls, and call order?
- Is a repeated command idempotent? Does a re-run double-actuate, or
  short-circuit as a defined no-op on byte-identical input?
- Is monotonicity enforced where required — versions and sequence numbers
  never regress — with attempted regressions rejected, not accepted?
- What is the defined outcome of failure at each stage: bounded and
  fail-closed (nothing promoted, prior state unchanged), or undefined?
- Does correctness depend on an implicit order of side effects that no
  conformance gate or test pins down?
- Where a closed vocabulary or single source of truth should exist, has a
  hidden heuristic crept into a downstream component instead?
- Are invariants covered by property or conformance tests, or only by
  happy-path examples?
- Is there branching that no recorded decision explains — magic special
  cases only their author could justify?

## Good-State Examples

- A staged apply pipeline has an explicit order — descriptor → validate →
  render → check → promote → verify → rollback — and a conformance test
  fails if a stage is skipped or reordered.
- Re-applying a byte-identical artifact is a defined no-op: the command
  short-circuits without a second mutation, restart, or version bump.
- A failed validation has a defined outcome: nothing is promoted, the
  target's state is byte-identical to before the attempt, and the failure
  surfaces as a typed result.
- Versioned specs have one source of truth (a single version field, one
  manifest, one vocabulary file); consumers read that authority instead of
  re-deriving it, and version regression is rejected at write time.
- An interrupted run resumes from, or rolls back to, a named phase — never
  a half-applied hybrid that no table describes.

## Red Flags

- "It works because of how it is called right now" — correctness rests on
  current call sites, not on the contract.
- Implicit side-effect ordering with no conformance gate: reordering two
  calls would corrupt state, and nothing would notice.
- A heuristic living in a downstream component while the contract owner is
  another layer (a consumer guessing what the producer should declare).
- An undefined failure path: a broad exception swallow inside a control
  loop, leaving state neither promoted nor rolled back.
- A state transition that cannot be written as a table.
- Unknown retry, duplicate, or restart behavior — nobody can say what a
  re-run of the command actually does.
- A version or sequence value that can silently regress.
- Magic branching that no recorded decision explains.

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

Typical for this lens: the pipeline or loop body showing the undefined
failure branch (file + lines); a missing property/conformance test for a
stated invariant; a runtime log showing a double actuation after a retry;
a doc/code contradiction where the spec declares an ordering the code does
not enforce; a schema that permits version regression.

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

Claim: The release pipeline does not fail closed: a validation error is
logged at warn level and execution continues into the promote step, so the
outcome of invalid input is undefined.

Evidence: `internal/release/pipeline.go:96-133` — the error returned by
`ValidateBundle` is logged and dropped; execution falls through to
`PromoteBundle`; `docs/deploy-spec.md:41` states "a failed validation
promotes nothing, target byte-identical" (doc/code contradiction).

Risk: An invalid or corrupted bundle can reach production; after a failed
run the target is in a state no table describes — neither the old version
nor a verified new one — and the written spec no longer matches behavior.

Recommended fix: Return a typed validation failure that aborts before
promote; add a conformance test asserting the target is byte-identical
after any failed validation; make the stage order itself a tested contract.

### S2 Example

Claim: Re-running the apply command double-actuates: there is no
idempotency short-circuit for byte-identical input, so every retry restarts
the managed service and bumps the revision.

Evidence: `scheduler/apply_job.py:47-83` — each run unconditionally
increments `revision` and calls `restart_service()` with no content-hash
check; no test under `tests/scheduler/` covers a repeated apply (missing
test); `ops/logs/apply-2026-06-14.log` shows two restarts 40 seconds
apart for the same artifact hash after a network retry (runtime log).

Risk: Retries — the normal case under network failure — cause spurious
restarts and revision churn; monitoring cannot distinguish a real change
from a duplicate, and automation keyed on revisions misfires.

Recommended fix: Short-circuit on byte-identical input as a defined no-op;
key actuation on content hash rather than invocation; add a property test
asserting that apply-twice equals apply-once.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Cormen Lens (id: cormen) from the invAIriant audit
protocol: algorithmic rigor and invariants.

Examine the provided code/diff/docs for:
- critical flows without a statable invariant or a test/gate enforcing it;
- state transitions that cannot be written as a finite phase table;
- idempotency: what a re-run, duplicate, or restarted command does;
- monotonicity where required: versions/sequence numbers never regress;
- failure behavior: bounded, fail-closed, defined outcome at every stage;
- hidden heuristics or magic branches where a closed vocabulary or single
  source of truth should be.

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
   Cormen Lens: N / 10
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
