# Ritchie Lens — Small Primitives and Sharp Interfaces

**Pack:** implementation · **ID:** `ritchie`

## Purpose

This lens protects against the opaque god framework: systems where every
capability is welded to one application object, nothing can be run, tested,
or replaced on its own, and "use the tool" means "boot the world." It checks
whether the system is built from small, composable, portable primitives —
tools that do one thing, speak documented formats, and expose surfaces an
operator can inspect with standard tools.

The question underneath every check: **can one piece of this system be
picked up and used alone, or must the whole machine be lifted to move a
bolt?**

## Scope

**Use when:**

- the system ships internal tools, pipeline stages, adapters, or SDK
  surfaces that other code (or other teams) compose;
- a plugin, driver, or engine layer claims replaceability;
- operators are expected to diagnose the system in production;
- a "platform", "framework", or "core" package sits under everything else.

**Skip when:**

- the deliverable is a single-purpose script with one caller and no
  operational life — note that explicitly instead of scoring;
- the concern is module knowledge or module depth rather than usable,
  composable pieces — Parnas and Ousterhout cover those.

## Core Questions

- Can each major capability be exercised in isolation — via a CLI, a small
  API, or a test harness — without booting the full application?
- For each primitive: are its inputs, outputs, and error/exit semantics
  stated sharply enough that a stranger could compose it correctly?
- Are interchange formats portable (plain text, JSON/JSONL, a documented
  schema), or do they exist only as in-memory objects of one framework?
- What can an operator observe with standard tools — files, logs, a status
  endpoint, a verbose flag — when the system misbehaves?
- Do convenience wrappers do exactly what the primitive does, or do they
  add hidden side effects (caching, retries, writes, network calls)?
- Is the implementation path boring — an obvious composition of named
  primitives — or does it require framework-specific ceremony to trace?
- Can the engine or adapter beneath each interface be replaced without
  touching callers, and has that ever actually been done?
- When two primitives are composed, do they communicate through declared
  inputs and outputs, or through shared hidden state?

## Good-State Examples

- The document ingester is a standalone CLI (`ingest --in raw.jsonl --out
  clean.jsonl`); the pipeline, the ops scripts, and the tests all invoke
  the same binary with the same flags.
- Every worker writes a heartbeat and progress counters to a status file; a
  stuck job is diagnosed with `cat` and `grep`, not a bespoke dashboard.
- The export format is documented, versioned JSONL; a downstream team
  consumes it with `jq` and never imports the producer's code.
- The storage adapter interface has five methods with stated error
  semantics; the SQLite-to-Postgres swap touched one package and its tests.
- A convenience wrapper's docstring lists the exact primitive calls it
  makes; it adds argument defaults and nothing else.

## Red Flags

- A god framework instead of composable primitives: every operation
  requires the application object and its full dependency graph.
- Side effects hidden in convenience wrappers: a "getter" writes caches,
  emits telemetry, or mutates state its name never admits.
- No CLI, status, or diagnostic surface: the only way to observe the
  system is to attach a debugger or read the database by hand.
- A tool cannot be used outside the full application: importing it drags
  in config, database, and message-bus initialization at import time.
- An interface is elegant but not composable: beautiful in isolation, yet
  its outputs cannot feed any other component's inputs.
- Interchange formats are private pickles or framework objects, so no
  standard tool can inspect or transform them.
- The "simple path" requires framework-specific incantations that only the
  original author can order correctly.

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

Typical for this lens: the import-time initialization that welds a tool to
the application (file + lines); the wrapper body showing undocumented side
effects (file + lines); a doc/code contradiction where the README promises
standalone tools the code cannot deliver; a missing test that exercises a
primitive outside the framework; a runtime log showing hidden side effects
firing on a nominal read path.

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

Claim: No stage of the media pipeline can run outside the full application:
importing any stage constructs `PlatformApp`, which opens Postgres, Redis,
and message-bus connections at import time.

Evidence: `platform/core/app.py:1-58` — module-level `PlatformApp()`
construction with three network connections; `README.md:24` states "each
pipeline stage is a standalone tool" (doc/code contradiction); no test in
`tests/stages/` runs any stage without the compose stack (missing test).

Risk: Stages cannot be tested, benchmarked, or reused in isolation; local
debugging requires the full stack; every new capability inherits the god
framework's dependency graph and all of its failure modes.

Recommended fix: Move connection setup from import time into an injected
context; give each stage a thin CLI entry point with file and stdin/stdout
modes; add a per-stage smoke test that must pass with no services running.

### S2 Example

Claim: The SDK convenience wrapper `getUserProfile` hides side effects: it
writes a disk cache and emits a telemetry event on every call, none of
which its name, signature, or documentation admits.

Evidence: `sdk/client/convenience.ts:140-172` — cache write and
`telemetry.emit()` inside the wrapper; staging log
`logs/edge-2026-06-14.log` shows telemetry bursts originating from a
read-only batch job (runtime log).

Risk: Callers composing the primitive get undeclared writes and network
traffic; read paths become non-idempotent; test and air-gapped
environments diverge from production in ways no signature reveals.

Recommended fix: Reduce the wrapper to defaults plus delegation; move
caching and telemetry into explicit, separately composable decorators;
document side effects in the SDK reference for any wrapper that keeps
them.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Ritchie Lens (id: ritchie) from the invAIriant audit
protocol: small primitives and sharp interfaces.

Examine the provided code/diff/docs for:
- capabilities that cannot be exercised outside the full application
  (import-time initialization, god-framework construction);
- convenience wrappers adding hidden side effects beyond the primitive
  they wrap;
- interchange formats: portable and documented versus private in-memory
  or pickled framework objects;
- observability surfaces: CLI entry points, status files, logs, and
  diagnostic flags an operator can use with standard tools;
- replaceability of the engines/adapters behind each sharp interface.

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
   Ritchie Lens: N / 10
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
