# Tanenbaum Lens — OS/Runtime, Processes, and Fault Tolerance

**Pack:** systems · **ID:** `tanenbaum`

## Purpose

This lens protects against a system decaying into a bag of connected
scripts on top of its host: control code re-implementing what the init
system or orchestrator already provides, managed processes without
supervision or a recovery strategy, subprocess and IO edges that crash or
silently succeed instead of failing in a typed way, and restarts that lose
authority or promoted state.

The question underneath every check: **does the application drive its
substrate — OS, init system, orchestrator, engine binaries — through
declared contracts, or is it quietly re-implementing it?**

## Scope

**Use when:**

- the system manages processes, daemons, containers, or engine binaries
  (init-system units, sidecars, workers, embedded runtimes);
- there are subprocess calls, shell-outs, or host-IO edges (journals,
  sockets, firewall rules, device files);
- the system must survive process restarts, host reboots, or the loss of a
  central coordinator;
- an engine/adapter/driver layer wraps vendor binaries or runtimes.

**Skip when:**

- the code is a pure library or stateless handler with no process
  management and no host-IO edges — the von Neumann and Kleppmann lenses
  cover its state and data concerns;
- supervision is fully delegated to a managed platform and the audit target
  never touches the substrate — note that explicitly instead of scoring.

## Core Questions

- Is there a clear boundary between the substrate (OS, init system,
  orchestrator, engine binaries) and the application's control runtime —
  does the application drive the substrate rather than re-implement it?
- Does every managed unit have a defined process lifecycle
  (active/inactive/failed, restart counts), with supervision and a
  recovery strategy (restart plus validate → promote → rollback)?
- Are runtime fabric, routing/policy, state, and history cleanly
  separated, or does one component blend all four?
- Is the engine/adapter boundary clean: does each adapter describe
  capability, or has it started to own routing or policy meaning?
- Does every subprocess and IO edge (config checks, status probes, journal
  reads) have a timeout/cancel/retry/fault taxonomy — does a failed binary
  or unreadable journal yield a typed, bounded outcome rather than a crash
  or a silent success?
- Does the system survive restart without losing safe state — are builds
  idempotent per source revision, and is promoted state persisted?
- Does a node or agent keep operating with local autonomy when the central
  coordinator is unreachable?
- Are host/IO faults isolated from domain semantics — does a journal-read
  failure degrade to a marked "unavailable" value instead of a panic?

## Good-State Examples

- The substrate owns the machine; the application owns its domain
  lifecycle. Bootstrap writes systemd unit and ufw rule definitions and
  lets the substrate enforce them — it does not re-implement either.
- The engine binary owns data-plane transport, not control policy; the
  config renderer delegates per-engine through a declared adapter interface.
- A failed pre-flight config validation rolls back: the live config is
  untouched and the unit's restart count is unchanged.
- A read-only diagnostics collector runs only status/version/journal
  probes and degrades to a typed "(journal unavailable)" value on fault.
- After a hard reboot, the node rebuilds identical output for the same
  source revision and comes back serving the last promoted config.

## Red Flags

- A domain component talks directly to a vendor/engine internal instead of
  through the declared contract.
- An adapter stores routing or policy meaning.
- A policy check living in engine or driver code.
- A normal request path mutating persistent state as a side effect.
- A restart losing authority or promoted state.
- A physical/IO failure with no typed fault path.
- The engine edge becoming an unbounded plugin zoo.

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

Typical for this lens: the subprocess call site with no deadline or fault
branch (file + lines); a runtime log showing a crash where a typed outcome
was required; a missing test for the binary-absent path; a doc/code
contradiction between the runbook's recovery strategy and the unit files.

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

Claim: Engine pre-flight validation runs without a timeout, and a missing
engine binary is treated as a passed check, so unvalidated configs can be
promoted to the live path.

Evidence: `nodectl/engine/preflight.go:96-128` — `exec.Command` with no
context deadline, and the not-found error branch logs a warning and
returns nil; node log from 2026-05-14 shows "preflight skipped: engine
binary not found" followed by "promoted revision 41f2" (runtime log).

Risk: A host with a missing or corrupted engine binary silently promotes
an unvalidated config, and a hung check blocks the deploy path
indefinitely; the fault taxonomy collapses to "crash or silent success."

Recommended fix: Bound the check with a deadline; make binary-absent,
timeout, and non-zero-exit three distinct typed outcomes that abort
promotion and leave the live config untouched; add tests for all three.

### S2 Example

Claim: A supervisor restart loses promoted state: boot regenerates config
from the latest mutable inputs instead of reloading the persisted promoted
revision.

Evidence: `supervisor/src/boot.rs:58-84` rebuilds from `inputs.latest()`;
`docs/operations.md:41` states "a restart always returns the node to its
last promoted configuration" (doc/code contradiction); no restart test
covers a newer unpromoted revision being present (missing test).

Risk: A reboot can activate a configuration that never passed validation
and was never promoted — restart changes the meaning of the system, and
the documented rollback guarantee is void.

Recommended fix: Persist the promoted revision id; on boot, load exactly
that revision and advance only through the validate → promote path; add a
restart test with a newer unpromoted revision present.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Tanenbaum Lens (id: tanenbaum) from the invAIriant
audit protocol: OS/runtime, processes, and fault tolerance.

Examine the provided code/diff/docs for:
- the substrate/runtime boundary: code re-implementing the init system,
  orchestrator, or engine instead of driving it through declared contracts;
- process lifecycle for managed units: supervision, restart accounting,
  and a validate → promote → rollback recovery strategy;
- subprocess and host-IO edges: timeout/cancel/retry behavior, and whether
  failures yield typed, bounded outcomes, not crashes or silent success;
- the engine/adapter boundary: adapters describing capability without
  owning routing or policy meaning;
- restart safety and autonomy: idempotent builds, persisted promoted
  state, continued local operation when the coordinator is unreachable;
- isolation of host/IO faults from domain semantics.

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
   Tanenbaum Lens: N / 10
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
