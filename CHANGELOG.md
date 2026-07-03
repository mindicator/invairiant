# Changelog

All notable changes to invAIriant are documented here. The format loosely
follows Keep a Changelog; versions track the protocol.

## [Unreleased]

### Added

- **Cross-agent adapters** — the skill now runs beyond Claude Code. A portable
  root [`AGENTS.md`](AGENTS.md) (Codex and any AGENTS.md-aware agent) and
  [`.cursor/rules/invairiant.mdc`](.cursor/rules/invairiant.mdc) (Cursor) reach
  the same protocol, both pointing to the canonical `skill/SKILL.md` instead of
  duplicating it. Per-agent install in `skill/README.md`; README badges link
  each.

## [0.1.0] — 2026-07-03

First public release. Extracted and generalized from the the origin project audit and
refactoring canon into a reusable, evidence-first, multi-lens audit protocol
for AI-era codebases. One rule underneath all of it: **no evidence, no
finding.**

### Protocol & lenses

- **Docs** (`docs/`): methodology, evidence rules, severity model, audit
  workflow, lens taxonomy, related work, CLI spec.
- **Lens library** (`lenses/`): 28 lenses across 7 packs — core, systems,
  implementation, correctness, security-safety, ai-generated-code, domain —
  each with purpose, scope, core questions, good-state examples, red flags,
  required evidence, a 0–10 rubric, finding examples, and an AI prompt block.
  New lenses include Turing, von Neumann, Ritchie, Kernighan, Hoare, Lamport,
  Liskov, Saltzer–Schroeder, and Leveson.
- **Schemas** (`schemas/`): finding, audit-report, lens, config, and
  evidence-bundle (JSON Schema draft 2020-12) — the stable contract for tooling.
- **Templates** (`templates/`): audit-report, finding, pr-comment,
  phase-transition-audit, event-triggered-audit.
- **Prompt pack** (`prompts/`): lens-auditor, evidence-verifier,
  severity-classifier, report-synthesizer — the four pipeline stages.

### Skill — the primary product

- **`/invairiant`** (`skill/`): an LLM coding agent runs the audit. Commands:
  `audit-pr`, `full-audit`, `verify-findings`, `classify-severity`,
  `synthesize-report`, `closure-verification`; a `--lenses a,b` override; and a
  concrete `audit-pr` runbook (collect → lens passes → verify → classify → PR
  comment). Other skills and tools attach as **evidence adapters**.

### CLI — the narrow helper (serves the audit, never performs one)

- **`invairiant`** (`cli/invairiant.py`, `pyproject.toml`, spec in
  `docs/cli.md`): `init`, `collect`, `validate-config`, `validate-report`,
  `render-report`, `render-comment`, `ci-gate`, `record`, `history`
  (+ `collect-evidence` alias). Installs as the `invairiant` command; no
  lenses, findings, or scores.
- **`collect`** builds a deterministic evidence bundle (diff scope, tree,
  language stats, grep signals, import hints, generated mass, known-rejected) —
  candidate pointers only.
- **`validate-report`** runs schema validation **plus a semantic pass**:
  verdict↔severity consistency (open S0 → fail; open S1 → not pass), S0/S1
  confidence, referential integrity, and a kept-`hypotheses` check.
  `--schema-only` / `--md`.
- **`render-comment`** turns a report into a paste-ready PR comment;
  **`ci-gate`** exits non-zero on open S0/S1.
- **Audit memory** (`record` / `history`): committed, **sanitized**
  `.invairiant/history/` (rejected hypotheses, finding registry, lens-score
  trends) — never raw evidence; secrets redacted; idempotent by audit label.
  Raw bundles and transcripts stay gitignored under `.invairiant/cache/`.

### Examples, case studies & dogfood

- **Examples** (`examples/`): minimal-webapp, infra-service, ai-agent-system
  configs + a worked infra-service report.
- **Case studies** (`case-studies/`): `persistent-mesh-transport` (**real** diff +
  finding) and three illustrative — each with the diff, selected lenses,
  candidate/rejected/verified findings, a schema-valid report, and a
  side-by-side of **what a normal AI reviewer missed**.
- **Two self-audits** of the framework recorded to audit memory, so
  `invairiant history` shows a real per-lens trend.

### Quality gates

- **CI** (`.github/workflows/validate.yml`): validates schemas, examples, and
  lens structure, and smoke-tests every CLI command (including a negative test
  that the semantic linter fails an inconsistent report).
- **Local authorship gate** (`commit-msg` hook): rejects AI co-author trailers
  — commits are authored by the maintainer alone.

### Principles enforced

- No evidence, no finding.
- A high average score never cancels an S0/S1 finding.
- Observations and hypotheses stay separate from verified findings.
- Default audits use 4–6 lenses, not 20.

[Unreleased]: https://github.com/mindicator/invairiant/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mindicator/invairiant/releases/tag/v0.1.0
