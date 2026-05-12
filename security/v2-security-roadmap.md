# ChangeSpec v1.1 / v2.0 Security Roadmap

Security improvements planned for ChangeSpec versions after v1.0. This document draws a clear line between what must be fixed before v1.0 launch (see `threat-model.md` executive summary) and what can be deferred with documented known gaps.

---

## What must ship in v1.0

Non-negotiable before public launch:

1. **Fixed signature canonicalization** using JCS + typed envelope. Without this the signature design does not provide what it claims.
2. **Minimum signed field set** enforced by consumers. Protects against field stripping.
3. **Domain separation** in signature input. Prevents cross-protocol attacks.
4. **Key authorization binding** (key_id + vendor_id in signed input, scoped key lookup). Prevents cross-vendor key abuse.
5. **Strict URL scheme** restriction to `https://`. Prevents XSS/SSRF/phishing via URL fields.
6. **Parser hardening** - size limits, depth limits, duplicate-key rejection, ext field count limits.
7. **Signature verification in reference implementations.** Reference code must demonstrate correct verification.
8. **Schema convergence** - Go reference must use the canonical schema.json, not a hand-maintained divergent copy.
9. **TS prototype pollution fix** - `.passthrough()` replaced with an allowlist that rejects unknown non-ext fields.
10. **Python build-backend fix.** Release blocker.

These are not roadmap items. They are launch blockers. If they slip v1.0, the spec is not ready.

---

## What can ship in v1.0 with known gaps

Each of these is documented explicitly in `SECURITY.md` Section 12.20 as a known limitation. Consumers operating in high-trust environments must apply compensating controls.

### Known gap 1: No key transparency log

**Current state:** Vendors publish keys at a well-known URL. TLS is the trust anchor. Consumers may pin keys.

**Risk:** TLS compromise, DNS compromise, or rogue CA can issue a key that passes verification.

**Compensating control:** Consumers pin vendor keys after out-of-band acquisition. Consumers refresh pins on a controlled cadence.

**Planned fix (v1.1):** Deploy a Sigstore Rekor-based transparency log. Extend the well-known document with log inclusion proofs. See `trust-bootstrap.md`.

**Target date:** Six months after v1.0 launch.

### Known gap 2: No event retraction mechanism

**Current state:** If a producer publishes an incorrect event, the only remedy is publishing a corrected event with the same `id`. Consumers that have already acted on the incorrect event may not re-process.

**Risk:** Incorrect events cannot be cryptographically withdrawn. A compromised producer key can be used to issue false events; revoking the key stops new signatures but does not retract old events.

**Compensating control:** Consumers SHOULD treat a new event with a matching `id` as an authoritative replacement.

**Planned fix (v1.1):** Define a `retraction` event type that cryptographically invalidates a previously-published event. Consumers that process the retraction update their state accordingly. The retraction format will reuse the signature infrastructure.

**Target date:** Six months after v1.0 launch.

### Known gap 3: No producer sequence numbers

**Current state:** Ordering between events from the same producer relies on `published_at` timestamps. An attacker who can delay or reorder events can influence consumer state.

**Risk:** Replay-with-reordering attacks. A delayed critical CVE event arriving after a "CVE resolved" event is confusing at best.

**Compensating control:** Consumers track last-seen `published_at` per producer and warn on regressions.

**Planned fix (v1.1):** Optional `producer_sequence` field - a producer-maintained monotonically-increasing integer, signed. Consumers reject events that are out of sequence. Producers opt in.

**Target date:** Six months after v1.0 launch.

### Known gap 4: No post-quantum signature option

**Current state:** Ed25519 only. Provides classical security only.

**Risk:** Future quantum computer can forge signatures. Low risk for short-lived CVE advisories. Higher risk for long-lived legal/compliance events.

**Compensating control:** None at spec level. Deployers aware of this risk can choose to treat all signatures as advisory only and require human verification for high-value automated decisions.

**Planned fix (v1.1):** Add optional hybrid signatures (Ed25519 + ML-DSA-44 concurrently). Producers opt in per event or per key.

**Planned fix (v2.0):** Require hybrid or pure PQ signatures; deprecate Ed25519-only.

**Target date:** v1.1 six months after v1.0 launch. v2.0 by end of 2028.

### Known gap 5: No formal specification of non-publisher-verified event authenticity

**Current state:** `crawled` and `community` events have no cryptographic authenticity at the event level. The spec relies on platform transport security.

**Risk:** A malicious platform can fabricate `crawled` events indistinguishable from legitimate ones.

**Compensating control:** Consumers restrict autonomous agent actions on non-`publisher_verified` events (see SECURITY.md Section 12.13).

**Planned fix (v1.1):** Define a `crawler_attestation` field where a platform signs the event with its own key (distinct from vendor signing). This is explicitly labeled as a platform attestation, not a vendor attestation.

**Target date:** Six months after v1.0 launch.

### Known gap 6: No formalized anti-homoglyph protection for vendor_id

**Current state:** `vendor_id` is constrained to ASCII. Homoglyphs between visually-similar ASCII chars (`rn` vs `m`, `l` vs `1`) still possible.

**Risk:** Registry pollution via look-alike vendor IDs.

**Compensating control:** Registry operators apply confusable detection during registration review.

**Planned fix (v1.1):** Publish a vendor_id canonicalization algorithm (lowercase, remove hyphens/underscores, Unicode Security Mechanisms UTS #39 confusable detection at registration time) as a registry policy document.

**Target date:** With v1.1 launch.

### Known gap 7: No specified authentication for community event submission

**Current state:** Spec is silent on how community events are submitted and moderated. Platform-dependent.

**Risk:** Community submission pipelines are a natural source of social-engineered events.

**Compensating control:** Consumers filter `source_type: community` events from automated pipelines entirely.

**Planned fix (v1.1):** Publish recommended community-submission guidelines (moderation requirements, minimum time-to-publish, verification steps) as an informational RFC.

**Target date:** Six months after v1.0 launch.

### Known gap 8: No specified CVE cross-verification requirement

**Current state:** `cve_id` is a free-form identifier. Nothing cross-verifies the CVE with NVD, OSV, or GHSA.

**Risk:** Fabricated CVE IDs, CVE-ID squatting.

**Compensating control:** Consumer-side: always cross-check `cve_id` against an authoritative source before acting.

**Planned fix (v1.1):** Optional `cve_verified_at` and `cve_source` fields indicating when and against which authoritative database a CVE was cross-checked.

**Target date:** v1.1 or later.

---

## v1.1 release plan

Target timeline: 6 months after v1.0 public launch.

### Must-have for v1.1

1. Key transparency log deployed (via Sigstore Rekor).
2. Well-known keys document extended with log inclusion proofs.
3. `revoked_keys` list format finalized.
4. `retraction` event type specified.
5. Reference implementations: signature verification with full strict-mode ed25519.
6. Reference implementations: key transparency log client.
7. Conformance test suite expanded with signature tests and log verification tests.
8. Test vendor key material published.

### Nice-to-have for v1.1

1. Hybrid post-quantum signature option (Ed25519 + ML-DSA-44).
2. `producer_sequence` optional field.
3. `crawler_attestation` field.
4. Community event submission guidelines.
5. `cve_verified_at` / `cve_source` fields.

### Non-breaking changes only

v1.1 adds fields only. v1.0 events remain conforming. v1.0 consumers see v1.1 events and ignore unknown fields, falling back to v1.0 trust semantics. v1.1 consumers verify v1.0 events with v1.0 rules.

---

## v2.0 release plan

Target timeline: 24+ months after v1.0. Definitely before end of 2028.

### Major changes considered

1. **Require post-quantum signatures** for new publisher_verified events. Grandfather Ed25519-only keys issued before 2028 to a sunset date.
2. **Replace signature canonicalization with DSSE.** v1.0/1.1 JCS signatures remain accepted during transition.
3. **Require key transparency log entry** for publisher_verified events. Unsigned-log keys become untrusted after the transition.
4. **Tighten category and severity definitions** based on ecosystem feedback.
5. **Formal agent safety conformance level.** Separate conformance classes: "consumer" (reads events), "automated consumer" (may take actions with human review), "autonomous agent" (strict requirements).

### What is NOT planned for v2.0

- Multilingual summaries. Still scoped as future extension via `ext:i18n.*` if ever needed.
- Binary encoding (CBOR/Protobuf). JSON remains the on-wire format.
- Native GraphQL subscription semantics. Platforms handle subscriptions.

---

## Review cadence

This roadmap is reviewed:

- Quarterly by the security team, with updates published.
- When a security report reveals a gap not on this list (added immediately).
- When a dependent ecosystem matures (e.g., NIST PQ standards finalize, Sigstore adds ChangeSpec support natively).

Security-driven spec changes are proposed via Spec Enhancement Proposals (SEPs) with mandatory security review. The SEP process is defined in the governance documents.

---

## Summary

ChangeSpec v1.0 ships with a known-gap list. Consumers are informed. Compensating controls are documented. The roadmap to close each gap is public. The spec evolves under a security-first review process.

v1.0 is not the final answer. It is the smallest viable secure foundation. v1.1 closes the known gaps that can be closed without breaking changes. v2.0 makes the breaking changes that long-term security requires.

No showstopper is deferred. Every showstopper in `threat-model.md` is in the "must ship in v1.0" list above.
