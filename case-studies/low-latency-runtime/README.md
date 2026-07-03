# Case study — low-latency-runtime

> **Real audit — redacted (project name withheld) · full-scale · finding OPEN.**
> A genuine finding from a private low-latency runtime. The project is not
> named, every proprietary specific is abstracted behind generic paths, and no
> secrets, hashes, or real entity names appear. The two constants — a 950 ms
> client abort and a 0.95 s server timeout — are kept verbatim, because their
> being *equal* is the whole lesson.

## Context

A low-latency runtime hands work between two entities. A **listener** detects a
wake event and forwards it to a separate, latency-sensitive **body** process
over an **internal HTTP POST**. The listener records that it handed the wake
off; the body applies it. Two processes over HTTP — already a distributed
system, timeouts and all.

## The change under review

A recent commit added **single-flight backpressure** to that handoff, and it
looks like textbook backpressure:

- an **in-flight mutex** so only one handoff runs at a time;
- a **429-busy** response when a second one arrives;
- a **client fetch-abort + backoff** (`CLIENT_ABORT_MS = 950`);
- a **new passing test**.

It builds, it is localized, the test is green. A diff-level reviewer approves —
this is exactly what backpressure is supposed to look like. See
[`diff.patch`](diff.patch) for the redacted change.

## What the full core-lens pass + Lamport caught

Scoring the whole core block gives a healthy picture — **parnas 8, brooks 8,
turing 8, mcconnell 7, dijkstra 7, cormen 6** — a lens average around 7. The
handoff really is a clean boundary (parnas), the roles really are clear
(brooks), the backpressure really is a genuine bound (turing).

Then **Lamport (4)** looks at the one thing breadth skipped: the handoff is
**serialized but not idempotent**.

- **The body applies every POST unconditionally** — no dedup on a
  decision/correlation id (`runtime/body.py:55-75`), and per accepted decision
  it prepends an event and fires the wake signal (`runtime/service.py:890-896`).
- **The client abort equals the server’s upstream timeout** —
  `CLIENT_ABORT_MS = 950` (`web/console.py:949`) is *exactly*
  `UPSTREAM_TIMEOUT_S = 0.95` (`web/server.py:100`). On a timeout the caller
  cannot tell *"the body never got it"* from *"the body applied it but the
  reply was cut off."*
- **The payload carries no idempotency id** (`web/console.py:1530`) — so even a
  body that *wanted* to dedup has nothing to dedup on.

Result: a **timed-out handoff can still land a state-changing wake at the body**
(orphaned side effect / double-wake) **while the listener records failure**,
with nothing reconciling the two records (`RTH-001`, S2, lamport).

Two more lenses converge on the same spot:

- **cormen** — the "single-flight" invariant the CHANGELOG and the test assert
  is not the one the handoff needs. Single-flight bounds *concurrency*; it does
  not make the handoff *idempotent*. And the at-least-once pattern was known:
  the **same file sends an `idempotency_key` on a sibling "rescue" endpoint ~30
  lines away** (`web/console.py:1458`) and skips it on the wake handoff at
  `:1530` (`RTH-002`, S2).
- **mcconnell** — the one new concurrency test **pre-sets the in-flight flag by
  hand and asserts a 429**; it never issues two concurrent requests and never
  exercises the 950 ms timeout or the duplicate path. It proves the *reject*
  branch, not the *race* (`RTH-003`, NOTE).

## Outcome

Verdict **pass** — both open findings are **S2 / NOTE next-cycle debt** on an
internal handoff, so they are non-blocking; `invairiant ci-gate` on this report
**exits zero**. But *pass is not a clean bill of health*: the required actions
are real work, tracked with `OWNER?` placeholders —

1. make the handoff idempotent (decision id on the payload + dedup at the body
   + reconciliation for the ambiguous window);
2. make the client abort and the server timeout **unequal** (client strictly
   greater), so a timeout unambiguously means nothing applied;
3. add a genuine two-concurrent-request test **and** a timeout/duplicate test.

**The teaching point:** the average lens score is ~7 and the verdict is pass,
yet **Lamport (4) files a real correctness finding the reviewer never saw**.
Depth surfaces what breadth misses — one deep lens is not offset by six shallow
green ones. See [`ai-reviewer-miss.md`](ai-reviewer-miss.md).

Files: [`report.json`](report.json) · [`report.md`](report.md) ·
[`diff.patch`](diff.patch) · [`rejected-hypotheses.md`](rejected-hypotheses.md) ·
[`ai-reviewer-miss.md`](ai-reviewer-miss.md) ·
[`invairiant.config.yml`](invairiant.config.yml)
