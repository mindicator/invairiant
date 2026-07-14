# Changelog

All notable changes to invAIriant are documented here. The format loosely
follows Keep a Changelog; versions track the protocol.

## [Unreleased]

### Added

- **Evidence provenance — first step** (from external review, [#2](https://github.com/mindicator/invairiant/issues/2)).
  `collect` now emits a `provenance` block: `commit_sha`, `scope_hash`, and a
  `bundle_hash` that recomputes over the bundle (minus itself) — so a later step
  can prove a report was built from **this** bundle at **this** commit, and that
  the bundle wasn't edited after the fact. `validate-report` now **warns** when a
  finding is `status: verified` without a `verification` record (`verified_by` +
  `method`). Both are structure/integrity checks — the CLI still never judges
  truth. Additive: existing bundles and reports stay valid (the warning is a
  nudge, slated to become an error in a later release).

### Changed

- **Typed scope models.** The scope resolvers now return a frozen
  `ResolvedScope` dataclass with a `ScopeKind` enum instead of a loose `dict`,
  so a field-name typo (`scope.head_cheked_out`) fails loudly at attribute
  access instead of silently reading `None`, and the set of scope kinds is
  explicit. `ScopeKind` is `str`-valued, so the emitted evidence bundle is
  byte-for-byte identical (verified across every scope kind, old CLI vs new,
  over a fixed repo).
- **The CLI is now a package**, `invairiant/`, split from the single
  ~1500-line `cli/invairiant.py` into focused modules
  (`cli` / `scopes` / `schemas` / `evidence` / `render` / `history` /
  `subprocesses` / `term`) with a cycle-free import graph. Behaviour is
  unchanged — the split was verified byte-for-byte equivalent across every
  command. `cli/invairiant.py` stays as a thin shim, so `python3
  cli/invairiant.py …` (the Action, CI, the demo, the docs) works exactly as
  before; `python -m invairiant` and the installed `invairiant` command work
  too. Installed wheels bundle the framework data *inside* the package
  (`invairiant/invairiant_framework/`), so `pip install` still resolves schemas
  with no `INVAIRIANT_HOME` outside a checkout.
- **`ci-gate` now validates the report before it gates it** — `parse → schema
  validate → semantic validate → gate`. It no longer assumes `validate-report`
  ran first: a report that fails to parse, breaks the schema, or breaks a
  semantic rule exits **3** (`refusing to gate an invalid report`) instead of
  being gated on a broken shape. Valid reports gate exactly as before (open
  `S0`/`S1` → exit 1). New optional `--config` lets the gate's semantic pass read
  the same `low_score_threshold` as `validate-report`.
- **Internal: narrowed every `except Exception`** in the CLI to the specific
  errors each site can raise (`ImportError`, `OSError`,
  `subprocess.SubprocessError`, `json.JSONDecodeError`, `yaml.YAMLError`, …), so
  an unexpected bug surfaces instead of being silently swallowed. No behavior
  change for well-formed inputs.

## [0.2.5] — 2026-07-04

### Added

- **Colored, TTY-aware CLI output.** `validate-config` / `validate-report`,
  `collect`, and `ci-gate` now use semantic color on a real terminal — green for
  `✓`/`OK`/pass, red for `✗`/`FAILED`/fail and S0, amber for `⚠` and S1, dim for
  asides. Color is emitted **only** when stdout is a terminal, honoring
  `NO_COLOR` and `TERM=dumb`; piped and CI output stay byte-for-byte plain, so
  exit codes, rendered markdown, and anything parsed downstream are unaffected.

## [0.2.4] — 2026-07-04

### Added

- **On PyPI.** [`pip install invairiant`](https://pypi.org/project/invairiant/)
  is live. Uploads run over **GitHub Trusted Publishing** (OIDC, no stored token)
  via [`.github/workflows/publish.yml`](.github/workflows/publish.yml), so cutting
  a release auto-publishes that version. A step-by-step guide (manual `twine` and
  the automated path) is in [`docs/publishing.md`](docs/publishing.md).

### Changed

- **README and `cli/README.md` lead with `pip install invairiant`** (checkout
  `-e .` kept as the dev note); the CLI readme — the package's PyPI
  long_description — now uses absolute GitHub links so they resolve on pypi.org.
- **`action.yml` description trimmed to <125 chars** so the Action is eligible
  for the GitHub Marketplace (name/icon/color already passed).

## [0.2.3] — 2026-07-04

### Changed

- **README quickstart split into two independent tracks** — *enable the skill*
  (the product) and *install the CLI helper* (optional infrastructure) — leading
  with the skill and framing `pip install` as the seatbelt the skill shells out
  to, not "installing invAIriant". The two install independently.
- **`pip install` is now production-grade.** The wheel and sdist bundle the
  framework data the CLI reads at runtime (schemas, examples, lens ids) under
  `invairiant_framework/`, and `framework_root()` falls back to it — so a plain
  `pip install invairiant` works **outside a checkout**, no `INVAIRIANT_HOME`
  needed. Before, a non-editable install shipped only the module and any real
  command died with `schema not found`. The build backend moved to hatchling
  (`force-include` maps the repo-root dirs into the distribution without moving
  or duplicating them — the checkout stays the single source of truth). A CI
  **packaging smoke** installs the wheel in a clean venv and runs a command from
  outside the checkout, so this can't silently regress.

### Added

- **GitHub Action understands the bounded scopes.** The Action's optional
  `collect` step gains `scope` / `pr` / `commit` / `path` / `narrow` inputs
  (`range` kept), so CI can gather a bundle for a PR, module, ADR, or
  refactoring proposal — not just a range. Inputs pass via env; the step builds
  only the flags that are set, so it stays a bounded gather.

### Fixed

- **PR scope warns when the head isn't checked out.** `collect --scope pr` now
  records `head_checked_out` in `resolved_scope` and prints a NOTICE (pointing
  at `gh pr checkout <N>`, or auditing in CI where the PR head is the checkout)
  when the PR head is not the working tree — because content-level grep signals
  are then sparse. The diff, file set, and mass stay correct from git regardless.

## [0.2.2] — 2026-07-04

### Added

- **`--scope pr` — first-class PR resolver (the main entrypoint, now backed).**
  `invairiant collect --scope pr --pr <N>` pins a pull request **by number** and
  resolves it to an ordinary bounded `base...head` range — so `audit-pr <N>` is
  finally real, not just a promise in the command signature. It is an **optional
  resolver adapter**: every other scope is pure-local git, and **only** `--scope
  pr` may reach the remote — via `gh` if present, else the `pull/<n>/head` ref.
  If the PR can't be reached (no remote, offline, non-GitHub remote) it **fails
  closed and suggests `--range`**, never widening to the repo. `resolved_scope`
  records `base`, `head`, and `resolver` (`gh`/`git`). Content-level signals read
  the working tree, so check out the PR (or run in CI) for full fidelity; the
  diff, file set, and mass are correct from git regardless. Documented across the
  skill, `docs/methodology.md` §4.1, `docs/cli.md`, the schema, and the adapters;
  6 hermetic tests (fail-closed cases + pull-ref resolution against a bare remote
  carrying `refs/pull/1/head`, no gh/network). 82 tests total.

## [0.2.1] — 2026-07-04

### Added

- **`audit-rp` — refactoring-proposal scope.** A sixth bounded scope kind
  (`collect --scope rp --path <proposal.md>`) and skill command `audit-rp`. An
  RP is the mirror image of an ADR: an ADR is a *made* decision (audit for
  drift — does the code still match?), an RP is a *proposed* change (audit for
  risk — would applying it break an invariant the code holds now?). It resolves
  the proposal to the tracked code it references, snapshots that code, and
  reuses the same fail-closed bounding as `adr` (no refs / too broad → exit 2,
  `--narrow` to tighten). Documented across the skill, `docs/methodology.md`
  §4.1 (seven scope kinds; adr = decision drift, rp = invariant risk),
  `docs/cli.md`, the schema enum, and the cross-agent adapters. **No new
  lenses**; the CLI still performs no judgment.

### Changed

- **README positioning.** Lead with the one-line promise — *invAIriant keeps
  architectural invariants from drifting under AI-assisted change* — with the
  slogan **No evidence. No finding.** as the brand stamp; the
  "mindicator & silicon bags quartet" credit moves off the very top (it still
  stands in Contributing and the License). The product row lists the bounded
  targets, and "What it is not" states the discipline outright: **invAIriant
  audits bounded engineering scopes, not vibes** — a scope it cannot bound is
  refused, not widened.

## [0.2.0] — 2026-07-04

### Added

- **Scope resolvers — the audit target beyond PRs.** `invairiant collect` now
  takes `--scope {working,range,commit,module,adr,repo}` and resolves the pin to
  a **bounded file set**; the entire evidence bundle (tree, language stats, grep
  signals, generated mass) is computed over that set only — scoped gathering, not
  a whole-repo scan. It **fails closed** (exit 2) when a scope can't be bounded —
  a missing `--range`, an unknown `--path`/`--commit`, or an ADR whose references
  don't resolve or resolve too broadly (unless `--narrow` tightens them) — and
  never silently widens; `repo` is the one opt-in unbounded scope. Every bundle
  now carries a **`resolved_scope`** block (documented in the evidence-bundle
  schema) making the boundary explicit and auditable.
- **`adr` scope** — `collect --scope adr --path <ADR.md>` pins an
  **ADR ↔ code** audit: the ADR text joins the canonical docs and its referenced
  paths/symbols resolve to the tracked files in scope, so decision-vs-code drift
  is first-class evidence.
- **Skill commands `audit-range`, `audit-commit`, `audit-module`, `audit-adr`**
  ([`skill/SKILL.md`](skill/SKILL.md)) — thin scope-selectors over the **same**
  four-stage pipeline, plus the unifying **audit target** concept
  (`pinned scope + evidence bundle + selected lenses + report type`) in the skill
  and [`docs/methodology.md`](docs/methodology.md) §4.1. **No new lenses** — a
  wider set of things to point the audit at, not new judgment. Cross-agent
  adapters (`AGENTS.md`, Cursor rule) updated to match.
- **14 scope tests** (`tests/test_scope.py`): per-kind resolution, fail-closed
  exit-2 cases, the `resolved_scope` shape, ADR reference/identifier resolution
  with `--narrow`, and an end-to-end proof that a module scan stays inside its
  subtree. 69 tests total.

### Non-goal reaffirmed

- invAIriant audits **bounded engineering scopes** — PRs, ranges, commits,
  modules, ADR↔code drift, the repo by explicit choice. It does **not** perform
  general repository search or brainstorming; an unbounded scope is refused, not
  widened ([`docs/methodology.md`](docs/methodology.md) §7).

## [0.1.2] — 2026-07-04

### Added

- **Two real (redacted) case studies** (`case-studies/`): `low-latency-runtime`
  — a **full-scale** audit scoring the whole core lens block + Lamport, where a
  ~7 average and a *pass* verdict still surface a real correctness finding
  (anti-averaging on real code); and `social-autopost` — a focused PR audit of
  raw model output auto-published with no content gate. Both from private
  codebases with names and specifics withheld. The case set now spans the
  depth × source × status range (see `case-studies/README.md`).
- **GitHub Action** ([`action.yml`](action.yml)) — a composite action that
  validates an audit report (schema + semantic), renders it into the job
  summary, and **gates CI on open S0/S1** findings. Use it as
  `uses: mindicator/invairiant@v0.1.2`. Docs:
  [`docs/github-action.md`](docs/github-action.md).
- **Unit-test suite** (`tests/`, 55 tests) for the CLI — parser dispatch,
  `validate-report` semantic-linter rules, secret redaction, `record`
  idempotency + sanitization, claim-key matching, `history` trends, repo-root
  memory resolution, and the bounded `collect` scan. CI runs `pytest`. (Closes
  self-audit finding CLOSE-003.)
- **Roadmap for v0.2** ([`ROADMAP.md`](ROADMAP.md)) — hardening and reach, **no
  new lenses**.
- A **60-second Quickstart** at the top of the README and a demo PR-comment
  visual ([`assets/pr-comment.svg`](assets/pr-comment.svg)).

### Changed

- **Origin narrative** reframed (README / NOTICE): invAIriant was forged in
  AI-assisted development of complex, high-load systems — that is its story.
- **`pyproject.toml` version bumped to 0.1.2** for this release.

### Fixed

- **Memory & `collect` hardening on large repos** (from self-audit #2):
  - `record` / `history` / the memory-aware linter now resolve
    `.invairiant/history/` from the **repo root**, not the current directory,
    so running the CLI from a subdirectory no longer silently misses committed
    audit memory (**CLOSE-001**).
  - `collect` bounds its scan — skips large (>512 KB) and binary files, caps the
    file count, does a single O(files) pass, and reports `limits` in the bundle
    (no silent truncation) (**CLOSE-002**).
  - `record` secret redaction hardened: full PEM blocks (not just the header),
    AWS/GitHub/Slack tokens, and `Authorization` / `Bearer` values.

## [0.1.1] — 2026-07-03

### Added

- **Cross-agent adapters** — the skill now runs beyond Claude Code. A portable
  root [`AGENTS.md`](AGENTS.md) (Codex and any AGENTS.md-aware agent) and
  [`.cursor/rules/invairiant.mdc`](.cursor/rules/invairiant.mdc) (Cursor) reach
  the same protocol, both pointing to the canonical `skill/SKILL.md` instead of
  duplicating it. Per-agent install in `skill/README.md`; README badges link
  each.

## [0.1.0] — 2026-07-03

First public release. A reusable, evidence-first, multi-lens architecture-audit
protocol for AI-era codebases, distilled from real-world auditing of AI-assisted
development on complex, high-load systems. One rule underneath all of it: **no
evidence, no finding.**

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
- **Case studies** (`case-studies/`): four illustrative worked audits
  (`persistent-mesh-transport`, `ai-agent-refund-bot`,
  `generated-typescript-api`, `p2p-network-transport-change`) — each with the
  diff, selected lenses, candidate/rejected/verified findings, a schema-valid
  report, and a
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

[Unreleased]: https://github.com/mindicator/invairiant/compare/v0.2.5...HEAD
[0.2.5]: https://github.com/mindicator/invairiant/releases/tag/v0.2.5
[0.2.4]: https://github.com/mindicator/invairiant/releases/tag/v0.2.4
[0.2.3]: https://github.com/mindicator/invairiant/releases/tag/v0.2.3
[0.2.2]: https://github.com/mindicator/invairiant/releases/tag/v0.2.2
[0.2.1]: https://github.com/mindicator/invairiant/releases/tag/v0.2.1
[0.2.0]: https://github.com/mindicator/invairiant/releases/tag/v0.2.0
[0.1.2]: https://github.com/mindicator/invairiant/releases/tag/v0.1.2
[0.1.1]: https://github.com/mindicator/invairiant/releases/tag/v0.1.1
[0.1.0]: https://github.com/mindicator/invairiant/releases/tag/v0.1.0
