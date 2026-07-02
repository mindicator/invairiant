# Dijkstra Lens — Simplicity, Structured Reasoning, and Negative Space

**Pack:** core · **ID:** `dijkstra`

## Purpose

This lens protects against solving a simple problem with an overly clever
mechanism, and against complexity hiding behind appealing names: implicit
control flow, hidden branches, unbounded special cases, abstractions that
mask real side effects, and clever fallbacks that quietly break declared
safety properties.

It equally audits the negative space: the explicit statements of what the
system must NOT do, and the checks that enforce each one.

## Scope

**Use when:**

- the system declares safety properties ("fail closed", "never send
  unencrypted", "never write outside the sandbox") whose negation must be
  checkable;
- control flow includes fallbacks, degraded modes, or automatic recovery
  decisions;
- a "smart" mechanism (heuristic, auto-tuning, dynamic dispatch) sits
  where an explicit policy declaration could;
- long-running control loops, supervisors, or daemons handle errors.

**Skip when:**

- the cleverness concern is termination or oracle output — the Turing
  lens owns model loops and oracle boundaries;
- the concern is plain readability with no safety property or control
  flow at stake — McConnell covers construction quality.

## Core Questions

- Can the flow be simplified without losing a stated property? What does
  each clever mechanism buy, in one sentence?
- Is control flow explicit, or does behavior emerge from reflection,
  dynamic dispatch, or decorator stacks a reader cannot trace statically?
- Does any abstraction hide a real side effect — for example, silently
  switching to a less-safe path while presenting the same interface?
- Do fallbacks preserve declared safety properties, or degrade to an
  unverified or unencrypted mode without a marker and policy consent?
- Where is the negative space written down — the list of things the
  system must never do — and which named check enforces each item?
- Is error handling structured: a typed outcome per failure class, or a
  broad catch that swallows critical failures inside a control loop?
- Is the number of states, modes, and special cases growing without
  necessity — and can anyone still enumerate them?
- Are unrelated responsibilities mixed inside a single method, so
  reasoning about one requires reasoning about all of them?

## Good-State Examples

- A degraded mode exists, but entering it requires an explicit policy
  flag, emits a distinct marker and metric, and is refused by default —
  never a silent switch.
- The docs carry a short list of "the system must never ..." statements,
  each paired with a named test or CI check that enforces it.
- A control loop handles each failure class as a typed outcome; unknown
  exceptions terminate the iteration loudly instead of being absorbed.
- A proposed adaptive selector was replaced by a declared policy table;
  behavior is enumerable, diffable, and reviewable.
- Each method does one thing — parse, decide, or actuate — and the
  calling flow reads top to bottom without hidden dispatch.

## Red Flags

- An implicit fallback to a less-safe mode without an explicit marker and
  policy consent.
- A broad `except`/`catch` that swallows a critical failure inside a
  control loop.
- A "smart" heuristic where an explicit policy declaration belongs.
- An extra layer that owns nothing: it forwards calls and adds a name.
- Two distinct concepts conflated under one name, so reasoning about one
  silently leaks onto the other.
- No written negative space, so no check can enforce what must not happen.
- Special cases accumulating without bound — each incident adds a branch
  that no one can enumerate afterward.
- Control flow untraceable statically; indirection for its own sake.

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

Typical for this lens: the fallback branch that silently degrades safety
(file + lines); the broad exception handler wrapped around a control-loop
body (file + lines); a declared "must never" statement with no test or
check enforcing it (missing test); a runtime log showing the system in a
mode the documentation says does not exist.

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

Claim: On handshake timeout the client silently retries with peer
verification disabled, inverting the declared "never connect unverified"
property with no marker and no policy consent.

Evidence: `src/transport/connect.ts:74-109` — the retry path constructs
the session with `verifyPeer: false`; `docs/security.md:23` declares "the
client never establishes a session without peer verification" (doc/code
contradiction).

Risk: Under degraded network conditions — exactly when interception is
most likely — the system breaks its own safety property, and neither logs
nor policy show that the downgrade happened.

Recommended fix: Remove the silent downgrade; gate any degraded mode
behind an explicit policy flag with a distinct typed state and metric;
add a test asserting handshake failure yields refusal, not downgrade.

### S2 Example

Claim: The supervisor loop swallows every exception, so a critical failure
such as state-store corruption is logged as a routine warning while the
loop keeps actuating on stale state.

Evidence: `daemon/supervisor.py:141-166` — `except Exception:
log.warning(...); continue` wraps the whole iteration body; no test
exercises a poisoned iteration (missing test); `var/log/supervisor.log`
from 2026-05-30 shows 4,200 identical warnings over six hours while
actuation continued (runtime log).

Risk: The loop cannot distinguish recoverable from critical failures; a
corrupted store drives hours of wrong actuation with no alert, and the
failure stays invisible until external damage surfaces.

Recommended fix: Replace the broad catch with typed handlers per failure
class; route unknown exceptions to a halt-and-alert path; add a test that
a poisoned iteration stops the loop instead of degrading it into a
warning generator.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Dijkstra Lens (id: dijkstra) from the invAIriant audit
protocol: simplicity, structured reasoning, and negative space.

Examine the provided code/diff/docs for:
- clever mechanisms where a simpler explicit construct would preserve all
  stated properties;
- fallbacks and degraded modes: explicit, marked, and policy-gated — or
  silent downgrades that break declared safety properties;
- negative space: written "must never" statements and the checks that
  enforce them;
- error handling structure: typed failure outcomes versus broad swallows
  in control loops;
- hidden control flow, layers that own nothing, and distinct concepts
  conflated under one name;
- growth in states, modes, and special cases without necessity.

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
   Dijkstra Lens: N / 10
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
