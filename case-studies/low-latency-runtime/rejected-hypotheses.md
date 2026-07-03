# Rejected hypotheses — low-latency-runtime

Kept, not deleted. Each was proposed during the lens passes and **refuted** at
the evidence-verification stage. Recording them stops the next audit from
re-litigating the same ground, and it is why the finding landed where it did.

### H1 — "The single-flight mutex already prevents this." → **Refuted**

The obvious first read: only one handoff is ever in flight, so there is nothing
to double-apply. Verification refutes it. The mutex prevents **concurrent**
handoffs, not **duplicate** or **timed-out-but-landed** ones. Single-flight
bounds concurrency to one; it does nothing about a POST the client abandons at
950 ms while the body still applies it (`runtime/body.py:55-75`), which lands a
wake the listener has already recorded as failed. **Serialization is not
idempotency** — that gap is `RTH-001`.

### H2 — "The 950 ms abort leaves margin below the server timeout." → **Refuted**

If the client gave up comfortably before the server did, the ambiguous
"applied but timed out" window would be small. Verification reads the two
constants: `CLIENT_ABORT_MS = 950` (`web/console.py:949`) is **exactly equal**
to `UPSTREAM_TIMEOUT_S = 0.95` (`web/server.py:100`). There is no margin. Equal
deadlines **maximize** the window in which the client aborts at the same instant
the server is still applying, so "never applied" and "applied but timed out" are
indistinguishable precisely when it matters. The equal timeout is not a detail —
it is half of `RTH-001`.

### H3 — "It's an internal, same-host handoff, so at-least-once concerns don't apply." → **Refuted**

Tempting to treat listener→body as a local call. Refuted: two processes over
HTTP are a distributed system regardless of host — the POST can time out, be
retried, or land after the client gives up. The team already knows this: a
sibling **"rescue" endpoint in the same file** sends an `idempotency_key`
(`web/console.py:1458`); the wake handoff at `:1530` simply omits it. "It's
local" does not make a networked, timeout-bearing side effect idempotent. The
skipped-but-known pattern is the tell recorded as `RTH-002`.
