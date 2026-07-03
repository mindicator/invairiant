# invAIriant as an agent skill — the primary product

[`SKILL.md`](SKILL.md) is the main way to use invAIriant: an LLM coding agent
runs the audit itself. The schemas, templates, and prompt pack are the layer it
stands on; the [CLI](../cli/README.md) is only infrastructure around it.

**`SKILL.md` is the single source of truth; it is agent-agnostic.** Claude Code
loads it as a skill; Codex and Cursor reach the same protocol through the
portable [`AGENTS.md`](../AGENTS.md) and
[`.cursor/rules/invairiant.mdc`](../.cursor/rules/invairiant.mdc), which point
back here rather than duplicating it.

## Commands

`/invairiant <command>`:

| Command | Does |
|---|---|
| `audit-pr [<pr#\|range>] [--lenses a,b]` | PR-scoped audit: checklist + ≤2 focused lenses → verdict |
| `full-audit [<range>]` | full-scale audit: all mandatory lenses → report |
| `verify-findings <candidates>` | adversarially verify candidate findings (stage 2) |
| `classify-severity <verified>` | map verified findings to severity (stage 3) |
| `synthesize-report <inputs>` | assemble the final report (stage 4) |
| `closure-verification` | re-verify claimed fixes closed (no re-search) |

`--lenses a,b` overrides lens selection; omit it to pick by risk surface.
All under one rule: **no evidence, no finding.**

## Install — per agent

Same protocol, three discovery mechanisms. Point any of them at the framework
tree (set `INVAIRIANT_HOME=/path/to/framework` if it lives outside your repo;
without the lens library a documented degraded mode runs four generic lenses).

- **Claude Code** — load `skill/` as a skill:
  `mkdir -p .claude/skills && cp -r <framework>/skill .claude/skills/invairiant`
  (or symlink). Local `.claude/` is gitignored, so run this once per clone.
  Personal: `cp -r <framework>/skill ~/.claude/skills/invairiant`. Drive it
  with `/invairiant <command>`.
- **Codex** (and any `AGENTS.md`-aware agent) — copy [`AGENTS.md`](../AGENTS.md)
  into your repo root (merge with an existing one). Then ask the agent to "run
  an invAIriant audit-pr"; it follows the protocol from `AGENTS.md` →
  `SKILL.md`.
- **Cursor** — copy [`.cursor/rules/invairiant.mdc`](../.cursor/rules/invairiant.mdc)
  into your repo's `.cursor/rules/`. Cursor also reads `AGENTS.md`.

In all three, the `invairiant` CLI (`pip install -e .`) is the same
judgment-free seatbelt.

## How it relates to other skills and tools

Other skills and tools are **evidence adapters**, not competitors: the skill
(often via `invairiant collect`) runs your tests, linters, scanners,
and review skills and feeds their output in as *candidate evidence*. Nothing
any tool says becomes a finding until it survives the evidence-verification
stage. See [`../docs/evidence-rules.md`](../docs/evidence-rules.md) §7.

## Requirements

Read access to the repo at a pinned commit; the framework tree for full mode.
No network, no services.
