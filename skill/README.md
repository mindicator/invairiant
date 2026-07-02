# invAIriant as an agent skill

[`SKILL.md`](SKILL.md) packages the invAIriant protocol as an installable
skill for Claude Code and compatible agent harnesses: `/invairiant` runs
config discovery → lens selection → the four-stage pipeline (lens passes →
evidence verification → severity classification → synthesis) → a written
audit report, with humans owning all gate decisions.

## Install

Any one of:

- **Project skill (this repo or any repo):**
  `mkdir -p .claude/skills && cp -r <framework>/skill .claude/skills/invairiant`
  (or symlink: `ln -s <framework>/skill .claude/skills/invairiant`).
  Local `.claude/` state is gitignored, so run this one-liner once per
  clone to make `/invairiant` available.
- **Personal skill:** `cp -r <framework>/skill ~/.claude/skills/invairiant`.
- **With the framework elsewhere:** set `INVAIRIANT_HOME=/path/to/framework`
  so the skill finds the full lens library; without it the skill runs in a
  documented degraded mode with four generic lenses.

## How it relates to other skills and tools

Other skills and tools are **evidence adapters**, not competitors: the
skill runs your test suite, linters, security scanners, and review skills
first, and feeds their raw output into the audit as *candidate evidence*.
Nothing any tool says becomes a finding until it survives the evidence
verification stage. See
[`../docs/evidence-rules.md`](../docs/evidence-rules.md) §7.

## Requirements

- Read access to the audited repo at a pinned commit/range.
- The framework tree (`lenses/`, `prompts/`, `schemas/`, `templates/`,
  `docs/`) for full mode; nothing else. No network, no services.
