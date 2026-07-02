# Operational Resilience Lens — Degradation, Recovery, and Anti-Flapping

**Pack:** security-safety · **ID:** `operational-resilience`

## Purpose

This lens protects against systems that fail instead of degrading: one lost
dependency halting everything, auto-remediation that flaps until it becomes
the outage, recovery objectives that exist as sentences rather than
measurements, restarts that forget safe state, and failovers that quietly
trade away a declared security or privacy property for availability. Losing
a node, dependency, or component should slow the system, not stop it — and
every degraded mode should be explicit, observable, and chosen.

The principle underneath every check: **degradation, not failure.**

## Scope

**Use when:**

- the system runs in production and its components or dependencies can fail
  independently;
- a change touches health checks, failover, retries, auto-remediation,
  leader election, caching of last-known-good state, or restart and
  bootstrap paths;
- the system must operate through partial outages, dependency brownouts, or
  adversarial network conditions;
- a recovery-time objective exists in docs, contracts, or promises.

**Skip when:**

- the tool is offline or batch and "retry tomorrow" is an acceptable
  failure mode — note that explicitly instead of scoring.

## Core Questions

- For each dependency and component: what happens when it is lost? Is there
  an explicit degraded-but-working mode, or does the system crash — or fall
  silently into an unsafe fallback?
- Can work be rerouted around a failed segment (instance, zone, provider,
  dependency), and has that path been executed recently rather than only
  designed?
- Which single components, if lost, halt everything? Has a coordinator,
  config service, or license check quietly become a kill switch?
- Does every auto-remediation — restart, rotate, failover, scale — have
  limits, cooldown or hysteresis, and rollback? What stops a remediation
  loop from flapping and amplifying the outage it is trying to fix?
- Is recovery time defined and measured — a number from a real or rehearsed
  incident — or an objective asserted in words only?
- Does a component survive restart without losing safe state, coming back
  in the configuration that held before the incident rather than defaults?
- Can a brand-new instance bootstrap when the primary discovery or
  first-contact path is down or degraded?
- Are degraded states observable: can operators tell which mode the system
  is in, when it entered, and when it exited?
- Do degraded modes preserve declared security and privacy properties, or
  does failover widen access or disable verification without an explicit
  policy?

## Good-State Examples

- Losing the recommendation service degrades to a static fallback list; the
  mode is explicit in code, visible as a metric, and exercised by a
  scheduled chaos test.
- When the config service is down, nodes continue on last-known-good signed
  configuration with a bounded age; expiry behavior is defined and tested —
  the config service is not a kill switch.
- Failover has a cooldown and a cap — at most two reroutes per ten minutes,
  then hold and page a human — so the loop cannot flap faster than its own
  damping.
- Recovery time is a measured number: the last game day recorded 6m40s
  against a ten-minute objective, and the report is linked from the SLO
  document.
- Restart and bootstrap are rehearsed: a node restores safe state from
  local persistence, and a fresh instance has a tested secondary
  first-contact path for degraded environments.

## Red Flags

- Loss of one coordinator or dependency halts everything — a component
  nobody named a kill switch is one in practice.
- Auto-remediation has no limits: restart/rotate/failover loops with no
  cap, cooldown, or hysteresis flap until they are the outage.
- Recovery time is not measurable: the objective exists by word only, never
  measured from a real or rehearsed incident.
- Failover breaks a security or privacy boundary — falling back to
  unauthenticated mode, disabling verification, or widening data exposure
  for availability's sake.
- Degradation lands in an unsafe mode nobody explicitly chose: the fallback
  exists, but no policy authorizes it.
- Restart loses safe state: a node returns with defaults that predate the
  incident, re-opening what had been closed.
- A brand-new instance has exactly one bootstrap path, unavailable
  precisely in the degraded environment where new instances are needed.
- Degraded modes are invisible: no metric or log separates "degraded" from
  "healthy," so users discover the degradation first.

## Required Evidence

Findings under this lens must cite one or more of:

- file path + line range
- diff hunk
- test failure
- missing test
- doc/code contradiction
- runtime log
- incident report
- CI output
- configuration/schema mismatch

Typical for this lens: the code path that exits or crashes when a
dependency is unreachable (file + lines); a remediation loop with no cap or
cooldown (file + lines); a runtime log showing repeated failover cycles; an
incident report where a brief dependency blip became a full stop; a
doc/code contradiction between a stated recovery objective and the absence
of any measurement; a missing test for restart or degraded bootstrap.

## Scoring Rubric

| Score | Meaning |
|---:|---|
| 0–2 | Dangerous / uncontrolled |
| 3–4 | Prototype with serious architectural risk |
| 5–6 | Meaningful but debt-heavy |
| 7 | Strong prototype |
| 8 | Strong engineering, not yet boring |
| 9 | Near-reference, survives growth |
| 10 | Mature, boring, repeatedly proven |

## Finding Examples

### S1 Example

Claim: Every pipeline worker exits when the config service is unreachable —
at startup and on each refresh failure — with no last-known-good path, so a
single dependency outage halts all processing.

Evidence: `workers/pipeline/bootstrap.go:48-71` — `log.Fatal` on config
fetch error in both the startup path and the refresh goroutine;
`postmortems/2026-03-11-config-outage.md:12-30` records a five-minute
config-service blip that produced a 47-minute full stop (incident report).

Risk: An auxiliary service is a de facto kill switch: any outage, however
brief, converts into total downtime plus a slow restart tail, and the
system's real availability ceiling is the config service's availability.

Recommended fix: Cache last-known-good signed configuration with a bounded
age; continue in an explicit degraded mode on refresh failure, exposed as a
metric; add a test that kills the config dependency mid-run and asserts
continued processing.

### S2 Example

Claim: The connection-pool rotator recycles a backend after a single failed
probe with no cooldown or hysteresis, so a slow-but-alive backend is
rotated out and back repeatedly.

Evidence: `services/pool/rotator.py:92-118` — one probe failure triggers
rotation, and reinstatement is immediate on the next success;
`logs/staging/pool-2026-06-20.log:310-402` shows backend `b-7` rotated 41
times in twelve minutes (runtime log); no test covers a marginal backend
with alternating probe results (missing test).

Risk: Under partial degradation the remediation multiplies connection churn
and load on the remaining backends, turning a brownout into an outage — the
remediation loop itself becomes the amplifier.

Recommended fix: Require N consecutive probe failures before rotation; add
a cooldown and hysteresis on reinstatement; cap rotations per window and
page when the cap is hit; add a flapping-backend test.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Operational Resilience Lens (id: operational-resilience)
from the invAIriant audit protocol: degradation, recovery, and anti-flapping.

Examine the provided code/diff/docs for:
- behavior on loss of each dependency or component: explicit
  degraded-but-working modes versus crashes or silent unsafe fallbacks;
- single components whose loss halts the system (accidental kill switches),
  and whether rerouting around failed segments is real and exercised;
- auto-remediation loops: limits, cooldown, hysteresis, and rollback —
  whatever prevents flapping from amplifying an outage;
- recovery objectives that are measured rather than asserted, restart
  safety, and bootstrap of a fresh instance in a degraded environment;
- observability of degraded states, and degraded modes that sacrifice a
  declared security or privacy property without an explicit policy.

Rules:
- No evidence, no finding. Every finding must cite file+lines, a diff hunk,
  a test (failing or missing), a doc/code contradiction, a log, CI output,
  or a config/schema mismatch.
- If you cannot cite evidence, record the item as an Observation,
  Hypothesis, or Open question — never as a finding.
- Do not average away critical risks.
- Do not produce confident claims from vibes.

Output:
1. A score block:
   Operational Resilience Lens: N / 10
   Strengths:
   - ...
   Concerns:
   - ...
   Candidate findings:
   - ...
2. Candidate findings as JSON conforming to schemas/finding.schema.json
   (severity is provisional; the severity classifier assigns the final one).
3. Observations / hypotheses / open questions, clearly separated.
```
