# What a normal AI reviewer missed — low-latency-runtime

The diff adds single-flight backpressure to a wake handoff: an in-flight mutex,
a 429, a client abort with backoff, and a passing test. Here is the gap between
a diff-level reviewer and a full core-lens pass with Lamport — on **real,
redacted** code, with the finding still **open**.

## A generic AI PR reviewer says

> ✅ Solid backpressure. The in-flight mutex serializes the handoff so the body
> is never hit by two wakes at once, the 429 is the right signal for "busy," and
> the client aborts the fetch at `CLIENT_ABORT_MS = 950` so a slow body can't
> stall the listener. There's even a new test asserting the 429. Clean,
> localized, well-named. Approving.

Every sentence is *locally* true. The mutex works, the 429 is correct, the abort
exists, the test is green. Nothing here is wrong at the diff level — which is
exactly why it merges.

## The full lens pass says

**parnas 8 · brooks 8 · turing 8 · mcconnell 7 · dijkstra 7 · cormen 6.** The
breadth pass is *genuinely happy*: the handoff is a clean boundary, the roles
are clear, the backpressure is a real bound, the change is well-constructed.
Average ≈ 7. A reviewer reading only the scores would ship it with confidence.

**lamport 4.** Then one deep lens asks the question breadth skipped — *any
network effect can be duplicated by a retry or a timeout; is this write
idempotent?* — and the answer is no:

- **body (idempotency).** The body applies **every** POST unconditionally, with
  no dedup on a decision id (`runtime/body.py:55-75`), and fires the wake signal
  per accepted decision (`runtime/service.py:890-896`). A duplicate or a
  late-but-landed POST wakes the body again.
- **the equal timeout.** `CLIENT_ABORT_MS = 950` (`web/console.py:949`) **equals**
  `UPSTREAM_TIMEOUT_S = 0.95` (`web/server.py:100`). On a timeout the caller
  cannot tell "never applied" from "applied but timed out."
- **the payload.** It carries no idempotency id (`web/console.py:1530`), so the
  body has nothing to dedup on even in principle.

→ A timed-out handoff can land a state-changing wake at the body while the
listener records failure, with no reconciliation (`RTH-001`).

**cormen 6.** The "single-flight" invariant the CHANGELOG and the test assert is
not the one the handoff needs — and the at-least-once pattern was **known and
skipped**: the same file sends an `idempotency_key` on a sibling endpoint ~30
lines away (`web/console.py:1458`) and omits it here (`web/console.py:1530`).
→ `RTH-002`.

**mcconnell 7.** The new test **pre-sets the in-flight flag by hand and asserts
a 429** — it proves the reject branch, never the race or the timeout path.
→ `RTH-003`.

## The difference in one line

> The reviewer asked **"is this backpressure correct?"** and the answer was yes.
> Lamport asked **"can a retry or a timeout double-apply this write?"** — and the
> answer was yes.

## Why the process matters, not just the catch

- **Anti-averaging, demonstrated on real code.** The lens average is ~7 and the
  verdict is **pass**, yet a single deep lens (Lamport, 4) files a real
  correctness finding six green lenses never surface. Breadth does not offset
  depth; **a pass is not a clean bill of health.** One weak deep lens is the
  whole story, and the scores are reported honestly rather than blended into a
  reassuring mean.
- **Evidence-bound.** Every claim cites the body apply path, the two equal
  constants, the bare payload, and the sibling endpoint that *does* it right — a
  second reviewer verifies it in minutes.
- **Severity is honest.** "The mutex already prevents this" and "the 950 ms abort
  leaves margin" were both *refuted* (serialization ≠ idempotency; the timeouts
  are equal, not margined), and the finding is held at **S2**, not inflated to a
  release-blocking S1 — it is next-cycle debt on an internal handoff. The finding
  stays **open**, tracked with `OWNER?` placeholders, because honest beats tidy.
