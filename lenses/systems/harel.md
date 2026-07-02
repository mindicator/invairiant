# Harel Lens — Statecharts and Reactive Behavior

**Pack:** systems · **ID:** `harel` · **Cross-listed in:** correctness

## Purpose

This lens protects against reactive systems whose behavior exists only as
an emergent property of scattered booleans: states nobody named,
transitions nobody enumerated, events arriving in modes nobody considered,
and waiting states with no way out.

If a component reacts to events over time, its behavior should be drawable
as a statechart — explicit states, guarded transitions, defined responses
to the unexpected. **What cannot be drawn cannot be reviewed, tested, or
trusted.**

## Scope

**Use when:**

- the system reacts to events over time: agents, session or connection
  managers, order/job/workflow lifecycles, protocol handlers, device
  controllers, multi-step UI flows;
- behavior is described with words like "pending," "active," "retrying,"
  "degraded," "closing";
- several booleans or status fields jointly encode a mode of operation;
- timeouts, retries, or recovery paths depend on what the system is
  currently doing.

**Skip when:**

- the code is a stateless transformation or a one-shot batch pipeline with
  no reaction to external events — termination and bounds belong to the
  Turing lens; note that explicitly instead of scoring.

## Core Questions

- Can the component's behavior be drawn as a statechart at all — a finite
  set of named states with defined transitions — and does any artifact
  (enum, table, diagram) actually enumerate them?
- Is the current state stored explicitly (one field, one enum), or
  reconstructed from booleans and nullable fields that can contradict?
- For each transition: what guards it, and are the guards checked at the
  transition point or scattered across callers?
- What happens when an event arrives in a state that does not expect it —
  ignored deliberately, rejected loudly, or applied blindly?
- Are dropped and duplicated events considered: does a missed callback
  strand the machine in a waiting state forever?
- Does every waiting state have a timeout transition and every failure
  state a recovery or terminal transition — is a stuck state reachable?
- Where behavior is hierarchical or concurrent (sub-states, parallel
  regions), is that structure explicit, or simulated with flag
  combinations whose product nobody enumerated?
- Do impossible transitions exist in code — a terminal state reachable back
  into an active one via an unguarded setter — and do tests reject them?

## Good-State Examples

- The order lifecycle is a single enum with a transition table; the only
  way to change state is `transition(event)`, which rejects undeclared
  transitions with a typed error.
- Every waiting state has a timeout transition to a defined outcome, and a
  stuck-state alert fires when a machine exceeds its expected dwell time.
- Unexpected events are handled by policy — logged-and-ignored in terminal
  states, rejected with an error elsewhere — and tests assert both.
- The connection manager's nested modes (connected → healthy/degraded) are
  modeled as explicit sub-states rather than as free-floating flag pairs.
- A statechart diagram lives next to the code, and a conformance test
  walks every declared transition and asserts that undeclared ones throw.

## Red Flags

- No explicit state variable: mode is derived from booleans and nullable
  fields (`isConnecting`, `hasError`, `retryCount > 0`) with contradictory
  combinations representable.
- State changed by direct field assignment scattered across the codebase,
  bypassing any guard or transition function.
- Events applied without checking the current state — a cancel processed
  after completion, a payment applied to a closed order.
- Waiting states with no timeout transition; failure states with no
  recovery or terminal transition.
- Unexpected events silently dropped with no log — or crashing the process.
- Flag combinations grow multiplicatively while tests cover only a handful
  of the representable modes.
- Docs or diagrams describe a lifecycle the code no longer implements.

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

Typical for this lens: the boolean cluster that encodes an implicit state
(file + lines); the field assignment that bypasses the transition function
(file + lines); a missing test for an event arriving in the wrong state; a
runtime log showing a machine stuck in a waiting state; a doc/code
contradiction between the lifecycle diagram and the implemented
transitions.

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

Claim: The upload session's mode is encoded in four independent booleans;
nine of sixteen combinations are meaningless, and two occur in production.

Evidence: `web/src/upload/session.ts:33-41` — `isUploading`, `isPaused`,
`isFinalizing`, `hasFailed` mutated independently from eleven call sites;
the frontend error feed from 2026-06-19 shows sessions with
`isUploading=true, hasFailed=true` stuck for hours (runtime log).

Risk: Undefined modes are reachable and unrecoverable; retry and cancel
logic branches on contradictory flags, so behavior in those modes is
accidental rather than designed.

Recommended fix: Replace the booleans with one state enum and a transition
function; map each legacy combination to a state or reject it; add a
stuck-state timeout and a test that enumerates every declared transition.

### S2 Example

Claim: The provisioning workflow's `WAITING_CALLBACK` state has no timeout
transition: a dropped webhook strands the workflow permanently, and the
documented lifecycle claims otherwise.

Evidence: `provisioner/workflow.py:118-152` — the only exit from
`WAITING_CALLBACK` is `on_callback()`; `docs/lifecycle.md:37` shows a
15-minute timeout edge to `FAILED` (doc/code contradiction); no test
covers callback loss (missing test).

Risk: Any dropped or misrouted callback permanently strands a customer's
provisioning in a state that looks healthy on dashboards; operators
discover it only through support tickets.

Recommended fix: Implement the documented timeout transition to `FAILED`
with an alert; add a dropped-callback test; reconcile the diagram and the
code in the same change.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Harel Lens (id: harel) from the invAIriant audit
protocol: statecharts and reactive behavior.

Examine the provided code/diff/docs for:
- whether behavior is expressible and expressed as explicit states and
  transitions (an enum and a transition function, not scattered booleans);
- transition guards: enforced at the transition point, or scattered and
  bypassed by direct assignment;
- handling of unexpected, duplicate, and dropped events in every state;
- timeout transitions for waiting states and recovery or terminal
  transitions for failure states — reachable stuck states;
- state explosion: flag combinations and parallel modes nobody enumerated;
- divergence between lifecycle docs/diagrams and implemented transitions.

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
   Harel Lens: N / 10
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
