# Audit memory (committed, sanitized)

This directory is invAIriant's own **audit memory** — written by
`invairiant record <report.json>` after each audit, read by
`invairiant history`, `invairiant collect`, and `invairiant validate-report`.

- `rejected-hypotheses.jsonl` — hypotheses refuted in past audits, so they are
  not re-proposed without new evidence.
- `finding-registry.jsonl` — the distilled finding history (recurring findings
  become candidates for lint rules / CI gates).
- `lens-score-history.csv` — lens scores over time (`history` flags two
  consecutive drops).

**Sanitized and safe to commit:** only distilled fields are stored — claim,
lens, severity, category, reason, score — **never raw evidence blobs, code,
diffs, or secrets** (secret-like text is redacted on write). Raw evidence
bundles from `invairiant collect` and any local agent transcripts stay under
`.invairiant/cache/`, which is gitignored. See
[`../../docs/cli.md`](../../docs/cli.md) and
[`../../docs/audit-workflow.md`](../../docs/audit-workflow.md) §8.
