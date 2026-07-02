# Prompt–Code Drift Lens — Instructions vs Reality

**Pack:** ai-generated-code · **ID:** `prompt-code-drift`

## Purpose

This lens protects against divergence between AI-facing instructions —
CLAUDE.md, AGENTS.md, system prompts, prompt templates — and the code they
describe. Stale instructions steer every future generation wrong at scale:
the model builds against an architecture that no longer exists, violates
constraints nobody enforces, and treats an unversioned prompt file as the
de facto spec. Where the core `turing` lens asks whether oracle decisions
are bounded, this lens asks whether the instructions feeding the oracle
still describe the system it is changing.

## Scope

**Use when:**

- the repository contains AI instruction files (CLAUDE.md, AGENTS.md,
  editor rules, system prompts, prompt templates);
- AI assistants routinely generate or modify code in this codebase;
- instructions encode architectural constraints ("never X", "always Y");
- a refactor has changed structure that the instructions describe.

**Skip when:**

- no AI-facing instruction files exist and no prompt encodes claims about
  the codebase — note the absence explicitly instead of scoring;
- the prompts in question are runtime product prompts whose output feeds
  decisions — that is the `oracle-boundary` lens.

## Core Questions

- Do the instruction files describe the current architecture or a previous
  one? When were they last reconciled with the code, and by whom?
- Does any instruction say "never X" while the code does X — or "always Y"
  while the code does not?
- Is every constraint stated in an instruction file also enforced by a
  test, lint rule, or arch-conformance check — or is the model itself the
  only enforcement mechanism?
- Are prompt files versioned, code-reviewed, and owned like code, or
  edited ad hoc with no history?
- Do instructions reference paths, modules, commands, or frameworks that
  no longer exist?
- Do prompts carry implicit assumptions (directory layout, naming,
  framework versions) that no test encodes?
- Has a prompt file become the only place a rule is written — an
  unversioned de facto spec — without being treated as one?
- When generated code violates a stated constraint, is that handled as
  drift (fix the instruction or the code) or silently merged?

## Good-State Examples

- CLAUDE.md has a named owner and a review cadence; architectural changes
  require a paired instruction update in the same PR.
- Every "never/always" statement in AGENTS.md maps to an enforcing test or
  lint rule, and the mapping table lives next to the instructions.
- Prompt templates sit in version control behind CODEOWNERS; every change
  is a reviewed diff, and prompt versions appear in generation metadata.
- A CI job checks instruction files for referenced paths and commands and
  fails when they no longer exist in the repository.
- The PR template asks "does this change invalidate any AI instruction?"
  and reviewers answer it with a file reference, not a checkbox reflex.

## Red Flags

- Instruction files reference modules or directories deleted months ago.
- "Never call the database from handlers" in the instructions; three
  handlers do it today.
- Prompt files edited directly in a console or dashboard, no VCS trail.
- Constraints that exist only in prompts, with no test or lint enforcing
  them anywhere.
- Nobody owns CLAUDE.md; its last commit predates the latest refactor.
- Generated code consistently violates a stated convention — the
  instructions are unread, wrong, or both.
- Two instruction files give contradictory guidance on the same topic.

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

Typical for this lens: the instruction line and the code that contradicts
it (doc/code contradiction with both references); a stale path or command
in an instruction file (file + lines); a constraint stated only in a prompt
with no enforcing test (missing test); version history showing a prompt
file untouched across a major refactor (diff hunk).

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

Claim: AGENTS.md forbids ledger writes outside the ledger package, but a
webhook handler writes ledger tables directly — and generation guided by
these instructions keeps producing both patterns.

Evidence: `AGENTS.md:34` — "never write to the ledger outside
`internal/ledger`"; `api/webhooks/handler.go:201-226` inserts into
`ledger_entries` over a raw connection (doc/code contradiction); no lint or
arch-conformance rule covers the constraint (missing test).

Risk: The stated invariant is fiction: humans and models generate against
different rulesets, and ledger consistency depends on which one touched
the file last.

Recommended fix: Decide the real rule; enforce it with an arch-conformance
test that fails on out-of-package ledger writes; fix the handler or amend
AGENTS.md in the same change.

### S2 Example

Claim: The code-generation system prompt mandates an ORM that was removed
from the codebase two major versions ago, steering every generation toward
dead patterns.

Evidence: `prompts/codegen/system.txt:12-19` requires `legacy-orm` query
builders; `package.json:18-44` no longer lists the dependency
(configuration/schema mismatch).

Risk: Generated code arrives pre-broken or gets hand-patched in review;
reviewer effort is spent correcting the same instructed-in mistake, and
trust in the instruction files erodes.

Recommended fix: Reconcile the prompt with the current stack; add a CI
check validating instruction-referenced packages and paths against the
repository; assign an owner for the prompt directory.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Prompt–Code Drift Lens (id: prompt-code-drift) from
the invAIriant audit protocol: instructions vs reality.

Examine the provided code/diff/docs for:
- divergence between AI instruction files (CLAUDE.md, AGENTS.md, system
  prompts, templates) and the current code and architecture;
- "never/always" constraints violated by code, or enforced only by the
  prompt with no test or lint behind them;
- stale references: paths, modules, commands, or frameworks that no
  longer exist;
- ownership, versioning, and review of prompt files, and when they were
  last reconciled with the code;
- implicit model assumptions not encoded in tests.

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
   Prompt–Code Drift Lens: N / 10
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
