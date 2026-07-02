# von Neumann Lens — State, Memory, Control, and Execution

**Pack:** systems · **ID:** `von-neumann`

## Purpose

This lens protects against systems where nobody can say where the state
actually lives: mutable data with no single owner, caches quietly promoted
to sources of truth, configuration doubling as a runtime database, secrets
mixed into state files, and restarts that change what the system means.

The question underneath every check: **what is stored, who is allowed to
write it, and does execution still mean the same thing after a restart?**

## Scope

**Use when:**

- the system persists anything (files, databases, key-value stores) or
  holds long-lived in-memory state;
- multiple components read or write shared state, or a control loop acts
  on stored values;
- configuration, feature flags, or environment variables influence runtime
  behavior;
- restart and recovery behavior matters (daemons, agents, schedulers,
  stateful services).

**Skip when:**

- the code is a pure transformation with no persistence and no shared
  mutable state — note that explicitly instead of scoring;
- the concern is ordering across nodes (Lamport lens) or data-model
  evolution and migrations (Kleppmann lens), not ownership of state.

## Core Questions

- For every piece of critical state: who owns it — exactly one component
  with write authority, or several writers with informal coordination?
- Which state is persistent and which transient — is the split deliberate?
  What is intentionally lost on restart, and what must survive?
- Are code, configuration, data, and secrets stored, versioned, and
  access-controlled separately, or does one file or store blend them?
- After a crash-restart, does the system reconstruct the same meaning —
  same routes, same permissions, same in-flight work — or does behavior
  depend on what happened to be in memory?
- Is any cache treated as truth: can the system distinguish "cached and
  possibly stale" from "authoritative," and can it rebuild from source?
- Does hidden mutable global state exist — module-level singletons, class
  variables, ambient environment reads — that changes behavior outside any
  declared interface?
- Do control loops read state, decide, and write back through a defined
  interface, or do they mutate shared structures mid-decision?
- When two stores disagree (config file vs database vs cache), which one
  wins, and is that precedence written down?

## Good-State Examples

- Every critical entity has exactly one writing component; all other
  access is read-only through its interface, and a table in the docs maps
  state → owner → store.
- Persistent state lives in one versioned store; transient and derived
  state is documented as rebuildable — and a `rebuild` command works.
- Configuration is read once at startup into a typed, immutable structure;
  runtime changes flow through the state store, never rewritten config.
- Secrets come from a secret manager, config from versioned files, state
  from the database — a backup of any one leaks nothing from the others.
- Kill-and-restart is a tested scenario: the service reloads authoritative
  state and re-derives caches; a test asserts identical behavior after.

## Red Flags

- One component stores state, decides policy, and performs side effects —
  memory, control, and execution fused in a single place.
- Restart changes the meaning of the system: permissions, routing, or
  ownership differ before and after.
- Config becomes an implicit runtime database — the process rewrites its
  own config files to store state.
- A cache becomes truth: the source is gone, unreachable, or never
  consulted again, and nobody can rebuild.
- Secrets, config, and state are mixed in one file, store, or environment
  blob.
- No clear owner for critical state: multiple writers, last write wins,
  no arbitration.

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

Typical for this lens: two write sites for the same record in different
components (two file references); the code path that rewrites a config
file at runtime (file + lines); a missing crash-restart test for a
stateful service; a config/schema mismatch where the same value lives in
both config and database; a runtime log differing across a restart.

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

Claim: The scheduler persists rotation state by rewriting its own YAML
config file at runtime, turning configuration into an implicit database
with two uncoordinated writers: the operator and the process.

Evidence: `scheduler/rotation.py:141-176` — `yaml.safe_dump` writes
`state.last_rotated` and `state.active_slot` back into
`conf/scheduler.yaml`; the same file is generated from
`deploy/ansible/templates/scheduler.yaml.j2`, so every deploy overwrites
runtime state (configuration/schema mismatch).

Risk: Deploys silently reset rotation state; operator edits race process
writes; config diffs no longer describe intent. A redeploy changes the
meaning of the running system.

Recommended fix: Move `last_rotated` and `active_slot` into the state
store with the scheduler as sole writer; make config read-only at runtime;
add a check asserting config files are never process-written.

### S2 Example

Claim: The permissions cache is the de facto source of truth: three
components write to it, and the authoritative table is never re-read after
startup.

Evidence: `authz/cache.ts:52-90` accepts writes from `authz/cache.ts`,
`admin/handlers.ts:203-219`, and `sync/worker.ts:77-92` (three writers);
`authz/cache.ts:64` reads the `permissions` table only inside `warmup()`;
no test evicts the cache and asserts reconstruction from the table
(missing test).

Risk: Grants applied directly to the cache vanish on restart while stale
revocations can resurrect; with no owning writer, actual permission state
is whichever component wrote last — a security-relevant ambiguity.

Recommended fix: Make the table the single source of truth with one
writing component; demote the cache to a read-through layer with TTL; add
an eviction-and-rebuild conformance test.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the von Neumann Lens (id: von-neumann) from the
invAIriant audit protocol: state, memory, control, and execution.

Examine the provided code/diff/docs for:
- ownership of critical state: a single writing owner per entity, or
  multiple uncoordinated writers;
- the persistent/transient split: what survives restart, what is rebuilt,
  and whether crash-restart preserves system meaning;
- separation of code, configuration, data, and secrets — including config
  rewritten at runtime as an implicit database;
- caches vs sources of truth: staleness handling and rebuild paths;
- hidden mutable global state, and control loops mutating shared
  structures outside declared interfaces.

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
   von Neumann Lens: N / 10
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
