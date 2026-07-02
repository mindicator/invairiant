<div align="center">

<a href="./thumbnail.jpg"><img src="./thumbnail.jpg" alt="invAIriant — evidence-based architecture audits for AI-era codebases" width="100%"></a>

<br/>

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](LICENSE)
[![Status: v0.1 alpha](https://img.shields.io/badge/status-v0.1%20alpha-orange?style=flat-square)](#status)
[![Lenses: 28](https://img.shields.io/badge/lenses-28-8A2BE2?style=flat-square)](docs/lens-taxonomy.md)
[![Packs: 7](https://img.shields.io/badge/packs-7-informational?style=flat-square)](lenses/)
[![Claude Code skill](https://img.shields.io/badge/Claude%20Code-skill-5A67D8?style=flat-square)](skill/SKILL.md)
[![Codex compatible](https://img.shields.io/badge/Codex-compatible-black?style=flat-square)](prompts/)
[![Evidence first](https://img.shields.io/badge/evidence-first-brightgreen?style=flat-square)](docs/evidence-rules.md)
[![No evidence, no finding](https://img.shields.io/badge/no%20evidence-no%20finding-critical?style=flat-square)](docs/evidence-rules.md)

**Evidence-based, multi-lens architecture audits for systems that must not drift.**

`AI-assisted analysis` · `human council` · `evidence first` · `complex systems, under control`

<sub>a protocol by <b>mindicator &amp; silicon bags quartet</b></sub>

</div>

---

## No evidence. No finding.

invAIriant turns senior-engineer judgment into a **reusable audit protocol**:
named lenses, evidence rules, a severity model, JSON schemas, report
templates, and AI-ready prompts — for complex software systems, especially
systems built with AI assistance, where architectural invariants have to
survive rapid change.

The council in the banner is not decoration. Each seat is a **lens** — a named
school of questioning (Parnas → information hiding; Turing → termination and
oracle boundaries; Lamport → time and ordering; Leveson → unsafe control). AI
assistants can convene that whole council against your diff in minutes. The
one rule that keeps it honest:

> **AI may propose hypotheses. Only evidence-backed, verified claims become
> findings.** A high average score never cancels a critical finding, and a
> rejected hypothesis is kept in the report — never silently dropped, never
> silently promoted.

## Quick start

Pick the mode that fits — the protocol works with zero tooling; the skill
automates it; the schemas are the contract for future product tooling.

**As a protocol (no tooling):**

```bash
# 1. Copy the closest starter config to your repo root
cp examples/infra-service/invairiant.config.yml ./invairiant.config.yml
#    (also: examples/minimal-webapp, examples/ai-agent-system)

# 2. Run your next PR audit from the checklist + <=2 focused lenses
#    -> templates/pr-comment.md

# 3. Run your first full-scale audit
#    -> docs/audit-workflow.md  (uses each lens file's Prompt Block)
#    -> templates/audit-report.md  (the output)
```

**As an agent skill (Claude Code / compatible):**

```bash
# Install as a project skill, then let the agent drive the whole pipeline
mkdir -p .claude/skills && ln -s "$PWD/skill" .claude/skills/invairiant
#   in the agent:  /invairiant   ->  config discovery, lens selection,
#   lens passes, evidence verification, severity, and a written report
```

See a full worked example: [`examples/infra-service/example-audit.md`](examples/infra-service/example-audit.md).

## How it works — the four-stage pipeline

Every audit, from a PR to a full-scale review, runs the same pipeline with
**hard boundaries between stages** so AI volume becomes signal instead of
noise. Each stage maps to a prompt in [`prompts/`](prompts/).

```text
   inputs: diff / repo @ commit, canonical docs, config, tool outputs
                              │
  [1] LENS PASS               │  one selected lens per pass
      lens auditor            ▼  → score (0–10) + candidate findings + hypotheses
                              │
  [2] EVIDENCE VERIFICATION   │  adversarial: try to REFUTE each candidate
      evidence verifier       ▼  → verified │ rejected │ demoted   (nothing dropped)
                              │
  [3] SEVERITY CLASSIFICATION │  rules, not averages
      severity classifier     ▼  → S0 / S1 / S2 / S3 / NOTE
                              │
  [4] SYNTHESIS               │  rejected hypotheses stay visible
      report synthesizer      ▼  → audit report + verdict (pass / conditions / fail)
```

- Stage 1 may not assign final severity. Stage 2 may not invent findings.
  Stage 3 touches only verified findings. Stage 4 may not drop a rejected
  hypothesis.
- Skills, scanners, and test suites plug in as **evidence adapters** — their
  output enters as *candidate evidence*, never as findings on their own
  authority ([docs/evidence-rules.md §7](docs/evidence-rules.md)).

## The lens council

A **lens** is a named school of questioning with a fixed structure: purpose,
scope, core questions, good-state examples, red flags, required evidence, a
0–10 rubric, finding examples, and a ready-to-paste AI prompt block. Lenses
are grouped into **opt-in packs** so audits select by risk surface, not by
famous name — **default audits use 4–6 lenses, not 20.**

| Pack | For | Lenses |
|---|---|---|
| [**core**](lenses/core/) | most non-trivial codebases | Cormen · Parnas · Brooks · Dijkstra · McConnell · Turing |
| [**systems**](lenses/systems/) | infra, runtime, distributed, stateful | Tanenbaum · von Neumann · Lamport · Harel · Kleppmann |
| [**implementation**](lenses/implementation/) | code-level engineering quality | Ritchie · Kernighan · Ousterhout · Liskov |
| [**correctness**](lenses/correctness/) | correctness-sensitive systems | Hoare (+ cross-listed Cormen · Turing · Harel) |
| [**security-safety**](lenses/security-safety/) | security, privacy, safety, autonomy | Saltzer–Schroeder · Leveson · Security/Threat · Privacy · Operational-Resilience |
| [**ai-generated-code**](lenses/ai-generated-code/) | AI-era codebases (first-class) | Oracle-Boundary · Prompt–Code-Drift · Generated-Surface-Area · Review-Bottleneck |
| [**domain**](lenses/domain/) | opt-in, domain-specific | Network-Persistence · Distributed-Systems · Product-Operability |

> **Lens names are mnemonic devices, not appeals to authority.** A finding is
> right because of its evidence, never because of the name on the lens. Full
> taxonomy and per-project selection guide: [docs/lens-taxonomy.md](docs/lens-taxonomy.md).

## Three ways to use it

invAIriant is deliberately a **framework, an agent skill, and a product
contract** at once — the same protocol at three levels of automation.

| Mode | What it is | Status |
|---|---|---|
| **1 · Protocol** | Docs + lenses + templates + schemas. Humans and/or AI run the pipeline by hand. | ✅ usable now |
| **2 · Agent skill** | [`/invairiant`](skill/SKILL.md) orchestrates config discovery → lens passes → verification → severity → report. Existing skills/tools attach as evidence adapters. | ✅ usable now |
| **3 · Product** | `invairiant validate` / `report` / a CI gate that fails on open S0/S1, built on the JSON [schemas](schemas/). | 🚧 roadmap |

**Does it pull in other skills?** Yes — by design it *orchestrates* rather
than *reinvents*. Security scanners, code-review skills, dependency auditors,
and test runners are **evidence adapters**: invAIriant runs them, ingests
their output as candidate evidence, and subjects it to the same verification
as any human claim. It is the connective protocol that binds evidence,
lenses, severity, and AI-assisted review into one auditable trail — not a
replacement for the tools it consumes.

## Evidence rules, in one screen

Valid evidence — `file path + line range` · `diff hunk` · `test failure` ·
`missing test` · `doc/code contradiction` · `CI output` · `runtime log` ·
`incident` · `reproducible command output` · `schema/config mismatch`.

Not evidence — "looks risky" · "probably overcomplicated" · "AI may have
generated this" · "feels wrong" · a lens name without the concrete leak · a
tool warning by itself.

Everything unsupported is recorded as an **observation**, **hypothesis**, or
**open question** — never as a finding. Full rules:
[docs/evidence-rules.md](docs/evidence-rules.md).

## Severity model, in one screen

| | Meaning | Gate |
|---|---|---|
| **S0** | Critical | blocks merge / release / phase transition |
| **S1** | High | fix before the next major step |
| **S2** | Medium | next work cycle |
| **S3** | Low | planned improvement |
| **NOTE** | Note | no mandatory action |

Scores map to severity by fixed rules (mandatory lens < 6.0 → ≥ S2; critical
lens < 5.0 with concrete user risk → S0), and **a high average never launders
a critical finding.** Full model: [docs/severity-model.md](docs/severity-model.md).

## Repository layout

```text
README.md                this file
docs/                    methodology · evidence-rules · severity-model ·
                         audit-workflow · lens-taxonomy · related-work
lenses/                  the lens library (7 packs, 28 lenses)
templates/               audit-report · finding · pr-comment ·
                         phase-transition-audit · event-triggered-audit
schemas/                 finding · audit-report · lens · config  (JSON Schema)
prompts/                 lens-auditor · evidence-verifier ·
                         severity-classifier · report-synthesizer
skill/                   the /invairiant agent-skill packaging
examples/                minimal-webapp · infra-service · ai-agent-system
.github/workflows/       framework self-validation
```

## Anti-overengineering rules (canon)

1. Default audits use **4–6 lenses, not 20**.
2. Additional packs are **opt-in**.
3. A small PR does not trigger a full philosophical tribunal.
4. Lens selection must match the **risk surface**.
5. Lens names are **mnemonic devices**, not appeals to authority.
6. A **boring concrete finding** beats a brilliant abstract concern.
7. The framework must **reduce** review ambiguity, not add ritual.

## What invAIriant is not

Not a security certification · not a replacement for human review · not a
proof of correctness · not a replacement for tests, static analysis,
SAST/DAST, threat modeling, or formal methods (it turns their output into
evidence — [docs/related-work.md](docs/related-work.md)) · not a generator of
findings without evidence · not architecture cosplay.

## Contributing

Single maintainer: **[@mindicator](https://github.com/mindicator)**. Docs
authorship is credited as *mindicator & silicon bags quartet*. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## Origins

invAIriant was extracted from the audit and refactoring canon of
**the origin project**, a persistent-mesh private network where user safety is
functional requirement #1 and every architecturally significant change is
audited. The general-engineering lenses, the 0–10 scale, the
score-to-severity mapping, the anti-averaging rules, and the audit types are
generalizations of that canon; the origin project's domain judgment survives in the
optional [network-persistence](lenses/domain/network-persistence.md) lens.
**Nothing in the core framework requires knowing the origin project.**

## Status

**v0.1 alpha.** The protocol layer — docs, 28 lenses, templates, schemas,
prompts, skill, examples — is usable as-is. CLI/CI product tooling is
roadmap. Treat the [schemas](schemas/) as the stable contract.

## License

[Apache-2.0](LICENSE). Copyright © 2026 **mindicator & silicon bags
quartet**.
