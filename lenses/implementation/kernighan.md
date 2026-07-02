# Kernighan Lens — Readability, Debuggability, and Operator Comprehension

**Pack:** implementation · **ID:** `kernighan`

## Purpose

This lens protects against systems that can be written but not debugged:
code at the limit of its author's cleverness, errors that say "failed" and
nothing else, documentation that describes architecture but not what to do
at 3 a.m., and failures whose cause is smeared across ten layers. Debugging
is twice as hard as writing, so code written at full cleverness is, by
construction, beyond its own author's ability to debug.

Every check reduces to one scenario: **a competent stranger is paged at
night — can they localize, reproduce, and fix the failure with what the
system gives them?**

## Scope

**Use when:**

- real maintainers or on-call operators are expected to run the system;
- the code will be modified by people (or AI agents) other than its author;
- error handling, logging, or runbooks are part of the review surface;
- a component has a history of long incident investigations.

**Skip when:**

- the artifact is throwaway analysis code with no operational life — note
  that explicitly instead of scoring;
- the concern is module boundaries or behavioral contracts rather than
  comprehension — Parnas and Liskov cover those.

## Core Questions

- Can a maintainer who did not write the code locate the failing component
  from the error message and logs alone, without a debugger?
- Does every operator-facing error state what failed, for which input or
  entity, and what to check or do next?
- Is there a minimal-repro path: a command or test that reproduces a
  reported failure in isolation, without the full production environment?
- Does a failure surface at the layer that can explain it, or does the
  cause sit many layers below the symptom?
- Where is the cleverness budget spent? Is any hot or critical section
  written at a level its own author could not debug under pressure?
- Do runbooks contain executable commands for the top failure modes, or
  only prose and diagrams?
- How much of the codebase must be read before a trivial fix can be made
  safely — one module, or the whole canon?
- Do logs carry the identifiers (request id, entity id, attempt number)
  needed to follow one failing operation across components?

## Good-State Examples

- A failed upload logs `upload rejected: object 4f2c exceeds 25MB limit
  (got 31MB); raise limit in storage.yaml or shrink input` — the entity,
  the bound, and two next actions in one line.
- Every incident-prone subsystem has a `--repro` mode that replays a
  captured failing input against a single process with no network.
- The runbook's top entry is a copy-pasteable triage sequence: three
  commands, their expected outputs, and the decision tree they feed.
- A deliberately plain retry loop replaced a metaprogrammed one; the diff
  notes "optimized for debuggability" and the on-call guide shrank.
- Log lines share a request id from ingress to storage, so one `grep`
  reconstructs the full path of any failing request.

## Red Flags

- Code is clever but not debuggable: dense one-liners, reflection, or
  metaprogramming on the paths where failures actually occur.
- An error says "failed" without context or action — no input, no entity,
  no bound, no hint what to check next.
- Documentation is beautiful but not operational: polished architecture
  prose, zero executable triage steps.
- A trivial fix requires reading a huge canon before it can be attempted
  safely.
- Failure cause is spread across ten layers: the symptom's origin can only
  be found by walking the whole stack by hand.
- Errors are caught and rethrown stripped of the underlying cause, so the
  original context is unrecoverable at the surface.
- Logs lack correlation identifiers, so concurrent operations cannot be
  told apart during an incident.
- No production failure has ever been reproduced locally, and no tooling
  exists to try.

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

Typical for this lens: the catch block that swallows or strips the cause
(file + lines); a context-free error string plus the runtime log where
hundreds of identical copies made an incident undiagnosable; a runbook with
no executable commands contradicting its own "operations guide" claim
(doc/code contradiction); a missing test or repro harness for a recurring
failure mode.

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

Claim: Replication errors are reduced to the string "sync failed": the
underlying error, peer, and shard are discarded, making incidents
undiagnosable from logs alone.

Evidence: `sync/replicator.go:214-228` — `return errors.New("sync failed")`
drops the wrapped cause and the peer id; incident log
`logs/incident-2026-05-30.log` contains 412 identical "sync failed" lines
across three shards with no distinguishing context (runtime log).

Risk: On-call cannot tell network partitions from checksum mismatches or
quota errors; time to diagnosis is bounded below by a live debugger
session; the same incident will repeat at the same cost.

Recommended fix: Wrap instead of replacing: include peer, shard, attempt,
and the underlying error; add per-cause counters; assert in a test that
every replicator error names its peer and cause.

### S2 Example

Claim: The proration calculator is written at maximum cleverness — a
44-line chained reduce with nested ternaries — and its edge branches are
untested, so nobody, including its author, can safely fix it.

Evidence: `billing/proration.ts:55-98` — single expression with nested
ternaries and no intermediate names; no test in `billing/__tests__/`
covers the leap-year or mid-cycle-downgrade branches (missing test).

Risk: The next billing bug lands in code no one can step through
confidently; a fix under time pressure risks silent overcharges — the
class of defect that costs refunds and trust.

Recommended fix: Unfold the expression into named intermediate steps with
a unit test per branch; add property tests around month boundaries; treat
readability of money paths as a review gate.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Kernighan Lens (id: kernighan) from the invAIriant
audit protocol: readability, debuggability, and operator comprehension.

Examine the provided code/diff/docs for:
- error paths: do messages carry input/entity context and a next action,
  or just "failed"; is the underlying cause preserved through rethrows;
- cleverness on failure-prone paths: dense, reflective, or metaprogrammed
  sections that cannot be stepped through under pressure;
- minimal repro: commands, harnesses, or tests that reproduce failures in
  isolation;
- operational docs: runbooks with executable triage steps versus
  architecture prose;
- failure localization: correlation ids in logs, and whether symptoms
  surface near their causes.

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
   Kernighan Lens: N / 10
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
