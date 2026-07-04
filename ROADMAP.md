# Roadmap

invAIriant is at **v0.2.0**. The core protocol — evidence rules, severity
model, lenses, schemas, prompts, the skill, and the CLI — is stable. **v0.2 was
hardening and reach — bounded audit scopes over the same pipeline, not new
surface.**

## Guardrail: no new core lenses

The 28 lenses across 7 packs are the stable vocabulary. v0.2 shipped with
**zero** new core lenses, and that guardrail holds forward. New domain
judgment, when a project needs it, goes through a custom project lens
([docs/lens-taxonomy.md](docs/lens-taxonomy.md)) — not the core packs.

## v0.3 — hardening & reach (planned)

**Packaging & distribution**
- Publish the `invairiant` CLI to PyPI (`pip install invairiant`).
- Publish the GitHub Action to the Marketplace (the `action.yml` already works
  via `uses: mindicator/invairiant@<ref>`).

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

## Shipped in v0.2

- **Scope resolvers — the audit target beyond PRs.**
  `invairiant collect --scope {working,range,commit,module,adr,repo}` turns a
  scope pin into a **bounded file set**; the whole evidence bundle is computed
  over that set only. Fails closed when a scope can't be bounded (and the ADR
  scope refuses references that resolve too broadly — a relative bound, not just
  an absolute cap), and records the boundary in a `resolved_scope` block.
- **Skill commands** `audit-range`, `audit-commit`, `audit-module`, `audit-adr`
  — thin scope-selectors over the **same** four-stage pipeline — plus the
  unifying **audit target** concept (pinned scope + evidence bundle + selected
  lenses + report type) in the skill and methodology. **No new lenses.**

## Shipped in v0.1

- The protocol: evidence rules, severity model, 28 lenses / 7 packs, schemas,
  templates, prompt pack.
- The `/invairiant` skill — Claude Code · Codex · Cursor.
- The CLI: `init`, `collect`, `validate-config`, `validate-report`,
  `render-report`, `render-comment`, `ci-gate`, `record`, `history`.
- Committed, sanitized audit memory; two self-audits with a per-lens trend.
- Unit tests for the CLI (55) *(Unreleased → v0.1.x)*.
- CLI robustness — repo-root memory resolution, bounded `collect` on large
  repos, hardened secret redaction (CLOSE-001/002) *(Unreleased → v0.1.x)*.
- A reusable **GitHub Action** (`action.yml`) — validate + render summary +
  gate on S0/S1 *(Unreleased → v0.1.x)*.
