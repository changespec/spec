# ChangeSpec Changelog

## v1.1.0 (2026-05-12)

### Added

- **`retraction` category** - New event category for supply-chain compromises, accidental publishes, and any case requiring consumers to stop using a previously distributed artifact. Addresses the known gap documented in v1.0 Section 12.20.
- **`provenance_invalidated` field** (boolean) - Signals that build provenance attestations (SLSA, Sigstore) are technically valid but were produced by a compromised build pipeline the vendor did not authorize. This is the key distinction: SLSA attests *build pipeline*, ChangeSpec attests *vendor intent*.
- **`do_not_install` field** (boolean) - Instructs consuming tooling to block installation of `affected_versions`. When `true`, `last_known_good_version` SHOULD also be set.
- **`last_known_good_version` field** (string) - The most recent vendor-affirmed safe version. Tooling uses this for auto-pinning after a retraction.
- **`retraction_reason` field** (string enum) - Machine-readable reason: `supply_chain_compromise`, `accidental_publish`, `security_vulnerability`, `policy_violation`, `key_compromise`.
- **`retraction_indicators` field** (array) - Machine-readable compromise type indicators for supply-chain events: `credential_exfiltration`, `unauthorized_publish`, `anomalous_postinstall_script`, `cache_poisoning`, `ci_pipeline_compromise`, `malicious_payload`.
- **`supersedes` field** (string) - Links an event to the event it replaces or retracts.
- **`related_events` field** (array) - Cross-vendor event references for correlated incidents (e.g., worm propagation across multiple package maintainers).
- **Section 7.6** - Key Separation from CI/CD Systems: signing keys for ChangeSpec events MUST NOT be present in the build/publish CI environment.
- **Appendix E** - Retraction event example with `provenance_invalidated: true` scenario.

### Changed

- `signed_fields` mandatory minimum extended to include new security-critical fields when present.
- Section 12.18 Supply Chain guidance updated with key separation requirements.
- Section 12.20 Known Limitations: retraction gap replaced with note on ordering guarantees.

---

## 1.0.0 (2026-04-16)

This is the first public release of ChangeSpec. The version was finalized after
a pre-launch security review and conformance audit that identified and resolved
the issues listed below.

### Security fixes (showstoppers resolved before launch)

**SIG-01 - Canonicalization under-specified.**
Section 7.3 now mandates JCS (RFC 8785) over a typed envelope. The previous
ad-hoc field-concatenation scheme was ambiguous for strings with Unicode
escapes, numbers with multiple representations, arrays, and nested objects.
Two conforming implementations signing the same event could produce different
byte strings. The JCS approach produces byte-exact signatures across
implementations.

**SIG-02 - signed_fields self-reference vulnerability.**
The `signed_fields` array is now part of the signed payload (included in the
typed envelope's `payload` object). A mandatory minimum field set is now
required; consumers MUST reject events whose `signed_fields` omits any field
from the mandatory minimum that is present in the event. Previously, an
attacker could modify `signed_fields` to remove entries and recompute a valid
signature over a reduced field set.

**SIG-03 - No domain separation.**
Every signature input now begins with the 24-byte domain separator
`ChangeSpec-Signature-1.0\n`. This prevents cross-protocol signature reuse
where the same Ed25519 key used for DNSSEC or SSH could be exploited to forge
ChangeSpec signatures.

**SIG-04 - No replay protection.**
`published_at` is now in the mandatory `signed_fields` minimum. Consumers MUST
enforce a freshness window (default: reject events more than 90 days in the past,
or more than 5 minutes in the future). Previously, captured signed events could
be replayed indefinitely.

**SIG-05 - No vendor_id to key_id binding.**
`vendor_id` is now part of the typed envelope. Key resolution MUST be scoped
by `(vendor_id, key_id)`. A key registered for one vendor cannot be used to
sign events claiming a different `vendor_id`. The `key_id` field now has a
restricted pattern (`^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$`) that prevents path
traversal attacks.

**SIG-06 - Trust bootstrap under-specified.**
Section 12.5 now defines three acceptable trust bootstrap mechanisms: key
pinning, transparency log, and multi-party cosigning. Key pinning is the
formally available mechanism for v1.0. A full key-transparency mechanism is
planned for v1.1 and documented as a known gap in Section 12.20.

**GEN-01 - Schema divergence between implementations.**
The Go reference implementation now embeds the canonical `schema.json` via
`//go:embed` instead of a hand-maintained simplified inline schema. This
eliminates drift and ensures all implementations validate against identical
constraints.

**GEN-02 - URL scheme not restricted.**
`source_url` and `migration_url` now require the `https://` scheme via a
`pattern: "^https://"` constraint in `schema.json`. Previously these fields
accepted `file://`, `javascript:`, `gopher://`, and other dangerous schemes.

### Conformance gaps closed

Ten conformance gaps identified in the pre-launch audit were closed:

**TS-01 - TypeScript passthrough prototype pollution risk.**
The TypeScript reference no longer uses `.passthrough()`. Instead, extension
fields are separated before schema validation. Prototype-polluting keys
(`__proto__`, `constructor`, `prototype`) are explicitly rejected before
any object merging can occur.

**PY-01 - Python build-backend invalid.**
`pyproject.toml` `build-backend` corrected from the non-existent
`setuptools.backends.legacy:build` to `setuptools.build_meta`.

**Go conformance gaps (6 total):**
- Canonical `schema.json` embedded via `//go:embed` (eliminates hand-maintained inline schema)
- `date-time` format enforced on `published_at` via `AssertFormat()` + custom validator
- `date` format enforced on `effective_date` and `sunset_date`
- `uri` format enforced on `source_url` and `migration_url`
- `https://` scheme pattern enforced for URL fields
- `cvss_vector` pattern and `tags` item lowercase pattern enforced

**Python conformance gaps (3 total):**
- `build-backend` corrected in `pyproject.toml`
- `Annotated[str, Field(...)]` syntax adopted for all length/pattern-constrained fields
- `extra="forbid"` added to reject unknown non-ext fields (matching schema's `additionalProperties: false`)
- `datetime` type with pre-validator to reject date-only strings for `published_at`

### Test vector updates

The following test vectors were updated to reflect the tightened spec:

- `valid-002`, `valid-008`, `edge-010`: Updated `signed_fields` arrays to include
  the full mandatory minimum set (all required fields + signature metadata).
- `valid-030`, `edge-015`: Changed from `valid: true` to `valid: false`. Unknown
  non-ext fields must use the `ext:` prefix per Section 10. Schema's
  `additionalProperties: false` rejects these at the producer level.
- `security-001`: Changed `input_type` from `json_string` with placeholder to
  `generated` with proper `oversized_field` spec so runners correctly generate
  the 100K-character title.
- `security-002`, `security-003`: Changed from `valid: true` to `valid: false`.
  `http://` URLs are now rejected by the `https://`-only schema pattern.
- `security-005`, `security-006`: Changed from `valid: true` to `valid: false`.
  `__proto__` and `constructor` are rejected by `additionalProperties: false`.
- `security-020`: Changed from `valid: true` to `valid: false`. Unknown non-ext
  fields with deeply nested values are rejected by `additionalProperties: false`.

### Section 12 expansion

Section 12 (Security Considerations) was expanded from a 4-section placeholder
to a full 20-section security considerations document covering: threat model,
event authenticity, signature canonicalization, Ed25519 strict verification,
key distribution and trust bootstrap, key revocation, replay and freshness,
key document caching, transport security, URL field handling, input size and
parser safety, injection and rendering, automated agent safety, CSRF and origin
validation, extension field security, confidence score trust boundary, denial
of service resistance, supply chain, logging and observability, and known
limitations.

### Spec references added

RFC 8785 (JCS), RFC 8259 (JSON), RFC 8996 (TLS deprecation), RFC 9110 (HTTP
semantics), BCP 195, and SLSA v1.0 added to normative references.

### Known limitations (v1.1 backlog)

- No key transparency log (key pinning only for v1.0).
- No cryptographic signer-authorization chain beyond registry binding.
- No event retraction mechanism.
- No signed producer sequence numbers.
- Ed25519 only (no post-quantum hybrid; planned for v2.0).
