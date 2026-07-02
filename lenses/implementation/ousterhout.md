# Ousterhout Lens — Complexity and Deep Modules

**Pack:** implementation · **ID:** `ousterhout`

## Purpose

This lens protects against complexity leaking out of modules and onto their
callers: shallow modules whose interfaces are as complicated as their
implementations, ritual call sequences every caller must repeat, design
decisions that echo through many files, and pass-through wrapper layers
that add names without absorbing difficulty.

A module earns its existence by being deep — a simple interface in front of
real functionality. **Interfaces exist to absorb complexity, not to
redistribute it.**

## Scope

**Use when:**

- the system has grown helper layers, wrappers, or "utils" strata;
- callers of a module perform multi-step rituals to use it correctly;
- a recent change touched many files for one logical decision;
- code is organized as step_1/step_2/step_3 pipelines.

**Skip when:**

- the codebase is small enough that every "module" is a single function —
  depth questions degenerate; note that instead of scoring;
- the concern is what a module is allowed to know rather than how hard it
  is to use — that is Parnas territory.

## Core Questions

- For each module: is the interface much simpler than the implementation
  it hides? If you cannot name what it absorbs, it is a pass-through.
- Must callers know internals to use the module correctly — initialization
  order, coupling between parameters, mandatory call sequences?
- Does one design decision (a format, an algorithm, a dependency choice)
  surface in more than one module, so changing it means a multi-file diff?
- How many methods merely forward to another layer with the same
  signature, and what does each wrapper layer actually add?
- Is code decomposed by execution order (fetch, then parse, then emit) so
  that knowledge of one concept is smeared across all the steps?
- Do comments explain why — invariants, units, rationale — or restate what
  the code already says?
- When an edge case appeared, was it defined out of existence inside the
  module, or exported to every caller as a flag or a new error?
- Which configuration options exist only because the module declined to
  choose a sensible default?

## Good-State Examples

- Retry, timeout, and backoff policy live inside the HTTP client; callers
  pass a URL and receive a result or a typed error — one decision, one home.
- A file-cache module exposes `get`/`put`; eviction, locking, and
  corruption recovery are invisible to its forty callers.
- The parser normalizes input internally; the "callers must trim and
  lowercase first" ritual was deleted along with the bugs it bred.
- A comment block on the scheduler states the invariant ("no two jobs with
  the same key run concurrently") and why the lock ordering preserves it.
- A proposed wrapper layer was rejected in review as "adds a name, absorbs
  nothing," and the record of that decision lives in the PR discussion.

## Red Flags

- A shallow module: the interface's parameter surface is roughly the same
  size and shape as the implementation behind it.
- Callers repeat a ritual (configure, connect, validate, call, clean up)
  that the module could perform internally.
- One logical change fans out across many files because a design decision
  leaked into every consumer.
- Wrapper strata that forward calls one-to-one, each layer adding a
  parameter and no behavior.
- Temporal decomposition: modules named after execution phases, with one
  concept's knowledge split across all of them.
- Comments restate the code while units, invariants, and rationale go
  unrecorded.
- A blizzard of configuration knobs standing in for decisions the module
  refused to make.
- Edge cases exported to callers as flags and special return values
  instead of being defined away inside the module.

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

Typical for this lens: the interface and implementation side by side
demonstrating shallowness (both files + lines); the same ritual repeated
at several call sites (two or three file references); a diff hunk where
one format change touched five step modules; a missing test for a caller
that skips a ritual step; comments restating code (file + lines).

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

Claim: The page-store reader is shallow: fourteen public methods mirror
its internals, every caller performs the open/seek/verify ritual itself,
and two production callers skip the checksum step.

Evidence: `storage/pagefile/reader.py:20-96` — public `open_segment`,
`seek_page`, `verify_crc`, and `read_raw` mirroring internal structure;
`compaction/worker.py:141-158` and `backup/streamer.py:77-90` call
`read_raw` without `verify_crc`; no test asserts that corrupted pages are
rejected on those paths (missing test).

Risk: Complexity the module should absorb is duplicated at every call
site; the two callers that skip verification can propagate corrupt pages
into compacted segments and backups — the copies of record.

Recommended fix: Collapse the surface to `read_page(segment, n)` that
opens, seeks, and verifies internally; make raw access private; add a
corruption-injection test that every public read path must fail.

### S2 Example

Claim: The ingest pipeline is temporally decomposed: record-schema
knowledge is spread across five step modules, so a single schema change
produced a five-file diff and still missed a sixth site.

Evidence: diff hunk for change `a41f9c2` touches `step_02_parse.go`,
`step_03_normalize.go`, `step_05_dedupe.go`, `step_07_emit.go`, and
`step_08_index.go` under `ingest/steps/` for one added `region` field;
`ingest/steps/step_06_enrich.go:33-41` still assumes the old field count
and failed in staging (configuration/schema mismatch).

Risk: Every schema evolution is a shotgun edit with a built-in chance of a
missed site; the pipeline's real unit of change is "all steps at once,"
which no module boundary reflects.

Recommended fix: Centralize schema knowledge in one record module with
typed accessors; make steps operate on the typed record, not positional
fields; add a schema-bump test that fails if any step bypasses the
accessors.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Ousterhout Lens (id: ousterhout) from the invAIriant
audit protocol: complexity and deep modules.

Examine the provided code/diff/docs for:
- shallow modules: interfaces roughly as complex as the implementations
  behind them, pass-through methods, wrapper strata that absorb nothing;
- complexity pushed onto callers: mandatory rituals, ordering constraints,
  flags and special cases every consumer must handle;
- information leakage: single design decisions whose change requires a
  multi-file diff;
- temporal decomposition: phase-named modules that split one concept's
  knowledge across execution steps;
- comments: do they record invariants, units, and rationale, or restate
  the code?

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
   Ousterhout Lens: N / 10
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
