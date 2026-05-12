# Signature Design Review

This document reviews ChangeSpec 1.0's signing design in depth. It evaluates the algorithm choice, the canonicalization approach, domain separation, key identification, envelope compatibility, and quantum readiness. It concludes with a recommended revision to the signature sections of the spec.

---

## Scope

The document reviews Section 7 of `spec.md` (Signing and Verification) as shipped in the v1.0 draft.

- Section 7.1: Why Ed25519
- Section 7.2: Signature object structure
- Section 7.3: Signature input construction
- Section 7.4: Key distribution
- Section 7.5: Verification steps

Plus the JSON Schema signature subschema in `schema.json`.

---

## Algorithm Choice

### Is Ed25519 the right algorithm?

**Yes, for v1.0.** Ed25519 is the correct algorithm for a new specification in 2026 for the reasons the RATIONALE document already articulates: compact signatures (64 bytes), small keys (32 bytes), fast verification, deterministic nonce derivation, broad standard-library support, and RFC 8032 standardization. However the spec's justification is incomplete in important ways.

### Comparison with alternatives

| Algorithm | Sig size | Pub key size | Verify speed | Standardization | Pros | Cons |
|---|---|---|---|---|---|---|
| Ed25519 | 64 B | 32 B | Fast | RFC 8032 | Deterministic, no nonce risk, wide support | Not post-quantum. 128-bit security level. |
| Ed448 | 114 B | 57 B | Slower | RFC 8032 | Higher security (224-bit) | Less library support, larger |
| ECDSA P-256 | 64-72 B | 64 B | Fast | FIPS 186-4 | FIPS compliant, HSM support | Nonce reuse catastrophic, DER encoding ambiguity |
| ECDSA P-384 | 96-104 B | 96 B | Slower | FIPS 186-4 | Higher security (192-bit) | Same ECDSA risks |
| RSA-PSS 2048 | 256 B | ~270 B | Slow sign | RFC 8017 | Long-established | Large, slow, parameter ambiguity |
| RSA-PSS 4096 | 512 B | ~520 B | Very slow sign | RFC 8017 | Higher security | Very large, slow |
| ML-DSA-44 | 2420 B | 1312 B | Fast | FIPS 204 | Post-quantum | Large, no ecosystem yet |
| Falcon-512 | 690 B | 897 B | Fast | FIPS 206 draft | Post-quantum, compact | Complex, side-channel risk |
| SLH-DSA-128s | 7856 B | 32 B | Slow | FIPS 205 | Post-quantum, conservative | Very slow to sign, large sigs |

Ed25519 is the best pure-classical choice. The remaining question is whether v1.0 should ship with post-quantum support. The answer is no, because:

1. No PQ signature algorithm has a standard library in Go, Node.js, or Python as of 2026.
2. NIST FIPS 204 (ML-DSA) was finalized in 2024 but implementations remain sparse and vary in conformance.
3. ChangeSpec events have a short useful lifetime (CVE advisories stop mattering within months, legal/compliance events within years). The harvest-now-decrypt-later threat model for signatures is less relevant than for long-lived data (signatures cannot be "decrypted" to reveal content because signatures do not encrypt content).

### Recommendation

- Keep Ed25519 as the algorithm for v1.0.
- Add an `alg` field already present in the signature block, but widen its set of acceptable values in the spec text to include `"ed25519"` only in v1.0 while reserving future values `"ed25519+ml-dsa-44"` (hybrid), `"ml-dsa-44"`, `"ml-dsa-65"`, `"slh-dsa-sha2-128s"`.
- Document the post-quantum migration plan in `v2-security-roadmap.md`.

### Required implementation rigor

The spec must require strict Ed25519 verification. RFC 8032 allows two valid verification equations: the cofactored and cofactor-free variants. Implementations disagreeing on which signatures are valid is a real interoperability hazard ("Taming the Many EdDSAs", Chalkias et al. 2020). The spec MUST:

1. Require the strict verification mode: reject malleable signatures where the scalar `S >= L` (the subgroup order).
2. Require rejection of small-order and low-order public keys.
3. Require rejection of non-canonical point encodings.
4. Specify whether the "cofactored" or "cofactor-less" equation is used (recommend cofactored, matching Sodium and most modern libraries).

Python's `cryptography.hazmat.primitives.asymmetric.ed25519` and Go's `ed25519consensus` package implement strict mode. Node's `crypto.verify` for ed25519 uses the OpenSSL default which does some but not all of these checks. The spec must require implementations to either use strict libraries or apply the checks themselves.

---

## What is being signed?

### Current spec

Section 7.3 describes signature input construction:

```
1. For each field name in signed_fields, in the order listed:
   a. Append the field name as UTF-8 bytes
   b. Append a newline character (\n)
   c. Append the field value, serialized as its JSON value
      (string fields without outer quotes, numbers as decimal,
       booleans as true/false)
   d. Append a newline character (\n)
2. Sign the resulting byte string with Ed25519.
```

### Problems with this approach

**Problem 1: Not a real canonical form.** The prose "serialized as its JSON value" is not a specification. What about:

- Strings containing `\n`? The field delimiter is `\n`. An attacker crafts a summary containing `\nvendor_id\nstripe\n...` and the signature input parses as having additional fields.
- Strings with Unicode escape sequences? `\u0041` and `A` are equivalent JSON but different bytes.
- Numbers: `1.0`, `1`, `1e0`, `1.00`, `10e-1` are all equivalent JSON but different decimal representations.
- Arrays: `["a","b"]` vs `[ "a" , "b" ]` vs `["a","b",]` (invalid but some parsers accept).
- Objects (for ext fields): key order, whitespace, Unicode escapes all vary.
- null: should it be signed as the string `null`, as empty, or as something else?
- Absent fields: if a field is in `signed_fields` but missing from the event, what is signed?

**Problem 2: Delimiter injection.** Field names are fixed but field values come from producer-controlled content. An attacker who controls `summary` can embed `\nvendor_id\nfake-vendor\n...` creating a signature input that looks like two signed events concatenated. If a verifier implementation is also permissive, the attacker can shift field boundaries.

**Problem 3: signed_fields not self-signed.** The `signed_fields` array itself is inside the `signature` block and is not part of the signature input. An intermediary can modify `signed_fields` to remove entries, forcing the verifier to compute a signature input over a smaller set, and the intermediary can provide a signature that matches. The intermediary needs a producer signature over some subset that matches the new reduced set - this is usually doable because the producer signed a larger set that includes the reduced one.

**Problem 4: No domain separation.** A raw concatenation of field names and values is indistinguishable from arbitrary attacker-chosen content. If the producer ever uses the same Ed25519 key for another protocol (DNSSEC signatures, SSH signatures, JWTs, document signatures), an attacker can cross-protocol substitute signatures.

**Problem 5: No inclusion of `alg` or `key_id`.** These are in the signature block and identify how to verify, but a signature-stripping attack can drop the `signature` block entirely and fall back to "no signature" acceptance. A defense-in-depth approach includes the algorithm identifier and key identifier in the signed input so that cross-algorithm confusion is prevented.

**Problem 6: Not compatible with existing standards.** JWS (RFC 7515), JAdES (ETSI), COSE (RFC 9052), and DSSE (in-toto Dead Simple Signing Envelope) all solve these problems. Defining a bespoke scheme when JWS-compact over a JCS canonical form would work is gratuitous.

### Recommendation

**Option A: Use JCS + typed envelope (MOST RECOMMENDED for v1.0).**

Replace Section 7.3 with:

> The signature input is the concatenation of:
>
> 1. The 16-byte ASCII domain separator `ChangeSpec-Sig-1\n` (or a similar fixed label).
> 2. The JCS (RFC 8785) canonicalization of a JSON object containing exactly these members:
>    - `alg`: the signature algorithm from the signature block.
>    - `key_id`: the key ID from the signature block.
>    - `vendor_id`: the event's `vendor_id`.
>    - `signed_fields`: the array from the signature block.
>    - `payload`: a JSON object containing exactly the field name/value pairs for each field listed in `signed_fields`, using the event's JSON-parsed value for each.
>
> Producers MUST ensure `signed_fields` includes at minimum every required event field and every field from the following set that is present: `cve_id`, `cvss_score`, `cvss_vector`, `fixed_in_version`, `effective_date`, `sunset_date`, `action_required`, `migration_url`, `source_url`, `affected_versions`.

JCS is a published IETF standard for JSON canonicalization (RFC 8785). It defines canonical Unicode normalization (no normalization; producers and consumers agree on byte-for-byte equivalence), canonical number formatting (IEEE-754 round-trip), and canonical object key ordering (UTF-16 code point order). JCS implementations exist in Go, Python, Node.js, Rust, and Java.

This approach:

- Eliminates ambiguity: JCS is byte-exact.
- Eliminates delimiter injection: the envelope is JSON, and string values are properly JSON-escaped.
- Includes `alg`, `key_id`, `vendor_id`, and `signed_fields` in the signed input, preventing stripping.
- Provides a domain separator.
- Works with any JSON data type, including nested objects and arrays in extension fields.

**Option B: Use JWS Compact serialization.**

Replace the custom signature block with a JWS Compact JWT string:

```
eyJhbGciOiJFZERTQSIsImtpZCI6InN0cmlwZS0yMDI2LTAxIiwidHlwIjoiYXBwbGljYXRpb24vdm5kLmNoYW5nZXNwZWMrano...
```

Fields:
- `alg`: `EdDSA` with `crv=Ed25519`.
- `typ`: `application/vnd.changespec+jwt`.
- `cty`: `application/vnd.changespec+json`.
- Payload: the JCS-canonicalized ChangeSpec event.

Pros:
- Well-understood standard with 10+ years of battle-testing.
- Libraries in every language (`jose` in Python/Node, `go-jose` in Go).
- Built-in domain separation via `typ`.
- Supports multiple signatures (JWS JSON Serialization) for cosigning.

Cons:
- The overall ChangeSpec event is now inside a JWT payload, which some consumers find unwieldy.
- The `alg=none` algorithm in JWS is famously dangerous; conforming implementations MUST explicitly enforce `alg=EdDSA`.

**Option C: Use DSSE (Dead Simple Signing Envelope).**

DSSE (in-toto) is designed exactly for this kind of envelope signing:

```json
{
  "payload": "<base64 of ChangeSpec JSON>",
  "payloadType": "application/vnd.changespec+json",
  "signatures": [
    {
      "keyid": "stripe-2026-01",
      "sig": "<base64 signature>"
    }
  ]
}
```

The signed bytes are `DSSEv1 <PAYLOAD_TYPE_LEN> <PAYLOAD_TYPE> <PAYLOAD_LEN> <PAYLOAD>` (with spaces as delimiters).

Pros:
- Minimal, purpose-built, explicitly designed to avoid the attacks described above.
- Domain separation via the `DSSEv1` prefix and `payloadType`.
- Multiple signatures supported.
- Used by Sigstore, in-toto, and the software supply-chain community.

Cons:
- Wraps the event in base64, doubling the perceived complexity for human readers.
- Less familiar to web developers than JWS.

### Recommendation summary

**For v1.0: adopt Option A (JCS + typed envelope) for minimum disruption to the existing spec structure.** The existing signature block stays in place; only the signature input construction is replaced.

If the spec authors are willing to accept a larger structural change, **Option C (DSSE) is the best long-term choice** because it is designed for this use case, supports multiple signatures (cosigning for trust bootstrap), and aligns with Sigstore infrastructure that ChangeSpec will likely want to integrate with.

Option B (JWS) is a middle ground but requires more care to avoid JWS gotchas (alg=none, key confusion, nested JWT attacks).

---

## Domain Separation

### Current spec

None. The signature input is raw concatenation with no fixed prefix.

### Recommendation

Every signature input MUST begin with an unambiguous domain separator. At minimum:

```
ChangeSpec-Sig-1\n
```

(exact ASCII, 16 bytes including the trailing newline.)

If Option A is adopted, include this separator as the first bytes before the JCS output. If Option C is adopted, DSSE's `DSSEv1` prefix plus `payloadType: application/vnd.changespec+json` serves the same purpose.

---

## Key Identification

### Current spec

`key_id` is a string, Section 7.2, described as "Identifies the signing key. Consumers use this to fetch the vendor's public key from the key registry."

### Issues

1. No format rules for `key_id`. The example `"stripe-2026-01"` is sensible but not enforced. An attacker can use `key_id: "../../etc/passwd"` to test path-traversal in consumer implementations that do naive lookups.
2. No binding between `key_id` and the claimed `vendor_id`. A malicious event with `vendor_id: "stripe"` and `key_id: "attacker-2026-01"` could verify if the consumer looks up `key_id` globally rather than within the vendor's namespace.
3. No mechanism for fingerprint-based key IDs. A fingerprint (hash of the public key) is self-authenticating: the key ID cannot point to the wrong key. A mnemonic ID like `"stripe-2026-01"` requires a trusted registry mapping.

### Recommendations

1. Constrain `key_id` format by schema: `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$`. No dots, no slashes, no colons. This prevents path traversal and namespacing attacks.
2. Require consumer-side key lookup to be scoped by `vendor_id`. The key lookup is `(vendor_id, key_id) -> public_key`, not `key_id -> public_key`.
3. Define an optional `key_fingerprint` field in the signature block. When present, it is the SHA-256 fingerprint of the public key (base64url-encoded, 43 characters). Consumers that have a pinned fingerprint verify both the `key_id` lookup and the fingerprint match.
4. Mandate that `vendor_id` and `key_id` be in the signed input (already covered by the canonicalization recommendation).

---

## Compatibility with Existing Standards

### JWS (RFC 7515)

Compatible if Option B is adopted. Not compatible with the current bespoke scheme.

### COSE (RFC 9052)

Compatible if the event is wrapped in a CBOR encoding, which is not what ChangeSpec does. COSE would be a natural choice for a binary ecosystem; since ChangeSpec is JSON-first, JWS is a closer fit.

### DSSE (in-toto)

Compatible if Option C is adopted. DSSE is purpose-built for this kind of envelope signing.

### Sigstore

Sigstore ecosystem integrates most cleanly with DSSE or with JWS. The current bespoke scheme would require a custom Sigstore verifier.

### Standard Webhooks

Orthogonal. Standard Webhooks signs the delivery channel (HTTP transport) with HMAC. ChangeSpec signatures are end-to-end. Both can coexist.

### CloudEvents

CloudEvents has no built-in signature. CloudEvents events can carry a ChangeSpec event in `data` and inherit whatever signature is embedded there.

### Recommendation

Adopt DSSE for v2.0 regardless. For v1.0, JCS+envelope (Option A) is the minimum fix. Document DSSE migration path.

---

## Quantum Readiness

### Current spec

Ed25519 only. Not post-quantum.

### Assessment

Ed25519 provides ~128-bit classical security. A sufficiently capable quantum computer running Shor's algorithm can recover a private key from a public key in polynomial time. Current estimates place "cryptographically relevant quantum computers" 10-20 years away, but the field is moving fast and harvest-now-decrypt-later is a real threat for long-lived signatures.

For ChangeSpec, the threat is not harvest-and-decrypt (signatures are not encryption) but forgery. An attacker with a quantum computer in 2040 who captures a public key today can forge signatures that look retroactively valid. This matters most for events with legal or compliance implications that remain relevant over long time horizons.

### Recommendations

**v1.0:** No change. Ed25519 is fine.

**v1.1 (2027):** Define a hybrid signature option. Two signatures in the `signature` block, one Ed25519 and one ML-DSA-44 (NIST FIPS 204). Consumers verify both; if either fails, the event is rejected. This provides classical-and-post-quantum security during the migration period. Producers opt in.

**v2.0 (2028-2030 depending on PQ library maturity):** Require hybrid or pure post-quantum. Deprecate Ed25519-only signatures with a 12-month sunset.

### Migration mechanism

The current `signature.alg` field accommodates algorithm migration. Add to v1.1:

```json
"signature": {
  "alg": "ed25519",
  "signatures": [
    {
      "alg": "ed25519",
      "value": "..."
    },
    {
      "alg": "ml-dsa-44",
      "value": "..."
    }
  ],
  "key_id": "stripe-2027-pq",
  "signed_fields": [...]
}
```

Where `alg` on the outer block indicates the primary (for backward compatibility) and `signatures` is an array of per-algorithm signatures. Consumers select based on policy (accept any, require all, require specific).

---

## Recommended Revisions to Section 7

### Section 7.1 - Why Ed25519

Keep current text. Add a paragraph about strict-mode verification and reference "Taming the Many EdDSAs". Add a note that Ed25519 is the v1.0 algorithm and that hybrid post-quantum signatures are planned for v1.1.

### Section 7.2 - Signature Object

Add to the signature block:

- `key_fingerprint` (OPTIONAL): SHA-256 fingerprint of the public key, base64url-encoded.
- Constrain `key_id` to pattern `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$`.

### Section 7.3 - Signature Input Construction

Replace entire section with Option A specification (JCS + typed envelope). Reproduced here for completeness:

> The signature input is the concatenation of:
>
> 1. The 16-byte ASCII domain separator `ChangeSpec-Sig-1\n`.
> 2. The JCS (RFC 8785) canonicalization of a JSON object containing exactly:
>    - `alg`: the signature block's `alg` value.
>    - `key_id`: the signature block's `key_id` value.
>    - `vendor_id`: the event's `vendor_id` value.
>    - `signed_fields`: the signature block's `signed_fields` array.
>    - `payload`: a JSON object containing field name/value pairs for each field listed in `signed_fields`, using the event's parsed JSON value for each.
>
> The `signed_fields` array MUST include at minimum every field in this set (where present in the event):
>
> - All required fields: `specversion`, `id`, `vendor_id`, `category`, `severity`, `title`, `summary`, `published_at`, `source_type`.
> - All security-critical fields: `cve_id`, `cvss_score`, `cvss_vector`, `fixed_in_version`, `action_required`.
> - All time-sensitive fields: `effective_date`, `sunset_date`.
> - All URL fields: `source_url`, `migration_url`.
> - `affected_versions`.
>
> Consumers MUST reject events whose `signed_fields` omits any field in this minimum set that is present in the event.

### Section 7.4 - Key Distribution

Expand with:

- `revoked_keys` array in the key document.
- Strict cache headers (`max-age=3600, must-revalidate`).
- ETag + conditional requests.
- HSTS preload required.
- Key lookup MUST be scoped by `vendor_id`.
- Must cover trust bootstrap (see `trust-bootstrap.md`).

### Section 7.5 - Verification Steps

Expand with:

1. Check that the event's `source_type` is `publisher_verified`.
2. Retrieve the public key for `(vendor_id, key_id)` from the key registry (scoped lookup).
3. Verify the key is not in the `revoked_keys` list.
4. Verify `now` is within the key's `valid_from` / `valid_until` range (allow 5 minutes of clock skew).
5. Verify `published_at` is within the acceptable freshness window (default 90 days past, 5 minutes future).
6. Verify `signed_fields` includes all fields required by Section 7.3's minimum set.
7. Construct the signature input per Section 7.3.
8. Verify the Ed25519 signature using strict mode.
9. Reject the event if any step fails.

---

## Summary

Ed25519 is the right algorithm. The spec's use of it has four significant problems:

1. Canonicalization is under-specified.
2. `signed_fields` is attacker-controlled without constraints.
3. No domain separation.
4. Key distribution does not bind keys to vendor identity cryptographically.

All four are fixable with the revisions above. None require changing the algorithm. The JCS + typed envelope approach (Option A) is the minimum change that addresses all four issues and keeps the spec's existing structure.

The one deferred decision is post-quantum readiness, which is correctly left to v1.1. The spec should document the migration plan publicly to give producers time to prepare.

With these revisions, the signature design is appropriate for a standards-track specification. Without them, it is a security liability that every implementation will have to work around or will get wrong.
