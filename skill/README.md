# invAIriant as an agent skill — the primary product

[`SKILL.md`](SKILL.md) is the main way to use invAIriant: an LLM coding agent
runs the audit itself. The schemas, templates, and prompt pack are the layer it
stands on; the [CLI](../cli/README.md) is only infrastructure around it.

## Commands

`/invairiant <command>`:

| Command | Does |
|---|---|
| `audit-pr [<pr#\|range>]` | PR-scoped audit: checklist + ≤2 focused lenses → verdict |
| `full-audit [<range>]` | full-scale audit: all mandatory lenses → report |
| `verify-findings <candidates>` | adversarially verify candidate findings (stage 2) |
| `classify-severity <verified>` | map verified findings to severity (stage 3) |
| `synthesize-report <inputs>` | assemble the final report (stage 4) |

All under one rule: **no evidence, no finding.**

## Install

- **Project skill:**
  `mkdir -p .claude/skills && cp -r <framework>/skill .claude/skills/invairiant`
  (or symlink). Local `.claude/` is gitignored, so run this once per clone.
- **Personal skill:** `cp -r <framework>/skill ~/.claude/skills/invairiant`.
- **Framework elsewhere:** set `INVAIRIANT_HOME=/path/to/framework` so the skill
  finds the lens library; without it, a documented degraded mode runs four
  generic lenses.

## How it relates to other skills and tools

Other skills and tools are **evidence adapters**, not competitors: the skill
(often via `invairiant collect-evidence`) runs your tests, linters, scanners,
and review skills and feeds their output in as *candidate evidence*. Nothing
any tool says becomes a finding until it survives the evidence-verification
stage. See [`../docs/evidence-rules.md`](../docs/evidence-rules.md) §7.

## Requirements

Read access to the repo at a pinned commit; the framework tree for full mode.
No network, no services.
