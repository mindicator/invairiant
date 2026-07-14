# The `invairiant` CLI — infrastructure, not an auditor

> **The CLI does not audit architecture.** It has no lenses, produces no
> findings, and assigns no scores. All architectural judgment lives in the
> [`/invairiant` skill](../skill/SKILL.md) and the [prompt pack](../prompts/).
> The CLI is the seatbelt around that judgment.

## Why this boundary

The market for CLI code auditors and linters is saturated — Semgrep, CodeQL,
SonarQube, dependency scanners, a hundred linters. invAIriant does not compete
there. Its wedge is a **protocol for AI-assisted architectural judgment**: the
audit is run by an LLM coding agent under an evidence discipline, and the CLI
exists only to make that loop safe and reproducible.

So the CLI's job is narrow and deterministic:

- **scaffold** a project's config,
- **validate** configs and reports against the schemas,
- **collect** raw evidence from other tools (as candidate evidence),
- **render** a report JSON to Markdown,
- **enforce** the gate in CI.

If a proposed CLI feature would require *judgment* — deciding whether a finding
is real, scoring a lens, choosing severity — it belongs in the skill, not here.

## Install / run

Install from a checkout to get the `invairiant` command (Python 3.9+;
`jsonschema` + `pyyaml` come with it):

```bash
pip install -e .        # or: pipx install -e .
invairiant <command> [...]
```

No install needed either — run the single module directly:

```bash
python3 cli/invairiant.py <command> [...]
```

It locates the framework tree via `$INVAIRIANT_HOME`, then the repo layout,
then by searching upward from the script and the current directory — so the
installed command works from inside a checkout. For a non-editable install
outside a checkout, set `INVAIRIANT_HOME`.

## Commands

### `invairiant init [--type TYPE] [--path P] [--force]`
Scaffold `./invairiant.config.yml` from a project-type template (copies the
matching `examples/<type>/` config, or writes a minimal one) and ensure
`docs/audits/`. Types: `minimal-webapp`, `infra-service`, `ai-agent-system`
(extend freely).

### `invairiant validate-config [paths...]`
Validate config(s) against
[`schemas/invairiant.config.schema.json`](../schemas/invairiant.config.schema.json).
Default path `invairiant.config.yml`. Exit 0 = valid, 1 = problems.

### `invairiant validate-report <paths...> [--schema-only] [--md]`
Validate audit report JSON against
[`schemas/audit-report.schema.json`](../schemas/audit-report.schema.json)
(findings resolve against the finding schema) **plus a semantic pass** for the
protocol rules a schema cannot express:

- verdict derives from open findings, never from score averages (open S0 →
  `fail`; open S1 → not `pass`);
- S0/S1 findings carry high/medium confidence;
- `lens_scores` referential integrity: `evidence_refs` that look like finding
  ids must exist; a lens scoring below the config's `low_score_threshold` with
  no finding and no `evidence_refs` is flagged (warning);
- `required_actions` reference real finding ids;
- the report keeps a `hypotheses` section (rejected hypotheses are not
  deleted);
- a finding marked `status: verified` carries a `verification` record
  (`verified_by` + `method`) — **warning** for now, so provenance is visible
  before it becomes required.

`--schema-only` runs just the schema check. `--md` structurally lints a
**rendered markdown** report (H1, sections, verdict, kept hypotheses present) —
JSON stays the source of truth. Exit 0 = valid, 1 = problems.

### `invairiant collect [--scope KIND] [--range A..B] [--commit SHA] [--pr N] [--path P] [--narrow P] [--out F] [--run-adapters] [--cap N]`
Gather a deterministic **evidence bundle** for the skill — the CLI's core
helper. One JSON object
([`schemas/evidence-bundle.schema.json`](../schemas/evidence-bundle.schema.json),
`invairiant.evidence-bundle/v1`) with: change `scope` (diff or snapshot),
`repo_tree`, `language_stats`, `tests_ci` (git status; adapters if
`--run-adapters`), `config` + `canonical_docs` excerpts, `signals` (grep
pointers for model calls / shell / SQL / secrets / TODO), `import_boundaries`,
`generated_mass`, and `known_rejected` (from committed audit memory). Uses `rg`
when present, else a **bounded** single-pass fallback over `git ls-files` that
skips large (>512 KB) and binary files and caps the file count — the bundle's
`limits` block reports the bounds and whether the scan truncated (no silent
caps).

**`--scope` pins the audit target.** Every field above is computed over the
resolved scope's file set *only* — this is what keeps `collect` a scoped
evidence-gatherer, not a whole-repo scanner:

| `--scope` | Needs | Resolves to |
|---|---|---|
| `working` (default) | — | uncommitted working-tree changes |
| `pr` | `--pr N` | a pull request **by number** → its `base...head` range. The one **optional resolver adapter**: reaches the remote via `gh`, else the `pull/<n>/head` ref; records `base`/`head`/`resolver` in `resolved_scope` |
| `range` | `--range A..B` | files changed in the range (diff) |
| `commit` | `--commit SHA` | files touched by one commit (diff) |
| `module` | `--path DIR\|FILE` | a snapshot of that subtree (no diff) |
| `adr` | `--path ADR.md` | the ADR text + the tracked paths/symbols it references; `--narrow P` restricts to a subpath |
| `rp` | `--path RP.md` | a refactoring proposal + the tracked code it references (snapshot); `--narrow P` restricts to a subpath |
| `repo` | — | the whole repo, **explicitly unbounded** (full-audit) |

**Local by default; `pr` is the one adapter.** Every scope but `pr` is pure-local
git — no network, no external tools. `--scope pr` is the sole exception: it may
call `gh` or fetch the `pull/<n>/head` ref to pin the PR, then collapses to an
ordinary `base...head` range like any other change scope. Its `resolved_scope`
records `base`, `head`, and `resolver` (`gh` or `git`). Note: content-level
signals (grep pointers) are read from the working tree, so for a PR that isn't
checked out they'll be sparse — the diff, file set, and mass are still correct
from git; check out the PR (or run in CI, where it's the checkout) for full
signal fidelity.

`collect` **fails closed** (exit 2, `scope could not be bounded`) when a scope
cannot be pinned — a missing `--range`, an unknown path or sha, an ADR /
refactoring proposal whose references don't resolve or resolve too broadly (past
a bound relative to repo size, unless `--narrow` tightens them), or a PR that
can't be reached (no remote, offline, or a non-GitHub remote — it suggests
`--range` instead). It never silently widens to the whole repo; `repo`
is the one deliberately unbounded scope. `--range A..B` with no `--scope` is a
shorthand for `--scope range`. Every bundle carries a **`resolved_scope`** block
(`kind`, `target`, `bounded`, `files_in_scope`, `sample_files`, `has_diff`) so
the boundary is explicit and auditable.

Every bundle also carries a **`provenance`** block — `commit_sha`, `scope_hash`,
and a `bundle_hash` (sha256 over the bundle minus itself). This binds the bundle
to the commit and scope it was built from, so a downstream report/Action can
prove it was built from *this* bundle and that the bundle wasn't edited. It is
integrity, not judgment — the CLI still never decides whether a finding is real.

**Everything in the bundle is a candidate pointer, not a finding** — it is
input for the `/invairiant` skill, which applies lenses; only verified,
evidence-bound claims become findings. Write the raw bundle under
`.invairiant/cache/` (gitignored) — it contains code excerpts and candidate
secret matches and must not be committed.

### `invairiant collect-evidence [--config P] [--out F] [--timeout S]`
Alias for the adapter-only subset of `collect`: runs the declared
`evidence_adapters` (recognized: `pytest`, `go-test`, `golangci-lint`,
`eslint`, `ruff`, `semgrep`, `vitest`) and emits their raw output as
candidate-evidence items. Prefer `collect` for the full bundle.

### `invairiant render-report <report.json> [--out F]`
Deterministically render a report JSON to Markdown in the shape of
[`templates/audit-report.md`](../templates/audit-report.md): header, executive
summary + verdict, lens-score table, findings by severity, and the kept
Unsupported Hypotheses. Formatting only — no content is added or judged.

### `invairiant render-comment <report.json> [--out F]`
Render a report JSON into a paste-ready **PR comment**
([`templates/pr-comment.md`](../templates/pr-comment.md) shape): verdict,
audited range, lenses, verified findings (severity-sorted, each with a
one-line evidence locator, risk, and fix), blocking conditions, and
observations/rejected-hypotheses. This is the deliverable of
`/invairiant audit-pr`. Deterministic formatting only — no posting, no
judgment.

### `invairiant ci-gate <report.json> [--max-severity S0|S1]`
The seatbelt. Exit non-zero when the report has open blocking findings — by
default any `S0` or `S1` whose `status` is not `rejected`; `--max-severity S0`
blocks only `S0`. Prints the blocking findings. Wire it into CI after the agent
files a report:

```yaml
- run: python3 cli/invairiant.py ci-gate docs/audits/latest.json
```

### `invairiant record <report.json> [--audit-id ID] [--dir D]`
Append a report's **distilled, sanitized** memory to `.invairiant/history/`
(committed, default dir):

- `rejected-hypotheses.jsonl` — `{date, audit, lens, text, rejected_reason, claim_key}`
- `finding-registry.jsonl` — `{date, audit, id, severity, lens, category, claim, status, claim_key}`
- `lens-score-history.csv` — `date,audit,lens,score`

Only these distilled fields are stored — **never raw evidence blobs**, code, or
diffs — and secret-like substrings (PEM keys, AWS/GitHub/Slack tokens,
`Authorization`/`Bearer`, `key=value`) are redacted. `date`/`audit` come from
the report (deterministic). The history dir defaults to
**`<repo-root>/.invairiant/history`** (resolved via git, so `record` / `history`
work from any subdirectory); override with `--dir`. Raw evidence bundles from
`collect` stay under `.invairiant/cache/` (gitignored); only `record` writes to
`history/`.

### `invairiant history [--lens X] [--dir D]`
Read audit memory and print lens-score trends (oldest → newest, flagging two
consecutive drops) and findings recurring across audits. `collect` also feeds
`known_rejected` back into the bundle so the skill does not re-propose a
hypothesis a past audit already refuted.

## Explicit non-goals

The CLI will never:

- run a lens or apply the prompt pack;
- decide whether a finding is real, or invent one;
- assign a score or a severity;
- replace the agent, human review, or any scanner.

Those are the audit. The CLI only serves it. See
[methodology.md](methodology.md) and [related-work.md](related-work.md) for the
positioning.

## Status

Reference implementation, installable as the `invairiant` command
([`pyproject.toml`](../pyproject.toml)). `init`, `validate-config`,
`validate-report`, and `ci-gate` are complete; `collect-evidence` and
`render-report` are functional and intentionally minimal. The schemas are the
stable contract underneath.
