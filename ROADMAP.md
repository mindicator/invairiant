# Roadmap

invAIriant is at **v0.1.1**. The core protocol — evidence rules, severity
model, lenses, schemas, prompts, the skill, and the CLI — is stable. **v0.2 is
hardening and reach, not new surface.**

## Guardrail: no new lenses in v0.2

The 28 lenses across 7 packs are the stable vocabulary. v0.2 adds **zero** new
core lenses. New domain judgment, when a project needs it, goes through a
custom project lens ([docs/lens-taxonomy.md](docs/lens-taxonomy.md)) — not the
core packs.

## v0.2 — hardening & reach

**Packaging & distribution**
- Publish the `invairiant` CLI to PyPI (`pip install invairiant`).
- A reusable GitHub Action wrapping `collect → validate-report → ci-gate`.

**CLI robustness** (from self-audit #2)
- Resolve `.invairiant/history/` from the repo root, not the CWD (CLOSE-001).
- Bound the `collect` grep fallback on very large repos (CLOSE-002).
- Harden `record` secret redaction (more patterns, all tested).

**Evidence base**
- More worked case studies across project types (SaaS, data platform, infra),
  ideally from real, opted-in diffs.
- A screenshot / GIF of the `audit-pr → PR comment` flow.

**Memory & trends**
- `history --json` for tooling; a compact lens-score-trend view.
- Surface recurring findings as suggested lint rules / CI gates.

## Not planned

- New lenses in the core packs.
- The CLI ever running a lens, producing a finding, or scoring — it stays a
  judgment-free seatbelt.
- Replacing human review, tests, SAST/DAST, threat modeling, or formal methods.

## Shipped in v0.1

- The protocol: evidence rules, severity model, 28 lenses / 7 packs, schemas,
  templates, prompt pack.
- The `/invairiant` skill — Claude Code · Codex · Cursor.
- The CLI: `init`, `collect`, `validate-config`, `validate-report`,
  `render-report`, `render-comment`, `ci-gate`, `record`, `history`.
- Committed, sanitized audit memory; two self-audits with a per-lens trend.
- Unit tests for the CLI *(Unreleased → v0.1.x)*.
