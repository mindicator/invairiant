# invAIriant Event-Triggered Audit — <event>

<!--
An audit triggered by an event, not a calendar. Scope and lens selection
are determined by what the event stressed or changed.

Trigger taxonomy (extend per project):
  - production incident / outage / real adversarial event;
  - suspected or confirmed compromise, secret exposure, or data leak;
  - a new external surface: endpoint class, transport, membership class,
    integration, automation authority;
  - a change to discovery/trust/identity/degradation mechanisms;
  - a major refactor (blast radius above the project's cap);
  - technical debt or review debt crossing a declared threshold;
  - a dependency/platform event (breaking upgrade, EOL, license change).
-->

- **Date / participants:**
- **Event:** <!-- what happened, when, detected how -->
- **Trigger class:** <!-- from the taxonomy above -->
- **Commit range / systems in scope:**

## Scope

<!-- Determined by the event: the components the event touched, the
     assumptions it tested, the controls that did or did not hold. -->

## Timeline (for incidents)

<!-- Detection → response → mitigation → recovery, with timestamps.
     Include what the system did AUTONOMOUSLY (rotations, failovers,
     retries) — automation behavior during incidents is audit input. -->

## What the Event Tested

<!-- The load-bearing questions of a post-event audit: -->

- Which declared properties held? (with evidence)
- Which failed or degraded — and was the degradation an explicit policy or
  a silent branch?
- What recovered automatically, what required humans, how long did each
  take vs the SLO?
- Which assumptions in the canonical docs / threat model did the event
  falsify?
- Did any workaround applied during the event trade away a declared
  safety/privacy/correctness property? (each such workaround = a finding
  with a trigger-to-remove)

## Lens Scores

<!-- Only lenses relevant to the event — typically 2-4 (e.g. incident →
     operational-resilience + the lens owning the failed assumption).
     Post-incident audits: operational-resilience is mandatory. -->

| Pack | Lens | Score | Verdict |
|---|---|---:|---|

## Findings

<!-- By severity. The incident report itself is valid evidence
     (type: incident). -->

## Unsupported Hypotheses

<!-- Especially important post-incident: suspected causes that were NOT
     confirmed, recorded with what evidence would confirm/refute them. -->

## Actions

<!-- Owner + deadline + blocking|non-blocking. Include:
     - fixes to the failed control;
     - detection/observability gaps exposed;
     - doc/threat-model updates the event demands;
     - removal triggers for temporary workarounds. -->

1.

## Closure Verification Plan

<!-- After the fix wave, a short closure-verification report must confirm:
     each claimed fix closed (conformance evidence per claim), no new
     boundary drift, CI green at verified HEAD, canonical docs synced,
     temporary workarounds removed, remaining findings listed with owners.
     Name here: who runs it, and the date/condition that triggers it. -->

## Evidence Appendix
