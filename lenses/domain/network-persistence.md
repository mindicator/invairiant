# Network Persistence Lens — Reachability Under Adversarial Pressure

**Pack:** domain · **ID:** `network-persistence`

## Purpose

This lens protects the property such systems exist for: staying reachable
under a realistic adversary — large-scale behavioral blocking, ML-based
traffic classification, AS-level blocking, protocol cutting (UDP/QUIC),
and endpoint enumeration. It detects transports that are merely
"obfuscated" rather than indistinguishable, redundancy that has quietly
collapsed to a single blockable point, control planes more fragile than
the data plane they configure, and rotation schemes whose flapping is
itself a signature.

## Scope

**Use when:**

- the system is a persistent-mesh network, P2P/overlay network, or
  anonymity system;
- transports are designed to traverse hostile or filtered networks;
- discovery, bootstrap, or config distribution must survive blocking;
- membership is open or semi-open and endpoints must resist enumeration.

**Skip when:**

- the system is a generic web application or internal service with no
  blocking adversary — this lens must not be forced onto it; use the
  core operational lenses instead.

Distilled from real-world practice building and auditing persistent-mesh
and overlay networks.

## Core Questions

- Which adversary capabilities is reachability claimed against —
  behavioral blocking, ML classification, AS-level blocking, protocol
  cutting, endpoint enumeration — and where is that claim written down?
- Is traffic statistically similar to legitimate HTTPS/QUIC — handshake
  fields, timing, packet-size distributions — and does it survive active
  probing, or is it merely "obfuscated"?
- Do multiple transports, ports, endpoints, and providers operate
  simultaneously, so that no single blockable point exists?
- Is infrastructure spread across autonomous systems and providers, with
  spare capacity in different ASes — and is the "handshake passes, data
  dies" degradation pattern detected and handled?
- Are the control plane and bootstrap — config distribution,
  first-contact endpoints — at least as survivable as the data plane, or
  do they hang on one domain or certificate that can be cut in minutes?
- What does joining cost (invites, social graph, proof-of-work), and does
  a knowledge gradient limit how many ingress endpoints a new member sees?
- When a transport or endpoint is blocked, does the system reconfigure
  in minutes rather than hours — and is that time actually measured?
- Does rotation avoid flapping that itself becomes a blocking signal
  (hysteresis, damping, confirmation of block events)?

## Good-State Examples

- Every transport ships a fingerprint evaluation: statistical comparison
  against legitimate traffic plus active-probe results, re-run per release.
- Ingress endpoints span at least three ASes and two providers, on
  multiple ports and transports; losing any one degrades, none severs.
- Config distribution reachable over several independent channels (multiple
  domains, fronted paths, out-of-band seeds); losing one is routine.
- New members join through an invite or cost mechanism and initially learn
  a small slice of endpoints; the enumeration curve is measured and bounded.
- End-to-end probes distinguish "handshake ok, data dead" from full
  blocks; a confirmed block reconfigures within minutes, with damping.

## Red Flags

- A transport with a recognizable signature — a bare protocol dressed as TLS.
- Everything in one AS, one distribution domain, or one certificate name.
- Discovery enumerable by a linear walk of the directory or DHT.
- Open membership with zero entry cost while endpoints should stay scarce.
- Auto-rotation that flaps in practice and becomes its own blocking signal.
- A redundant data plane configured by a control plane on one domain.
- Reachability validated against passive filtering only, never active probing.
- No measurement of time-to-reconfigure after a block event.

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

Typical for this lens: transport handshake or padding code producing a
distinguishable pattern (file + lines); infrastructure definitions showing
single-AS or single-domain concentration (configuration/schema mismatch);
a discovery endpoint permitting linear enumeration (file + lines plus
missing test); rotation flapping or probe failures in logs (runtime log);
a threat-model claim the deployment contradicts (doc/code contradiction).

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

### S0 Example

Claim: The entire network — data plane, config distribution, and
bootstrap — resolves to infrastructure in a single autonomous system
behind one certificate name, forming a single point of block.

Evidence: `deploy/terraform/edge.tf:12-58` provisions all ingress and the
config distribution endpoint in one provider region (one AS) under one
certificate name; `docs/threat-model.md:44` claims "no single AS or
domain can sever the network" (doc/code contradiction).

Risk: One AS-level block or certificate-name filter severs every user
simultaneously — data plane, control plane, and recovery path together;
the adversary needs one decision, not a campaign.

Recommended fix: Spread ingress and config distribution across
independent ASes, providers, and names; add out-of-band bootstrap seeds;
add a deploy gate that fails when endpoint diversity drops below the
documented floor.

### S1 Example

Claim: The discovery service allows a cheap linear walk of ingress
endpoints: an unauthenticated client can page through the full directory.

Evidence: `discovery/directory.go:88-140` serves paginated endpoint
listings with no join cost or knowledge gradient; production logs show a
single client IP retrieving 92% of records in under an hour (runtime
log); no test bounds what a new member can enumerate (missing test).

Risk: An adversary enumerates most ingress endpoints for the price of a
crawler, then blocks them in bulk; redundancy on paper collapses in
practice.

Recommended fix: Gate membership with an entry cost (invites or
proof-of-work); serve each member a bounded, per-identity slice of
endpoints; rate-limit and alert on enumeration patterns; add a test
asserting the knowledge gradient.

## Prompt Block

Use this prompt block when asking an AI auditor to apply this lens.

```text
You are applying the Network Persistence Lens (id: network-persistence)
from the invAIriant audit protocol: reachability under adversarial
pressure.

Examine the provided code/diff/docs for:
- statistical indistinguishability from legitimate traffic and survival
  of active probing (handshake fields, timing, sizes, probe behavior);
- redundancy: simultaneous transports, ports, endpoints, providers —
  and any single blockable point;
- AS and infrastructure diversity, including detection of the
  "handshake passes, data dies" pattern;
- survivability of the control plane and bootstrap relative to the data
  plane;
- enumeration and sybil resistance: join cost, knowledge gradient;
- adaptation speed after a block, and rotation that avoids flapping.

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
   Network Persistence Lens: N / 10
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
