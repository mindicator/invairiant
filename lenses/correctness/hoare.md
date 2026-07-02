# Hoare Lens — Contracts, Preconditions, and Postconditions

**Pack:** correctness · **ID:** `hoare`

## Purpose

This lens protects against operations whose correctness is a private hope:
mutations with no stated precondition or postcondition, invalid states that
any constructor can produce, contracts that live in comments while tests
check only that no exception was thrown, and error paths that abandon the
system in a state nobody defined.

For every critical operation the lens demands three answers: **what must
hold before, what holds after success, and what holds after failure.**

## Scope

**Use when:**

- the code mutates persistent or shared state — money, inventory,
  permissions, schedules, files;
- an operation spans multiple writes and can fail between them;
- domain objects are constructed from user input, storage, or the wire;
- correctness claims appear in comments, docstrings, or design docs.

**Skip when:**

- the code is pure transformation already covered by property-based
  invariant checks — Cormen subsumes this lens there;
- the interesting failure is oracle uncertainty or unbounded search —
  Turing covers those boundaries.

## Core Questions

- For each state-mutating operation: what must be true before it runs,
  and what checks it — types, guard clauses, DB constraints, or nothing?
- What does the operation guarantee after success, and is that
  postcondition asserted anywhere — a test, an invariant, a constraint?
- What is guaranteed after failure: rolled back, fully applied, or a
  documented partial state? Where is that written, and where is it tested?
- Can an invalid state be constructed through public constructors,
  setters, deserialization, or a permissive schema?
- Are contracts enforced by construction (types, constraints, sealed state
  transitions) or merely described in comments?
- Do tests assert postconditions on the resulting state, or only that the
  call returned without raising?
- Are preconditions validated once at a defined boundary, or re-checked
  inconsistently at several layers with different rules?
- After a crash mid-operation, what does recovery assume about state, and
  does anything verify that assumption?

## Good-State Examples

- The transfer routine states its contract in code: guard clauses check
  amount and account status, the mutation runs in one transaction, and a
  test kills the process mid-transfer and asserts balances sum unchanged.
- `Order` cannot exist with `status = shipped` and no `shipped_at`: the
  type makes the pair inseparable and a database CHECK backs it.
- Every state-machine transition documents "requires / ensures / on
  failure," and a table-driven test walks all three clauses.
- Deserialization runs the same validator as the constructor, so no wire
  input can smuggle in a state the code could not build itself.
- The migration runbook states the postcondition ("row counts equal, all
  checksums match") and the verification query that proves it.

## Red Flags

- A function mutates state without a stated postcondition — what the world
  looks like afterward is whatever the code happens to do.
- An invalid state can be constructed freely: public setters, permissive
  constructors, or deserializers that skip validation.
- Comments describe contracts but tests do not check them.
- An error path leaves the system in an unknown state: partial writes with
  no rollback, compensation, or documented residue.
- Preconditions enforced in some callers and not others, with the callee
  trusting all of them equally.
- Assertions disabled or stripped in production with no compensating
  runtime check on critical mutations.
- Tests assert only "no exception" while the resulting state goes
  uninspected.
- A schema permits what the domain forbids: nullable columns for mandatory
  pairs, unconstrained status enums.

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

Typical for this lens: the mutation body with no guard, transaction, or
postcondition check (file + lines); the constructor or schema that admits
an invalid state (file + lines, or a configuration/schema mismatch); a
comment stating a contract beside a test suite that never checks it
(doc/code contradiction plus missing test); a runtime log showing state
drift that a postcondition check would have caught.

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

Claim: `transfer` debits and credits in two separate writes with no
transaction and no failure postcondition: if the credit write fails, the
debit persists and no code path detects or repairs the imbalance.

Evidence: `wallet/transfer.py:66-92` — `debit()` commits before `credit()`
runs; the exception propagates with no compensation; no test in
`tests/wallet/` fails the credit write (missing test); reconciliation log
`logs/reconcile-2026-05-19.log` shows a 340-cent drift (runtime log).

Risk: Money is created or destroyed by an ordinary failure; the books are
eventually wrong by construction, and only a batch job notices — after the
fact and without attribution to the failing operation.

Recommended fix: Wrap both writes in a single transaction or an idempotent
saga with a compensating credit; state the failure postcondition in the
docstring; add a fault-injection test asserting balances are conserved
when the credit write fails.

### S2 Example

Claim: An invalid `Order` state is freely constructible — `status:
"shipped"` with `shippedAt: null`. A comment promises the pair is
inseparable, but no type, constraint, or test enforces it.

Evidence: `orders/models.ts:18-42` — `shippedAt?: Date` with a public
setter and the comment "always set when status is shipped";
`db/schema.sql:57` leaves `shipped_at` nullable with no CHECK constraint
(configuration/schema mismatch); no test attempts to construct the
forbidden pair (missing test).

Risk: Any code path or manual DB edit can create shipped orders with no
timestamp; SLA reports and customer notifications downstream consume the
impossible state and fail far from the cause.

Recommended fix: Model shipment as a variant type (`Shipped { at: Date }`)
or add a CHECK constraint pairing status and timestamp; validate on
deserialization; add a test proving the forbidden pair cannot persist.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Hoare Lens (id: hoare) from the invAIriant audit
protocol: contracts, preconditions, and postconditions.

Examine the provided code/diff/docs for:
- state-mutating operations: stated and checked preconditions, and
  postconditions asserted by tests, invariant checks, or constraints;
- failure postconditions: what is guaranteed when an operation fails
  midway — rollback, compensation, or a documented partial state;
- constructibility of invalid states via constructors, setters,
  deserialization, or permissive schemas;
- contracts living only in comments while tests check merely that no
  exception was thrown;
- consistency of precondition enforcement across layers and callers.

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
   Hoare Lens: N / 10
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
