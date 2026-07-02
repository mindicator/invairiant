# Oracle Boundary Lens — What the Model May Decide

**Pack:** ai-generated-code · **ID:** `oracle-boundary`

## Purpose

This lens protects against systems where a model quietly becomes the
decision maker for things nobody explicitly delegated to it: state mutations
shaped by unvalidated output, "the model handles that case" standing in for
a written contract, and upgrades that change behavior with no regression
evidence. It audits the boundary itself — which decisions the model owns,
which must remain deterministic, and what contract wraps every crossing.
This is the AI-specific application of the core `turing` lens: `turing`
audits oracle discipline in any system; this lens audits the model-as-oracle
in AI-assisted ones.

## Scope

**Use when:**

- an LLM or other model participates in runtime decisions (classification,
  routing, action selection, content or config generation);
- model output can reach state: database writes, API calls, queues, shell
  commands, SQL, or distributed configuration;
- a prompt, model version, or sampling parameter is being changed;
- an agent or tool-calling loop can trigger side effects.

**Skip when:**

- no model participates at runtime (models only wrote the code — that is
  the territory of the other `ai-generated-code` lenses);
- generic loop/termination discipline is already scored under the core
  `turing` lens for this audit (avoid double-charging the same risk).

## Core Questions

- Is there a written list of which decisions the model may make and which
  must remain deterministic? Where does it live, and who keeps it current?
- Is every model output validated by deterministic code — schema, allowlist,
  bounds check — before it touches state?
- Can model output reach a production mutation, shell command, or SQL
  statement without passing through that validation layer?
- What is the defined behavior when the model is uncertain, times out, or
  contradicts itself across calls — a typed outcome or an unhandled branch?
- Can every model-mediated decision be replayed: prompt version, model id,
  sampling parameters, and raw response persisted per decision?
- Are model or prompt upgrades treated as behavior changes, with regression
  evidence (eval suite, side-by-side diff) required before rollout?
- Is the blast radius of a wrong model decision bounded — rate limits,
  reversibility, human confirmation for irreversible actions?
- Do tests exercise the garbage, timeout, and contradiction paths, or only
  the happy path with a well-behaved mock?

## Good-State Examples

- A one-page decision registry names every model-owned decision and its
  deterministic counterpart; an arch-conformance test fails when a new
  model call site is not listed there.
- The model proposes, deterministic code disposes: output is parsed into a
  typed value against an allowlist; anything unparseable becomes a typed
  `ModelRejected` outcome with a deterministic default.
- Tool calls emitted by the model pass an argument schema and an action
  allowlist; destructive actions additionally require human confirmation.
- Every decision record persists prompt version, model id, parameters, and
  raw response; a replay command reproduces any past decision for diffing.
- A model upgrade ships like a schema migration: pinned version bump, eval
  suite results recorded in the PR, rollback path documented.

## Red Flags

- Model output interpolated into SQL, shell commands, or config templates.
- No written boundary anywhere; "the model handles it" is the design.
- Uncertainty has no typed representation — only success paths are handled.
- A model upgrade shipped as a silent dependency bump with no eval evidence.
- Raw responses discarded, sampling parameters unrecorded — replay is
  impossible.
- Free-text model output parsed with a regex and trusted downstream.
- The model contradicts itself across calls; no reconciliation rule exists.
- A validation layer exists but sits after the mutation it should guard.

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

Typical for this lens: the call site where model output feeds a mutation,
shell command, or SQL with no validation between (file + lines); a missing
test for the garbage/timeout/contradiction path; a doc/code contradiction
between the stated decision boundary and an actual model call site; a model
version change in config with no eval evidence attached
(configuration/schema mismatch).

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

Claim: Model-generated SQL fragments are executed against the production
replica with no schema validation or allowlist between the model and the
database.

Evidence: `billing/copilot/query_runner.py:64-92` — the model's text
response is formatted into a SQL string and passed to `execute()`
unmodified; nothing under `tests/billing/copilot/` exercises a malformed or
hostile model response (missing test).

Risk: A model regression or prompt injection can read or mutate arbitrary
billing data; the effective data-access contract is whatever the model
emits today.

Recommended fix: Replace free-form SQL generation with a parameterized
query builder fed by validated, typed fields; allowlist permitted tables
and operations; add tests feeding hostile and malformed model output.

### S2 Example

Claim: Queue-routing decisions made by the triage model cannot be replayed:
prompt version and sampling parameters are never persisted.

Evidence: `services/triage/llm_router.go:118-149` logs only the chosen
queue name; `docs/ai-decisions.md:22` states "every model decision is
reproducible from the audit log" (doc/code contradiction).

Risk: Misrouting incidents cannot be root-caused; after a prompt or model
change, regressions are indistinguishable from input drift; the audit
claim is false.

Recommended fix: Persist prompt version, model id, parameters, and raw
response per decision; add a replay command; correct or fulfill the
documentation claim.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Oracle Boundary Lens (id: oracle-boundary) from the
invAIriant audit protocol: what the model may decide.

Examine the provided code/diff/docs for:
- an explicit, written boundary between model-owned and deterministic
  decisions, and whether the code respects it;
- validation (schema, allowlist, bounds) between model output and any
  state mutation, shell command, or SQL;
- defined, typed behavior for model uncertainty, timeout, and
  self-contradiction, with deterministic fallbacks;
- replayability: prompt version, model id, sampling parameters, and raw
  responses persisted per decision;
- model/prompt upgrades treated as behavior changes, with regression
  evidence and tests covering the non-happy paths.

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
   Oracle Boundary Lens: N / 10
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
