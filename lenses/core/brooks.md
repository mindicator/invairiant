# Brooks Lens — Conceptual Integrity and Accidental Complexity

**Pack:** core · **ID:** `brooks`

## Purpose

This lens protects against a system dissolving into a collection of locally
sensible but globally incompatible decisions: entities multiplying without
nameable responsibility, "temporary" shapes quietly becoming undeclared
canon, names that decorate instead of inform, and convenience choices that
bend the global architecture one PR at a time.

Conceptual integrity means one coherent story: a small set of stable layers
and concepts that survive while the implementations beneath them change.

## Scope

**Use when:**

- the system has grown past a few modules and new components, services, or
  layers keep appearing;
- a review introduces a new entity (service, manager, queue, coordinator)
  or repurposes an existing one;
- the architecture docs claim a small set of stable layers or concepts;
- "temporary" scaffolding exists: migration bridges, phase-specific
  components, compatibility shims.

**Skip when:**

- the review is confined to one module's internals and adds no entities —
  Parnas and McConnell cover that ground;
- the artifact is an explicitly labeled disposable spike that will not be
  merged — note that explicitly instead of scoring.

## Core Questions

- Is there one architecture story — a few stable layers or concepts — and
  does this change fit the story or quietly fork it?
- Can the system still be explained through a few stable formulas, or does
  each subsystem now carry its own list of exceptions?
- Are "managers", "controllers", and "orchestrators" multiplying, and can
  a distinct responsibility be named for each one?
- For each entity added in the diff: does the architecture need it, or was
  it added for the convenience of a single phase or PR?
- Do component names encode role and failure mode, or are they decorative?
- Which components are declared temporary, and does each carry a written
  trigger-to-remove? Has any quietly become permanently required?
- Do local decisions preserve the global shape, or does each locally
  reasonable choice bend a layer boundary a little further?
- Where the docs record an intentional divergence, is the rationale
  visible enough that a later cleanup will not "reconcile" it away?

## Good-State Examples

- The architecture names a handful of stable layers; two backend swaps
  later the layer list is unchanged, and new code slots under an existing
  layer instead of beside the stack.
- A migration bridge carries an explicit trigger-to-remove ("delete when
  all clients are on v2, tracked in issue #412") — and gets deleted.
- A proposed new "sync manager" is rejected in review; the responsibility
  already belongs to an existing component, per the cited decision record.
- Component names state role and failure mode — `artifact-verifier`
  (rejects on bad signature) rather than `helper-service-2`.
- An intentional divergence between two deployment defaults carries its
  rationale, so a later PR trying to "unify" them is caught in review.

## Red Flags

- "Another service because it's easier" — an entity added to dodge the
  question of where the responsibility belongs.
- A temporary component silently becomes permanently required: nothing
  runs without it, yet no decision ever declared it canon.
- A component name is decorative and does not encode the component's role
  or failure mode.
- `temporary` without a trigger-to-remove.
- An intentional, documented divergence gets "reconciled" away by someone
  who did not read why it exists.
- Several components each own a sliver of one responsibility that nobody
  can state in a sentence.
- The architecture story stays true only via a growing exception list.
- Two differently named components doing the same job because merging them
  was never anyone's PR.

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

Typical for this lens: the diff hunk introducing an entity whose
responsibility duplicates an existing component (two file references); a
doc/code contradiction where the architecture doc lists the layers and the
code has grown a component outside all of them; a "temporary" marker in a
comment or doc with no trigger-to-remove; a production config that requires
a component the docs describe as optional scaffolding.

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

Claim: A component introduced as temporary migration scaffolding has become
permanently required: production depends on it, no decision declares it
canon, and it carries no trigger-to-remove.

Evidence: `services/legacy-bridge/src/index.ts:1-14` — header comment reads
"temporary bridge for the v1→v2 migration, remove after cutover";
`deploy/prod/compose.yaml:34-52` lists `legacy-bridge` as a hard dependency
of two core services eleven months after cutover completed (doc/code
contradiction); no decision record under `docs/decisions/` mentions it.

Risk: The real architecture contains an undeclared extra layer; every
change must route around a component with no owner, no contract, and no
stated failure mode, and removing it later becomes a megaproject.

Recommended fix: Either promote the bridge to a declared permanent
component — decision record, named responsibility, stated failure mode —
or write the removal trigger and schedule the deletion; update the
architecture doc to match whichever reality is chosen.

### S2 Example

Claim: Upload handling is split across three "manager" components whose
responsibilities overlap and cannot be stated independently, contradicting
the documented single-pipeline design.

Evidence: `internal/upload/manager.go:22-64`,
`internal/upload/state_manager.go:15-49`, and
`internal/upload/flow_manager.go:30-71` all mutate the same retry counters
and status map; `docs/architecture.md:57` describes upload as "a single
pipeline component" (doc/code contradiction).

Risk: Every upload change spans three files with no clear owner; bugs land
in the seams between the managers; the documented architecture no longer
predicts where behavior lives.

Recommended fix: Collapse the three managers into one component with a
stated contract, or split along a seam where each side's responsibility
can be named; record the decision and update the architecture doc.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Brooks Lens (id: brooks) from the invAIriant audit
protocol: conceptual integrity and accidental complexity.

Examine the provided code/diff/docs for:
- whether the change fits the declared architecture story or quietly
  forks it;
- new entities (services, managers, controllers): a nameable
  responsibility for each, or convenience for a single phase or PR;
- temporary components: an explicit trigger-to-remove, or silent
  promotion to undeclared canon;
- component names that encode role and failure mode versus decoration;
- local decisions that bend a layer boundary or add a story exception;
- documented intentional divergences at risk of being "reconciled" away.

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
   Brooks Lens: N / 10
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
