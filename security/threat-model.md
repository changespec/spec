# ChangeSpec 1.0 Threat Model

**Status:** Pre-launch security review
**Reviewer:** Security engineering
**Date:** 2026-04-16
**Spec version reviewed:** 1.0 (commit as of review date)

---

## Executive Summary

This document is the adversarial threat model for ChangeSpec 1.0 prior to public launch as an open standard for software change communication. The spec is expected to be consumed by autonomous agents, CI/CD pipelines, dependency management tools, GRC workflows, and human operators across tens of thousands of enterprises. A flaw in the spec becomes a flaw in every conforming implementation.

### Showstoppers (must fix before v1.0 launch)

The following issues are blocking. Shipping v1.0 with them present will set a damaging precedent that will be difficult to reverse once implementations are in the wild.

1. **SIG-01: Canonicalization is under-specified.** Section 7.3 of spec.md describes signature input construction in prose but does not define canonical serialization for arrays, objects, strings with Unicode escapes, numbers with multiple decimal representations (`1.0` vs `1` vs `1e0`), or null values. Two conforming implementations signing the same event will produce different byte strings and different signatures. This breaks interoperability immediately and silently. **Fix:** adopt JCS (RFC 8785) over the signed subset, or replace the ad-hoc scheme with a documented canonical form (see `signature-design-review.md`).
2. **SIG-02: `signed_fields` is attacker-controlled and not authenticated.** The list of fields covered by the signature is placed inside the `signature` block itself. An attacker who intercepts and modifies a signed event can remove entries from `signed_fields`, regenerate the signature input, and produce a verifying event that omits the fields they wanted to strip. Combined with the fact that `signed_fields` has no required minimum content, this is a complete signature bypass for any fields the attacker wants to manipulate. **Fix:** either require a fixed minimum set of signed fields by spec (including `signed_fields` itself, `vendor_id`, `key_id`, `alg`, and all security-relevant fields), or commit the `signed_fields` list into the signature input.
3. **SIG-03: No domain separation.** The signature input is a raw concatenation of field names and values. The same Ed25519 key used to sign ChangeSpec events can be tricked into signing cross-protocol messages (DNS TXT records, JWT tokens, SSH challenges) that happen to have the same byte layout. **Fix:** prepend a domain separator such as `ChangeSpec-1.0\x00` or use a signing scheme with built-in domain separation (Ed25519ctx, or a JWS/COSE envelope with `typ`/`cty`).
4. **SIG-04: No replay protection in the signature layer.** `published_at` is not required to be in `signed_fields`. Even when it is, there is no freshness check, no signed expiry, no signed nonce. An attacker who captures a signed event can re-publish it indefinitely, or re-order events to trick consumers. **Fix:** require `published_at` in the signed field set and require consumers to enforce a freshness window.
5. **SIG-05: No signer-authorization binding.** A vendor publishes keys at `https://{vendor-domain}/.well-known/changespec-keys.json` but nothing in the event cryptographically binds `vendor_id` to the key that signed it. An attacker who compromises any single vendor key (or runs their own vendor with a legitimate key) can sign events claiming to be from any other vendor by careful choice of `signed_fields`. **Fix:** require `vendor_id` and `key_id` in the signed field set, and require the key resolver to check that the key is authorized to sign for the claimed `vendor_id` (see `trust-bootstrap.md`).
6. **SIG-06: Trust bootstrap is hand-wavy.** Section 7.4 says "vendors publish keys at a well-known URL" but does not specify key pinning, key transparency, revocation discovery, or what to do on TLS failure. A passive network attacker who controls DNS for a vendor domain (or who takes over an abandoned subdomain) can issue keys that pass all current checks. **Fix:** specify a trust-bootstrap scheme before the signature design can be shipped (see `trust-bootstrap.md`).
7. **GEN-01: Schema `additionalProperties: false` combined with `patternProperties: ^ext:` interacts with ext fields in a way that is implementation-dependent pre-2019-09 JSON Schema.** The Go reference schema omits pattern-based extension support entirely, which means the Go and Python/TS reference implementations accept different events. **Fix:** unify reference schemas and make extension field semantics explicit and unambiguous.
8. **GEN-02: URL scheme is not restricted.** `source_url` and `migration_url` are validated only as `format: uri`. This accepts `javascript:`, `data:`, `file:`, `gopher:`, `ftp:`, and other schemes. A malicious event delivered to a consumer that renders these URLs in a UI or fetches them programmatically yields XSS, SSRF, or local file disclosure. The spec's security considerations say HTTPS is RECOMMENDED; it should be REQUIRED. **Fix:** restrict URL fields to `https:` by schema.

The remaining findings are serious but not launch-blocking. They are documented in the threat inventory below and many are addressed by the integrated `SECURITY.md` and `conformance-security-tests.md` deliverables.

### Risk summary

| Category | Critical | High | Medium | Low |
|---|---|---|---|---|
| Authenticity (signatures, identity) | 6 | 3 | 2 | 1 |
| Input handling (parsing, validation) | 1 | 4 | 5 | 2 |
| Transport and distribution | 1 | 2 | 4 | 3 |
| Agent and downstream impact | 2 | 3 | 2 | 1 |
| Supply chain | 0 | 2 | 3 | 2 |

---

## Threat Inventory

Each threat includes attacker profile, attack surface, impact, current spec mitigation (if any), residual risk after mitigation, and recommended action.

---

### T-01: Vendor impersonation via unverified `vendor_id` (Critical)

**Attacker profile.** Any internet-connected adversary with the ability to publish events to a ChangeSpec aggregator, webhook endpoint, or public feed. No special privileges required.

**Attack surface.** `vendor_id` is a free-form string. Any actor can set `vendor_id: "stripe"` or `vendor_id: "anthropic"` on an event they publish. The `source_type: publisher_verified` value is also self-asserted. Without signature verification a consumer has no way to tell a real Stripe event from a forgery.

**Impact.** An attacker publishes a fake `api_breaking` event for `stripe` claiming that `PaymentIntent.confirm()` has a new required parameter, causing thousands of downstream builds to fail. Or publishes a fake `security`/`critical` event for a popular npm package claiming a fictitious CVE, driving mass panicked patching to attacker-controlled repositories referenced via `migration_url`.

**Current spec mitigation.** `source_type: publisher_verified` is paired with an optional Ed25519 signature. Consumers are advised to verify signatures for untrusted transports.

**Residual risk after mitigation.** High. Signing is optional. Key distribution is under-specified (see T-05, T-06). Many consumers will not verify. Consumers that ingest from an aggregator are trusting the aggregator to verify, which creates a single point of compromise.

**Recommended action.**
- Make signature verification mandatory for any event claiming `source_type: publisher_verified` under the conformance spec (see SIG-05).
- Bind `vendor_id` to a specific key via the trust-bootstrap layer (see `trust-bootstrap.md`).
- Add the conformance test suite `conformance-security-tests.md` to prevent implementations from silently accepting unsigned `publisher_verified` events.

---

### T-02: Signature forgery via ad-hoc canonicalization (Critical)

**Attacker profile.** Active network attacker, malicious aggregator, or attacker with access to a vendor's event generation pipeline.

**Attack surface.** Section 7.3 defines the signature input as concatenation of field name, newline, field value, newline. The definition of "field value" is incomplete:

- Strings: "without outer quotes" - what about JSON escapes inside? Is `"hello\n"` rendered as `hello\n` (two chars), `hello<LF>` (six chars), or literally `hello\n` (seven chars including backslash)?
- Numbers: "as decimal" - is `1.0` signed as `1`, `1.0`, `1.00`, or `1e0`? Is `0.1` signed with full IEEE-754 precision or a specific formatting?
- Arrays: not specified at all. Is `["a","b"]` signed as `ab`, `a,b`, `[a,b]`, or something else?
- Objects: ext fields can be nested objects - entirely unspecified.
- null: unspecified.
- Unicode: normalization not specified. NFC vs NFD produces different bytes.

**Impact.** Two honest implementations produce different signature inputs for the same event and reject each other's signatures. An attacker exploits an implementation that treats strings one way while the verifying implementation treats them another way to produce an event that verifies under one implementation but carries different semantics than the signer intended. This is a complete authenticity bypass across the ecosystem and is silently exploitable.

**Current spec mitigation.** None.

**Residual risk.** Critical.

**Recommended action.** Adopt JSON Canonicalization Scheme (JCS, RFC 8785) for the signed subset, OR adopt a typed-field canonical form with explicit rules, OR switch to JWS Compact / DSSE envelope where canonicalization is solved. See `signature-design-review.md`.

---

### T-03: Signature downgrade and field stripping (Critical)

**Attacker profile.** Active network attacker or malicious intermediate (aggregator, mirror, CDN, webhook relay).

**Attack surface.** An attacker intercepts a signed event with `signed_fields: ["id","vendor_id","category","severity","title","summary","published_at"]`. They modify the event:

- Change `category` from `security` to `informational`
- Change `severity` from `critical` to `low`
- Strip the `cve_id`, `cvss_score`, `cvss_vector`, `action_required`, and `migration_hint` fields
- Leave `signed_fields` unchanged

Because category, severity, and title are unchanged, and those ARE in `signed_fields`, the signature still verifies. But the attacker has hidden the fact that this was a critical CVE. Alternatively, the attacker changes `signed_fields` to `["id","vendor_id"]`, re-signs the trivial input with a key they control, and provides a `key_id` pointing to their own key for a vendor they control.

A more subtle variant: attacker only removes entries from `signed_fields`, does NOT re-sign, and relies on the consumer failing open. This depends on implementation, but any consumer that computes the signature input from `signed_fields` will compute a valid signature for the reduced set if the attacker has re-published a version with matching field values.

**Impact.** Silent suppression of security advisories. Auto-patching agents miss critical CVEs. Compliance workflows miss DPA changes.

**Current spec mitigation.** None. The spec lets producers choose `signed_fields` freely and does not require any minimum set.

**Residual risk.** Critical.

**Recommended action.**
- Define a REQUIRED set of signed fields for each event category (all required fields always, plus category-specific fields like `cve_id`, `fixed_in_version` when present).
- Include `signed_fields` in its own signature input (signed_fields covers itself).
- Reject events on the consumer side whose `signed_fields` does not meet the minimum.

---

### T-04: Event replay (High)

**Attacker profile.** Any party that observes a legitimate signed event, including a passive network observer when TLS is not end-to-end.

**Attack surface.** There is no required `exp`, `iat`, `nbf`, or nonce field in the signature. Even when `published_at` is in `signed_fields`, the spec does not require consumers to check freshness.

**Impact.**
- Replay an old `api_breaking` event months later to cause spurious CI failures.
- Replay an old `security/critical` event for a vulnerability that has since been fixed, causing automated agents to roll back to an older version or apply a patch that has been superseded.
- Replay old `deprecation` events to mask a newer critical event (if the consumer processes events in received order without checking `published_at`).

**Current spec mitigation.** Section 12.4 says "Consumers SHOULD implement idempotency using `id` to prevent processing duplicate deliveries. Events older than the consumer's configured retention window SHOULD be rejected." SHOULD, not MUST. No freshness window is specified.

**Residual risk.** High. Consumers that follow the letter of the spec but not the spirit will be vulnerable.

**Recommended action.**
- Require `published_at` in the minimum signed field set.
- Require consumers to reject events with `published_at` more than a configured window (default 30 days) in the past or more than a short window (default 5 minutes) in the future.
- Consider a signed `expires_at` field in v1.1 to bind the validity window cryptographically.

---

### T-05: Key distribution / trust bootstrap compromise (Critical)

**Attacker profile.** Attacker with temporary control over a vendor's DNS, an expired domain, a subdomain takeover, or a CA that mis-issues a certificate for a vendor domain.

**Attack surface.** Section 7.4: "Vendors publish their Ed25519 public keys at a well-known URL: `https://{vendor-domain}/.well-known/changespec-keys.json`." The only trust anchor is TLS to that URL.

Attack scenarios:
- Vendor lets `stripe-keys.example.com` expire and attacker registers it.
- Vendor has a subdomain takeover (e.g., forgotten `status.vendor.com` CNAME pointing to an abandoned S3 bucket).
- Attacker obtains a domain-validated TLS cert via a BGP attack, DNS cache poisoning, or an email provider compromise.
- Vendor's well-known URL returns a 404 and consumers fall back to "allow unsigned" behavior.

Also: the spec says "The ChangeSpec platform registry also mirrors vendor public keys." The registry is a single centralized trust point. If an attacker compromises the registry, they can silently replace any vendor's keys and every consumer that key-pins against the registry accepts malicious events as authentic.

**Impact.** Complete ecosystem-level authenticity bypass for the affected vendor(s). If the registry is compromised, the entire ecosystem.

**Current spec mitigation.** Weak. The spec mentions key pinning as RECOMMENDED but does not specify how.

**Residual risk.** Critical. This is the signature system's single point of failure.

**Recommended action.** See `trust-bootstrap.md` for a full proposal. Short version: require either a key-transparency log or a multi-party cosigning requirement before an event's signature is considered publisher-verified.

---

### T-06: Key revocation and rotation (High)

**Attacker profile.** Attacker who has stolen a vendor private key, plus the vendor itself learning of the compromise.

**Attack surface.** The key document has `valid_from` and `valid_until` fields but no revocation mechanism. If a key is compromised mid-validity, the only remedy is for the vendor to update the key document, which relies on consumers re-fetching it (cache behavior unspecified) and on consumers not having pinned the compromised key.

**Impact.** An attacker with a stolen key can continue signing events until key `valid_until` expires, even if the vendor publicly announces compromise.

**Current spec mitigation.** None.

**Residual risk.** High.

**Recommended action.**
- Define a revocation list format in the well-known document, e.g. `"revoked_keys": [{"key_id": "stripe-2025-12", "revoked_at": "2026-02-01T00:00:00Z", "reason": "compromised"}]`.
- Require consumers to reject events signed by a revoked key.
- Consumers MUST NOT cache key documents for longer than a defined TTL (recommend 1 hour maximum).
- Require vendors to rotate keys annually with overlap periods to give consumers time to discover new keys.

---

### T-07: Event tampering in transit when not signed (High)

**Attacker profile.** Active network attacker on any segment between producer and consumer.

**Attack surface.** Most events will be `source_type: crawled` or `community`, which the spec does not allow to be signed (Section 7 restricts signing to `publisher_verified`). These events rely entirely on transport security. A compromised webhook, aggregator, or CDN can modify any field.

**Impact.** Same as T-03 but with a wider attacker population because no cryptographic guarantee exists.

**Current spec mitigation.** Section 9.1 points to Standard Webhooks for transport signing. This is delivery-channel authentication, not event-origin authentication.

**Residual risk.** High. The spec does not clearly communicate that non-`publisher_verified` events are fundamentally unauthenticated.

**Recommended action.**
- Spec should be explicit that `crawled` and `community` events carry no origin authenticity guarantee.
- Allow crawler-signed events with a distinct key role (e.g., the aggregator signs with its own key, clearly labeled as "crawler attestation, not vendor attestation").
- Document the trust model clearly so consumers do not conflate "came from the platform" with "authored by the vendor".

---

### T-08: Timing attacks on validation (Low)

**Attacker profile.** Remote attacker with the ability to send many events and measure response time.

**Attack surface.** Naive reference implementations may short-circuit on first validation failure, leaking which field failed. This is generally not exploitable in the ChangeSpec context (the schema is public) but could matter for signature verification in a side-channel context.

**Current spec mitigation.** None specified.

**Residual risk.** Low for schema validation. Medium for signature verification if not done with constant-time libraries - the Go `crypto/ed25519` and Python `cryptography` libraries use constant-time verification. TS `node:crypto` ed25519 is also constant-time. OK.

**Recommended action.**
- Spec should explicitly require constant-time signature comparison (`crypto_sign_verify`-style).
- Do NOT require constant-time schema validation (unnecessary and would slow everyone down).

---

### T-09: Denial of service via large or pathological payloads (High)

**Attacker profile.** Any attacker who can deliver events to a consumer endpoint.

**Attack surface.**

- **Oversized payloads.** Schema caps individual strings (`title` 200, `summary` 2000, etc.) but does not cap total event size. `affected_systems` + `affected_sections` + `tags` + many `ext:*` fields can exceed 500KB per event.
- **Deeply nested extensions.** Extension field values are `any`. An attacker can send `ext:a.b: {a: {b: {c: ...}}}` with 10000 levels of nesting, consuming parser stack.
- **Billion-laughs / array explosion.** JSON doesn't have entity expansion, but a pathological ext field could be a 1M-element array.
- **Pathological regex.** The `vendor_id` pattern `^[a-zA-Z0-9][a-zA-Z0-9._/@:-]*$` is linear time. But the CVE pattern, CVSS pattern, and tag pattern are all safe. No obvious ReDoS.
- **JSON parser nesting.** Go's `encoding/json`, Python's `json`, and Node's `JSON.parse` all have configurable depth limits but the reference implementations do not set them.

**Impact.** Consumer crashes, memory exhaustion, OOM-killed containers, cascading failures in downstream pipelines.

**Current spec mitigation.** None explicit. Individual field length caps help.

**Residual risk.** High.

**Recommended action.**
- Spec MUST set a total event size limit. Recommended: 64 KB.
- Spec MUST set a JSON nesting depth limit. Recommended: 32 levels.
- Spec MUST cap the number of ext:* fields. Recommended: 64.
- Spec MUST cap per-extension-field size. Recommended: 4 KB.
- Reference implementations MUST enforce these limits at parse time, before schema validation.

---

### T-10: Malicious JSON / parser attacks (Medium)

**Attacker profile.** Any attacker who can deliver events.

**Attack surface.**

- **Prototype pollution in TS/JS.** The TS reference uses Zod, which returns a plain object. `extensions["__proto__"]` or `ext:evil.__proto__` would be a property of the extensions map, not Object.prototype, so direct prototype pollution is limited. However, downstream consumers that use `Object.assign(defaults, event)` with an event containing `__proto__`, `constructor`, or `prototype` keys (not starting with `ext:`) could still be affected. The spec's `additionalProperties: false` should reject these, but the TS reference uses `.passthrough()` which does not enforce schema-level additionalProperties. **This is a real bug in the TS reference.**
- **Duplicate keys.** RFC 8259 says behavior is implementation-defined. Go `encoding/json` accepts and takes the last value. Python `json.loads` accepts and takes the last. An attacker can smuggle a signed-looking value past validation and a different value into the application logic if the validation happens on a pre-parsed structure and business logic re-parses.
- **Unicode shenanigans.** Homoglyph attacks on `vendor_id` (Cyrillic `а` vs Latin `a`), right-to-left override characters in `title` and `summary`.

**Impact.** Prototype pollution leads to arbitrary code execution in Node consumers that downstream-merge events. Duplicate-key smuggling bypasses signature verification. Homoglyphs enable vendor impersonation even in signed events (a registered `stripe` vendor vs. an attacker's `stripe` with Cyrillic `e`).

**Current spec mitigation.** Schema rejects unknown top-level fields. Regex patterns on some fields.

**Residual risk.** Medium.

**Recommended action.**
- Spec MUST require duplicate-key rejection at parse time.
- `vendor_id` pattern MUST restrict to ASCII-only (current pattern already does: `^[a-zA-Z0-9][a-zA-Z0-9._/@:-]*$`).
- `title`, `summary`, `migration_hint` MUST be NFC-normalized and MUST reject C0/C1 control characters except `\t` (and not even that in `title`).
- Spec MUST require reference implementations to use strict JSON parsing (reject duplicate keys, reject trailing data, reject comments, reject BOM).

---

### T-11: Malicious URLs (High)

**Attacker profile.** Any event producer.

**Attack surface.** `source_url` and `migration_url` are validated only by `format: uri`. Valid values include:

- `javascript:alert(document.cookie)` - XSS if rendered as a link
- `data:text/html,<script>...</script>` - XSS
- `file:///etc/passwd` - local file disclosure if fetched by consumer
- `http://internal-service:8080/admin` - SSRF against consumer's private network
- `gopher://`, `ftp://`, `ldap://`, `jar://` - various protocol attacks
- Phishing URLs - `https://stripe-security.evil.com/patch.tar.gz`

**Impact.**
- XSS on consumer dashboards that render URLs as anchor tags without sanitization.
- SSRF from consumer services that automatically fetch `migration_url` for analysis (e.g., automated documentation aggregators).
- Phishing: an "autonomous agent" directed by ChangeSpec to fetch a migration guide may download and execute malicious code.
- Credential theft: `migration_url` pointing to `https://attacker.com/login?return=https://github.com` tricks users into entering credentials.

**Current spec mitigation.** Section 12.2 says consumers "MUST use a safelist of permitted URL schemes (HTTPS required, HTTP not recommended)". But the schema does not enforce this and the conformance definition is based on schema validation.

**Residual risk.** High.

**Recommended action.**
- Schema MUST constrain `source_url` and `migration_url` to `^https://`.
- Length cap is already 2048, which is appropriate.
- Conformance tests MUST include rejection of non-HTTPS URLs.
- Spec MUST explicitly warn that agents fetching these URLs are a critical attack surface and must sandbox, sanitize, and rate-limit.

---

### T-12: Extension field abuse (Medium)

**Attacker profile.** Any event producer.

**Attack surface.** Extension fields `ext:*` accept arbitrary JSON values. An attacker can use them to smuggle:

- Very large blobs (mitigated by payload size cap if adopted).
- Executable markdown/HTML that downstream renderers trust because the field is "just an extension".
- Command injection payloads if a consumer shells out using an ext field value (e.g., a consumer that runs `echo {{ ext:internal.ticket_id }}` in a shell template).
- Structured data designed to confuse LLM agents that consume ChangeSpec events (prompt injection).

**Impact.** Injection attacks, prompt injection against LLM agents, data exfiltration.

**Current spec mitigation.** None. The spec says consumers MUST ignore unknown ext fields, but this does not mean consumers will not process ext fields they have registered.

**Residual risk.** Medium. This is more of a consumer hygiene issue than a spec flaw, but the spec should articulate the risk.

**Recommended action.**
- Spec SHOULD limit ext field values to scalars (string, number, boolean, null), short arrays of scalars, and flat objects. Disallow deeply nested objects.
- Cap per-ext-field size (4 KB recommended).
- Cap total ext fields per event (64 recommended).
- Add a Security Considerations subsection specifically for ext fields.
- Extension namespaces SHOULD be registered publicly and reviewed.

---

### T-13: Cache poisoning in distribution (Medium)

**Attacker profile.** Attacker with ability to poison a CDN, HTTP cache, or aggregator cache.

**Attack surface.** Events delivered over HTTP with cacheable responses. Key document fetched from `.well-known/changespec-keys.json` - if cached, stale keys may be served past revocation. Aggregators caching events keyed on event `id` - if an attacker can get a fake event into the cache before the real one, it may poison downstream.

**Impact.** Stale or malicious keys accepted as authentic. Wrong events served to consumers.

**Current spec mitigation.** None.

**Residual risk.** Medium.

**Recommended action.**
- Spec MUST require `Cache-Control: max-age=300, must-revalidate` (or stricter) on the key document response.
- Key document fetches MUST use conditional requests (ETag/If-None-Match) to detect tampering.
- Spec MUST require aggregator caches to key events by `(vendor_id, id, published_at)` tuple, not `id` alone.

---

### T-14: Event ordering attacks (High)

**Attacker profile.** Active network attacker or malicious aggregator.

**Attack surface.**
- Delay a critical CVE event while delivering subsequent lower-severity events, so the critical event is buried in history when it finally arrives.
- Replay an old `api_deprecation` event with a `sunset_date` in the past, triggering auto-retirement of a feature that the vendor never retired.
- Reorder a correction event ("ignore the previous notice, there is no CVE") to arrive BEFORE the original event, so the correction is filed and the original later appears un-corrected.

**Impact.** Automated agents make wrong decisions. Security events delayed. Deprecations forced prematurely.

**Current spec mitigation.** `published_at` is required. `id` is stable for dedup.

**Residual risk.** High. Consumers must reconstruct temporal ordering, but nothing signs the ordering.

**Recommended action.**
- Consumers MUST compare `published_at` against a signed monotonic counter if the event is `publisher_verified` and the producer offers one.
- v1.1 should add `producer_sequence` - an optional, signed, monotonically-increasing integer per producer. Consumers that see a gap or regression reject the event or flag it.

---

### T-15: Confidence score manipulation (Medium)

**Attacker profile.** Malicious aggregator, malicious community submitter.

**Attack surface.** `confidence_score` is a float set by the producer. An attacker can set `confidence_score: 1.0` on a fabricated community event to trick automated consumers that filter `confidence_score > 0.9`.

**Impact.** Automated systems that use `confidence_score` as a trust signal can be socially engineered.

**Current spec mitigation.** Schema rule: `publisher_verified` events must have `confidence_score: 1.0`. But this only matters if the event is also signed and the signature is verified. An unsigned `publisher_verified` event with forged `vendor_id` is already the stronger attack (see T-01).

**Residual risk.** Medium.

**Recommended action.**
- `confidence_score` is informational. Consumers MUST NOT make automated auto-patching decisions based solely on `confidence_score`.
- Spec should clarify: confidence_score is a hint, not a trust anchor. Document this in Security Considerations.

---

### T-16: Supply chain - malicious reference implementations (High)

**Attacker profile.** Compromised maintainer account, malicious PR merged into reference repos, compromised dependency.

**Attack surface.**
- The Go reference embeds a schema as a Go string literal - different from the canonical `schema.json`. A malicious PR could subtly weaken the embedded schema.
- TS reference depends on `zod@4.3.6`. A malicious zod update could break validation.
- Python reference depends on `pydantic==2.13.1`. Same risk.
- Python reference has an invalid `build-backend = "setuptools.backends.legacy:build"` which does not exist - packages will not build without maintainer intervention.
- No checksums / SBOM / provenance attestations for the reference implementation releases.

**Impact.** Every consumer that pulls in the reference implementation inherits the compromise. An attacker who can push to the `changespec` package on npm/PyPI/pkg.go.dev owns all downstream consumers.

**Current spec mitigation.** None at spec level. Dependency pinning is present (good). Go does not pin full transitive graph (go.sum exists, helps).

**Residual risk.** High. This is standard supply-chain risk that applies to every OSS project.

**Recommended action.**
- All reference implementation releases MUST be published via Sigstore / SLSA provenance.
- All reference implementation releases MUST ship an SBOM.
- Reference implementations MUST be built via reproducible builds on audited CI.
- The embedded Go schema MUST be generated from `schema.json` at build time with a checksum check, not hand-maintained.
- Fix the Python `build-backend` (unrelated to security but blocks release).

---

### T-17: Agent-level attack - tricking an auto-patch agent (Critical)

**Attacker profile.** Any actor who can get a crafted event into the feed a consuming agent listens to.

**Attack surface.** An autonomous agent hears "CVE-2025-99999 fixed in npm:left-pad 2.0.0" and auto-PRs a bump from 1.3.0 to 2.0.0. If the event was forged:
- The agent bumps to a version that doesn't exist (wasted CI time) or, worse, bumps to a version the attacker controls via a dependency-confusion attack.
- The `migration_url` points to attacker-controlled code that the agent copies into the repo.
- The event claims action_required=true, triggering an automatic override of code-review policies.

**Impact.** Mass compromise. The scale factor here is enormous: one forged `security/critical` event for a popular package could automatically deploy malicious code into thousands of codebases.

**Current spec mitigation.** `source_type` is expected to be filtered by automation; signatures exist (optional).

**Residual risk.** Critical.

**Recommended action.**
- Spec MUST prohibit agents from acting on `crawled` or `community` events without human review.
- Spec MUST prohibit agents from acting on unsigned `publisher_verified` events.
- Agent best practices document should be published alongside v1.0 (`reference/agent-security.md`).
- The conformance tests MUST include a test that a conforming implementation exposes the fields agents need to make these distinctions (`source_type`, `signature.alg`, `signature.key_id`, whether verification succeeded).

---

### T-18: Aggregator integrity - "backdooring" a vendor's feed (Critical)

**Attacker profile.** Malicious insider at the ChangeSpec platform, attacker with access to the platform's database, attacker with compromised credentials to the publisher API.

**Attack surface.** The ChangeSpec platform registry aggregates events from many vendors. If the platform's signing keys are compromised, or if the platform itself is compromised, an attacker can:
- Publish events that appear verified because the platform mirror vouches for them.
- Silently drop legitimate vendor events (denial of advisory delivery).
- Modify events en route from vendor to consumer.

**Impact.** Ecosystem-wide compromise. Every consumer that trusts the platform trusts a single compromised point.

**Current spec mitigation.** Signatures, if end-to-end (vendor signs, consumer verifies). But the registry mirroring creates ambiguity: is the consumer verifying the vendor's signature, or a registry mirror signature?

**Residual risk.** Critical.

**Recommended action.**
- The vendor signature MUST be end-to-end - the registry does NOT re-sign. The registry is a transport, not a trust authority.
- The registry MUST be verifiable - ideally via a transparency log (see `trust-bootstrap.md`).
- Spec MUST clearly say: the ChangeSpec platform is not a root of trust; vendor keys are the root of trust.

---

### T-19: Spec-evolution attacks (Medium)

**Attacker profile.** Participant in the spec's governance process, malicious PR submitter.

**Attack surface.** Spec evolution rules (Section 11.3) allow minor releases to add optional fields and extend enums. An attacker who can influence spec evolution could propose a new category value like `fake_security` or extend severity semantics to be misleading. More subtly: propose a new optional field `auto_apply: bool` that encourages automatic action.

**Impact.** Long-term ecosystem harm. Spec co-option.

**Current spec mitigation.** Social (open process, governance).

**Residual risk.** Medium.

**Recommended action.**
- Define a security-review requirement for every spec change (any PR affecting schema, signatures, or security considerations must have security sign-off).
- Document this in `disclosure-policy.md` and the governance docs.

---

### T-20: CVE ID fabrication (High)

**Attacker profile.** Anyone publishing an event.

**Attack surface.** `cve_id` matches the pattern `^CVE-[0-9]{4}-[0-9]{4,}$`. No check that the CVE exists. An attacker can claim `CVE-2026-99999` on a fabricated event.

**Impact.** False positives in vulnerability management pipelines. CVE-ID squatting. Denial of attention (analysts waste time investigating non-existent CVEs).

**Current spec mitigation.** None.

**Residual risk.** High.

**Recommended action.**
- Spec SHOULD recommend consumers cross-reference CVE IDs against an authoritative source (NVD, OSV, GHSA) before acting.
- Consider requiring that events with `cve_id` include `source_url` pointing to a matching advisory.
- Conformance test: event with `cve_id: CVE-9999-99999` (known-invalid) should be flagged.

---

### T-21: CVSS vector injection (Low)

**Attacker profile.** Malicious event producer.

**Attack surface.** `cvss_vector` pattern in schema is `^CVSS:[0-9]\\.[0-9]/` - this is a prefix check. Arbitrary bytes can follow. The TS schema doesn't even check the full vector.

**Impact.** CVSS parsers may error on malformed vectors, potentially crashing. Inflated scores may be used to manipulate triage priority.

**Current spec mitigation.** Length cap 128 chars.

**Residual risk.** Low.

**Recommended action.**
- Tighten the regex to match full CVSS 3.0/3.1/4.0 vector grammar.
- Reject vectors whose computed base score does not match the claimed `cvss_score`.

---

## Attack scenario walkthroughs

### Scenario A: Mass false-advisory flood

1. Attacker creates a legitimate-looking `publisher_verified` key pair, hosts keys at `fake-vendor.com/.well-known/changespec-keys.json`.
2. Attacker submits `fake-vendor` as a no-namespace vendor to the ChangeSpec registry.
3. Once accepted, attacker publishes a fabricated `security/critical` event for a popular npm package, setting `vendor_id: "npm:express"` (NOT their own vendor).
4. If the consumer signature verifier does not require `vendor_id` in `signed_fields`, or does not check that key `fake-vendor-2026-01` is authorized to sign for `vendor_id: "npm:express"`, the event verifies.
5. Thousands of auto-patching agents roll out the "fix" - the attacker's migration URL - or roll back to an old version for a non-existent vulnerability.

**Mitigation depends on:** SIG-05 (signer authorization binding).

### Scenario B: Silent CVE suppression

1. Vendor publishes `security/critical` event for CVE-2026-12345 with signature covering `{id, vendor_id, category, severity, title, summary, published_at}`.
2. Attacker on the network path strips `cve_id`, `cvss_score`, `cvss_vector`, and `fixed_in_version` from the event.
3. Signature still verifies (those fields not in `signed_fields`).
4. Consumer's vulnerability scanner sees a generic `security/critical` event with no actionable CVE and deprioritizes it.

**Mitigation depends on:** SIG-02 (attacker-controlled signed_fields) and a required minimum field set.

### Scenario C: Cross-protocol signature reuse

1. Vendor uses an Ed25519 key that also signs their DNS DNSSEC records or SSH host keys (bad practice, but happens).
2. Attacker crafts a ChangeSpec signature input that matches the byte layout of a DNSSEC signature or an SSH challenge.
3. Attacker captures a legitimate DNSSEC/SSH signature from the vendor and submits it as a ChangeSpec event signature.
4. Without domain separation, the signature verifies.

**Mitigation depends on:** SIG-03 (domain separation).

---

## Recommended launch blocker remediation

Before v1.0 public launch, the following MUST be addressed:

1. Adopt JCS RFC 8785 (or replace signing with JWS) - fixes SIG-01 and SIG-03.
2. Define a required minimum signed-field set, include `signed_fields` in the signed input - fixes SIG-02.
3. Require `published_at` in signed input and freshness enforcement - fixes SIG-04.
4. Bind `vendor_id` to key via key registry + include `vendor_id` and `key_id` in signed input - fixes SIG-05.
5. Specify trust bootstrap with key transparency or multi-party cosigning - fixes SIG-06 (see `trust-bootstrap.md`).
6. Restrict `source_url` and `migration_url` to HTTPS in schema - fixes GEN-02.
7. Fix the Go reference schema divergence - fixes GEN-01.
8. Add total event size cap, nesting depth cap, ext field count cap - mitigates T-09, T-12.
9. Add Security Considerations section expansion per `SECURITY.md` deliverable.
10. Fix Python `build-backend` (supply-chain/distribution blocker, not security-critical).

Everything else can be addressed in v1.1 with a documented known-gap in `v2-security-roadmap.md`.
