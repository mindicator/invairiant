# Generated Surface Area Lens — Diff Mass and Blast Radius

**Pack:** ai-generated-code · **ID:** `generated-surface-area`

## Purpose

This lens protects against AI-generated code volume growing faster than the
structures that keep code safe: tests, review, and ownership. It detects
oversized diffs with unexamined blast radius, near-duplicate abstractions
with tiny behavioral inconsistencies, dead or speculative code shipped
because it "came with the generation", and generated clusters no human
owns. The core `turing` lens bounds what an oracle may decide at runtime;
this lens bounds what an oracle may add to a codebase per unit of human
attention.

## Scope

**Use when:**

- a meaningful fraction of new code is AI-generated;
- large multi-file generated diffs are merging regularly;
- similar-looking helpers, clients, or wrappers keep appearing;
- the codebase grows much faster than the team or the test suite.

**Skip when:**

- generation is autocomplete-scale and ordinary review absorbs it — note
  that explicitly instead of scoring;
- the concern is reviewer capacity and merge gates rather than the shape
  of the generated code itself — that is the `review-bottleneck` lens.

## Core Questions

- For recent large generated diffs: what was the blast radius — modules
  touched, public surfaces changed — and did the task justify it?
- What is the test-to-code ratio for generated versus hand-written code,
  and do the generated tests assert behavior or merely mirror the
  implementation?
- Can a human genuinely review the typical generated PR in reasonable
  time, or is approval a formality on a diff nobody read?
- Are there near-duplicate implementations of the same abstraction with
  small inconsistencies — different timeouts, error handling, edge cases?
- Is dead or speculative code shipping because it came with the
  generation: unused exports, parameters, endpoints, config knobs?
- Does every cluster of generated code have a named owner who can answer
  for it, or is the answer a tool name?
- Is diff mass measured at all — lines added per week against test and
  review capacity?
- When duplication is found, does consolidation get scheduled, or does
  the next generation add another copy?

## Good-State Examples

- Generated PRs are size-capped unless produced by an idempotent,
  reviewed codemod script; oversized generations are split before review.
- A similarity check in CI flags near-duplicate files; each hit becomes a
  consolidation ticket with an owner, and the duplicate count trends down.
- Generated modules land with tests held to the same bar as hand-written
  code, and each PR shows the coverage delta on changed lines.
- Dead-code detection runs in CI; speculative endpoints and unused knobs
  are deleted before merge, not after.
- CODEOWNERS covers every generated cluster; "who owns this?" has a human
  answer for each directory.

## Red Flags

- A 3,000-line generated PR approved in minutes with no comments.
- Four near-identical HTTP client wrappers, one of which silently
  disables TLS verification or retries forever.
- Generated test files whose assertions restate the implementation, or
  assert nothing at all.
- Unused exports, parameters, and feature-flagged endpoints shipped
  repeatedly "because they came with the generation".
- Codebase LOC up severalfold while test runtime and reviewer headcount
  stay flat.
- Ownership questions answered with a tool name instead of a person.
- The same utility re-generated per feature directory instead of shared.

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

Typical for this lens: the pair of near-duplicate files with their
divergent lines (two file references); a diff hunk showing an oversized
generation relative to its task; coverage or dead-code output for
generated directories (CI output); an unused export or endpoint with no
caller (file + lines plus missing test).

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

Claim: Two generated mail-sending clients duplicate the same abstraction
with divergent security behavior: one disables TLS certificate
verification.

Evidence: `pkg/notify/emailer.go:40-96` and `pkg/alerts/mailer.go:33-90`
are near-identical; `pkg/alerts/mailer.go:71` sets
`InsecureSkipVerify: true`; no test pins TLS behavior for either client
(missing test).

Risk: Callers cannot know which behavior they get; the insecure copy is
one refactor away from carrying production alert traffic over unverified
TLS, and every future fix must be applied twice.

Recommended fix: Consolidate into one client with explicit TLS options;
delete the insecure default; add a test asserting verification stays on;
add a CI similarity check to catch the next near-duplicate.

### S2 Example

Claim: A generated export feature shipped with a speculative API surface
that nothing calls, inflating the maintained surface area.

Evidence: `web/src/features/export/api.ts:1-118` defines six endpoint
wrappers; coverage output for CI build 5142 reports 0% for the file
(CI output); a repository-wide search finds no callers for four of the
six functions.

Risk: Dead surface still costs review, security analysis, and dependency
upgrades; future generations imitate the unused patterns, compounding
the mass.

Recommended fix: Delete the uncalled endpoints; enable dead-code
detection as a merge gate for generated directories; regenerate from a
prompt that excludes speculative surface.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Generated Surface Area Lens (id:
generated-surface-area) from the invAIriant audit protocol: diff mass and
blast radius.

Examine the provided code/diff/docs for:
- blast radius of large generated diffs relative to the motivating task;
- test-to-code ratio and assertion quality for generated code;
- reviewability of typical generated PRs (size, cohesion, split
  strategy);
- near-duplicate abstractions with small behavioral inconsistencies;
- dead or speculative generated code: unused exports, endpoints, knobs;
- ownership of generated clusters.

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
   Generated Surface Area Lens: N / 10
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
