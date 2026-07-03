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
  `verify-findings`, `classify-severity`, `synthesize-report`, and
  `closure-verification` — end-to-end audits plus individual pipeline stages.
  Added a `--lenses a,b` override, a copy-paste "Try it" block, and a concrete
  `audit-pr` runbook (collect → lens passes → verify → classify → PR comment).
- **CLI** (`cli/invairiant.py`, spec in `docs/cli.md`): `init`,
  `validate-config`, `validate-report`, `collect-evidence`, `render-report`,
  `ci-gate` — deterministic infrastructure only (no lenses, findings, or
  scores). `ci-gate` exits non-zero on open S0/S1.
- **Machine-readable example report** (`examples/infra-service/example-report.json`)
  validating against the audit-report schema; CI now smoke-tests the CLI.
- **Packaging** (`pyproject.toml`): the CLI installs as the `invairiant`
  console command (`pip install -e .`), with robust framework-root discovery
  ($INVAIRIANT_HOME → repo layout → upward search).
- **Self-audit** (`docs/audits/2026-07-03-self-audit.{md,json}`): the first
  full-scale audit of the framework against itself — verdict pass.
- **`invairiant collect`** + `schemas/evidence-bundle.schema.json`: a
  deterministic evidence bundle (diff scope, repo tree, language stats, grep
  signals for model-calls/shell/SQL/secrets/TODO, import hints, generated
  mass, known-rejected) handed to the skill as input. Every item is a
  candidate pointer, never a finding. `collect-evidence` is kept as an alias.
- **Case studies** (`case-studies/`): one **real** (`persistent-mesh-transport`, built
  from an actual diff + finding) and three illustrative
  (`ai-agent-refund-bot`, `generated-typescript-api`,
  `p2p-network-transport-change`). Each carries the diff, selected lenses,
  candidate/rejected/verified findings, a schema-valid report, and a
  side-by-side of **what a normal AI reviewer missed**.
- **`invairiant render-comment`**: deterministically renders a report JSON into
  a paste-ready PR comment (`templates/pr-comment.md` shape) — verdict, lenses,
  severity-sorted findings with evidence, conditions, and kept hypotheses. The
  deliverable of `/invairiant audit-pr`. No posting, no judgment.
- **Audit memory** (`invairiant record` / `history`, committed
  `.invairiant/history/`): each audit's distilled, **sanitized** findings /
  rejected hypotheses / lens scores are appended (never raw evidence; secrets
  redacted). `collect` feeds `known_rejected` back so the skill won't
  re-propose refuted hypotheses; `validate-report` warns if a finding revives
  one; `history` shows lens-score trends and recurring findings. Raw bundles and
  transcripts stay gitignored under `.invairiant/cache/`.

### Changed

- **`invairiant validate-report`** now runs a **semantic pass** on top of schema
  validation: verdict↔severity consistency (open S0 → fail; open S1 → not
  pass), S0/S1 confidence, `lens_scores`/`required_actions` referential
  integrity, and a kept-`hypotheses` check. `--schema-only` skips it; `--md`
  structurally lints a rendered markdown report.

### Fixed

- Closed self-audit finding **INV-001**: config `mandatory_lenses` and
  `critical_lenses` are now cross-checked against the lens library in both
  `scripts/validate_framework.py` and `invairiant validate-config`, so a
  typo'd lens id fails at validate time instead of mid-audit.
- Closed self-audit finding **INV-002**: `examples/infra-service/example-report.json`
  now defines CNV-043 and CNV-044 (referenced in its verdicts/summary), making
  it a complete twin of the prose example.

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
