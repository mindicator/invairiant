# McConnell Lens — Construction Quality and Refactoring Discipline

**Pack:** core · **ID:** `mcconnell`

## Purpose

This lens protects against the slow loss of a team's ability to change the
system safely: changes that scatter instead of localize, names that stop
meaning what they say, documentation describing a system two versions gone,
refactors that add ambiguity instead of removing it, and high-blast-radius
changes shipped without a staged migration or a rollback path.

Construction quality is not polish; it is whether the next change is safe
to make.

## Scope

This lens is mandatory by default in invAIriant: every audit applies it
unless the engagement explicitly descopes it in writing.

**Use when:**

- always, by default — any code change, refactor, or release is in scope;
- a refactor touches many files or renames core concepts;
- a change alters a contract, security-relevant behavior, or a published
  version;
- documentation, changelog, or decision records accompany (or should
  accompany) the change.

**Skip when:**

- only under an explicit engagement-level descope — for example, auditing
  a frozen third-party snapshot the team cannot modify — and record that
  descope explicitly.

## Core Questions

- Is the change localized? If one logical change touches dozens of
  files, is the scatter forced by the architecture or by skipped staging?
- Are component and state names clear — do they still mean what they say
  after this change?
- Is accidental complexity growing: more indirection, flags, and knobs
  than the facts require?
- Do code, README, architecture docs, threat model, decision records,
  and changelog still agree — or does one now describe an older system?
- Are tests alongside the change: does the diff that changes behavior also
  add or update the tests that pin it?
- For high-blast-radius changes: is there a staged migration and a
  rollback path, and has either been exercised?
- Does the version bump reflect the actual blast radius of the change?
- Have comments and docstrings become stale boundary sources — describing
  defaults, parameters, or invariants the code no longer has?
- Does the refactor remove ambiguity or add it — are there fewer concepts
  after than before?

## Good-State Examples

- A contract change lands as one reviewable unit: code, tests pinning the
  new behavior, README and architecture updates, a changelog entry, and a
  version bump that matches the blast radius — nothing deferred.
- A rename refactor ships in stages — introduce the new name, migrate call
  sites in bounded batches, remove the old name — with each stage
  releasable and revertible.
- A storage-format change carries a written rollback procedure that was
  rehearsed in a staging environment before rollout.
- Docstrings state the invariant the tests enforce; when the invariant
  changed, the same PR changed both.
- After the refactor there are fewer concepts than before, and the old
  pattern is gone rather than coexisting with its replacement.

## Red Flags

- "We'll fix the docs later" after changing a contract or
  security-relevant behavior.
- README or architecture docs describe an old version of the system.
- A single refactor changes dozens of files with no staged migration.
- No rollback path for a high-blast-radius change.
- Tests for changed behavior deferred to a future PR — or to nowhere.
- A patch version bump on a behavior-changing or contract-breaking diff.
- Comments or docstrings contradict the code they sit next to.
- A refactor leaves old and new patterns alive indefinitely, doubling the
  concept count it set out to reduce.

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

Typical for this lens: the diff hunk that changes behavior with no
accompanying test change (missing test); a doc/code contradiction where
the README or threat model describes the previous contract; a version or
changelog entry whose bump does not match the diff's blast radius; the
stale docstring sitting directly above the changed code (file + lines).

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

Claim: A security-relevant default changed without documentation, test, or
changelog updates: session token lifetime was raised from 15 minutes to 24
hours while the README and threat model still promise 15 minutes.

Evidence: `internal/auth/session.go:41` — `defaultTTL = 24 * time.Hour`;
`README.md:88` and `docs/threat-model.md:52` both state that sessions
expire after 15 minutes (doc/code contradiction); no test asserts the TTL
(missing test); the release shipped as a patch version.

Risk: Operators and reviewers reason from false documents; a stolen token
is now valid 96 times longer than the threat model assumes; the
patch-level bump hides the change from anyone triaging upgrades by
version.

Recommended fix: Decide the intended TTL and pin it with a test; update
README, threat model, and changelog in the same PR; re-release with a
version bump that matches the behavioral change.

### S2 Example

Claim: A cross-cutting rename refactor changed 63 files in one commit with
no staged migration and no rollback path, and left the API boundary
speaking two naming schemes.

Evidence: PR #518 spans 63 files across `api/routes/` and
`web/src/client/` in a single commit; `api/routes/exports.py:19-26` still
accepts only the old field `job_ref` while `web/src/client/jobs.ts:33-47`
now sends `job_id` (configuration/schema mismatch across the boundary);
the PR description contains no migration or rollback notes.

Risk: A partial deploy breaks the API boundary in production; the commit
cannot be reverted cleanly because unrelated fixes rode along; the
refactor increased ambiguity by leaving both names live.

Recommended fix: Split the change into staged batches — accept both
names, migrate senders, remove the old name — each releasable and
revertible; add a boundary contract test that fails on field-name drift.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the McConnell Lens (id: mcconnell) from the invAIriant
audit protocol: construction quality and refactoring discipline.

Examine the provided code/diff/docs for:
- change locality: one logical change scattered across the codebase
  without a staged migration;
- naming and comments: components, states, and docstrings that still mean
  what they say;
- documentation synchrony: code versus README, architecture docs, threat
  model, decision records, and changelog;
- test proximity: behavior changes carrying their tests in the same
  change;
- migration and rollback for high-blast-radius changes, and version bumps
  that match actual blast radius;
- refactors that add ambiguity instead of removing it.

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
   McConnell Lens: N / 10
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
