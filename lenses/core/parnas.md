# Parnas Lens — Information Hiding and Modularity

**Pack:** core · **ID:** `parnas`

## Purpose

This lens protects against the slow leak of design decisions across module
boundaries: modules that read each other's internals, interfaces that expose
what they should hide, components that cannot be replaced without rewriting
their neighbors, and auxiliary services (registries, config stores, caches)
that quietly accumulate knowledge until they become runtime oracles the whole
system secretly depends on.

Information hiding is knowledge minimization between modules: each component
should know only what its contract entitles it to know.

## Scope

**Use when:**

- the system has more than one module, layer, or service;
- there are adapters, plugins, drivers, or replaceable backends;
- a central registry, coordinator, config service, or shared cache exists;
- a review touches any contract between components.

**Skip when:**

- the codebase is a single-owner, single-module script or prototype where
  boundaries would be ceremony — note that explicitly instead of scoring.

## Core Questions

- Does one module read another's internal fields, tables, files, or private
  structures, bypassing the declared interface?
- For each interface: which design decision does it *hide*? If you cannot
  name one, the interface is probably a pass-through leak.
- Can each major implementation (storage engine, transport, provider,
  framework, model vendor) be replaced without rewriting adjacent modules?
  What would that diff actually touch?
- Has an auxiliary component (registry, config endpoint, descriptor store,
  cache) accumulated knowledge beyond its contract — becoming a runtime
  oracle that knows too much about the system or its users?
- Does the public surface expose internal topology, naming, or structure
  that consumers do not need?
- Are "temporary" direct links between modules recorded anywhere, with a
  trigger to remove them?
- Do integrity-sensitive steps (fetch, validate, sign, promote) live in one
  swappable place, or are they scattered across callers?

## Good-State Examples

- Transport/provider-specific details are hidden behind a capability
  interface; the routing layer consumes declared capabilities, not vendor
  structs.
- Replacing the storage engine touches one adapter package and its
  conformance tests — nothing else.
- The config service distributes signed artifacts but holds no runtime
  knowledge of which client uses which route; it cannot answer questions it
  has no contract to answer.
- A module's on-disk formats are private; every consumer goes through the
  API, so the format can change without a migration megaproject.
- Telemetry is emit-only by contract; nothing can query a component for
  aggregated cross-system state it was never meant to serve.

## Red Flags

- One layer reaches into private structures of a specific implementation
  (e.g., a routing module importing a vendor client's internals).
- A component holds a complete map of the system when it only needs its
  own neighborhood.
- Swapping one engine/provider/backend for another requires changes across
  all layers.
- A registry or config endpoint becomes a source of truth about runtime
  relationships it has no contract to hold.
- Integrity-checked fetch/validate logic is scattered out of its single
  swappable step, so each caller re-implements (or skips) the checks.
- An emit-only reporting contract silently grows a queryable endpoint that
  aggregates state across components.
- An interface whose parameters mirror the current implementation's
  internals one-to-one.

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

Typical for this lens: the import or field access that crosses a boundary
(file + lines); the pair of files that must change together for one logical
change (two file references); a doc/code contradiction where ARCHITECTURE
declares a boundary the code bypasses; a schema that exposes internal
identifiers to external consumers.

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

Claim: The routing layer reads transport internals directly, bypassing the
declared data-plane contract.

Evidence: `internal/router/router.go:120-148` — direct access to
`transport.conn.tlsState` and `transport.privateEndpoints`;
`docs/ARCHITECTURE.md:88` declares that routing consumes only the
`TransportCapability` interface (doc/code contradiction).

Risk: Transport replacement now requires routing changes; hidden coupling
means a transport refactor can silently break path selection, and the
declared architecture no longer describes the real system.

Recommended fix: Introduce a transport capability interface owned by the
data-plane boundary; move the two fields routing genuinely needs into the
declared contract; add an arch-conformance test that fails on direct imports.

### S2 Example

Claim: The config registry stores per-client connection history it has no
contract to hold.

Evidence: `registry/store.go:203-241` — writes `client_id → last_endpoints[]`
on every fetch; `docs/ARCHITECTURE.md:132` describes the registry as a
"stateless artifact distributor" (doc/code contradiction).

Risk: An auxiliary component is becoming a runtime oracle: it now knows
system topology and client behavior, which widens blast radius on compromise
and makes the registry unreplaceable.

Recommended fix: Drop the history table or move it behind an explicitly
contracted, minimized telemetry path; update ARCHITECTURE either way; add a
test asserting the registry's storage schema matches its declared contract.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Parnas Lens (id: parnas) from the invAIriant audit
protocol: information hiding and modularity.

Examine the provided code/diff/docs for:
- modules reading other modules' internal fields/tables/files, bypassing
  declared interfaces;
- interfaces that leak the implementation decision they exist to hide;
- replaceability: what a realistic engine/provider/backend swap would touch;
- auxiliary components (registries, config stores, caches) accumulating
  knowledge beyond their contract — registry/oracle drift;
- public surfaces exposing internal topology or identifiers unnecessarily.

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
   Parnas Lens: N / 10
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
