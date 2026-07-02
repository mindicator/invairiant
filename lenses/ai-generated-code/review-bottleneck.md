# Review Bottleneck Lens — Human Capacity vs Generation Rate

**Pack:** ai-generated-code · **ID:** `review-bottleneck`

## Purpose

This lens protects against merge pipelines where AI has raised code volume
past what humans can actually review, and nothing deterministic has taken
up the slack. It detects rubber-stamp approvals, gates waived "for
velocity", untracked provenance, and review debt nobody measures. It
applies the core `turing` lens's demand for deterministic contracts around
oracle output to the development pipeline itself: whatever a reviewer can
no longer check, a deterministic gate must.

## Scope

**Use when:**

- AI assistance has materially increased merge rate or diff size;
- approvals are near-instant on large diffs, or review latency climbs;
- it is unclear which merged code was generated, by what, reviewed by
  whom;
- the team is debating how review should keep up with generation.

**Skip when:**

- generation volume is trivial and review absorbs it comfortably — note
  that explicitly instead of scoring;
- the concern is the shape of generated code (duplication, dead surface)
  rather than pipeline capacity — that is the `generated-surface-area`
  lens.

## Core Questions

- What is the trend of merged lines and PRs per reviewer-week, and what
  has happened to review time per changed line over the same period?
- Which deterministic gates guard every merge — types, tests, lint,
  property checks, schema validation, arch-conformance tests — and which
  merge paths bypass them?
- Are PRs sized so a human can actually review them, or are large
  generated diffs approved wholesale?
- Do merge rationales reduce to "the model probably got it right" —
  approvals without comments on non-trivial diffs?
- Is provenance tracked: which code is generated, by what prompt or
  session, and which human is accountable for it?
- Is review debt a measured quantity — unreviewed or rubber-stamped
  merged lines — with an owner and a trend, or invisible?
- When a gate fails on generated code, is the failure root-caused, or is
  the code regenerated until green?
- Do hotfix, bot, or admin merge paths skip the gates entirely?

## Good-State Examples

- A dashboard tracks merged lines per reviewer-week and median review
  depth; crossing an agreed threshold triggers a process change, not a
  shrug.
- Merges are blocked without type checks, tests with a coverage floor on
  changed lines, lint, schema validation, and the arch-conformance suite
  — regardless of author or tool.
- The PR template records provenance: generated-by, prompt or session
  reference, and the accountable human reviewer.
- Large generated changes are split into stacked, individually
  reviewable PRs, and the sizing policy is written down.
- A rubber-stamp metric (approval under N minutes on more than M changed
  lines) is reported weekly; review debt has tickets and an owner.

## Red Flags

- Thousand-line diffs approved in minutes, consistently, with no
  comments.
- Coverage or lint gates waived for generated code "to keep velocity".
- No way to tell generated from hand-written code after merge.
- "Tests pass" as the whole merge rationale, where the tests were
  generated alongside the code and assert little.
- CI failures on generated code cleared by regenerate-and-retry loops
  with no root cause.
- Review debt invisible: no metric, no tickets, no owner.
- A bot or admin merge path that skips CI entirely.

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

Typical for this lens: the CI configuration exempting a path from gates
(file + lines, configuration/schema mismatch); a stated review policy the
pipeline does not enforce (doc/code contradiction); CI history showing
regenerate-until-green sequences (CI output); generated changes merged
with no test delta on changed lines (missing test).

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

Claim: The coverage gate is disabled for the fastest-growing generated
service, contradicting the written quality policy.

Evidence: `.github/workflows/ci.yml:44-58` sets `coverage-threshold: 0`
for `services/reports/**` (configuration/schema mismatch);
`docs/quality-gates.md:9` states "an 80% changed-line floor applies to
all services" (doc/code contradiction).

Risk: The highest-volume generated code is the least-guarded code: with
review already thin, neither humans nor gates check it, and defects
surface first in production.

Recommended fix: Restore the floor for `services/reports/**`; if the
floor is genuinely unreachable, fix the tests rather than the threshold;
alert on gate-config drift from the written policy.

### S2 Example

Claim: Gate failures on generated code are cleared by regenerating until
CI passes, with no root-cause analysis or reviewer engagement.

Evidence: CI runs 2214–2226 for a single PR show twelve consecutive
"regenerate" commits until green (CI output); `payments/reconcile.py:52-118`
changed materially between attempts with zero review comments.

Risk: The gate becomes a slot machine: code that passes by chance carries
unexamined behavior into a payments path, and the team learns nothing
from each failure.

Recommended fix: Require a human-written root-cause note after N failed
attempts on one PR; block force-regeneration loops in merge policy;
track a retry-to-green metric per service.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Review Bottleneck Lens (id: review-bottleneck) from
the invAIriant audit protocol: human capacity vs generation rate.

Examine the provided code/diff/docs for:
- code volume versus review capacity trends, and rubber-stamp approval
  patterns;
- deterministic gates (types, tests, lint, property checks, schema
  validation, arch-conformance) and merge paths that bypass them;
- PR sizing and genuine reviewability of generated changes;
- provenance: which code is generated, by what prompt, reviewed by whom;
- merge rationales that reduce to trusting the model;
- review debt as a measured, owned quantity.

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
   Review Bottleneck Lens: N / 10
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
