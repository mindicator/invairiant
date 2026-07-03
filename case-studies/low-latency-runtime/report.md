# invAIriant Audit Report

- **Date:** 2026-07-03
- **Audit type:** full-scale
- **Scope:** The listener→body wake handoff over internal HTTP POST and the single-flight backpressure recently added to it (in-flight mutex, 429-busy, client fetch-abort + backoff, one new test). Full-scale pass: the whole core lens block (cormen, parnas, brooks, dijkstra, mcconnell, turing) plus lamport. REAL audit, REDACTED — the project name is withheld and all proprietary specifics are abstracted behind generic paths; the constants (950 ms / 0.95 s) are kept because they carry the lesson. Not in scope: the wake-detection logic upstream of the handoff and the body’s downstream actuation.

## Executive Summary

The change adds textbook-looking single-flight backpressure to the listener→body wake handoff — an in-flight mutex, a 429-busy response, a client fetch-abort + backoff, and a new passing test — and it scores well: parnas 8, brooks 8, turing 8, mcconnell 7, dijkstra 7, cormen 6, with a lens average around 7. Yet Lamport (4) files a real correctness finding the diff-level reviewer never saw: the handoff is serialized but NOT idempotent. The body applies every POST unconditionally (runtime/body.py:55-75), the payload carries no idempotency id (web/console.py:1530), and the client abort equals the server upstream timeout (CLIENT_ABORT_MS = 950 == UPSTREAM_TIMEOUT_S = 0.95), so a timed-out handoff can still land a state-changing wake at the body while the listener records failure — with no reconciliation (RTH-001). The 'single-flight' invariant the CHANGELOG and the one test assert is not the invariant the handoff needs, and the at-least-once idempotency_key pattern already lives ~30 lines away on a sibling endpoint (web/console.py:1458) and was skipped here (RTH-002); the one concurrency test pre-sets the busy flag and asserts a 429, never exercising the race or the timeout path (RTH-003). This is the anti-averaging lesson on real code: the average lens score is ~7 and the verdict is pass, yet depth (Lamport) surfaces a correctness defect that breadth (a high average) never would — a pass is NOT a clean bill of health. The verdict is pass because both open findings are S2/NOTE next-cycle debt on an internal handoff, non-blocking; they are recorded as required actions, not release gates.

**Verdict:** pass

## Lens Scores

| Pack | Lens | Score | Verdict |
|---|---|---:|---|
| systems | lamport | 4 | the handoff is serialized but not idempotent: the body applies every POST unconditionally (runtime/body.py:55-75), the payload carries no idempotency id (web/console.py:1530), and the client abort equals the server upstream timeout (950 ms == 0.95 s) so a timed-out handoff can still land a state-changing wake at the body while the caller records failure (RTH-001) |
| core | cormen | 6 | the 'single-flight' invariant is asserted in the CHANGELOG and the one new test but is not enforced against duplicates or timeouts; the at-least-once idempotency mechanism exists ~30 lines away (web/console.py:1458) and was skipped on this handoff (RTH-002) |
| core | mcconnell | 7 | well-constructed change — mutex, 429, client backoff, and a passing test all present and localized — but the one concurrency test pre-sets the in-flight flag by hand and asserts a 429; it exercises the reject branch, not the race (RTH-003) |
| core | parnas | 8 | the listener→body handoff is a clean interface boundary: one HTTP POST across a named seam, the body owns its own apply path, no reach-through into internals (runtime/body.py:55-75, web/console.py:1530) |
| core | brooks | 8 | the two entities have clear, nameable roles — the listener detects and forwards, the body applies — and the change adds no new entity; single coherent story |
| core | dijkstra | 7 | control flow is mostly simple and traceable — acquire mutex, POST, release, 429 on contention — no hidden dispatch; the one subtlety is the equal client/server timeout, which is a silent-ambiguity smell rather than a control-flow tangle (web/console.py:949, web/server.py:100) |
| core | turing | 8 | the backpressure is a real bound: the in-flight mutex plus 429 cap concurrency at one, the client backoff is finite, and the handoff loop terminates — no unbounded retry or 'act until done' loop introduced |

## Medium Findings (S2)

### RTH-001 — The wake handoff is serialized by the single-flight mutex but is not idempotent: (S2, lamport, confidence: high)

- **Claim:** The wake handoff is serialized by the single-flight mutex but is not idempotent: on a timeout the client cannot tell 'never applied' from 'applied but timed out', so a timed-out handoff can still land a state-changing wake signal at the body while the listener records failure, with no reconciliation.
- **Evidence:**
  - file_lines — runtime/body.py:55-75 — the body applies every accepted POST unconditionally — there is no dedup on a decision/correlation id, so a duplicate or a late-but-landed POST is applied again
  - file_lines — runtime/service.py:890-896 — per accepted decision the service prepends an event and emits the wake signal unconditionally — the state-changing side effect fires once per POST the body accepts, with no idempotency guard
  - file_lines — web/console.py:1530 — the handoff payload carries no message/idempotency id, so the body has nothing to dedup on even if it wanted to
  - file_lines — web/console.py:949 — CLIENT_ABORT_MS = 950 — the client aborts the fetch at 950 ms
  - file_lines — web/server.py:100 — UPSTREAM_TIMEOUT_S = 0.95 — the server’s own upstream timeout is 950 ms, EXACTLY equal to the client abort; on a timeout the caller cannot distinguish 'the body never got it' from 'the body applied it but the response was cut off'
- **Risk:** A timed-out handoff can still deliver a wake signal to the low-latency body (orphaned side effect / double-wake) while the listener records the handoff as failed. Because the caller cannot tell 'never applied' from 'applied but timed out' and nothing reconciles the two records, the runtime can wake the body when its own bookkeeping says it did not — a state divergence with no self-healing path.
- **Recommendation:** Make the handoff idempotent at least once: attach a decision/correlation (idempotency) id to the payload; have the body dedup on it so a re-POST of the same id is a defined no-op; and make the client abort and the server upstream timeout UNEQUAL (client strictly greater than server) so a timeout unambiguously means 'the server gave up first, nothing applied'. Add a reconciliation for the ambiguous window.
- **Category:** ORDERING_ASSUMPTION

### RTH-002 — The 'single-flight' invariant the CHANGELOG and the new test assert is not the i (S2, cormen, confidence: high)

- **Claim:** The 'single-flight' invariant the CHANGELOG and the new test assert is not the invariant the handoff needs: single-flight bounds concurrency to one, but it does not make the handoff idempotent, and the at-least-once idempotency pattern was known and skipped on exactly this endpoint.
- **Evidence:**
  - doc_code_contradiction — the changelog’s 'single-flight' claim implies the handoff is safe against re-delivery, but the body applies every POST unconditionally with no dedup — single-flight serializes, it does not de-duplicate a timed-out-but-landed POST
  - file_lines — web/console.py:1458 — the SAME file already sends an idempotency_key on a neighboring 'rescue' endpoint ~30 lines away from the handoff payload at :1530 — the at-least-once pattern was available and used elsewhere in this file, and skipped on the wake handoff
  - file_lines — web/console.py:1530 — the wake-handoff payload carries no idempotency id, unlike its sibling at :1458 — the invariant 'a re-delivered handoff applies at most once' is stated in prose but enforced nowhere
- **Risk:** A correctness property that is asserted in the changelog and 'proven' by a green test but not actually enforced hides the gap from the next reader: someone triaging a double-wake will trust the 'single-flight' label and look everywhere except the missing idempotency guard. Correctness rests on the handoff never timing out, which is not a design property.
- **Recommendation:** Enforce the invariant the handoff actually needs (apply-at-most-once per decision id), not just single-flight; add the idempotency_key to the handoff payload to match the sibling rescue endpoint at :1458; and state in the CHANGELOG that the handoff is at-least-once + idempotent, not merely single-flight.
- **Category:** FALSE_INVARIANT

## Unsupported Hypotheses

- The single-flight mutex already prevents this — only one handoff is ever in flight, so there is nothing to double-apply. — Refuted — the mutex prevents CONCURRENT handoffs, not DUPLICATE or TIMED-OUT-BUT-LANDED ones. Single-flight bounds concurrency to one; it does nothing about a POST that the client abandons at 950 ms while the body still applies it (runtime/body.py:55-75), which lands a wake the caller has already recorded as failed. Serialization is not idempotency.
- The 950 ms client abort leaves enough margin below the server timeout that the ambiguous 'applied but timed out' window is negligible. — Refuted — there is no margin: CLIENT_ABORT_MS = 950 (web/console.py:949) is EXACTLY equal to UPSTREAM_TIMEOUT_S = 0.95 (web/server.py:100). Equal deadlines maximize, rather than minimize, the window in which the client aborts at the same instant the server is still applying, so 'never applied' and 'applied but timed out' are indistinguishable precisely when it matters.
- This handoff is internal (listener→body on the same host), so at-least-once delivery concerns do not apply — treat it as a local call. — Refuted — two communicating processes over HTTP are already a distributed system regardless of host: the POST can time out, be retried, or land after the client gives up. The team already treats a sibling endpoint this way, sending an idempotency_key at web/console.py:1458; the handoff at :1530 simply omits it. 'It’s local' does not make a networked, timeout-bearing side effect idempotent.

