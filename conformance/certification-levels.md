# ChangeSpec Certification Levels

Each level is a strict superset of all lower levels. A library certified at Level 3 has passed all Level 1, 2, and 3 requirements. There is no path to Level 3 that skips Level 1 or 2.

---

## Level 1 - Syntactic

**What it proves:** The implementation correctly accepts all syntactically valid ChangeSpec 1.0 events and correctly rejects all syntactically invalid events.

### Criteria

Pass all test vectors in `test-vectors/valid/` (approximately 30 vectors) and `test-vectors/invalid/` (approximately 40 vectors).

The runner must report 0 failures across both directories.

### What "correctly accepts" means

- Returns a success result (not an error) for every vector in `valid/`.
- The parsed event exposes all required fields with correct types.
- Extension fields (`ext:*`) are collected and made accessible without causing errors.
- Unknown non-extension fields are silently ignored (forward compatibility).

### What "correctly rejects" means

- Returns an error result (not a success) for every vector in `invalid/`.
- The error is returned from validation, not from parsing (the parser must not panic or crash on invalid input).
- The error is structured enough to identify which field or constraint failed (not required for certification but strongly recommended).

### Required field validations tested

- All 9 required fields must be present.
- `specversion` must be exactly `"1.0"`.
- `category` must be one of the 9 defined enum values.
- `severity` must be one of the 5 defined enum values.
- `source_type` must be one of the 3 defined enum values.
- `title` must not contain newline characters.
- `title` must not exceed 200 characters.
- `summary` must not exceed 2000 characters.
- `id` must not exceed 128 characters.
- `vendor_id` must not exceed 256 characters.
- `confidence_score` must be in [0.0, 1.0] when present.
- `cvss_score` must be in [0.0, 10.0] when present.
- `cve_id` must match `CVE-YYYY-NNNNN` pattern when present.
- `cvss_vector` must match `CVSS:X.Y/...` pattern when present.
- `signature.alg` must be `"ed25519"` when present.
- `tags` items must match lowercase pattern when present.

### Self-certification path

1. Clone the conformance repository.
2. Run the runner for your language: `runner/<lang>/runner.{go,ts,py} test-vectors/valid test-vectors/invalid`
3. Confirm 0 failures.
4. Add the Level 1 badge to your README.
5. File a self-certification report at `github.com/changespec/conformance/issues/new?template=self-cert.md`.

### Official certification path

1. Complete self-certification above.
2. Ensure the test run is reproducible in a public CI system (GitHub Actions, CircleCI, etc.).
3. Submit a certification request at `changespec.com/certify` with a link to a passing CI run.
4. A maintainer reviews and approves. Turnaround target: 5 business days.
5. The implementation is listed at `changespec.com/certified`.

### Mark usage rights

- May display: "ChangeSpec Certified: Level 1"
- May display the Level 1 SVG badge from `conformance-badge.md`.
- May state: "ChangeSpec 1.0 Certified (Syntactic, Level 1)"
- Must not claim Level 2, 3, or 4 unless those levels are also achieved.

---

## Level 2 - Semantic

**What it proves:** The implementation correctly handles boundary conditions, edge cases, and the semantic requirements beyond basic field presence and type checking.

### Criteria

Pass all Level 1 vectors plus all test vectors in `test-vectors/edge-cases/` (approximately 15 vectors).

### What edge-case handling means

- Correctly handles maximum-length strings at exactly the allowed limit.
- Correctly handles minimum-length strings (1 character for required string fields).
- Correctly parses RFC 3339 datetimes including timezone offsets (not just UTC `Z`).
- Correctly validates `effective_date` and `sunset_date` as full-date (`YYYY-MM-DD`), not datetimes.
- Correctly handles Unicode in string fields (multibyte characters, emoji in summary/title within length limits).
- Correctly handles the minimum and maximum values for numeric fields (`confidence_score: 0.0`, `confidence_score: 1.0`, `cvss_score: 0.0`, `cvss_score: 10.0`).
- Correctly handles events with all optional fields populated simultaneously.
- Correctly handles `tags` with the maximum count (20 items) and items at the maximum length (50 characters).
- Correctly handles `affected_systems` and `affected_sections` at maximum item count (50 items).
- Correctly handles `recommended_reviewers` at maximum count (6 roles).
- Correctly handles signed events where `source_type` is `publisher_verified` (structural validation of the signature object, not cryptographic verification).
- Correctly handles namespaced `vendor_id` values (e.g., `npm:lodash`, `go:golang.org/x/net`, `maven:org.springframework:spring-core`).

### Self-certification path

Same as Level 1, but include all three vector directories: `valid/`, `invalid/`, `edge-cases/`.

### Mark usage rights

- May display: "ChangeSpec Certified: Level 2"
- Supersedes Level 1 mark. Do not display both.

---

## Level 3 - Secure

**What it proves:** The implementation handles adversarial inputs safely. It does not panic, crash, hang, consume unbounded memory, or produce incorrect results when given malicious input.

### Criteria

Pass all Level 1 and Level 2 vectors plus all test vectors in `test-vectors/security/` (approximately 20 vectors).

### What secure handling means

For security vectors, the expected result is either:
- `valid: false` - the input is rejected cleanly (no panic, no crash, returns an error).
- `valid: true, no_side_effects: true` - the input is accepted but no external network call, file read, or other side effect was triggered.

Security vectors test:

- **Deeply nested JSON objects** - inputs with 100+ levels of nesting that should not cause stack overflows.
- **Very long strings at field positions** - strings of 100,000+ characters where the schema limit is 200. Must be rejected without consuming excessive memory.
- **SSRF-risk URLs** - `source_url` values pointing to `file://`, `gopher://`, `dict://`, `http://127.0.0.1`, `http://169.254.169.254` (AWS metadata endpoint), and similar. Must be accepted as strings (validation does not fetch URLs) but consumer implementations that fetch URLs must not fetch these.
- **Prototype pollution attempts** - JSON keys like `__proto__`, `constructor`, `prototype` at the top level. Must not corrupt the parser's object model.
- **Billion-laughs analog** - a JSON object with deeply repeated string values that would expand significantly if evaluated. Must not cause excessive CPU or memory use during parsing.
- **NUL bytes and control characters** - strings containing `\u0000` and other control characters in field values. Must be handled without crashing.
- **Oversized arrays** - arrays with 10,000+ items where the schema limit is 50. Must be rejected.
- **Duplicate keys** - JSON objects with duplicate field names. Must either take the last value (standard JSON behavior) or reject; must not crash.
- **Malformed base64url** - `signature.value` with characters outside the base64url alphabet. Must be rejected structurally (the schema enforces the pattern).
- **Number overflow** - numeric values at float64 overflow boundaries. Must not panic.

### Note on URL fetching

The ChangeSpec validator itself does not fetch URLs. Security vectors for SSRF apply to consumers that build on top of the validator and do fetch URLs. Level 3 certification for a pure validator library certifies that the library does not fetch URLs. Consumers that do fetch URLs must implement their own URL safelisting per spec Section 12.2.

### Self-certification path

Same as Level 2, adding `security/` vectors. Security vectors that test runtime behavior (no panics, no hangs) require the runner to impose a timeout per vector (default: 5 seconds). If a vector causes the validator to hang past the timeout, it is a test failure.

### Mark usage rights

- May display: "ChangeSpec Certified: Level 3"
- Appropriate for production deployments handling untrusted input.

---

## Level 4 - Full Producer

**What it proves:** A vendor's published ChangeSpec events meet all MUST requirements from the spec for producers. This level is for vendors and platforms publishing events, not for consumer libraries.

### Criteria

Pass all Level 1, 2, and 3 test vectors AND pass all MUST requirements in [producer-tests.md](producer-tests.md).

Producer certification requires submitting a sample of at least 20 real events published by the vendor. These events are validated automatically against the test suite and reviewed by a maintainer.

### What producer certification checks

- All events validate at Level 1 (schema conformance).
- All events have globally unique `id` values across the submitted sample.
- `published_at` values are real timestamps within a plausible range (not epoch 0, not far future).
- `vendor_id` follows the namespacing conventions.
- `source_type` is set appropriately for the production method.
- `confidence_score` is `1.0` for `publisher_verified` events.
- Events with `signature` blocks have valid structural signature objects (key_id, alg, value, signed_fields all present and correctly typed).
- Events with `source_type: publisher_verified` and no `signature` include a documented reason in the certification submission.
- All URL fields (`source_url`, `migration_url`) are reachable HTTPS URLs (verified by the certification tooling making a HEAD request).

Producer certification is not self-service. It requires a certification submission and maintainer review.

### Mark usage rights

- May display: "ChangeSpec Certified Producer: Level 4"
- May display: "Events published in ChangeSpec 1.0 format (Certified)"
- May include the certification mark in marketing materials describing the vendor's change communication capabilities.

---

## Certification Renewals and Revocation

Certifications are valid for 12 months from the date of issuance or until a new minor version of the spec is released, whichever comes first.

Revocation occurs when:

- A regression test run (triggered by a new release of the implementation) fails previously passing vectors.
- The implementation is found to have bypassed the test suite (e.g., hardcoded vector inputs).
- The implementation's behavior diverges from the certified run due to a dependency update.

Revoked certifications are noted in the registry with the reason. The implementation may re-apply after fixing the regression.

---

## Summary Table

| Requirement | Level 1 | Level 2 | Level 3 | Level 4 |
|---|:---:|:---:|:---:|:---:|
| Pass valid/ vectors | yes | yes | yes | yes |
| Pass invalid/ vectors | yes | yes | yes | yes |
| Pass edge-cases/ vectors | - | yes | yes | yes |
| Pass security/ vectors | - | - | yes | yes |
| Producer MUST requirements | - | - | - | yes |
| Self-service | yes | yes | yes | no |
| Official review required | optional | optional | optional | yes |
