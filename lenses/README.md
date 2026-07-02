# Lens Library

Each file in this tree is one **lens**: a named school of questioning with a
fixed structure — Purpose, Scope, Core Questions, Good-State Examples, Red
Flags, Required Evidence, Scoring Rubric (identical 0–10 table in every
lens), Finding Examples, and a Prompt Block ready to hand to an AI auditor.

Full taxonomy, selection guide, and custom-lens rules:
[../docs/lens-taxonomy.md](../docs/lens-taxonomy.md).

## Packs

| Pack | For | Lenses |
|---|---|---|
| [`core/`](core/) | most non-trivial codebases | cormen, parnas, brooks, dijkstra, mcconnell, turing |
| [`systems/`](systems/) | infra, runtime, distributed, stateful systems | tanenbaum, von-neumann, lamport, harel, kleppmann |
| [`implementation/`](implementation/) | code-level engineering quality | ritchie, kernighan, ousterhout, liskov |
| [`correctness/`](correctness/) | correctness-sensitive systems | hoare, + cross-listed cormen / turing / harel |
| [`security-safety/`](security-safety/) | security, privacy, safety, autonomy | saltzer-schroeder, leveson, security-threat, privacy-knowledge-minimization, operational-resilience |
| [`ai-generated-code/`](ai-generated-code/) | AI-era codebases (first-class pack) | oracle-boundary, prompt-code-drift, generated-surface-area, review-bottleneck |
| [`domain/`](domain/) | opt-in, domain-specific | network-persistence, distributed-systems, product-operability |

## Rules of use

- **4–6 lenses per audit by default.** Mandatory lenses come from
  `invairiant.config.yml`; a sensible generic default is `security-threat`,
  `parnas`, `mcconnell`, `turing`.
- **Packs are opt-in**; domain packs must never be forced onto projects
  outside their domain.
- **One lens, one pass.** Score and findings per lens, using its Prompt
  Block; do not run "all lenses at once" — cross-lens averaging is the
  failure mode this library exists to prevent.
- **Cross-listed lenses have one canonical file**; stubs (see
  [`correctness/cormen.md`](correctness/cormen.md)) add emphasis, never
  content.
- **Findings obey the evidence rules** regardless of lens:
  [../docs/evidence-rules.md](../docs/evidence-rules.md).
- Scores map to severities by fixed rules, and a high average never cancels
  an S0/S1: [../docs/severity-model.md](../docs/severity-model.md).
