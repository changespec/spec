# Consumer Conformance Requirements

This document specifies the conformance requirements for **consumers**: libraries, tools, or services that parse, validate, or process ChangeSpec 1.0 events.

Requirements use RFC 2119 terms. MUST failures block certification at the relevant level. SHOULD failures are warnings.

---

## Section 1: Input Handling

### C-MUST-1.1 - Accept all valid events

A conforming consumer MUST accept every event in the `test-vectors/valid/` directory. "Accept" means: parse without error, return a structured result, and make all required fields accessible.

Failure mode: returning an error for a valid event causes downstream consumers to silently drop changes they should have processed.

### C-MUST-1.2 - Reject all invalid events

A conforming consumer MUST reject every event in the `test-vectors/invalid/` directory. "Reject" means: return a structured error or raise an exception. The consumer MUST NOT return a success result for an invalid event.

Failure mode: silently accepting invalid events means downstream systems receive malformed data without knowing it.

### C-MUST-1.3 - Never panic or crash on invalid input

Rejection MUST be graceful. A consumer MUST NOT panic, crash, or exit on any input, including malformed JSON, extremely large inputs, or deeply nested objects. Errors must be returned to the caller.

### C-MUST-1.4 - Validate before processing fields

A consumer MUST validate the event against the schema before accessing individual field values. Field-level access on unvalidated input bypasses all constraint checks.

### C-MUST-1.5 - Reject events with wrong specversion

Events where `specversion` is not `"1.0"` MUST be rejected. A consumer implementing ChangeSpec 1.0 MUST NOT accept events claiming `specversion: "2.0"` or any other value.

**Rationale:** A future incompatible major version may reuse field names with different semantics. Accepting events from an unknown major version is unsafe.

### C-MUST-1.6 - Reject events missing required fields

Events missing any of the 9 required fields (`specversion`, `id`, `vendor_id`, `category`, `severity`, `title`, `summary`, `published_at`, `source_type`) MUST be rejected.

### C-MUST-1.7 - Reject events with invalid enum values

Events where `category`, `severity`, or `source_type` contain a value not in the defined enum MUST be rejected. This applies to all values, including plausible-looking values like `"urgent"` (not a valid severity) or `"api_change"` (not a valid category).

**Exception for future spec versions:** Per spec Section 11.3, a 1.0 consumer that receives a ChangeSpec 1.1 event (same major version) with an unknown category value SHOULD treat it as `informational` rather than rejecting outright. This exception applies only when the event's `specversion` indicates a higher minor version. Test vectors in `valid/` that test this behavior are included.

### C-MUST-1.8 - Reject events where title contains newlines

Events where the `title` field contains a newline (`\n`) or carriage return (`\r`) character MUST be rejected.

### C-MUST-1.9 - Reject events exceeding field length limits

Events where string fields exceed their defined maximum lengths MUST be rejected:
- `title`: 200 characters
- `summary`: 2000 characters
- `id`: 128 characters
- `vendor_id`: 256 characters
- `migration_hint`: 500 characters
- `source_url`: 2048 characters
- `migration_url`: 2048 characters
- `affected_versions`: 256 characters
- `fixed_in_version`: 64 characters
- `cvss_vector`: 128 characters
- `cve_id`: implicit (pattern constraint enforces length)

### C-MUST-1.10 - Reject events with out-of-range numeric values

Events where `confidence_score` is outside [0.0, 1.0] or `cvss_score` is outside [0.0, 10.0] MUST be rejected.

### C-MUST-1.11 - Reject events with invalid CVE format

Events where `cve_id` is present but does not match `CVE-YYYY-NNNNN` (4-digit year, 4+ digit sequence) MUST be rejected.

### C-MUST-1.12 - Reject events with oversized arrays

Events where arrays exceed their maximum item counts MUST be rejected:
- `tags`: 20 items
- `affected_systems`: 50 items
- `affected_sections`: 50 items
- `recommended_reviewers`: 6 items

---

## Section 2: Extension Field Handling

### C-MUST-2.1 - Ignore unknown fields without error

A conforming consumer MUST NOT reject an event solely because it contains fields that are not defined in the ChangeSpec 1.0 schema. This includes:
- Extension fields (`ext:*`)
- Fields that may be added in future minor versions

### C-MUST-2.2 - Pass extension fields through

A conforming consumer MUST make extension fields (`ext:*`) accessible to caller code. Extension fields MUST NOT be silently dropped. The consumer MAY collect all extension fields into a dedicated map or dictionary rather than exposing them as top-level properties.

**Example:** An event with `"ext:compliance.gdpr_article": "28"` must result in the caller being able to retrieve the value `"28"` by key `"ext:compliance.gdpr_article"`.

### C-MUST-2.3 - Do not corrupt extension field values

Extension fields may have values of any JSON type: string, number, boolean, array, or object. The consumer MUST preserve the type of extension field values. A string MUST remain a string; a boolean MUST remain a boolean.

### C-SHOULD-2.4 - Distinguish extension fields from core fields

Consumer implementations SHOULD separate extension fields from core event fields in the returned data structure. This prevents confusion between spec-defined fields and producer-specific extensions.

---

## Section 3: Signature Verification Behavior

### C-MUST-3.1 - Structural validation of signature objects

When a `signature` field is present, the consumer MUST validate its structure:
- `alg` must be `"ed25519"`.
- `key_id` must be a non-empty string with length <= 128.
- `value` must match the base64url pattern `[A-Za-z0-9_-]+`.
- `signed_fields` must be a non-empty array of strings.

Structural validation failure MUST result in rejection of the event.

### C-SHOULD-3.2 - Consumers should verify Ed25519 signatures when key is available

Consumers that receive events from untrusted sources SHOULD perform cryptographic signature verification when the signing key is retrievable. Verification follows the steps in spec Section 7.5:

1. Check `source_type` is `publisher_verified`.
2. Retrieve the public key by `signature.key_id`.
3. Confirm the current time is within the key's validity window.
4. Reconstruct the signature input from `signed_fields`.
5. Verify the Ed25519 signature.
6. Reject if verification fails.

### C-MAY-3.3 - Consumers receiving from trusted platforms may skip verification

A consumer that receives events from a trusted platform that has already verified signatures MAY skip re-verification. The trust decision is the consumer's responsibility.

### C-MUST-3.4 - Never accept a failed signature verification as valid

A consumer that performs cryptographic verification and gets a verification failure MUST NOT accept the event. There is no fallback.

---

## Section 4: Error Reporting Semantics

### C-MUST-4.1 - Errors must be structured

Validation errors MUST be returned in a structured form. The minimum structure is an error type or error code that distinguishes schema validation failure from JSON parse failure. Returning a plain string error message is permitted but not recommended.

Preferred error structure provides:
- The specific field that failed validation.
- The constraint that was violated (e.g., "exceeds max length", "invalid enum value").
- The received value (or a truncated representation for large values).

### C-SHOULD-4.2 - Distinguish JSON parse errors from schema errors

A consumer SHOULD distinguish between two error categories:
1. **JSON parse error** - the input is not valid JSON at all.
2. **Schema validation error** - the input is valid JSON but fails the ChangeSpec schema.

These represent different failure modes. A schema error means the producer is broken. A JSON parse error may mean the transport is broken.

### C-SHOULD-4.3 - Report all constraint failures, not just the first

When an event fails multiple constraints (e.g., missing `id` AND invalid `category`), the consumer SHOULD report all failures, not just the first one discovered. This reduces the number of round-trips needed to fix a broken producer.

### C-MUST-4.4 - Do not include sensitive data in error messages

Error messages MUST NOT include the full content of oversized string fields. Truncate values in error messages to a safe length (e.g., 200 characters) to prevent log injection or log flooding.

---

## Section 5: Backward Compatibility

### C-MUST-5.1 - Accept future optional fields without error

If a future version of the spec adds new optional fields, a 1.0 consumer MUST NOT reject events containing those fields. Unknown fields are silently ignored per C-MUST-2.1.

### C-MUST-5.2 - Handle unknown category and severity values from minor versions

Per spec Section 11.3, a 1.0 consumer receiving an event with a `specversion` of `"1.1"` (or any `"1.x"`) and an unknown `category` value SHOULD treat the category as `informational`. A 1.0 consumer MUST NOT fail hard on an unknown category from a higher minor version.

**Test vector:** `edge-cases/forward-compat-unknown-category.yml` provides an event with `specversion: "1.0"` and a known category. Additional vectors test the forward-compat behavior.

### C-MUST-5.3 - Reject events from incompatible major versions

A 1.0 consumer MUST reject events where `specversion` indicates a major version other than `1`. For example, `specversion: "2.0"` MUST be rejected.

### C-SHOULD-5.4 - Expose the specversion to callers

The consumer SHOULD expose the `specversion` field in the parsed result so callers can implement their own version-routing logic if needed.

---

## Section 6: Security Requirements

### C-MUST-6.1 - Do not fetch URLs during validation

The validator MUST NOT make network requests to `source_url`, `migration_url`, or any other URL field during validation. URL validation is syntactic only (RFC 3986 format check). Fetching is a caller responsibility.

### C-MUST-6.2 - Impose resource limits

The consumer MUST NOT allow validation of a single event to consume unbounded memory or CPU. Implementations SHOULD impose:
- A maximum input size (recommended: 1 MB per event).
- A maximum depth for JSON parsing (recommended: 50 levels).
- A timeout for parsing (recommended: configurable, default 100ms).

These limits are tested by the security test vectors.

### C-MUST-6.3 - Handle oversized input safely

When the input exceeds size limits, the consumer MUST return an error. It MUST NOT truncate the input and validate the truncated version (which could produce false positives).

### C-MUST-6.4 - Do not use extension field keys for code execution

Extension field keys and values are untrusted input. The consumer MUST NOT evaluate extension field keys as code, use them in SQL queries without parameterization, or pass them unescaped to system calls.

---

## Section 7: Interface Requirements

These requirements specify what the public API of a conforming consumer library must expose. See also [runner/spec.md](runner/spec.md) for the precise interface definition used by the conformance runner.

### C-MUST-7.1 - Expose a validate function

The library MUST expose a function (or method) that:
- Accepts raw JSON input (bytes, string, or parsed object, depending on language idioms).
- Returns either a success result with the typed event, or an error.
- Never panics on any input.

### C-MUST-7.2 - Expose typed field access

The returned success result MUST expose all required and optional fields with their correct types. String fields must be strings, numbers must be numbers, booleans must be booleans, arrays must be iterable.

### C-MUST-7.3 - Expose extension fields separately

Extension fields (`ext:*`) MUST be accessible separately from core event fields. The mechanism is language-idiomatic (a map, dict, or dedicated property on the result type).

### C-SHOULD-7.4 - Expose typed enums

Category, Severity, and SourceType values SHOULD be exposed as typed enumerations (Go const group, TypeScript string union, Python Enum) rather than raw strings. Typed enums prevent consumer code from comparing against misspelled string literals.

---

## Test Vector Coverage

| Requirement | Vector Directory | Vector Count |
|---|---|---|
| Valid event acceptance | `valid/` | ~30 |
| Invalid event rejection | `invalid/` | ~40 |
| Edge case handling | `edge-cases/` | ~15 |
| Security input handling | `security/` | ~20 |

All test vectors reference the specific requirement clause they test in their `spec_clause` field.
