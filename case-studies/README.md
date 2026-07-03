# Case Studies

A case study shows invAIriant applied to a code change, end to end:

```
the diff → selected lenses → candidate findings → rejected hypotheses (kept)
        → verified findings → final report → what a normal AI reviewer missed
```

The last line is the point. A generic AI PR reviewer comments on style,
naming, and the happy path. invAIriant is built to catch the *architectural*
defect a diff-level reviewer waves through — and to make that catch
evidence-bound and auditable, not a vibe.

Every finding in every case study cites concrete evidence. Reports are
schema-valid (`invairiant validate-report`) and gate-able (`invairiant
ci-gate`).

The set spans the **range** of audits — quick PR reviews (≤2 focused lenses)
through a **full-scale** audit that scores the whole core lens block; findings
both **open** and **fixed**; sources both **real (redacted)** and illustrative.

| Case | Source | Depth | Status | Lenses | The miss |
|---|---|---|---|---|---|
| [`low-latency-runtime`](low-latency-runtime/) | **real** (redacted) | full-scale | open | core block **+ lamport** | "single-flight" ≠ idempotent — a timed-out handoff double-applies a state change |
| [`social-autopost`](social-autopost/) | **real** (redacted) | PR | open | oracle-boundary · leveson | raw model output auto-published with no content gate |
| [`persistent-mesh-transport`](persistent-mesh-transport/) | illustrative | PR | **fixed** | cormen · security-threat · parnas · network-persistence | a documented "fail-closed" fallback actually ships a cert/SNI active-probe tell |
| [`ai-agent-refund-bot`](ai-agent-refund-bot/) | illustrative | PR | open | oracle-boundary · leveson | model output moves customer money with no cap or validation |
| [`generated-typescript-api`](generated-typescript-api/) | illustrative | PR | open | generated-surface-area · review-bottleneck | one near-duplicate handler silently drops an authz check |
| [`p2p-network-transport-change`](p2p-network-transport-change/) | illustrative | PR | open | lamport · network-persistence | an ordering assumption + a distinguishable handshake fingerprint |

**Real vs illustrative.** The two **real** cases are drawn from private
codebases and published with the project name and all proprietary specifics
withheld — generic file paths, no secrets, no identifiers. `low-latency-runtime`
is the deep end: a full-scale audit whose average lens score is ~7 and whose
verdict is *pass*, yet Lamport (4) files a real correctness finding the reviewer
never saw — **depth surfaces what breadth misses, and a high average never
launders a finding.** The four **illustrative** cases model real, recurring
defect classes without naming any project; `persistent-mesh-transport` shows the
*found → fixed* narrative (its recommendation is the shipped fix).

Each case directory contains: `README.md` (narrative), `diff.*` (the change),
`invairiant.config.yml` (scope), `report.json` + `report.md` (the audit),
`rejected-hypotheses.md` (kept), and `ai-reviewer-miss.md` (the side-by-side).
