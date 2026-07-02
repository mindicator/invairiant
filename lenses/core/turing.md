# Turing Lens — Computability, Termination, and Oracle Boundaries

**Pack:** core · **ID:** `turing` · **Cross-listed in:** correctness

## Purpose

This lens protects against systems that pretend to solve an unbounded or
underspecified problem by hiding behind an AI model, heuristic, or other
oracle. It detects loops without termination guarantees, retries without
bounds, decisions that cannot be replayed or debugged, model output treated
as truth, and system states left undefined behind the words "the model was
uncertain."

The question underneath every check: **is this a computation with a defined
result, or a hope with an API key?**

## Scope

**Use when:**

- the system contains agent loops, planners, or any "act until done" control flow;
- an LLM, ML model, ranking heuristic, or external oracle participates in decisions;
- there is retry, polling, convergence, or queue-consumption logic;
- a component's success criteria are underspecified ("improve", "resolve", "handle").

**Skip when:**

- the code path is fully deterministic, bounded, and side-effect-explicit
  (plain CRUD, pure transformations) — Cormen and McConnell cover it;
- the AI-specific concerns are already covered in depth by the
  `ai-generated-code` pack for this audit (avoid double-charging the same risk).

## Core Questions

- For every loop that depends on external state or model output: what is the
  explicit termination condition, and what *enforces* it (iteration cap,
  deadline, token/cost budget)?
- Where is the boundary between deterministic decisions and
  probabilistic/oracle decisions? Is that boundary written down anywhere?
- Is every search bounded — retries capped, backoff finite, queue depth
  limited, recursion depth checked?
- What is the defined system state when the oracle fails, times out, or
  returns garbage? Is "uncertain" a typed outcome or an unhandled branch?
- Can a model-mediated decision be replayed: are prompt version, model id,
  inputs, and raw output persisted?
- Is there a deterministic, non-LLM contract wrapped around every LLM output
  (schema validation, allowlist, bounds check) before it touches state?
- Can an operator debug *why* the system decided X, or only observe *that* it did?
- Is there a safe fallback for low-confidence or contradictory oracle output,
  and is it deterministic code rather than another oracle call?

## Good-State Examples

- An agent loop has `max_iterations`, a wall-clock deadline, and a cost
  budget; hitting any bound produces a typed `BudgetExceeded` outcome that
  deterministic code handles explicitly.
- LLM output is parsed against a schema; parse failure has a defined
  fallback; the raw prompt, model id, and response are persisted so the
  decision can be replayed and diffed after a model upgrade.
- A heuristic ranking function is documented *as a heuristic*; ties and
  low-confidence cases route to a deterministic default, not to a second
  heuristic.
- Retries are capped with backoff and jitter; a poison message moves to a
  dead-letter queue with an alert instead of retrying forever.
- The docs state explicitly which decisions the model is allowed to make and
  which must remain deterministic — and tests enforce the deterministic side.

## Red Flags

- "AI decides" without a bounded contract around the decision.
- An agent loop without a stop condition (`while True:` around a model call).
- LLM output directly mutates production state with no validation layer between.
- Heuristic output is treated as truth by downstream components.
- No replay path for model-mediated decisions: prompts not versioned,
  responses not persisted, model version not pinned or recorded.
- Undefined system state hidden behind "model uncertainty."
- A retry mechanism with no cap, or a budget that nothing actually enforces.
- Tests that mock the oracle as always-correct and never exercise the
  garbage/timeout/contradiction paths.

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

Typical for this lens: the loop body (file + lines) showing the absence of a
bound; the call site where model output feeds a mutation with no validation
between (file + lines); a missing test for the bound or the garbage path; a
runtime log showing a retry storm; a doc/code contradiction ("docs say max 3
attempts, code loops until success").

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

Claim: The `plan_and_execute` agent loop has no iteration cap, deadline, or
cost budget; termination depends entirely on the model emitting a
`final_answer` action.

Evidence: `agent/loop.py:41-88` — `while True:` with no counter, deadline, or
budget check; no test under `tests/agent/` exercises a never-finishing model
(missing test).

Risk: A model regression or adversarial input drives unbounded API spend and
hangs worker processes; the system has no defined state for "the loop did not
finish."

Recommended fix: Add a hard iteration cap and wall-clock deadline enforced
outside the model call; emit a typed `LoopBudgetExceeded` result handled by a
deterministic fallback; add a conformance test with a mocked never-finishing
model.

### S2 Example

Claim: Decisions made by the ticket classifier cannot be replayed: prompt
template version and raw model responses are not persisted.

Evidence: `classify/service.py:112-140` logs only the final label;
`docs/runbook.md:12` claims "all model decisions are auditable"
(doc/code contradiction).

Risk: Misclassification incidents cannot be root-caused; regressions after a
prompt or model change cannot be distinguished from input drift; the runbook's
audit claim is false.

Recommended fix: Persist prompt version, model id, and response id per
decision; add a replay command; correct the runbook.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Turing Lens (id: turing) from the invAIriant audit
protocol: computability, termination, and oracle boundaries.

Examine the provided code/diff/docs for:
- loops or retries whose termination depends on external state or model
  output, and whether any bound (iterations, deadline, budget) is enforced;
- the boundary between deterministic and probabilistic/oracle decisions,
  and whether it is documented;
- LLM/heuristic output paths: validation before state mutation, defined
  behavior on garbage/timeout/uncertainty, safe deterministic fallback;
- replayability: are prompt version, model id, inputs, and raw outputs
  persisted for model-mediated decisions;
- tests covering the non-happy oracle paths.

Rules:
- No evidence, no finding. Every finding must cite file+lines, a diff hunk,
  a test (failing or missing), a doc/code contradiction, a log, CI output,
  or a config/schema mismatch.
- If you cannot cite evidence, record the item as an Observation,
  Hypothesis, or Open question — never as a finding.
- Do not average away critical risks; one unbounded production loop is not
  offset by ten clean modules.
- Do not produce confident claims from vibes.

Output:
1. A score block:
   Turing Lens: N / 10
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
