# invAIriant Audit Report

> Example of a **full-scale audit** on a fictional infra service
> ("conveyor", a multi-tenant job scheduler in Go). Every file path, line
> number, and log excerpt below is invented for illustration; the structure,
> rule applications, and phrasing are the point.

- **Date:** 2026-06-19
- **Audit type:** full-scale
- **Project / commit range:** conveyor · `v0.7.0..a41f9cc`
- **Phase / milestone (if used):** pre-GA hardening
- **Participants:** m.orlova (system architect, gates), d.reyes
  (security/threat auditor), claude-agent (lens auditor: parnas, turing,
  von-neumann, lamport, review-bottleneck), claude-agent-2 (evidence
  verifier), m.orlova (severity classifier, synthesis review)
- **Config:** `invairiant.config.yml` (this directory)

## Scope

The scheduler control plane (`scheduler/`, `dispatch/`), worker runtime
(`worker/`), tenant API (`api/`), and artifact distribution (`distrib/`)
at commit `a41f9cc`, against canonical docs README, ARCHITECTURE,
THREAT_MODEL. **Out of scope:** the billing exporter (audited 2026-05-02),
the Terraform stack, and the web console.

## Inputs Reviewed

- Repo at `a41f9cc` (≈41k LOC Go); diff `v0.7.0..a41f9cc` (+6.2k/−1.9k)
- `docs/ARCHITECTURE.md` (2026-05-28), `docs/THREAT_MODEL.md` (2026-04-11),
  ADRs 0007–0019
- CI history for the range (`github-actions`, 61 runs)
- `go test ./...` at `a41f9cc` (2 failures, see Evidence Appendix E-3)
- semgrep default + custom ruleset output (14 hits → candidate evidence)
- Incident report INC-118 (2026-06-07, worker crash-loop in eu-1)

## Executive Summary

Conveyor's module boundaries and construction discipline are in good shape
for a pre-GA system: contracts between API, scheduler, and workers are
explicit, changes in the audited range were localized, and docs mostly track
reality. The audit still fails the pre-GA gate, for one reason: on worker
crash, the recovery path logs the full job environment — including tenant
API keys — to the shared operator log (CNV-041, S0 `SECRET_LEAK`). Two S1
findings compound the risk story: webhook delivery can double-fire side
effects on retry (CNV-042), and the scheduler treats the Redis job-state
cache as the source of truth during recovery, so a restart can resurrect
cancelled jobs (CNV-043). A high average lens score (7.0) does not offset
any of this — per protocol, the S0 alone decides the verdict.

**Verdict:** fail (pre-GA gate) — blocked on CNV-041; conditions on
CNV-042/043 for the next release cut.

## Lens Scores

| Pack | Lens | Score | Verdict |
|---|---|---:|---|
| security-safety | security-threat | 4.5 | THREAT_MODEL row "credential exposure via logs" closed on paper only — refuted by `worker/recover.go:88-104` (CNV-041); other rows verified in code |
| core | parnas | 8 | boundaries hold; one leak: `api/handlers/jobs.go:210-232` imports `scheduler/internal` types (CNV-044) |
| core | mcconnell | 8 | changes localized, ADRs current; CHANGELOG missed two contract-relevant entries (obs O-2) |
| core | turing | 7 | dispatch/retry loops bounded (`dispatch/loop.go:51`, cap+deadline); replay tooling for scheduler decisions missing (obs O-1) |
| systems | von-neumann | 5.5 | Redis cache treated as truth on recovery, `scheduler/recover.go:61-97` vs ARCHITECTURE §"State" (CNV-043) |
| systems | lamport | 6 | webhook retry lacks idempotency key end-to-end (CNV-042); elsewhere writes are idempotent by job ULID |
| ai-generated-code | review-bottleneck | 7 | generated handler code has tests + provenance trailers; two >1.5k-line PRs merged with single-pass review (obs O-3) |

## Critical Findings

### CNV-041 — Tenant secrets written to shared operator log on worker crash (S0, security-threat, confidence: high)

- **Claim:** The worker crash-recovery path serializes the entire job
  environment, including tenant-scoped API keys, into the shared operator
  log.
- **Evidence:**
  - `file_lines` — `worker/recover.go:88-104` @ a41f9cc: `log.Errorw("job
    crashed", "env", job.Env)` where `job.Env` includes `CONVEYOR_TENANT_KEY`
    (set in `worker/exec.go:57-63`)
  - `runtime_log` — INC-118 operator log excerpt (Evidence Appendix E-1):
    `env":{"CONVEYOR_TENANT_KEY":"ck_live_9t...` (redacted here)
  - `doc_code_contradiction` — `docs/THREAT_MODEL.md:141` marks "credential
    exposure via logs" as mitigated by "env scrubbing in worker" — no
    scrubbing exists in `worker/` (`rg -n scrub worker/` → 0 hits,
    Appendix E-2)
- **Risk:** Any operator (and the log pipeline vendor) can read live tenant
  credentials; INC-118 already wrote at least 7 tenants' keys to retained
  logs. Direct hit on risk assets "tenant credentials" and "operator
  safety".
- **Recommendation:** Scrub/allowlist env at the logging boundary; rotate
  all keys present in retained logs since 2026-06-07; add a no-secrets
  conformance test on the log schema; correct THREAT_MODEL only after the
  control exists.
- **Category:** SECRET_LEAK
- **Owner / deadline:** d.reyes / 2026-06-24 (blocking GA)

## High Findings

### CNV-042 — Webhook retry can double-apply tenant side effects (S1, lamport, confidence: high)

- **Claim:** Delivery retries re-POST webhooks without an idempotency key,
  so a timeout-then-success sequence applies tenant side effects twice.
- **Evidence:**
  - `file_lines` — `distrib/webhook.go:71-96` @ a41f9cc: retry loop re-sends
    the identical request; no `Idempotency-Key` header, no delivery ULID
  - `missing_test` — no test under `distrib/` exercises
    timeout-after-delivery (`rg -n "timeout" distrib/*_test.go` → connection
    timeouts only, Appendix E-4)
- **Risk:** Tenants performing non-idempotent actions on webhooks (several
  do, per support tickets referenced in INC-104) get duplicate side effects
  during network degradation — data corruption on the tenant side,
  attributed to conveyor.
- **Recommendation:** Add a per-delivery idempotency key (job ULID +
  attempt-independent delivery ID), document the contract, add the
  timeout-after-delivery test.
- **Owner / deadline:** platform team / next release cut

### CNV-043 — Redis cache is the source of truth during scheduler recovery (S1, von-neumann, confidence: high)

- **Claim:** On restart, the scheduler rebuilds its run queue from the Redis
  cache instead of Postgres, so cancellations that raced the crash are
  resurrected.
- **Evidence:**
  - `file_lines` — `scheduler/recover.go:61-97` @ a41f9cc: queue rebuilt
    exclusively from `cache.ScanJobs()`; Postgres reconciliation is a TODO
    at line 95
  - `doc_code_contradiction` — `docs/ARCHITECTURE.md:203` ("Postgres is the
    single source of truth for job state; Redis is a disposable
    accelerator") vs the code above
  - `command_output` — reproduction: cancel-then-SIGKILL script re-runs job
    (Appendix E-5)
- **Risk:** Restart changes the meaning of the system: cancelled jobs run,
  violating tenant expectations and — for destructive jobs — tenant data.
  Named category `CONFLICTING_SOURCE_OF_TRUTH` applies (two authorities
  over job state, no owner during recovery).
- **Recommendation:** Rebuild from Postgres, then warm the cache; add a
  crash-cancel conformance test; delete the TODO by implementing it.
- **Category:** CONFLICTING_SOURCE_OF_TRUTH
- **Owner / deadline:** scheduler team / next release cut

## Medium Findings

### CNV-044 — API handlers import scheduler internals (S2, parnas, confidence: high)

- **Claim:** Tenant API handlers construct `scheduler/internal` types
  directly, bypassing the submission contract.
- **Evidence:** `file_lines` — `api/handlers/jobs.go:210-232` @ a41f9cc:
  imports `scheduler/internal/model` and sets private queue hints.
- **Risk:** Scheduler refactors now break the API layer; queue hints become
  an undocumented tenant-visible behavior.
- **Recommendation:** Extend the public submission DTO with the one hint
  actually needed; add an import-boundary lint rule (`depguard`).
- **Owner / deadline:** api team / this cycle

## Notes / Observations

- **O-1 (turing):** Scheduler decisions (why job X ran on worker Y) are not
  replayable — inputs are logged but the decision function version is not.
  No defect shown; recorded as debt.
- **O-2 (mcconnell):** CHANGELOG missed the webhook-timeout change
  (`distrib/webhook.go`) and the recovery rewrite — both contract-relevant.
- **O-3 (review-bottleneck):** PRs #412 (+1.8k) and #431 (+1.6k), largely
  generated, merged with single-pass review. Tests and provenance trailers
  present; volume trend worth watching, no evidence of a slipped defect.

## Unsupported Hypotheses

| Hypothesis | Proposed by | Rejection / status |
|---|---|---|
| Dispatch loop starves low-priority tenants under saturation | claude-agent (turing pass) | **Rejected:** fairness property test `dispatch/fairness_test.go:12-88` exists and passes at a41f9cc; no starvation evidence in logs |
| Generated handler near-duplicates hide divergent validation | claude-agent (review-bottleneck pass) | **Demoted to observation:** three near-duplicate validators found (`api/handlers/{jobs,runs,artifacts}.go`) but behaviorally identical per table-driven test added during verification |
| semgrep: possible SSRF in artifact fetch (`distrib/fetch.go:40`) | semgrep (evidence adapter) | **Rejected:** URL host is pinned to tenant-registered endpoints validated at registration (`api/tenants.go:118-141`); scanner unaware of the invariant |

## Strongest Lens

**parnas (8/10).** Contracts between API, scheduler, worker, and distrib
are explicit and mostly honored; the one violation (CNV-044) is localized
and cheap to fix. Verified by the replaceability probe: the queue backend
swap in ADR-0016 touched one package.

## Weakest Lens

**security-threat (4.5/10).** A threat-model row was closed on paper while
the control did not exist (CNV-041) — the exact failure mode this lens
exists to catch. Per the severity model, a critical lens below 5.0 tied to
a concrete user/operational risk yields S0; that rule fired here.

## Required Actions Before Next Phase / Major PR

1. **CNV-041** — scrub env at log boundary + rotate exposed keys + log-schema
   conformance test. Owner d.reyes, due 2026-06-24. **Blocking GA.**
2. **CNV-042** — idempotent webhook delivery + timeout-after-delivery test.
   Owner platform, next release cut. Blocking release.
3. **CNV-043** — recovery rebuilds from Postgres; crash-cancel test. Owner
   scheduler team, next release cut. Blocking release.
4. **CNV-044** — public DTO extension + depguard rule. Owner api team, this
   cycle. Non-blocking.
5. Re-audit: closure verification on items 1–3 before the GA go/no-go
   (expected 2026-07-01).

## Evidence Appendix

- **E-1** — INC-118 operator log excerpt (redacted), 2026-06-07T14:22:31Z,
  worker eu-1-w7: `{"level":"error","msg":"job crashed","job":"01J...",
  "env":{"CONVEYOR_TENANT_KEY":"ck_live_9t[REDACTED]","PATH":...}}`
- **E-2** — `rg -n "scrub|redact" worker/` → no matches (full output).
- **E-3** — `go test ./...`: `TestRecoverRequeuesCancelled` FAIL (expected —
  written during verification of CNV-043), `TestWebhookTimeout` FAIL (flaky,
  tracked #388). Full transcript.
- **E-4** — `rg -n "timeout" distrib/*_test.go` output.
- **E-5** — cancel-then-SIGKILL reproduction script and transcript
  (3 runs, job re-executed 3/3).

## Reviewer Notes

Verification statistics: 11 candidates proposed → 7 verified, 3
rejected/demoted (kept above), 1 merged into CNV-043. The semgrep SSRF
rejection is a good example of why adapters feed evidence rather than
findings. Next audit should start from: replay tooling for scheduler
decisions (O-1) and the generated-code volume trend (O-3).
