# `invairiant` CLI

Infrastructure around the agentic audit — **not an architecture auditor.** No
lenses, no findings, no scores. All judgment lives in the
[`/invairiant` skill](https://github.com/mindicator/invAIriant/blob/main/skill/SKILL.md); this CLI scaffolds, validates,
collects evidence, renders, and gates.

Full spec and rationale: [`docs/cli.md`](https://github.com/mindicator/invAIriant/blob/main/docs/cli.md).

## Install

```bash
pip install invairiant          # from a checkout for dev: pip install -e .
```

Gives the `invairiant` command; the framework it needs rides in the wheel, so no
checkout is required. (No install? Run `python3 cli/invairiant.py <command>`
directly.) Python 3.9+; `jsonschema` + `pyyaml` are pulled in as dependencies.

## Commands

| Command | Purpose |
|---|---|
| `init [--type T]` | scaffold `invairiant.config.yml` |
| `collect [--range A..B] [--out F]` | build a deterministic evidence bundle (candidate pointers only) |
| `validate-config [paths…]` | schema-check configs + cross-check lens ids |
| `validate-report <paths…> [--schema-only] [--md]` | schema **+ semantic** checks on a report |
| `render-report <report.json> [--out F]` | report JSON → Markdown |
| `render-comment <report.json> [--out F]` | report JSON → paste-ready PR comment |
| `ci-gate <report.json> [--max-severity S0\|S1]` | exit non-zero on open S0/S1 |
| `record <report.json> [--force]` | append distilled, **sanitized** memory to `.invairiant/history/` |
| `history [--lens L]` | lens-score trends + recurring findings |

`collect-evidence` is a thin alias for the adapter-only subset of `collect`.

Full spec: [`docs/cli.md`](https://github.com/mindicator/invAIriant/blob/main/docs/cli.md). Worked flow:
[`docs/demo.md`](https://github.com/mindicator/invAIriant/blob/main/docs/demo.md). Resolves the framework via
`$INVAIRIANT_HOME`, the repo layout, or by searching upward from the current
directory.
