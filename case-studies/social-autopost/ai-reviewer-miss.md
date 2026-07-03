# What a normal AI reviewer missed — social-autopost

The diff adds an auto-publish path: ask a hosted LLM for post text, then publish
it. It arrives wrapped in a circuit breaker, a concurrency lock, rate limiting,
human-like delays, and structured logging, and the tests pass. Here is the gap
between a diff-level reviewer and an invAIriant lens pass.

## A generic AI PR reviewer says

> ✅ Nice, defensively-engineered pipeline. Good use of a **circuit breaker**
> and a **concurrency lock** around the publish, **rate limiting** so we don't
> spam the platform, and **human-like delays** to look natural. `complete()`
> returns `None` on failure and the caller handles it. The action pipeline
> validates the account, the platform, and the rate budget before posting.
> Logging is in place. Tests are green. This is careful work — approving.

Every sentence is *locally* true. The breaker is real, the lock is real, the
rate limiter is real, the tests are green. Nothing here is wrong at the diff
level — which is exactly why it merges.

## invAIriant's lens pass says

**oracle-boundary (what the model may decide).** Where is the written boundary
between what the model decides and what stays deterministic? *There isn't one.*
Is model output validated — schema, allowlist, bounds, moderation — before it
touches the world? *No.* Can it reach a production side effect with nothing in
between? *Yes:* `services/auto_publish.py:139` → `:155-166` hands the raw
completion straight to `publish()`, and `services/action_pipeline.py:74-180`
never inspects it. The effective content policy for a public identity is
"whatever the model emits today." And the model is steerable from untrusted
input — the upstream post is interpolated into the prompt
(`services/auto_publish.py:242-252`). → `SAP-001` (S1, trending S0).

**leveson (unsafe control).** Which control action is unsafe in which state, and
what stops it being issued there? *Publishing unreviewed text is unsafe in every
state, and nothing stops it.* The loop is autonomous
(`services/monitor.py:88-95`); there is no human override on the executing path,
no content precondition at execution time, and no effect feedback — the docs
themselves note a post can be silently shadowbanned with no auto-detection. The
controller acts, then never learns whether the action had the intended effect.
→ `SAP-002` (S2).

**turing (oracle discipline, supporting).** Is this a computation with a defined
result, or a hope with an API key? Probabilistic output is treated as truth; the
empty / garbage / injected path is undefined and untested. There is no defined
system state for "the model emitted something unsafe." → score 4/10.

## The difference in one line

> The reviewer graded the **plumbing** — breaker, lock, rate limit — and it was
> excellent. The lens asked **what the plumbing carries**: raw, unvalidated,
> injection-steerable model text, straight to a public, irreversible post.

Every guard the reviewer praised protects **VOLUME and MECHANICS**. Not one
protects **CONTENT**. The defensiveness is real — and it is aimed at the wrong
axis, which is what makes the gap so easy to approve past.

## Why the process matters, not just the catch

- **Evidence-bound:** every claim cites the model-to-publish handoff, the
  content-blind action pipeline, the autonomous loop, the prompt-injection site,
  the doc/code contradiction, and the missing test — a second reviewer verifies
  it in minutes.
- **Severity is honest:** `SAP-001` is held at **S1**, with the **S0 trend**
  recorded (untrusted input reaches an irreversible public action) rather than
  claimed as a demonstrated exploit. The comforting hypotheses — "the rate
  limiter gates it," "a human reviews it," "the model won't misbehave" — were
  each **refuted**, not assumed.
- **The tell is written down:** the project's own docs hold a **sibling**
  pipeline to a deterministic, no-LLM, human-approved standard; this path
  violates that standard silently. The audit surfaces the contradiction instead
  of trusting the plumbing.
