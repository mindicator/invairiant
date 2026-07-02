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

Reference implementation: [`cli/invairiant.py`](../cli/invairiant.py) (Python
3.9+; `pip install jsonschema pyyaml` for the validate/collect commands).

```bash
python3 cli/invairiant.py <command> [...]
# convenience alias:
alias invairiant='python3 /path/to/invairiant/cli/invairiant.py'
```

It locates the framework via `$INVAIRIANT_HOME`, else relative to the script.

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

### `invairiant validate-report <paths...>`
Validate audit report JSON against
[`schemas/audit-report.schema.json`](../schemas/audit-report.schema.json)
(findings resolve against the finding schema). Exit 0/1.

### `invairiant collect-evidence [--config P] [--out F] [--timeout S]`
Run the evidence adapters declared in the config (`evidence_adapters`), capture
each tool's raw output, and emit a JSON array of **candidate-evidence** items
(`type: command_output`, with `exit_code` and truncated `output`). Recognized
adapters: `pytest`, `go-test`, `golangci-lint`, `eslint`, `ruff`, `semgrep`,
`vitest`. It runs only tools that are installed, times each out, and **judges
nothing** — every item must still pass the skill's stage-2 verification before
it can become a finding.

### `invairiant render-report <report.json> [--out F]`
Deterministically render a report JSON to Markdown in the shape of
[`templates/audit-report.md`](../templates/audit-report.md): header, executive
summary + verdict, lens-score table, findings by severity, and the kept
Unsupported Hypotheses. Formatting only — no content is added or judged.

### `invairiant ci-gate <report.json> [--max-severity S0|S1]`
The seatbelt. Exit non-zero when the report has open blocking findings — by
default any `S0` or `S1` whose `status` is not `rejected`; `--max-severity S0`
blocks only `S0`. Prints the blocking findings. Wire it into CI after the agent
files a report:

```yaml
- run: python3 cli/invairiant.py ci-gate docs/audits/latest.json
```

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

Reference implementation. `init`, `validate-config`, `validate-report`, and
`ci-gate` are complete; `collect-evidence` and `render-report` are functional
and intentionally minimal. Packaging as an installable `invairiant` entry point
is a thin future wrapper; the schemas are the stable contract underneath.
