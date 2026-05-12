# Security Considerations

This section is intended to be integrated as an expanded Section 12 of the ChangeSpec specification. It follows the style and conventions of RFC Security Considerations sections (see RFC 9457 Section 5, RFC 7519 Section 11, RFC 8017 Section 9).

---

## 12. Security Considerations

ChangeSpec events flow from producers (vendors, package maintainers, automated crawlers, community submitters) to consumers (developers, automated agents, compliance systems, CI/CD pipelines). The information carried in a ChangeSpec event can drive automated decisions including software updates, security patches, legal and regulatory workflows, and policy enforcement. A forged, tampered, or replayed event can therefore cause significant harm. This section describes the threats this specification considers, the mitigations the specification provides, and the responsibilities of producers, consumers, and intermediaries.

Implementers MUST read this section in full. Deployers MUST understand which threats are in scope for the mitigations this specification provides and which threats must be addressed at a higher layer.

### 12.1 Threat Model Summary

The threat model assumes:

- The network between producer and consumer may be under full active adversary control. An intermediary may drop, modify, reorder, delay, or replay events.
- The consumer trusts the producer's public key only if it has been bound to the producer's identity through a secure out-of-band mechanism.
- The consumer does not trust any intermediary to modify event content.
- Compromise of an individual consumer does not affect other consumers.
- Compromise of a producer's private signing key is detectable by the producer and is communicated via key revocation (Section 12.6).

The threat model does NOT assume:

- That every event is signed. Signatures are OPTIONAL and only defined for `source_type: publisher_verified` events.
- That the transport layer (TLS, webhook delivery, queue) provides end-to-end authenticity.
- That consumers perform automated actions safely. Agent safety is out of scope for this specification; guidance is given in Section 12.13.

### 12.2 Event Authenticity

An event's authenticity comprises origin authentication (the claimed producer actually issued the event) and content integrity (the event has not been modified since issuance). ChangeSpec provides cryptographic authenticity only for `source_type: publisher_verified` events that carry a `signature` object conforming to Section 7.

Consumers MUST NOT treat unsigned events as authentic regardless of their `source_type` value. A `source_type: publisher_verified` event without a valid `signature` carries the same trust level as a `source_type: crawled` event.

Consumers MUST verify signatures for untrusted transports. Consumers that receive events through a trusted platform that has performed verification MAY defer to the platform's verification result, provided the platform's identity and verification behaviour is established by policy.

### 12.3 Signature Input Canonicalization

The signature input construction in Section 7.3 MUST be followed exactly. Implementations that deviate will produce signatures incompatible with other implementations and will create a risk of semantic confusion: a signature valid under one canonicalization may authenticate a different semantic event under another canonicalization.

The signature input is constructed over a specific subset of fields enumerated in the `signed_fields` array. The following rules apply:

1. The `signed_fields` array MUST contain at minimum every required event field (see Section 1.1), the `signature.alg` and `signature.key_id` values, and every field from the following set that is present in the event: `cve_id`, `cvss_score`, `cvss_vector`, `fixed_in_version`, `effective_date`, `sunset_date`, `action_required`, `migration_hint`, `migration_url`, `source_url`, `affected_versions`.
2. The `signed_fields` array itself MUST be signed. Its serialization for signature input is the JSON array form produced by JCS (RFC 8785) with the array name `signed_fields` prepended as if it were a field.
3. The signature input MUST begin with the domain separator `ChangeSpec-Signature-1.0\n` (UTF-8 bytes, terminated by a single LF character). This prevents cross-protocol signature reuse.
4. Field values MUST be serialized using JCS (RFC 8785) applied to the JSON value of each field.
5. The signature algorithm and verification MUST both use the strict Ed25519 mode described in Section 12.4.

Consumers MUST reject events whose `signed_fields` array omits any field required by rule 1. Consumers MUST reject events where the reconstructed signature input does not verify against the producer's public key.

Implementation note: rule 1 protects against the field-stripping attack where an intermediary removes fields from a signed event without breaking the signature, because the removed field would be required to be in `signed_fields`, and its absence from `signed_fields` is itself a rejection reason.

### 12.4 Ed25519 Strict Verification

Signature verification MUST use Ed25519 as defined in RFC 8032. Implementations MUST:

- Reject signatures whose scalar component S is not in the range `[0, ell)` where `ell` is the order of the Ed25519 base point.
- Reject non-canonical encodings of the point R.
- Reject signatures that use small-order or low-order points.
- Use the library's strict verification mode where available (for example, `ed25519consensus` in Go, `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey.verify` in Python, `crypto.verify` with `algorithm: 'ed25519'` in Node.js 18+).

These requirements eliminate the signature malleability and equivalent-signature issues described in the "Taming the Many EdDSAs" analysis (Chalkias, Garillot, Kondi 2020).

### 12.5 Key Distribution and Trust Bootstrap

Section 7.4 specifies a well-known URL for publishing vendor public keys. This mechanism alone is not sufficient to establish trust. Consumers MUST additionally apply at least one of the following:

1. **Key pinning.** The consumer obtains the producer's public key through an out-of-band channel (direct vendor relationship, vendor documentation, verified press release) and stores the key fingerprint. The consumer compares subsequent key fetches against the pinned fingerprint and alerts on mismatch.
2. **Key transparency log.** The producer publishes its key rotations to an append-only transparency log (see `trust-bootstrap.md` for the proposed v1.1 mechanism). Consumers verify that the served key appears in the log at a position consistent with the log's Merkle tree.
3. **Multi-party cosigning.** The producer's key is co-signed by a quorum of independent cosigners. Consumers verify that at least a policy-defined quorum of cosigners have attested to the key.

At launch, key pinning is the only mechanism formally available. Consumers that cannot pin MUST NOT treat signed events as more trustworthy than unsigned events from the same producer. This is a known gap; see `v2-security-roadmap.md`.

### 12.6 Key Revocation

A producer that has lost control of a private signing key MUST:

1. Remove the compromised key from the well-known keys document.
2. Add the compromised key to a `revoked_keys` array in the well-known document with fields `key_id`, `revoked_at`, and `reason`.
3. Issue new keys and resume signing with the new keys.
4. Publicly announce the revocation through the same channels used to announce initial key distribution.

Consumers MUST:

1. Fetch the well-known document no less frequently than once per hour (subject to caching rules in Section 12.8).
2. Reject any event whose `signature.key_id` appears in the `revoked_keys` list.
3. Reject any event whose `signature.key_id` matches a key whose `valid_until` has passed.
4. When a key not in the well-known document is referenced, reject the event.

Keys MUST have a `valid_until` no more than one year from `valid_from`. Producers SHOULD rotate keys annually.

### 12.7 Replay, Freshness, and Ordering

The `published_at` field is required on every event and MUST be included in the signed field set (Section 12.3, rule 1). Consumers MUST:

1. Reject events with `published_at` more than the consumer's configured retention window in the past. Recommended default: 90 days.
2. Reject events with `published_at` more than 300 seconds (5 minutes) in the future, accounting for clock skew.
3. Deduplicate events by the tuple `(vendor_id, id)`. When a duplicate `id` is received with a later `published_at`, treat the newer event as an authoritative replacement (Section 1.3 allows producers to re-issue events with the same `id`).

Event ordering between unrelated events is not cryptographically enforced by this specification. Consumers that require total ordering SHOULD obtain events from a single trusted ordered source (for example, a platform API that returns events in `published_at` order with pagination cursors).

### 12.8 Caching of Key Documents

The well-known keys document at `https://{vendor-domain}/.well-known/changespec-keys.json` MUST be served with:

- `Cache-Control: max-age=3600, must-revalidate` (or more restrictive).
- An `ETag` header that changes whenever any key is added, removed, or revoked.
- `X-Content-Type-Options: nosniff`.
- `Strict-Transport-Security: max-age=31536000`.

Consumers MUST NOT cache the keys document for more than one hour. Consumers MUST use conditional requests (If-None-Match) on refresh.

### 12.9 Transport Security

All HTTP endpoints referenced in this specification - well-known keys document, webhook delivery, polling API, event source URLs - MUST use TLS 1.2 or later with strong cipher suites as defined in BCP 195 (RFC 8996 and successors). Consumers MUST reject HTTP responses served without TLS or with weak or unverified certificates.

When a consumer fetches an event, a key document, or a referenced URL, the consumer MUST verify the full certificate chain including revocation status (OCSP stapling or CRL), MUST verify the hostname matches the requested URL, and MUST NOT proceed on any validation failure.

### 12.10 URL Field Handling

The `source_url` and `migration_url` fields are untrusted input. This specification restricts these fields to the `https://` scheme by schema. Consumers that fetch, render, or pass these URLs downstream MUST:

- Reject any URL not beginning with `https://`. This is enforced by schema but consumers MUST NOT rely solely on producer-side validation.
- Reject URLs containing authentication credentials (`https://user:pass@host/`).
- Rate-limit fetches to prevent a single event from triggering SSRF-style traffic patterns.
- Apply egress filtering to prevent fetches to private IP ranges (RFC 1918), localhost, link-local addresses, and the IMDS address ranges.
- When rendering URLs in a user interface, escape them as text and do not automatically follow, preview, or open them.
- When passing URLs to downstream systems that may execute instructions (such as LLM agents), annotate them as untrusted.

### 12.11 Input Size and Parser Safety

Consumers MUST enforce the following limits at parse time, before JSON Schema validation:

- Total event size: 65,536 bytes (64 KiB) or less.
- JSON nesting depth: 32 levels or less.
- Count of `ext:*` fields: 64 or fewer.
- Size per `ext:*` field value (serialized JSON): 4,096 bytes (4 KiB) or less.

Producers MUST NOT emit events exceeding these limits. Consumers MUST reject events exceeding these limits with an explicit error and MUST NOT proceed to schema validation on an over-limit event.

Consumers MUST use JSON parsers configured in strict mode:

- Reject duplicate object keys.
- Reject trailing data after the top-level value.
- Reject comments, trailing commas, and JSON5-like extensions.
- Reject BOMs and other non-JSON byte sequences at the start of the input.

These limits prevent denial of service, parser confusion, and duplicate-key smuggling attacks.

### 12.12 Injection and Rendering

The `title`, `summary`, `migration_hint`, and similar human-readable fields are plain text per Section 1.3. Consumers MUST NOT interpret these fields as Markdown, HTML, shell commands, SQL, or any other executable or structured content. Consumers that render these fields MUST escape output appropriately for the rendering context (HTML escaping for web UIs, shell quoting for CLI output, parameterized queries for database storage).

Consumers that pass event fields to LLM agents or other natural-language processors MUST apply prompt-injection mitigations (delimiter tokens, instructional boilerplate, content-type annotations). ChangeSpec events are not inherently safe input for LLM agents.

### 12.13 Automated Agent Safety

ChangeSpec is designed to support automated consumers including dependency-update agents, security-response agents, and compliance workflows. The specification imposes the following constraints on automated consumers to limit blast radius:

1. An agent MUST NOT take an irreversible automated action on an event whose signature has not been verified.
2. An agent MUST NOT take an irreversible automated action on a `source_type: crawled` event without human review.
3. An agent MUST NOT take an irreversible automated action on a `source_type: community` event under any circumstance.
4. An agent that acts on a `security/critical` event MUST cross-verify against an authoritative CVE source (NVD, OSV, GHSA) before acting.
5. An agent MUST log every event-driven action with the full event payload, verification status, and the agent's decision chain for later audit.
6. An agent SHOULD implement rate limiting on event-driven actions, such that no single event or burst of events can cause more than a policy-defined number of actions in a bounded time window.

These are MUST and SHOULD requirements on conforming automated consumers. A consumer that cannot comply with these requirements MUST NOT claim ChangeSpec agent conformance.

### 12.14 Cross-Site Request Forgery and Origin Validation

Webhook deliveries (Section 9.1) are subject to CSRF-like attacks where a third party sends forged webhook events to a consumer's ingest endpoint. Consumers MUST:

- Implement webhook delivery authentication (HMAC via Standard Webhooks is recommended at the transport layer).
- Verify the `signature` field for end-to-end event authenticity where applicable.
- Treat webhook ingest endpoints as untrusted even when webhook delivery authentication passes, because webhook authentication establishes the delivery channel, not the event origin.

### 12.15 Extension Field Security

Extension fields (`ext:*`) carry content defined by the extension's namespace owner. Consumers that process extension fields MUST:

- Validate extension values against the extension's published schema before consuming.
- Reject unknown extension namespaces or treat them as opaque bags that cannot drive automated decisions.
- Apply the same sanitization rules to extension string values as to core string values.

Extension fields MUST NOT be used to carry executable content, code, credentials, personal data requiring special handling, or content that requires special legal treatment (for example, CSAM, export-controlled information, data subject to healthcare privacy rules).

### 12.16 Confidence Score Trust Boundary

The `confidence_score` field is a producer self-assessment. Consumers MUST NOT use `confidence_score` as the sole basis for trust decisions. A `confidence_score: 1.0` on an unsigned event is no more trustworthy than a `confidence_score: 0.3` on the same event. Confidence score is a classification-quality signal, not an authenticity signal.

### 12.17 Denial of Service Resistance

Consumers exposed to untrusted event sources MUST:

- Apply per-source rate limiting.
- Apply the payload size and parser safety limits in Section 12.11.
- Use bounded-memory schema validators. Reference implementations provided with this specification are configured to be bounded-memory.
- Monitor validation failure rates and alert on spikes.

Producers exposed to public submission (for example, `community` events) MUST:

- Rate-limit submissions per source IP, per submitting account, and globally.
- Implement anti-abuse moderation before events are made available to consumers.
- Provide a mechanism to retract abusive events from the feed.

### 12.18 Supply Chain

Reference implementations of this specification are themselves a supply-chain dependency for consumers. The reference implementations SHOULD be published with:

- SLSA level 3 build provenance (https://slsa.dev).
- Software bill of materials (SPDX or CycloneDX).
- Signed release artifacts (Sigstore keyless signing recommended).
- Pinned dependencies as enforced by each language's lock file.

Consumers SHOULD verify the provenance and signatures of any reference-implementation dependency they pull in.

### 12.19 Logging and Observability

Consumers MUST log:

- Every received event with its `id`, `vendor_id`, `source_type`, and verification status.
- Every validation failure with the failure reason.
- Every signature verification failure with the failing field.

Consumers MUST NOT log:

- Raw secret material (signing keys, webhook HMAC secrets).
- Full event bodies if the body contains credentials (extension fields are a possible source).

Logs MUST be protected from tampering by the party who issued the log entry.

### 12.20 Known Limitations of This Specification

The following known limitations exist in ChangeSpec 1.0 and are planned for future specification versions. Consumers MUST be aware of these limitations:

- No transparency log. Current key distribution relies on TLS trust and key pinning. A signed key-transparency log is planned for v1.1.
- No signer-authorization chain. A ChangeSpec key identifies a producer, but the binding between a vendor identifier and a key relies on the vendor registry. A cryptographic signer-authorization mechanism is planned for v1.1.
- No event retraction. An event cannot be cryptographically withdrawn. A `retraction` mechanism is planned for v1.1.
- No producer sequence numbers. Ordering between events from the same producer relies on `published_at` timestamps rather than signed sequence numbers. Signed sequence numbers are planned for v1.1.
- Post-quantum readiness. Ed25519 is not post-quantum secure. A hybrid signature scheme is planned for v2.0.

Deployers relying on these features MUST delay production deployment until v1.1 or apply compensating controls at the consumer side.

---

## Implementer Responsibilities Checklist

Producers MUST:

- Generate events that validate against the JSON Schema.
- Sign `publisher_verified` events using Ed25519 per Section 7 and Section 12.3.
- Include `published_at`, `vendor_id`, and all required fields in the signed field set.
- Rotate signing keys at least annually.
- Revoke compromised keys immediately upon discovery.
- Serve the well-known keys document with strict cache and security headers (Section 12.8).

Consumers MUST:

- Validate every received event against the JSON Schema before processing.
- Verify signatures on `publisher_verified` events received from untrusted transports.
- Apply the input limits in Section 12.11.
- Reject events that fail any security check with an explicit error.
- Deduplicate by `(vendor_id, id)` and enforce freshness per Section 12.7.
- Follow the automated agent constraints in Section 12.13 if operating as an agent.

Intermediaries (aggregators, mirrors, platforms) MUST:

- Not modify event content. Intermediaries MAY add transport-layer headers but MUST NOT alter the event payload including its `signature`.
- Deliver events verbatim.
- Not re-sign events with intermediary keys claiming to represent producers.
- Pass through producer signatures unchanged.

---

## Normative references

- RFC 2119: Key words for use in RFCs to Indicate Requirement Levels
- RFC 7519: JSON Web Token (JWT)
- RFC 8017: PKCS #1: RSA Cryptography Specifications Version 2.2
- RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA)
- RFC 8259: The JavaScript Object Notation (JSON) Data Interchange Format
- RFC 8785: JSON Canonicalization Scheme (JCS)
- RFC 8996: Deprecating TLS 1.0 and TLS 1.1
- RFC 9110: HTTP Semantics
- RFC 9457: Problem Details for HTTP APIs
- BCP 195: Recommendations for Secure Use of TLS and DTLS
- SLSA v1.0: Supply-chain Levels for Software Artifacts (https://slsa.dev)
- NIST SP 800-57: Recommendation for Key Management

## Informative references

- Chalkias, Garillot, Kondi. "Taming the Many EdDSAs." IACR ePrint 2020/1244.
- Certificate Transparency: RFC 6962 and RFC 9162.
- Sigstore: https://www.sigstore.dev
