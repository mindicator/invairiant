# Lens Taxonomy

A **lens** is a named school of questioning: purpose, scope, core questions,
good-state examples, red flags, required evidence, a scoring rubric, finding
examples, and a ready-to-use AI prompt block. Every lens file follows the
same strict structure (see any file under [`lenses/`](../lenses/)).

Lenses are organized into **packs** — classes of concern — so that audits
select by risk surface, not by famous name. Nothing outside the project's
mandatory set is required; packs are opt-in.

## Naming policy

Lens names are **mnemonic devices**, not appeals to authority. "Cormen"
compresses "algorithmic rigor and invariants" into one word that reviewers
remember; it claims no endorsement and settles no argument. A finding is
right because of its evidence, never because of the name on the lens. If a
name distracts your team, rename the lens locally — the id and the questions
are what matter.

## Packs

### 1. Core Pack (`lenses/core/`) — most non-trivial codebases

| Lens | ID | Examines |
|---|---|---|
| [Cormen](../lenses/core/cormen.md) | `cormen` | invariants, state transitions, idempotency, explicit failure behavior, property tests |
| [Parnas](../lenses/core/parnas.md) | `parnas` | information hiding, knowledge minimization between modules, replaceability, registry/oracle drift |
| [Brooks](../lenses/core/brooks.md) | `brooks` | conceptual integrity, entity proliferation, accidental complexity |
| [Dijkstra](../lenses/core/dijkstra.md) | `dijkstra` | simplicity, implicit control flow, negative space (what the system must NOT do) |
| [McConnell](../lenses/core/mcconnell.md) | `mcconnell` | construction quality, staged migration, rollback, doc synchrony, blast radius |
| [Turing](../lenses/core/turing.md) | `turing` | termination, bounded search, oracle/LLM boundaries, replayability, safe fallback |

### 2. Systems Pack (`lenses/systems/`) — infrastructure, runtime, distributed, stateful

| Lens | ID | Examines |
|---|---|---|
| [Tanenbaum](../lenses/systems/tanenbaum.md) | `tanenbaum` | runtime/substrate boundary, process lifecycle, supervision, fault taxonomy |
| [von Neumann](../lenses/systems/von-neumann.md) | `von-neumann` | state ownership, cache vs truth, code/config/data/secrets separation, restart recovery |
| [Lamport](../lenses/systems/lamport.md) | `lamport` | ordering, retries, races, partitions, clock assumptions, idempotent writes |
| [Harel](../lenses/systems/harel.md) | `harel` | explicit states, transition guards, timeout/recovery transitions, state explosion |
| [Kleppmann](../lenses/systems/kleppmann.md) | `kleppmann` | schema evolution, event logs, materialized views, migration/backfill safety |

### 3. Implementation Pack (`lenses/implementation/`) — code-level engineering quality

| Lens | ID | Examines |
|---|---|---|
| [Ritchie](../lenses/implementation/ritchie.md) | `ritchie` | small composable primitives, sharp interfaces, portable formats, diagnostic surfaces |
| [Kernighan](../lenses/implementation/kernighan.md) | `kernighan` | readability, debuggability, error messages, operator comprehension under pressure |
| [Ousterhout](../lenses/implementation/ousterhout.md) | `ousterhout` | deep vs shallow modules, information leakage, complexity localization |
| [Liskov](../lenses/implementation/liskov.md) | `liskov` | contracts, substitutability, adapter consistency, conformance suites |

### 4. Correctness Pack (`lenses/correctness/`) — correctness-sensitive systems

| Lens | ID | Examines |
|---|---|---|
| [Hoare](../lenses/correctness/hoare.md) | `hoare` | preconditions, postconditions, failure postconditions, invalid states unrepresentable |
| [Cormen (cross-listed)](../lenses/correctness/cormen.md) | `cormen` | canonical: core pack |
| [Turing (cross-listed)](../lenses/correctness/turing.md) | `turing` | canonical: core pack |
| [Harel (cross-listed)](../lenses/correctness/harel.md) | `harel` | canonical: systems pack |

### 5. Security/Safety Pack (`lenses/security-safety/`) — security, privacy, user safety, autonomy

| Lens | ID | Examines |
|---|---|---|
| [Saltzer–Schroeder](../lenses/security-safety/saltzer-schroeder.md) | `saltzer-schroeder` | least privilege, fail-safe defaults, complete mediation, separation of privilege |
| [Leveson](../lenses/security-safety/leveson.md) | `leveson` | unsafe control actions, controller model drift, automation authority, human override |
| [Security/Threat](../lenses/security-safety/security-threat.md) | `security-threat` | threat-model coverage in code, attack surface, secrets, authn/authz, secure defaults |
| [Privacy](../lenses/security-safety/privacy-knowledge-minimization.md) | `privacy-knowledge-minimization` | what each component knows, PII minimization, correlation, retention |
| [Operational Resilience](../lenses/security-safety/operational-resilience.md) | `operational-resilience` | degradation-not-failure, rollback, restart safety, SLOs, anti-flapping |

### 6. AI-Generated Code Pack (`lenses/ai-generated-code/`) — first-class, for AI-era codebases

| Lens | ID | Examines |
|---|---|---|
| [Oracle Boundary](../lenses/ai-generated-code/oracle-boundary.md) | `oracle-boundary` | what the model may decide, validation of model output, uncertainty behavior, replayability |
| [Prompt–Code Drift](../lenses/ai-generated-code/prompt-code-drift.md) | `prompt-code-drift` | CLAUDE.md/AGENTS.md/prompts vs actual code, stale AI instructions, "never" violations |
| [Generated Surface Area](../lenses/ai-generated-code/generated-surface-area.md) | `generated-surface-area` | diff mass, blast radius, test ratio, near-duplicate patterns, reviewability |
| [Review Bottleneck](../lenses/ai-generated-code/review-bottleneck.md) | `review-bottleneck` | generation rate vs review capacity, deterministic gates, provenance, review debt |

`turing` (core) is the general computability/oracle lens; this pack applies
the same discipline specifically to AI-assisted development.

### 7. Domain Packs (`lenses/domain/`) — opt-in, domain-specific

| Lens | ID | For |
|---|---|---|
| [Network Persistence](../lenses/domain/network-persistence.md) | `network-persistence` | persistent-mesh / P2P / overlay / anonymity networks: reachability, indistinguishability, enumeration, sybil resistance, AS diversity |
| [Distributed Systems](../lenses/domain/distributed-systems.md) | `distributed-systems` | multi-node systems: membership, partitions, coordinator failure, convergence |
| [Product Operability](../lenses/domain/product-operability.md) | `product-operability` | SaaS/product teams: deployability, user-facing errors, migrations, runbooks, supportability |

Domain packs carry the deepest project-specific judgment. **Never force a
domain pack onto a project outside its domain** — network-persistence on a
CRUD webapp is cosplay.

## Selection guide

Pick mandatory lenses by project type; add packs by the change under audit.

| Project type | Suggested mandatory set (4–6) | Packs to keep available |
|---|---|---|
| minimal webapp | `mcconnell`, `parnas`, `security-threat`, `kernighan` | implementation |
| SaaS product | `mcconnell`, `parnas`, `security-threat`, `product-operability` | implementation, ai-generated-code |
| infra service | `security-threat`, `parnas`, `mcconnell`, `turing` | systems, ai-generated-code |
| data platform | `kleppmann`, `security-threat`, `privacy-knowledge-minimization`, `mcconnell` | systems, correctness |
| AI agent system | `turing`, `oracle-boundary`, `security-threat`, `leveson`, `mcconnell` | ai-generated-code, correctness |
| distributed / P2P system | `security-threat`, `lamport`, `parnas`, `operational-resilience` (+ domain pack) | systems, domain |
| safety-critical / autonomous | `leveson`, `hoare`, `security-threat`, `harel`, `mcconnell` | correctness, systems |

Per-change additions: new agent loop → `turing`/`oracle-boundary`; new
endpoint → `security-threat`, `saltzer-schroeder`; migration →
`kleppmann`, `mcconnell`; new state store → `von-neumann`; big generated
diff → `generated-surface-area`, `review-bottleneck`.

## Cross-listing rules

A lens lives in exactly **one canonical file**. Other packs reference it via
a short stub (see [`lenses/correctness/cormen.md`](../lenses/correctness/cormen.md))
that adds pack-specific emphasis but never forks content. If you find
yourself editing a stub's rubric, you are in the wrong file.

## Precedence

When lenses disagree, [severity-model.md](severity-model.md) rule 8 applies:
the lens closest to the project's declared risk assets wins. Domain and
security/safety lenses therefore dominate general-engineering lenses on the
systems they exist for — the project's value is its core property, not code
beauty.

## Writing a custom lens

1. Copy the structure of an existing lens file — every section, same order
   (Purpose, Scope, Core Questions, Good-State Examples, Red Flags, Required
   Evidence, Scoring Rubric, Finding Examples, Prompt Block).
2. Keep the scoring rubric table **verbatim** — comparability across lenses
   is the point.
3. Write core questions that are checkable ("does X exist / happen / get
   tested"), not aesthetic ("is X elegant").
4. Give it a kebab-case id, a pack, and (optionally) a machine-readable
   descriptor validating against
   [`schemas/lens.schema.json`](../schemas/lens.schema.json).
5. If it encodes recurring defects, add named categories to your project
   config rather than inventing severities inline.
6. A custom pack needs a README stating what class of system it serves and
   when **not** to use it.
