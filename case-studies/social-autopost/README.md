# Case study — social-autopost

> **Real audit — redacted (project & platform withheld) · PR audit · finding OPEN**
>
> This is a **real** finding from a private content-automation tool. It is
> published **redacted**: the project name and the third-party social platform
> are withheld and all proprietary specifics are abstracted. File paths,
> identifiers, and strings below are **generic stand-ins** for the real modules.
> No real names, model ids, account handles, tokens, or secrets appear. The
> finding is **OPEN** — not fixed.

## Context

A content-automation tool runs an autonomous background loop. On each pass it
takes a raw completion from **a hosted LLM** and publishes it directly as a
**public post** on **a third-party social platform**, under a managed account.

The only thing between *"the model emitted text"* and *"the text is live"* is a
**post-frequency counter**. There is no schema validation, no allowlist, no
content moderation, no length/format contract, and no human approval between the
model output and the publish call.

## The change under review

The path is short and reads cleanly:

```py
text = await model_client.complete(prompt)   # raw model output
if text is None:                             # None only on call failure
    return
await action_pipeline.publish(account=account, content=text)  # goes live, as-is
```

`model_client.complete()` is the only transformation the text gets: it strips
and truncates the model's output and returns `None` on failure
(`services/model_client.py:120-128`). The `publish()` action then validates
account existence, platform match, a concurrency lock, and rate limits
(`services/action_pipeline.py:74-180`) — and **never inspects the content**.
The loop that drives all this is autonomous, not a manual or API trigger
(`services/monitor.py:88-95`). And the upstream post is interpolated into the
prompt (`services/auto_publish.py:242-252`), so untrusted input reaches the
completion that becomes an irreversible public post.

It builds. It has a circuit breaker, a concurrency lock, rate limiting,
human-like delays, structured logging, and passing tests. A diff-level reviewer
approves.

## What invAIriant caught

There is **no boundary artifact at all** — nothing written down about what the
model may decide, and no deterministic disposition of what it emits — so the
effective content policy for a public identity is *"whatever the model outputs
today."*

Two lenses converge, with a third supporting:

- **oracle-boundary** — raw model output reaches a public, irreversible publish
  with **no validation and no written boundary** between them (`SAP-001`, S1).
  It **trends toward S0**: the prompt-injection vector
  (`services/auto_publish.py:242-252`) makes that output reachable from
  untrusted input, and the action is public and irreversible — the escalation
  condition for `UNVALIDATED_ORACLE_OUTPUT`.
- **leveson** — the loop wields **unbounded automation authority** over an
  irreversible public action: no human override on the executing path, no
  content precondition at execution time, and no effect feedback. The docs even
  note a post can be **silently shadowbanned** with no auto-detection
  (`SAP-002`, S2).
- **turing** (supporting) — probabilistic output is treated as truth; the
  garbage / empty / injected path is undefined and untested (score 4/10).

### The tell: the project's own docs

The project **loudly documents a sibling pipeline** as deliberately
**deterministic, no-LLM, and human-approved** — *"unit coverage asserts no GPT
dependency."* **This** pipeline does the exact opposite — unreviewed LLM text
published autonomously — and **no doc marks the difference**. The project's own
written standard for a public-writing pipeline is determinism plus human
approval; this path silently violates it (`docs/pipelines.md` vs
`services/auto_publish.py:139,155-166`).

### The missing test

The auto-publish service's tests exercise only **no-op paths** — no configs
present, feature disabled, target account not found. The publish path itself —
and any empty, oversized, hostile, or prompt-injected model output — is
**entirely unexercised** (`tests/test_services.py`).

## The killer point

The service **looks defensively engineered**: circuit breaker, concurrency
lock, rate limiting, human-like delays, logging, passing tests. But **every one
of those guards protects VOLUME and MECHANICS — none protects CONTENT.** The
rate limiter bounds how *often* it posts; the lock bounds *concurrency*; the
breaker bounds *reliability*. Not one of them asks *what* is about to be
published.

So the composed system reliably publishes **unsafe text** — and the safety
theater is worse than nothing, because it **disguises the gap**. A reviewer sees
all that plumbing and concludes the path is careful. The plumbing is careful
about the wrong axis.

> The reviewer asked **"is this code correct and defensive?"** — and the answer
> was yes. The lens asked **"what must never happen, and is that guaranteed?"**
> — and the answer was: raw model text, steerable from untrusted input, goes
> live under a managed identity with nothing in between.

## Outcome

Verdict **pass_with_conditions** — one open S1 (`SAP-001`). `invairiant
ci-gate` on this report **exits non-zero**, so a merge would be gated. The
finding is **OPEN**; the required actions (owners left as `OWNER?`):

1. **[blocking]** Add a deterministic validation/allowlist + length/format
   contract + a human-approval (or auto-block) step **before** publish; treat
   the model's score and text as a *candidate*, not truth; write down the
   boundary and mark how this pipeline differs from its deterministic sibling.
2. **[blocking]** Add tests feeding empty / oversized / hostile / injected model
   output through to the (mocked) publish boundary and assert it is blocked.
3. Bound the automation authority on the executing path: a content precondition
   at execution time, a real override/kill path, and effect feedback that
   detects silent suppression.

Files: [`report.json`](report.json) · [`report.md`](report.md) ·
[`diff.patch`](diff.patch) · [`rejected-hypotheses.md`](rejected-hypotheses.md) ·
[`ai-reviewer-miss.md`](ai-reviewer-miss.md) ·
[`invairiant.config.yml`](invairiant.config.yml)
