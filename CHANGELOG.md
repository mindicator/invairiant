# Changelog

All notable changes to invAIriant are documented here. The format loosely
follows Keep a Changelog; versions track the protocol, not any tooling.

## [Unreleased]

### Changed — positioning

- Reframed the project as an **audit discipline layer for AI-era software
  engineering**, not another CLI auditor. The **agent skill is the primary
  product**; schemas + templates + prompt pack are the secondary layer; the
  CLI is a narrow helper that serves the audit and never performs one.

### Added

- **Skill commands** (`skill/SKILL.md`): `audit-pr`, `full-audit`,
  `verify-findings`, `classify-severity`, `synthesize-report` — end-to-end
  audits plus individual pipeline stages.
- **CLI** (`cli/invairiant.py`, spec in `docs/cli.md`): `init`,
  `validate-config`, `validate-report`, `collect-evidence`, `render-report`,
  `ci-gate` — deterministic infrastructure only (no lenses, findings, or
  scores). `ci-gate` exits non-zero on open S0/S1.
- **Machine-readable example report** (`examples/infra-service/example-report.json`)
  validating against the audit-report schema; CI now smoke-tests the CLI.

## [0.1.0] — 2026-07-02

Initial public draft. Extracted and generalized from the the origin project audit and
refactoring canon into a reusable, evidence-first audit protocol.

### Added

- **Protocol docs** (`docs/`): methodology, evidence rules, severity model,
  audit workflow, lens taxonomy, related work.
- **Lens library** (`lenses/`): 28 lenses across 7 packs — core, systems,
  implementation, correctness, security-safety, ai-generated-code, domain —
  each with purpose, scope, core questions, good-state examples, red flags,
  required evidence, a 0–10 rubric, finding examples, and an AI prompt block.
  New lenses include Turing, von Neumann, Ritchie, Kernighan, Hoare, Lamport,
  Liskov, Saltzer–Schroeder, and Leveson.
- **Schemas** (`schemas/`): finding, audit-report, lens, and config
  (JSON Schema, draft 2020-12) — the stable contract for tooling.
- **Templates** (`templates/`): audit report, finding, PR comment,
  phase-transition audit, event-triggered audit.
- **Prompt pack** (`prompts/`): lens-auditor, evidence-verifier,
  severity-classifier, report-synthesizer — the four pipeline stages.
- **Agent skill** (`skill/`): `/invairiant` orchestrates the full pipeline;
  other skills/tools attach as evidence adapters.
- **Examples** (`examples/`): minimal-webapp, infra-service, ai-agent-system
  configs, plus a worked infra-service audit report and machine-readable
  findings.
- **CI** (`.github/workflows/`): a framework self-validation workflow
  (schemas, examples, and lens structure).

### Principles enforced

- No evidence, no finding.
- A high average score never cancels an S0/S1 finding.
- Observations and hypotheses stay separate from verified findings.
- Default audits use 4–6 lenses, not 20.

[0.1.0]: https://github.com/mindicator/invairiant/releases/tag/v0.1.0
