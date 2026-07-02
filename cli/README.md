# `invairiant` CLI

Infrastructure around the agentic audit — **not an architecture auditor.** No
lenses, no findings, no scores. All judgment lives in the
[`/invairiant` skill](../skill/SKILL.md); this CLI scaffolds, validates,
collects evidence, renders, and gates.

Full spec and rationale: [`docs/cli.md`](../docs/cli.md).

## Quick use

```bash
python3 cli/invairiant.py init --type infra-service
python3 cli/invairiant.py validate-config
python3 cli/invairiant.py collect-evidence --out evidence.json
python3 cli/invairiant.py validate-report docs/audits/2026-06-19.json
python3 cli/invairiant.py render-report docs/audits/2026-06-19.json --out report.md
python3 cli/invairiant.py ci-gate docs/audits/2026-06-19.json   # exits 1 on open S0/S1
```

Requires Python 3.9+; `pip install jsonschema pyyaml` for the validate/collect
commands. Resolves the framework via `$INVAIRIANT_HOME` or its own location.
