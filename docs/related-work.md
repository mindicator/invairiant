# Related Work

invAIriant deliberately overlaps with several established practice families.
This page places it among them — what each family does well, and what
invAIriant does with its output. The honest summary:

```text
Static tools find code patterns.
Architecture methods structure human review.
AI reviewers comment on PRs.
invAIriant binds evidence, lenses, severity, and AI-assisted review
into one protocol.
```

## Architecture evaluation methods — ATAM, SAAM, ARID

Scenario-driven architecture evaluations run as structured workshops:
quality-attribute scenarios, tradeoff identification, risk themes. They are
thorough and heavyweight — days of senior time, episodic by design.

**Relation:** invAIriant borrows the multi-perspective evaluation idea but
optimizes for *continuous* use (PR/tactical cadence), for AI participation
(prompt pack, schemas), and for a hard evidence rule that workshop formats
leave implicit. An ATAM-style workshop's outputs slot directly into a
full-scale audit as inputs and evidence.

## Static analysis — Semgrep, SonarQube, CodeQL, linters

Fast, repeatable, pattern-precise, blind to intent: they find what can be
expressed as a code pattern or dataflow query, and they say nothing about
whether the architecture story holds or a component now knows too much.

**Relation:** evidence adapters ([evidence-rules.md §7](evidence-rules.md)).
Tool hits enter audits as candidate evidence (`command_output`, `ci_output`),
pass the same verification as any claim, and never become findings on the
tool's authority alone. Conversely, a recurring audit finding is a hint that
a rule should be written — the cheapest fix for a lens is often a new
Semgrep rule or CI gate that makes the whole class impossible.

## Policy-as-code and conformance — OPA, ArchUnit-style rules, custom CI gates

Executable rules over code structure, configs, or requests: dependency
direction, layer imports, naming, infrastructure policy. Deterministic and
cheap forever after being written — but only for properties someone managed
to formalize.

**Relation:** the target state for many findings. invAIriant's
recommendation field should prefer "add a conformance test/gate that makes
this recurrence impossible" over "be more careful." Named finding categories
([severity-model.md §6](severity-model.md)) are a natural backlog of gates
worth writing.

## AI code-review assistants

Useful and noisy: they propose plausible concerns at zero marginal cost,
with no evidence discipline, no severity model, and no memory of what was
already rejected. Teams either over-trust or learn to ignore them.

**Relation:** this is the failure mode invAIriant is built around. AI
reviewers plug in as stage-1 lens auditors or as evidence adapters; the
verification stage exists precisely so their volume becomes signal instead
of noise. "No evidence, no finding" is the contract that makes an AI
reviewer admissible.

## Threat modeling — STRIDE, attack trees, misuse cases

The structured enumeration of attackers, assets, and attack paths. Produces
the threat model — which invAIriant treats as a canonical doc.

**Relation:** upstream input, not competition. The `security-threat` lens
audits the *gap between the threat model and the code* ("every attack row
has a working response"); it cannot function without a threat model to
audit against. THREAT_MODEL_DRIFT exists as a named category because this
gap is the most common security failure in fast-moving codebases.

## Formal methods — TLA+, Alloy, model checking, property-based testing

The strongest guarantees available for the properties you can afford to
specify. Nothing in invAIriant approaches a proof.

**Relation:** invAIriant's `cormen`/`hoare`/`harel`/`lamport` lenses ask
"where are the invariants, contracts, and state machines, and are they
checked?" — and their best recommendations are often "make this property a
property test" or "model this protocol before scaling it." Formal artifacts
(specs, model-checker output, property-test suites) are first-class
evidence.

## What invAIriant adds

1. **A hard evidence rule** binding humans, tools, and AI to the same bar.
2. **Lenses** — reusable, structured senior judgment with rubrics and
   prompts, instead of "get the architect to look at it."
3. **A severity model with anti-averaging rules** — critical findings cannot
   be laundered by good scores.
4. **A pipeline for AI participation** — propose → verify → classify →
   synthesize, with rejected hypotheses kept visible.
5. **Schemas** so findings, reports, lenses, and configs are machine-checkable
   and tool-buildable.

## What invAIriant does not add

No proofs, no certifications, no substitute for tests, static analysis,
threat modeling, security audits, or human judgment. If a claim matters
enough to prove, use a prover; if it can be a lint rule, write the lint
rule. invAIriant is the protocol that decides *what deserves that
investment* and keeps the reasoning auditable in the meantime.
