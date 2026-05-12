# Trust Bootstrap

How does a ChangeSpec consumer discover and trust a vendor's public key? This is the unsolved problem in v1.0. This document proposes a solution suitable for v1.1.

---

## Problem Statement

A consumer receives a signed ChangeSpec event from `vendor_id: "stripe"` with `signature.key_id: "stripe-2026-01"`. To verify the signature, the consumer must:

1. Discover the public key for `(stripe, stripe-2026-01)`.
2. Trust that the public key actually belongs to Stripe, not to an attacker impersonating Stripe.

Step 1 is easy. Step 2 is the hard part and is the entire problem.

---

## Why this is hard

Trust bootstrap is the problem every cryptographic system faces at its edges. TLS solves it with Certificate Authorities (hundreds of CAs, any of which can issue a cert for any domain, with browser vendors as ultimate arbiters). PGP solved it with a web of trust (which nobody could make usable). SSH solves it with TOFU (trust on first use, which assumes the first use is uncompromised). Signed software updates usually solve it with a built-in public key that ships with the OS or package manager.

ChangeSpec has several distinguishing features that shape the trust-bootstrap problem:

1. **Many producers, many consumers.** Stripe, Anthropic, GitHub, plus thousands of package maintainers. A dedicated trust root per vendor does not scale.
2. **Open ecosystem.** Anyone should be able to publish ChangeSpec events for their own vendor without asking permission. A centralized gatekeeper is politically and operationally unattractive.
3. **Trust decisions are automated.** Unlike TLS where a human clicks through a certificate warning, ChangeSpec events drive automated workflows. A trust failure results in a silent security gap, not a user prompt.
4. **Low but nonzero value-at-risk per event.** A single forged event causes real damage (mass patching, compliance action, supply-chain compromise) but individual events are not worth individual trust decisions.
5. **Short event useful life.** Most ChangeSpec events lose urgency within weeks (patch a CVE, update a DPA). Long-term signature validity matters less than for, say, software release signatures.

---

## Options evaluated

### Option 1: Well-known URI only (current v1.0)

Vendor publishes keys at `https://{vendor-domain}/.well-known/changespec-keys.json`. Consumer fetches over TLS.

**Trust anchor:** TLS certificate for the vendor domain.

**Pros:** Zero extra infrastructure, familiar pattern (OAuth, OpenID Connect, WebFinger use well-known URIs).

**Cons:**
- Compromises of the vendor's DNS, TLS chain, hosting provider, or .well-known path are all catastrophic.
- Does not defend against a malicious CA issuing a rogue cert.
- Does not defend against subdomain takeover.
- Does not defend against a nation-state MITM against a consumer.
- No key transparency: a vendor cannot easily detect if its own keys have been silently replaced.
- Vendor-domain mapping is unclear for namespaced vendor IDs (`npm:lodash` - whose domain? npmjs.com? github.com? lodash.com?).

**Verdict:** Insufficient as sole trust anchor. Acceptable as one of several layers.

---

### Option 2: DNS-based (TXT records, DANE)

Vendor publishes a TXT record `_changespec.vendor.com` pointing to key fingerprints. Consumers query DNS.

**Trust anchor:** DNSSEC chain.

**Pros:**
- DNS is a universally deployed identity mechanism.
- DNSSEC provides origin authentication for DNS records.
- Resilient to web-server compromise (attacker needs DNS control, not HTTP control).

**Cons:**
- DNSSEC deployment is spotty. Many vendor domains do not deploy DNSSEC.
- Resolving DNSSEC-validated records from application code requires a DNSSEC-validating resolver, which is operationally complex.
- DNS has slow propagation times (TTL-bounded), making key rotation and revocation slow.
- DNS caching can delay revocation by hours.
- Most consumers run in cloud environments where DNS is resolver-handled and DNSSEC status is opaque to the application.
- Still does not solve the `npm:lodash` problem (no DNS domain).

**Verdict:** Better than Option 1 for vendors with DNSSEC, but not a universal solution. Useful as a defense-in-depth signal, not as the primary trust anchor.

---

### Option 3: Key Transparency Log (Certificate-Transparency-style)

A public, append-only Merkle tree log records every vendor key issuance. Consumers verify that a served key appears in the log at a Merkle tree position consistent with the log's signed root.

**Trust anchor:** The log operator (usually: multiple independent log operators, with consumers verifying inclusion in a quorum).

**Pros:**
- Full auditability: any vendor key issuance is publicly visible.
- A vendor can monitor the log for unauthorized keys and detect compromises that pass Options 1 and 2 silently.
- Consumers do not need per-vendor trust decisions; they trust the log operator(s).
- Scales to any number of vendors.
- Works for namespaced vendor IDs (`npm:lodash` gets log entries the same way `stripe` does).
- Models exist: Certificate Transparency (RFC 6962), Key Transparency (Google, WhatsApp), Sigstore Rekor.

**Cons:**
- Requires running transparency log infrastructure (non-trivial but Sigstore / Rekor provides a ready model).
- Initial trust in the log operator is its own bootstrap problem. Solved by using multiple operators with consumer-side quorum.
- Requires a cold-start: how does a consumer know a vendor's first legitimate key? Typically this is done by having the vendor publish the fingerprint during onboarding (via press release, documentation, support ticket) and the consumer key-pins for a period.
- Log witnesses are required (independent parties that periodically attest the log has not been rewound).

**Verdict:** This is the best scalable solution and the closest match to ChangeSpec's threat model. Has the downside of requiring operational infrastructure, but Sigstore Rekor is a ready-made option.

---

### Option 4: Web of Trust / Cosigning

Vendor keys are co-signed by a quorum of independent parties (other vendors, auditors, the ChangeSpec foundation, CT log operators). Consumers verify that at least N of M cosigners have attested to a vendor key.

**Trust anchor:** Aggregate of cosigners.

**Pros:**
- Defense in depth: an attacker must compromise multiple cosigners to forge a key.
- Aligns with ecosystem patterns like Debian's keyring model and Arch's trusted users.
- Allows gradual trust building.

**Cons:**
- Who are the cosigners? This question is politically fraught. If the ChangeSpec foundation picks them, the foundation becomes a centralized trust authority. If the community picks them, governance becomes complex.
- Operational overhead for every vendor onboarding.
- Does not provide transparency (attacker who compromises all cosigners leaves no public trace).

**Verdict:** Useful as a defense-in-depth layer on top of Options 1-3. Not a standalone solution.

---

### Option 5: Central Registry (ChangeSpec Foundation runs a CA)

The ChangeSpec foundation operates a key registry. Vendors submit keys, the registry signs them, consumers trust the registry's signing key.

**Trust anchor:** The ChangeSpec foundation.

**Pros:**
- Simple. One trust root.
- Easy for consumers: pin the foundation's key, done.
- Aligns with how most closed-source standards handle trust.

**Cons:**
- Politically unattractive for an open standard. Vendors and consumers may resist depending on a single foundation as a CA.
- The foundation becomes a high-value target for nation-state attackers.
- Operational burden on the foundation (incident response, compromise handling, revocation).
- Does not scale if the foundation is slow.
- No transparency: consumers cannot detect if the foundation is issuing bogus keys.

**Verdict:** Works short-term but bad long-term. A transparency log is almost always a better choice.

---

## Recommended Solution

**Primary:** Key transparency log operated as a Sigstore Rekor tile (Option 3).

**Secondary (defense in depth):** Well-known URI (Option 1) cross-checked against the log.

**Tertiary (optional):** Multi-party cosigning (Option 4) for high-value vendors.

**Not adopted:** Central registry as trust root (Option 5), DNS-only (Option 2).

---

## Detailed design

### Trust architecture

```
 Vendor (e.g., Stripe)
    |
    | publishes event with signature
    v
 Event: {... signature: {alg, key_id, value, signed_fields}}
    |
    | delivered via transport (webhook, polling API)
    v
 Consumer
    |
    | 1. Extract vendor_id, key_id
    | 2. Fetch vendor's well-known keys doc (optional optimization)
    | 3. Verify key appears in transparency log
    | 4. Cross-check key document against log record
    | 5. Verify signature
    v
 Verified event
```

### Key transparency log structure

The log is an append-only Merkle tree. Each leaf is a signed statement:

```json
{
  "type": "changespec.key.v1",
  "vendor_id": "stripe",
  "key_id": "stripe-2026-01",
  "public_key": "<base64url>",
  "alg": "ed25519",
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": "2027-01-01T00:00:00Z",
  "issued_at": "2025-12-15T10:00:00Z",
  "issuer_proof": {
    "method": "dns-txt",
    "evidence": "_changespec-issuer.stripe.com"
  }
}
```

Leaves are signed by the log operator. The log root is signed hourly by the log operator and by independent witnesses. Consumers verify:

- The leaf is signed by a trusted log operator.
- The leaf is included in a log root signed by the operator and N of M witnesses.
- The log root is monotonically increasing (no rewinds).

### Issuer proof

The `issuer_proof` establishes that the log entry was submitted by someone with control over the vendor. Options:

- **DNS TXT record** (most vendors): vendor creates `_changespec-issuer.vendor.com` with a challenge value during log submission.
- **Namespaced vendor proof** (for `npm:lodash`, `pypi:requests`): the log operator queries the registry to verify the submitter matches the package maintainer.
- **Cosigning** (optional, higher trust): multiple unrelated cosigners attest to the submission.

The log operator runs these checks at submission time, not at query time. Consumers trust the operator's check.

### Well-known keys document (kept but extended)

The well-known document at `https://{vendor-domain}/.well-known/changespec-keys.json` is still used as a performance optimization and as a secondary verification path. It is extended with log-inclusion proofs:

```json
{
  "keys": [
    {
      "key_id": "stripe-2026-01",
      "alg": "ed25519",
      "public_key": "<base64url>",
      "valid_from": "2026-01-01T00:00:00Z",
      "valid_until": "2027-01-01T00:00:00Z",
      "log_inclusion_proof": {
        "log_id": "rekor-ct-changespec-public-log",
        "tree_size": 10042317,
        "leaf_index": 10042316,
        "root_hash": "sha256:...",
        "inclusion_proof": ["...", "...", "..."],
        "signed_tree_head": "..."
      }
    }
  ],
  "revoked_keys": [
    {
      "key_id": "stripe-2025-12",
      "revoked_at": "2026-02-01T00:00:00Z",
      "reason": "compromised"
    }
  ]
}
```

### Revocation

Three revocation channels, all of which consumers check:

1. The well-known document's `revoked_keys` list.
2. The transparency log's revocation leaves (log entries of type `changespec.key-revocation.v1`).
3. The key's `valid_until` expiration.

Consumers MUST treat a key as revoked if any of the three channels indicates revocation.

### Consumer verification algorithm

Pseudocode:

```
fn verify_event(event):
    if event.source_type != "publisher_verified":
        return Unsigned
    if not event.signature:
        return NotSigned

    # 1. Fetch candidate public key from well-known URL
    keydoc = fetch_well_known(event.vendor_id)   # HTTPS + ETag check
    candidate = keydoc.keys.find(k => k.key_id == event.signature.key_id)
    if not candidate:
        return UnknownKey

    # 2. Check key is not revoked
    if candidate.key_id in keydoc.revoked_keys:
        return KeyRevoked
    if now() > candidate.valid_until:
        return KeyExpired
    if now() < candidate.valid_from - 5min:
        return KeyNotYetValid

    # 3. Verify log inclusion proof
    proof = candidate.log_inclusion_proof
    if not verify_merkle_inclusion(proof, trusted_log_public_keys):
        return UntrustedKey
    if not verify_tree_head_signature(proof.signed_tree_head,
                                       trusted_log_public_keys,
                                       trusted_witness_keys,
                                       quorum=2):
        return UntrustedLogHead

    # 4. Cross-check with log directly if out-of-date local tree
    if proof.tree_size < local_known_tree_size:
        # Potential log rewind - reject
        return LogRewindSuspected

    # 5. Reconstruct signature input per spec Section 7.3 (revised)
    signature_input = build_canonical_signature_input(event)

    # 6. Verify the ed25519 signature (strict mode)
    if not ed25519_verify_strict(candidate.public_key,
                                  signature_input,
                                  event.signature.value):
        return BadSignature

    # 7. Check freshness
    if event.published_at < now() - 90.days or event.published_at > now() + 5.min:
        return NotFresh

    return Verified
```

### Log operator trust bootstrap

The log operator's public key is the ultimate trust anchor. It must be distributed through multiple channels:

1. Shipped with consumer libraries (hardcoded in the reference implementations).
2. Published at `https://logs.changespec.com/.well-known/log-keys.json`.
3. Published in a DNSSEC-signed TXT record.
4. Announced via press release and social media when the log is bootstrapped.
5. Cross-signed by multiple independent witnesses.

A consumer that trusts any one of these channels can bootstrap. Consumers SHOULD pin the log operator's key after first acquisition.

---

## Migration from v1.0

The v1.0 spec permits unsigned events and uses only the well-known URL. v1.1 extends this without breaking v1.0:

- v1.0 consumers continue to work (well-known URL still exists; log inclusion proof is in an additional field that v1.0 consumers ignore).
- v1.1 consumers gain transparency verification on top of v1.0 behavior.
- Producers that want to opt into v1.1 verification include `log_inclusion_proof` in their keys document. Producers that do not are treated as v1.0-only and their signatures carry less trust.

A 12-month period is allocated after v1.1 release during which producers are encouraged to register their keys in the log. After 24 months, consumers SHOULD reject `publisher_verified` events whose keys are not in the log.

---

## Non-goals

- **Eliminating all trust roots.** Trust has to start somewhere. We minimize and distribute the trust roots but cannot eliminate them.
- **Protecting against compromise of the vendor at the source.** If Stripe's production signing key is stolen, the thief can issue signed events until Stripe revokes the key. No mechanism can prevent this on the timescale of a single incident. The transparency log makes the theft detectable, which is the best achievable outcome.
- **Cryptographic proof of vendor identity for every ChangeSpec event in existence.** Events predating v1.1 will remain unsigned or verifiable only via v1.0 mechanisms. Historical data is trusted at the level it was trusted when issued.

---

## Operational requirements for the ChangeSpec foundation

If the foundation operates the log:

- The log MUST be run with infrastructure security at least equivalent to a public CA: HSMs for signing keys, 24/7 monitoring, incident response plan, published disclosure policy.
- The log operator MUST NOT be the sole trust anchor. At least two independent witness operators must be appointed.
- The log software MUST be open source and independently auditable.
- The log MUST publish a public status dashboard showing tree size, latest signed root, and witness attestations.
- The log MUST have a published retention policy (recommend: forever, since log entries are small).

Alternative: leverage Sigstore Rekor directly. Sigstore already provides all of this infrastructure. ChangeSpec would be one of many event types in Rekor. This is cheaper and faster to deploy but ties ChangeSpec's trust to Sigstore's operational model.

**Recommendation: use Sigstore Rekor for v1.1 launch.** Build a dedicated log only if Rekor's constraints become binding.

---

## Security properties achieved

With this design:

- **Origin authenticity:** an event signed by `key_id=stripe-2026-01` can only be produced by someone with access to that key. Verified via Ed25519 signature.
- **Key authorization:** the key `stripe-2026-01` can only be used for `vendor_id=stripe`. Verified via log entry which binds (vendor_id, key_id, public_key) at issuance time.
- **Key transparency:** a compromise of the vendor's key-publishing infrastructure is detectable. Vendors monitor the log for unauthorized entries under their vendor_id.
- **Revocation:** compromised keys are revoked through three independent channels. Consumers check all three.
- **Freshness:** signed `published_at` plus a consumer-enforced window prevents replay.
- **Cross-protocol safety:** the domain separator in the signature input prevents cross-protocol reuse.

Remaining risks:
- Vendor's private key is compromised in a way not detected for a long time. Mitigated by regular rotation and log monitoring.
- Log operator and all witnesses colluding to backdate entries. Mitigated by quorum requirement and by witnesses being independent.
- TLS compromise of the well-known URL. Mitigated by log cross-check: a forged key document that does not match the log is rejected.

---

## Summary

The unsolved trust-bootstrap problem in v1.0 has a proven solution: a key transparency log modeled on Certificate Transparency and implemented via Sigstore Rekor. The solution:

- Scales to any number of vendors and consumers.
- Requires no central CA.
- Provides auditability and compromise detection.
- Can be deployed incrementally alongside the existing well-known URL mechanism.

v1.1 should adopt this mechanism. v1.0 should ship with explicit documentation that key distribution is insufficient for high-trust automated use cases (see `v2-security-roadmap.md` and the SECURITY.md section 12.5 text).
