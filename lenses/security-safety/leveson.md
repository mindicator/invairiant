# Leveson Lens — System Safety and Unsafe Control

**Pack:** security-safety · **ID:** `leveson`

## Purpose

This lens protects against systems where every component passes its tests
while the composed system does harm: automation issuing an action that is
safe in one state and unsafe in the actual state of the world, controllers
whose model has drifted from the process they control, feedback arriving
too late to matter, and overrides that live in the runbook but not in the
loop. Safety is a control problem, not a component-failure problem.

The question underneath every check: **which control action is unsafe in
which state — and what prevents it from being issued there?**

## Scope

**Use when:**

- automation acts on the world: auto-remediation, autoscaling, schedulers,
  deployment automation, agents with tools, actuation of any kind;
- a controller keeps a model of external state (cache, status store,
  last-seen metrics) and issues actions based on it;
- humans supervise, approve, or override automated behavior;
- an action's safety depends on system state or timing.

**Skip when:**

- the code only computes or renders and takes no action on external state;
- operations are single-shot and human-confirmed, with no autonomous loop —
  note that explicitly instead of scoring.

## Core Questions

- For each automated action: in which states is it unsafe, and is the state
  precondition enforced at execution time, not only at planning time?
- What is the controller's model of the process, how stale can that model
  get, and what bounds the staleness before an action is issued?
- What feedback confirms an action happened and had the intended effect —
  and can an unsafe state develop faster than that feedback arrives?
- Can an operator see in real time what the automation is doing and why:
  the current plan, recent actions, and the state model they were based on?
- Is automation authority bounded — actions per window, blast radius per
  action, scope limits — and enforced by code rather than by convention?
- Does human override interrupt in-flight work, with measured latency and a
  test proving it, or does it apply only at the next iteration?
- Are safety constraints explicit invariants ("never drain more than N",
  "never act on data older than T"), asserted in code and covered by tests?
- Do incident reviews ask which control action was unsafe and why the
  controller's model allowed it — or only which component failed?

## Good-State Examples

- The remediation controller re-reads live state and re-validates
  preconditions immediately before each action; staleness beyond a bound
  aborts with a typed outcome instead of acting.
- Automation has hard authority limits — at most one node drained per ten
  minutes, never below N healthy replicas — asserted in code and tested.
- A dashboard shows the controller's world-model beside measured reality;
  divergence beyond a threshold pauses actuation and raises an alarm.
- The kill switch is exercised in game days: pressing it halts in-flight
  actions, and the halt latency is measured and recorded each time.
- Safety constraints live in a reviewed document, each mapped to the code
  that enforces it and the test that proves the enforcement.

## Red Flags

- The controller acts on stale or incomplete state: a snapshot taken at
  plan time is executed later with no freshness re-check.
- Every local component is correct and tested, but the composed behavior is
  unsafe — and no test exercises the composition.
- Automation has no bounded authority: nothing in code limits action rate,
  scope, or blast radius.
- Human override exists on paper but not in the real flow: unreachable in
  practice, untested, or applied only after the current batch completes.
- Feedback is too slow to prevent unsafe action: the next action is issued
  before the effect of the previous one is observable.
- Two controllers drive the same actuator with no coordination between them.
- Safety constraints exist only in prose; no invariant is asserted in code.
- Incident writeups stop at "component X failed" and never examine the
  control action that did the damage.

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

Typical for this lens: the actuation call site missing an execution-time
precondition or freshness check (file + lines); a runtime log showing an
action issued against state that had already changed; a missing test for
override-during-execution or for composed multi-component behavior; a
doc/code contradiction where the runbook promises an override or a bound
that the code does not implement.

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

Claim: The auto-remediation executor drains nodes from a plan computed
earlier, without re-checking node health at execution time; under queue
backlog the acted-on snapshot can be minutes old.

Evidence: `controllers/remediation/executor.go:141-176` — the drain loop
consumes the queued plan and never re-reads health before each drain;
`logs/incident-2417/remediation.log:88-104` shows two nodes drained four
minutes after they had recovered (runtime log).

Risk: The controller amplifies partial outages: it removes healthy capacity
exactly when the system is trying to recover, and no bound exists on how
stale the state behind a destructive action may be.

Recommended fix: Re-validate preconditions at execution time with a maximum
staleness bound; abort as a typed outcome when the bound is exceeded; add a
test that mutates state between plan and execution and asserts the abort.

### S2 Example

Claim: The operator "pause" control does not interrupt in-flight work: the
flag is read once per reconciliation cycle, so an active batch runs to
completion after pause is pressed.

Evidence: `orchestrator/reconcile.py:52-90` reads `pause_requested` only at
cycle start; `docs/operations/runbook.md:33` states "Pause immediately
halts all automated actions" (doc/code contradiction); no test covers a
pause issued during an active batch (missing test).

Risk: During a misbehaving rollout — precisely when unsafe actions cluster —
operators believe the system is stopped while it keeps acting; the gap
between believed and actual authority is where control-loop accidents live.

Recommended fix: Check the pause flag before each individual action; define
and measure pause latency; add a mid-batch pause test; correct the runbook
to state the real guarantee.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Leveson Lens (id: leveson) from the invAIriant audit
protocol: system safety and unsafe control.

Examine the provided code/diff/docs for:
- automated actions whose safety depends on system state, and whether
  preconditions are enforced at execution time rather than plan time;
- the controller's model of the process: staleness bounds, freshness
  checks, and behavior when the model and reality diverge;
- feedback loops: whether effects are confirmed, and whether feedback delay
  lets further actions be issued in the gap;
- authority bounds on automation (rate, scope, blast radius) and whether
  human override interrupts in-flight actions in practice;
- explicit safety constraints and the code and tests enforcing them,
  including composed behavior across locally-correct components.

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
   Leveson Lens: N / 10
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
