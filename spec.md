# ChangeSpec 1.1 Specification

**Status:** Released
**Version:** 1.1.0
**Date:** 2026-05-12
**License:** Apache 2.0

---

## Abstract

ChangeSpec defines a standard event format for communicating software changes from producers (vendors, library maintainers, service operators) to consumers (developers, agents, compliance teams). A ChangeSpec event is a self-describing JSON object with a fixed set of required fields and a rich set of optional fields covering severity, affected version ranges, migration guidance, and source attribution.

This document specifies:

1. The core event structure and field semantics
2. The category taxonomy
3. The severity taxonomy
4. Vendor identifier format
5. Source attribution model
6. Signing and verification for publisher-verified events
7. Envelope format and CloudEvents compatibility
8. Transport bindings: HTTPS webhook, MCP, RSS/Atom, polling API
9. Extension field convention
10. Backward compatibility rules
11. Security considerations
12. (Reserved)
13. Integration safety (companion document: integration-safety.md)

---

## Conformance

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

A **conforming event** is a JSON object that validates against the ChangeSpec JSON Schema (schema.json) included in this repository.

A **conforming producer** generates events that are conforming events.

A **conforming consumer** accepts conforming events and ignores unknown fields (including extension fields) without error.

---

## 1. Core Event Structure

A ChangeSpec event is a JSON object. All field names are lowercase with underscores.

### 1.1 Required Fields

| Field | Type | Description |
|---|---|---|
| `specversion` | string | Must be `"1.0"`. |
| `id` | string | Globally unique event identifier. Producers SHOULD use the format `cs_` followed by a ULID or UUIDv4. Must be stable - the same logical event must always have the same `id`. |
| `vendor_id` | string | Identifies the vendor or package. See Section 3. |
| `category` | string | Change category. One of the values defined in Section 4. |
| `severity` | string | Change severity. One of the values defined in Section 5. |
| `title` | string | Short, human-readable change title. Maximum 200 characters. Plain text; no markdown. |
| `summary` | string | 1-5 sentence plain-English description of what changed and what the impact is. No markdown. Maximum 2000 characters. |
| `published_at` | string | RFC 3339 timestamp when this event was published. Example: `"2026-04-10T14:00:00Z"`. |
| `source_type` | string | Indicates how this event was produced. One of: `publisher_verified`, `crawled`, `community`. See Section 6. |

### 1.2 Optional Fields

| Field | Type | Description |
|---|---|---|
| `effective_date` | string | RFC 3339 full-date (`YYYY-MM-DD`) when the change takes effect. For changes already live, this equals or precedes `published_at`. For upcoming changes, this is in the future. |
| `source_url` | string | URL of the primary source document for this event (changelog, blog post, advisory, etc.). |
| `affected_versions` | string | Semver range string (npm semver syntax) describing which versions are affected. Example: `">=14.0.0 <15.0.0"`. For non-versioned services, omit this field. |
| `fixed_in_version` | string | Exact semver version where this issue is resolved (common for security events). |
| `migration_hint` | string | One or two sentences describing the immediate action a consumer should take. Plain text. Maximum 500 characters. |
| `migration_url` | string | URL of a migration guide or detailed remediation instructions. |
| `confidence_score` | number | Float in [0.0, 1.0]. Indicates producer confidence in the classification. `1.0` for publisher-verified events. Lower values indicate automated classification uncertainty. |
| `sunset_date` | string | RFC 3339 full-date. For deprecations: when the deprecated feature is removed. For TOS/pricing: when the new terms take effect. |
| `cve_id` | string | CVE identifier in format `CVE-YYYY-NNNNN`. For security events only. |
| `cvss_score` | number | CVSS base score (0.0-10.0). For security events only. |
| `cvss_vector` | string | CVSS vector string. Example: `"CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"`. |
| `affected_systems` | array of string | Named systems, services, or products within the vendor that are affected. Example: `["Payments API", "Billing Portal"]`. |
| `affected_sections` | array of string | Document section headers affected (relevant for TOS/DPA changes). |
| `action_required` | boolean | Whether consumers must take action. `true` for breaking changes and critical security events. |
| `recommended_reviewers` | array of string | Suggested reviewer roles. Values are advisory. Common values: `"engineering"`, `"security"`, `"legal"`, `"compliance"`, `"procurement"`. |
| `tags` | array of string | Freeform tags for filtering. Maximum 20 tags, each maximum 50 characters. |
| `supersedes` | string | ID of a previously published ChangeSpec event that this event replaces or retracts. |
| `related_events` | array of string | IDs of related ChangeSpec events from any vendor (e.g., other packages compromised in the same supply-chain incident). Maximum 20 entries. |
| `provenance_invalidated` | boolean | When `true`, build provenance attestations (SLSA, Sigstore, etc.) for `affected_versions` are technically valid but were produced by a compromised build pipeline the vendor did not authorize. Consumers MUST NOT treat valid provenance as a safety signal when this field is `true`. |
| `do_not_install` | boolean | When `true`, consuming tooling MUST NOT install the versions in `affected_versions`. Used for retraction and critical security events where the artifact is actively harmful. |
| `last_known_good_version` | string | The most recent version the vendor affirms is safe. Tooling SHOULD pin to this version when `do_not_install` is `true`. |
| `retraction_reason` | string | For `retraction` events: reason for retraction. One of: `supply_chain_compromise`, `accidental_publish`, `security_vulnerability`, `policy_violation`, `key_compromise`. |
| `retraction_indicators` | array of string | For supply-chain compromise retractions: machine-readable compromise indicators. Values: `credential_exfiltration`, `unauthorized_publish`, `anomalous_postinstall_script`, `cache_poisoning`, `ci_pipeline_compromise`, `malicious_payload`. Maximum 10 entries. |
| `signature` | object | Ed25519 signature block. Present only on `publisher_verified` events. See Section 7. |
| `ext:*` | any | Extension fields. See Section 9. |

### 1.3 Field Constraints

- `source_url` and `migration_url`, when present, MUST use the `https://` scheme. Other URI schemes (`http://`, `file://`, `javascript://`, `data:`, `gopher://`, etc.) are not permitted. This is enforced by the JSON Schema pattern constraint.
- `published_at` MUST be a valid RFC 3339 datetime string (e.g., `"2026-04-10T14:00:00Z"`). Date-only strings (`"2026-04-10"`) and free-form text are not valid.
- `effective_date` and `sunset_date`, when present, MUST be valid RFC 3339 full-date strings (`YYYY-MM-DD`). Full datetime strings with time components are not valid for these fields.
- `id` MUST be unique across all events from a given producer. Consumers MAY use `id` for deduplication.
- `title` MUST NOT contain newlines.
- `summary` MUST be plain text. Producers MUST NOT include markdown syntax, HTML, or other markup.
- When `category` is `retraction`, `do_not_install` SHOULD be set. When `do_not_install` is `true`, `last_known_good_version` SHOULD also be set.
- `supersedes` MUST reference a valid `id` from a previously published event by the same `vendor_id`.
- `retraction_reason` and `retraction_indicators` MUST only be set when `category` is `retraction`.

---

## 2. Minimal Conforming Event

The smallest valid ChangeSpec event:

```json
{
  "specversion": "1.0",
  "id": "cs_01HXYZ1234ABCD",
  "vendor_id": "acme",
  "category": "informational",
  "severity": "informational",
  "title": "Documentation typo fix in authentication section",
  "summary": "Corrected a typo in the authentication section of the developer documentation. No behavior change.",
  "published_at": "2026-04-10T14:00:00Z",
  "source_type": "crawled"
}
```

---

## 3. Vendor Identifier Format

The `vendor_id` field identifies the vendor or package. It uses a namespaced format to avoid collisions between ecosystems.

### 3.1 Format Rules

A `vendor_id` MUST match the pattern:

```
vendor_id = [namespace ":"] slug
namespace = 1*( ALPHA / DIGIT )
slug      = 1*( ALPHA / DIGIT / "-" / "_" )
```

### 3.2 Namespace Conventions

| Namespace | Meaning | Example |
|---|---|---|
| (none) | Named company or service, globally unique | `stripe`, `anthropic`, `github` |
| `npm` | npm registry package | `npm:lodash`, `npm:express` |
| `pypi` | Python Package Index package | `pypi:requests`, `pypi:django` |
| `cargo` | Rust crates.io package | `cargo:serde`, `cargo:tokio` |
| `gem` | RubyGems package | `gem:rails`, `gem:devise` |
| `maven` | Maven Central artifact | `maven:org.springframework:spring-core` |
| `go` | Go module | `go:golang.org/x/net` |
| `docker` | Docker Hub image | `docker:nginx`, `docker:postgres` |
| `ghcr` | GitHub Container Registry image | `ghcr:myorg/myimage` |
| `gh` | GitHub repository | `gh:facebook/react` |

### 3.3 No-namespace Vendor IDs

Vendor IDs without a namespace represent named services and companies. The ChangeSpec registry (maintained by Roboticforce Inc.) is the canonical source for no-namespace vendor IDs. Registry submissions are open.

### 3.4 Slug Character Set

Slugs are lowercase. Producers MUST normalize slugs to lowercase. Scoped npm packages use the scoped name with the `@` replaced by a hyphen and `/` by a hyphen: `npm:-angular-core` is not valid; use `npm:angular-core` (dropping the `@angular/` scope prefix) or the full scoped form `npm:@angular/core` where `@` and `/` are preserved as literals (conforming consumers MUST accept both forms).

---

## 4. Category Taxonomy

The `category` field classifies what kind of change this event represents. Categories drive routing and filtering in consuming systems.

| Value | Description |
|---|---|
| `api_breaking` | A change to a public API, SDK, or service interface that is not backward compatible. Callers that do not update their code will break. |
| `api_deprecation` | A feature, endpoint, parameter, or behavior is deprecated and will be removed in a future version. Not immediately breaking. Carries a sunset date. |
| `security` | A security vulnerability, patch, or advisory. Use this for CVEs, credential exposure risks, authentication changes that affect security posture, and similar events. |
| `data_handling` | A change to how user or customer data is stored, processed, shared, or retained. Covers DPA changes, subprocessor additions or removals, data residency changes, and retention policy updates. |
| `liability` | A change to terms of service, SLA, indemnification clauses, limitation of liability, or warranty terms. |
| `pricing` | A change to pricing, billing, plan limits, free tier entitlements, or trial terms. |
| `tos` | A change to terms of service, acceptable use policy, or community guidelines not covered by `liability`. Use `liability` when the change specifically affects legal liability. Use `tos` for general policy changes. |
| `cosmetic` | A change to documentation, UI text, marketing copy, or visual design. No functional impact. |
| `informational` | A change that does not fit other categories and requires no action. General announcements, roadmap previews, deprecation notices without a concrete sunset date. |
| `retraction` | A previously published version or artifact is being retracted. Use for supply-chain compromises, accidental publishes, policy violations, or any case where consumers must stop using a previously distributed artifact. When present, `do_not_install` SHOULD be `true` and `last_known_good_version` SHOULD identify the safe pin target. |

### 4.1 Category Selection Guidance

Categories are mutually exclusive. A single event has one category. When a change fits multiple categories, use the most specific or highest-impact category:

- A DPA update that also constitutes a TOS change: use `data_handling`
- A security patch that also breaks an API: use `security`
- A pricing change that is also a TOS update: use `pricing`
- A new subprocessor announced in a blog post: use `data_handling`

When uncertain, prefer the category that triggers the most appropriate routing for consuming teams. `informational` is the appropriate default for ambiguous changes with no clear impact.

---

## 5. Severity Taxonomy

The `severity` field communicates urgency and potential impact.

| Value | Description |
|---|---|
| `critical` | Immediate action required. Examples: actively exploited vulnerability (CVSS >= 9.0), breaking change already in production with no migration path, data breach notification. |
| `high` | Action required within a short timeframe (days to weeks). Examples: breaking API change with migration path, CVSS 7.0-8.9 vulnerability, major pricing increase with short notice. |
| `medium` | Action required before a future deadline. Examples: deprecation with a 6-month sunset, CVSS 4.0-6.9 vulnerability, subprocessor change requiring DPA review. |
| `low` | Advisory. No immediate action required. Examples: long-horizon deprecations, minor pricing restructuring with no net increase, informational TOS clarification. |
| `informational` | No action required. Purely informational. Examples: documentation improvements, minor wording changes, cosmetic updates. |

### 5.1 Severity and Category Relationship

Not all category-severity combinations make sense. The following are RECOMMENDED pairings:

| Category | Typical Severity Range |
|---|---|
| `api_breaking` | `high` to `critical` |
| `api_deprecation` | `low` to `medium` |
| `security` | `medium` to `critical` |
| `data_handling` | `medium` to `high` |
| `liability` | `medium` to `high` |
| `pricing` | `low` to `high` |
| `tos` | `low` to `medium` |
| `cosmetic` | `informational` |
| `informational` | `informational` to `low` |

Producers MAY deviate from these ranges when warranted. Consumers MUST NOT assume a fixed mapping between category and severity.

---

## 6. Source Attribution

The `source_type` field communicates how this event was produced and how much trust a consumer should place in the classification.

| Value | Description |
|---|---|
| `publisher_verified` | The vendor that owns the `vendor_id` pushed this event directly through a publisher API. The event reflects the vendor's own characterization of the change. Eligible for signing (see Section 7). |
| `crawled` | The event was generated by an automated system that detected a change in vendor documentation, a changelog, or a policy document. Classification was performed by AI or automated rules. `confidence_score` SHOULD be set. |
| `community` | The event was submitted by a community member who is not the vendor. Subject to moderation. `confidence_score` SHOULD be set lower than for `crawled` unless independently verified. |

### 6.1 Confidence Score

The `confidence_score` field is a float in [0.0, 1.0]:

- `publisher_verified` events: SHOULD be `1.0`
- `crawled` events: SHOULD reflect AI model confidence in the classification. Values below `0.7` indicate uncertain classification and SHOULD trigger human review before delivery.
- `community` events: producers SHOULD default to `0.6` unless verification steps have been performed.

---

## 7. Signing and Verification

Publisher-verified events MAY be signed using Ed25519 to allow consumers to verify authenticity. This section defines the signature object structure, canonicalization scheme, key distribution mechanism, and verification procedure. Implementers MUST also read Section 12 (Security Considerations) for the full threat model and implementation requirements.

### 7.1 Why Ed25519

Ed25519 provides compact signatures (64 bytes), fast verification, deterministic nonce derivation (no weak-random risk), and is implemented in the Go standard library (`crypto/ed25519`), Node.js (`crypto`), and Python (`cryptography` package). RSA is not recommended due to key size overhead and parameter confusion risks.

Implementations MUST use strict Ed25519 verification as defined in RFC 8032, specifically:

- Reject signatures where the scalar S is not in `[0, ell)` (the subgroup order).
- Reject non-canonical encodings of the point R.
- Reject signatures using small-order or low-order public keys.

These requirements eliminate signature malleability vulnerabilities. See "Taming the Many EdDSAs" (Chalkias, Garillot, Kondi 2020) for background.

### 7.2 Signature Object

When present, the `signature` field is an object:

```json
{
  "signature": {
    "alg": "ed25519",
    "key_id": "stripe-2026-01",
    "value": "<base64url-encoded 64-byte signature>",
    "signed_fields": [
      "specversion", "id", "vendor_id", "category", "severity",
      "title", "summary", "published_at", "source_type",
      "signature.alg", "signature.key_id", "signature.signed_fields"
    ],
    "key_fingerprint": "<optional base64url SHA-256 fingerprint of public key>"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `alg` | string | REQUIRED | Signature algorithm. Must be `"ed25519"` in version 1.0. |
| `key_id` | string | REQUIRED | Identifies the signing key. Pattern: `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$`. Key resolution is scoped by `(vendor_id, key_id)`. |
| `value` | string | REQUIRED | Base64url-encoded Ed25519 signature (64 bytes, no padding). |
| `signed_fields` | array of string | REQUIRED | The list of field names covered by the signature. Must include all required fields plus signature metadata. See Section 7.3 for the mandatory minimum. |
| `key_fingerprint` | string | OPTIONAL | SHA-256 fingerprint of the public key, base64url-encoded without padding (43 characters). When present, consumers MUST verify the resolved key matches this fingerprint. |

### 7.3 Signature Input Construction

The signature input MUST be constructed as follows. Deviating from this procedure produces incompatible signatures.

**Step 1 - Domain separator.** Begin the byte string with the exact UTF-8 bytes:

```
ChangeSpec-Signature-1.0\n
```

This is 24 bytes (23 ASCII characters plus one LF byte, `0x0A`). This domain separator prevents cross-protocol signature reuse: the same Ed25519 key used for other purposes cannot be exploited to forge ChangeSpec signatures.

**Step 2 - Typed envelope.** Append the JCS (RFC 8785) canonicalization of a JSON object with exactly the following members, in this order as required by JCS key ordering (UTF-16 code point order):

```json
{
  "alg": "<signature.alg from the event>",
  "key_id": "<signature.key_id from the event>",
  "payload": { <field_name>: <field_value>, ... },
  "signed_fields": ["<field1>", "<field2>", ...],
  "vendor_id": "<vendor_id from the event>"
}
```

Where `payload` is a JSON object containing exactly the field name and parsed JSON value for each field listed in `signed_fields`. The `signed_fields` array MUST be included in the `payload` object under the key `"signed_fields"`. JCS produces a byte-exact canonical form regardless of JSON serialization choices (number formatting, key ordering, Unicode escaping).

**Mandatory minimum for `signed_fields`.** The `signed_fields` array MUST contain every field from the following set that is present in the event:

Required event fields (always present):
- `specversion`, `id`, `vendor_id`, `category`, `severity`, `title`, `summary`, `published_at`, `source_type`

Signature metadata (always required in `signed_fields`):
- `signature.alg`, `signature.key_id`, `signature.signed_fields`

Security-critical optional fields (required in `signed_fields` when present):
- `cve_id`, `cvss_score`, `cvss_vector`, `fixed_in_version`, `action_required`
- `effective_date`, `sunset_date`
- `source_url`, `migration_url`
- `affected_versions`
- `provenance_invalidated`, `do_not_install`, `last_known_good_version`, `retraction_reason`, `supersedes`

Consumers MUST reject events where `signed_fields` omits any field from the mandatory minimum that is present in the event. This prevents an attacker from stripping security-critical fields from a signed event while keeping the signature valid.

**Step 3 - Sign.** Sign the concatenation of the domain separator (Step 1) and the JCS-encoded envelope (Step 2) using Ed25519 in strict mode.

**Replay protection.** `published_at` is a required event field and therefore always in `signed_fields`. Consumers MUST enforce the freshness window defined in Section 12.7.

**Cryptographic binding of vendor_id to key_id.** `vendor_id` appears both in the event and in the typed envelope. Key lookup MUST be scoped: consumers MUST look up the key as `(vendor_id, key_id)`, not `key_id` alone. A key registered for `vendor_id: "attacker"` MUST NOT be accepted as valid for `vendor_id: "stripe"` even if the `key_id` matches.

### 7.4 Key Distribution

Vendors publish their Ed25519 public keys at a well-known URL:

```
https://{vendor-domain}/.well-known/changespec-keys.json
```

The key document format:

```json
{
  "vendor_id": "stripe",
  "keys": [
    {
      "key_id": "stripe-2026-01",
      "alg": "ed25519",
      "public_key": "<base64url-encoded 32-byte public key>",
      "valid_from": "2026-01-01T00:00:00Z",
      "valid_until": "2027-01-01T00:00:00Z"
    }
  ],
  "revoked_keys": [
    {
      "key_id": "stripe-2025-01",
      "revoked_at": "2026-02-01T00:00:00Z",
      "reason": "routine rotation"
    }
  ]
}
```

Key document requirements:

- The document MUST be served over HTTPS with a valid certificate.
- The document MUST be served with `Cache-Control: max-age=3600, must-revalidate` or stricter.
- The document MUST include an `ETag` header that changes when any key is added, removed, or revoked.
- Key `valid_until` MUST NOT exceed one year from `valid_from`. Producers SHOULD rotate keys annually.
- The ChangeSpec platform registry mirrors vendor public keys. Key pinning via the registry is RECOMMENDED for consumers.
- Key resolution by consumers MUST be scoped by `vendor_id`. The lookup is `(vendor_id, key_id) -> public_key`, not `key_id -> public_key`.

### 7.5 Verification Steps

A conforming consumer verifying a signed event MUST:

1. Check that `source_type` is `publisher_verified`. If not, the event cannot carry a valid ChangeSpec signature.
2. Retrieve the public key for `(vendor_id, key_id)` from the key registry, scoping the lookup to the event's `vendor_id`. Reject if no key is found.
3. Check that `key_id` is not in the `revoked_keys` list of the key document.
4. Check that the current time is within the key's `valid_from`/`valid_until` window (allow 300 seconds of clock skew).
5. Check that `published_at` is within the consumer's configured freshness window (default: no more than 90 days in the past, no more than 300 seconds in the future).
6. Check that `signature.signed_fields` includes all fields required by Section 7.3's mandatory minimum that are present in the event.
7. Construct the signature input per Section 7.3 (domain separator + JCS-encoded typed envelope).
8. Verify the Ed25519 signature in strict mode against the resolved public key.
9. If `key_fingerprint` is present, verify the resolved public key's SHA-256 fingerprint matches.
10. Reject the event if any step fails.

Consumers MAY accept events where `signature` is absent if the consumer does not require signing (e.g., when consuming from a trusted platform that has already verified signatures upstream). A `publisher_verified` event without a verified signature carries the same trust level as a `crawled` event.

### 7.6 Key Separation from CI/CD Systems

The integrity of ChangeSpec signatures depends on the signing key being under exclusive control of an authorized human or hardware security module (HSM). Signing keys used for ChangeSpec events MUST NOT be present in the CI/CD environment that builds or publishes package artifacts.

This requirement addresses the supply-chain attack pattern where a compromised CI pipeline can publish malicious artifacts while producing valid SLSA provenance. If the ChangeSpec signing key is also in CI, the attacker can additionally forge or suppress RETRACTION events, eliminating the one signal that could alert consumers.

**Anti-patterns that violate this requirement:**
- Storing the ChangeSpec signing key in GitHub Actions secrets or CI environment variables.
- Using the same key for both package registry publish operations and ChangeSpec event signing.
- Deriving the ChangeSpec signing key from any value accessible in the build environment.

**Recommended storage:**
1. Hardware security key (e.g., YubiKey 5 with PIV) held by a designated maintainer.
2. KMS-backed signing in a separate cloud account with no network path from the build environment.

Consumers SHOULD treat RETRACTION events signed with a key known to have been in the CI environment as having reduced trust, equivalent to `source_type: crawled`.

---

## 8. Envelope Format

### 8.1 Standalone Format

The default transport format is a standalone JSON object. The event fields defined in this spec are the top-level keys.

### 8.2 CloudEvents Envelope

ChangeSpec events MAY be transported inside a CloudEvents 1.0 envelope. This allows ChangeSpec events to ride existing CloudEvents infrastructure without modification.

Mapping:

| CloudEvents Field | Value |
|---|---|
| `specversion` | `"1.0"` (CloudEvents version) |
| `id` | The ChangeSpec event `id` |
| `source` | `"https://changespec.com/vendors/{vendor_id}"` |
| `type` | `"com.changespec.change.v1"` |
| `datacontenttype` | `"application/json"` |
| `time` | The ChangeSpec `published_at` value |
| `data` | The complete ChangeSpec event object |

Note that `specversion` is reused by CloudEvents for its own version. When using the CloudEvents envelope, the ChangeSpec `specversion` field is embedded inside `data`. Consumers reading the CloudEvents envelope MUST look for the ChangeSpec `specversion` inside `data`, not at the envelope level.

Example CloudEvents envelope:

```json
{
  "specversion": "1.0",
  "id": "cs_01HXYZ1234ABCD",
  "source": "https://changespec.com/vendors/stripe",
  "type": "com.changespec.change.v1",
  "datacontenttype": "application/json",
  "time": "2026-04-10T14:00:00Z",
  "data": {
    "specversion": "1.0",
    "id": "cs_01HXYZ1234ABCD",
    "vendor_id": "stripe",
    "category": "api_breaking",
    "severity": "high",
    "title": "confirm() now requires return_url parameter",
    "summary": "...",
    "published_at": "2026-04-10T14:00:00Z",
    "source_type": "publisher_verified"
  }
}
```

---

## 9. Transport Bindings

ChangeSpec defines four transport bindings. Platforms are free to implement any or all of them.

### 9.1 HTTPS POST Webhook

The event is delivered as an HTTP POST request with:

- `Content-Type: application/json`
- Body: standalone ChangeSpec event JSON

The delivery endpoint is configured by the consumer. The platform delivering the event SHOULD implement retry with exponential backoff for non-2xx responses.

Webhook security (payload signing, shared secrets, replay prevention) is outside the scope of ChangeSpec. Platforms SHOULD follow the Standard Webhooks specification (standardwebhooks.com) for webhook delivery signing.

### 9.2 MCP (Model Context Protocol)

ChangeSpec events are returned by MCP tool calls as JSON objects. Conforming MCP implementations MUST return the standalone ChangeSpec event format (Section 8.1) in tool responses. Events returned by MCP tools MAY be truncated (omitting large optional fields such as `affected_sections`) when context length is a concern; truncation MUST be indicated by setting `_truncated: true` in the returned object.

### 9.3 RSS/Atom Feed

ChangeSpec events MAY be published as RSS 2.0 or Atom 1.0 feed items. The following field mapping applies:

**RSS 2.0:**

| RSS Field | ChangeSpec Source |
|---|---|
| `<title>` | `title` |
| `<description>` | `summary` |
| `<link>` | `source_url` |
| `<pubDate>` | `published_at` (RFC 822 format) |
| `<guid>` | `id` |
| `<category>` | `category` |

The full ChangeSpec event object SHOULD be embedded as a `<changespec:event>` extension element with namespace `xmlns:changespec="https://changespec.com/ns/1.0"`.

**Atom 1.0:**

| Atom Field | ChangeSpec Source |
|---|---|
| `<title>` | `title` |
| `<summary>` | `summary` |
| `<link rel="alternate">` | `source_url` |
| `<published>` | `published_at` |
| `<id>` | `id` |

### 9.4 Polling API

Platforms providing a polling API MUST return events in the following envelope:

```json
{
  "events": [
    { ... ChangeSpec event ... },
    { ... ChangeSpec event ... }
  ],
  "next_cursor": "opaque-pagination-token",
  "has_more": true
}
```

Consumers paginate by passing `cursor=<next_cursor>` in subsequent requests. The `next_cursor` format is platform-specific and opaque to consumers.

---

## 10. Extension Fields

Producers MAY add extension fields to ChangeSpec events. Extension fields MUST use the `ext:` prefix followed by a namespace and field name:

```
ext:<namespace>.<fieldname>
```

Examples:

```json
{
  "ext:compliance.osfi_b10": true,
  "ext:compliance.dora_article": "32",
  "ext:internal.ticket_id": "ENG-4521",
  "ext:risk.vendor_tier": 1
}
```

Extension field namespaces SHOULD be registered to avoid conflicts. A public namespace registry is maintained at `changespec.com/extensions`. Unregistered namespaces are permitted but may conflict with future registered namespaces.

Conforming consumers MUST ignore unknown extension fields without error.

Core spec fields (Section 1) MUST NOT use the `ext:` prefix. The `ext:` namespace is reserved exclusively for extension fields.

---

## 11. Backward Compatibility Rules

### 11.1 Producer Rules

- Producers MUST set `specversion` to the version of this spec they conform to.
- Producers MUST NOT remove required fields.
- Producers MAY add extension fields at any time.

### 11.2 Consumer Rules

- Consumers MUST ignore fields they do not recognize, including extension fields.
- Consumers MUST NOT reject events solely because they contain unknown fields.
- Consumers MUST reject events where `specversion` indicates an incompatible major version (e.g., a 1.0 consumer receiving a `specversion: "2.0"` event MAY reject it).

### 11.3 Spec Evolution Rules

- **Patch releases** (1.0.1): Clarifications only. No field additions, removals, or semantic changes.
- **Minor releases** (1.1, 1.2): May add optional fields. May extend enum values in `category` and `severity`. Existing values MUST NOT be removed or redefined. A 1.0 consumer receiving a 1.1 event with an unknown category value SHOULD treat it as `informational`.
- **Major releases** (2.0): May change required fields, redefine semantics, or make breaking changes. Require a formal deprecation period of at least 12 months.

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
- That consumers perform automated actions safely. Agent safety is addressed in Section 12.13.

### 12.2 Event Authenticity

An event's authenticity comprises origin authentication (the claimed producer actually issued the event) and content integrity (the event has not been modified since issuance). ChangeSpec provides cryptographic authenticity only for `source_type: publisher_verified` events that carry a `signature` object conforming to Section 7.

Consumers MUST NOT treat unsigned events as authentic regardless of their `source_type` value. A `source_type: publisher_verified` event without a valid `signature` carries the same trust level as a `source_type: crawled` event.

Consumers MUST verify signatures for untrusted transports. Consumers that receive events through a trusted platform that has performed verification MAY defer to the platform's verification result, provided the platform's identity and verification behaviour is established by policy.

### 12.3 Signature Input Canonicalization

The signature input construction in Section 7.3 MUST be followed exactly. Implementations that deviate will produce signatures incompatible with other implementations and will create a risk of semantic confusion: a signature valid under one canonicalization may authenticate a different semantic event under another canonicalization.

The signature input is constructed over a specific subset of fields enumerated in the `signed_fields` array. The following rules apply:

1. The `signed_fields` array MUST contain at minimum every required event field (see Section 1.1), the `signature.alg`, `signature.key_id`, and `signature.signed_fields` values, and every field from the following set that is present in the event: `cve_id`, `cvss_score`, `cvss_vector`, `fixed_in_version`, `effective_date`, `sunset_date`, `action_required`, `migration_hint`, `migration_url`, `source_url`, `affected_versions`.
2. The `signed_fields` array itself MUST be part of the signature input (included in the typed envelope's `payload` object as `signed_fields`).
3. The signature input MUST begin with the domain separator `ChangeSpec-Signature-1.0\n` (24 UTF-8 bytes, terminated by a single LF character). This prevents cross-protocol signature reuse.
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
2. **Key transparency log.** The producer publishes its key rotations to an append-only transparency log (see the ChangeSpec trust-bootstrap specification for the proposed v1.1 mechanism). Consumers verify that the served key appears in the log at a position consistent with the log's Merkle tree.
3. **Multi-party cosigning.** The producer's key is co-signed by a quorum of independent cosigners. Consumers verify that at least a policy-defined quorum of cosigners have attested to the key.

At launch, key pinning is the only mechanism formally available. Consumers that cannot pin MUST NOT treat signed events as more trustworthy than unsigned events from the same producer. This is a known gap; see Section 12.20.

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

1. Reject events with `published_at` more than the consumer's configured retention window in the past. Recommended default: 90 days. Consumer-facing documentation MUST state the configured window.
2. Reject events with `published_at` more than 300 seconds (5 minutes) in the future, accounting for clock skew.
3. Deduplicate events by the tuple `(vendor_id, id)`. When a duplicate `id` is received with a later `published_at`, treat the newer event as an authoritative replacement.

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

The `source_url` and `migration_url` fields are restricted to the `https://` scheme by the JSON Schema (Section 1.3 and schema.json). Consumers that fetch, render, or pass these URLs downstream MUST:

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

Extension fields MUST NOT be used to carry executable content, code, credentials, personal data requiring special handling, or content that requires special legal treatment.

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

ChangeSpec signing keys used to authenticate RETRACTION events MUST be stored separately from any secrets accessible by the build pipeline that publishes package artifacts (see Section 7.6). An attacker controlling CI can publish malicious artifacts with valid SLSA provenance; if they also hold the ChangeSpec key, they can suppress the RETRACTION event that would alert consumers.

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
- No event retraction sequence numbers. The v1.1 `retraction` category and `supersedes` field enable retraction events, but there is no signed sequence number enforcing monotonic ordering between a RELEASE and its RETRACTION. Consumers SHOULD obtain events from a single trusted ordered source rather than relying on event timestamps alone.
- No producer sequence numbers. Ordering between events from the same producer relies on `published_at` timestamps rather than signed sequence numbers. Signed sequence numbers are planned for v1.1.
- Post-quantum readiness. Ed25519 is not post-quantum secure. A hybrid signature scheme is planned for v2.0.

---

## 13. Integration Safety

ChangeSpec MUST NEVER be the reason a developer's build, deploy, test run, or IDE session fails. This is a load-bearing product requirement.

All client integrations (CLI, MCP server, webhook consumers, SDKs) MUST conform to the Integration Safety specification. The full requirements are in `integration-safety.md` in this repository.

The key obligations, summarized:

- **Fail open.** Infrastructure failures MUST NOT produce non-zero exit codes in advisory mode or `isError: true` in MCP responses.
- **Hard timeouts.** Every outbound API call MUST time out within 2 seconds (interactive) or 5 seconds (batch). No hanging.
- **Always bypassable.** `CHANGESPEC_SKIP=1` MUST disable all network calls and return immediately. Document this in every integration.
- **Advisory by default.** Blocking behavior (non-zero exit on findings) requires explicit user opt-in via `--fail-on`. It is never the default.
- **Cache-first.** Every integration MUST cache the last successful response locally and serve from cache when the API is unavailable.
- **Circuit breaker.** After 3 consecutive failures, integrations MUST open the circuit and stop retrying for 120 seconds.
- **No forced upgrades.** Old client versions MUST continue to work against the current API. Breaking changes require a 12-month deprecation window.

See `integration-safety.md` for MUST/SHOULD conformance language, timeout tables, circuit breaker pseudocode, cache file format, degraded response envelopes, and the 10 mandatory conformance test scenarios.

See `spec/conformance/test-vectors/safety/` for the machine-readable test vectors.

---

## Appendix A: Field Quick Reference

**Required fields:** `specversion`, `id`, `vendor_id`, `category`, `severity`, `title`, `summary`, `published_at`, `source_type`

**Security fields:** `cve_id`, `cvss_score`, `cvss_vector`, `fixed_in_version`

**Version fields:** `affected_versions`, `fixed_in_version`

**Temporal fields:** `published_at`, `effective_date`, `sunset_date`

**Guidance fields:** `migration_hint`, `migration_url`, `action_required`, `recommended_reviewers`

**Attribution fields:** `source_url`, `source_type`, `confidence_score`

**Targeting fields:** `affected_systems`, `affected_sections`, `tags`

**Signing fields:** `signature`

---

## Appendix B: MIME Type

The MIME type for a ChangeSpec event document is:

```
application/vnd.changespec+json
```

When serving events over HTTP, producers SHOULD set `Content-Type: application/vnd.changespec+json`.

---

## Appendix C: Normative References

- RFC 2119: Key words for use in RFCs to Indicate Requirement Levels
- RFC 3339: Date and Time on the Internet: Timestamps
- RFC 3986: Uniform Resource Identifier (URI): Generic Syntax
- RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA)
- RFC 8259: The JavaScript Object Notation (JSON) Data Interchange Format
- RFC 8785: JSON Canonicalization Scheme (JCS)
- RFC 8996: Deprecating TLS 1.0 and TLS 1.1
- RFC 9110: HTTP Semantics
- BCP 195: Recommendations for Secure Use of TLS and DTLS
- JSON Schema draft 2020-12: https://json-schema.org/draft/2020-12
- CloudEvents 1.0: https://github.com/cloudevents/spec/blob/v1.0/cloudevents/spec.md
- Semantic Versioning 2.0.0: https://semver.org
- Standard Webhooks: https://standardwebhooks.com
- CVE format: https://www.cve.org
- CVSS 3.1: https://www.first.org/cvss
- SLSA v1.0: Supply-chain Levels for Software Artifacts (https://slsa.dev)

## Appendix D: Changes from Draft to 1.0.0

This appendix documents the security and conformance fixes applied between the initial draft and the 1.0.0 release. These changes were identified by the pre-launch security review (threat-model.md) and conformance audit (run-against-references.md).

### Signature System Overhaul

**SIG-01 (Canonicalization under-specified) - FIXED.**
Section 7.3 now mandates JCS (RFC 8785) over a typed envelope. The previous ad-hoc concatenation scheme was replaced with a byte-exact canonical form that handles strings, numbers, arrays, objects, and Unicode without ambiguity.

**SIG-02 (signed_fields self-reference vulnerability) - FIXED.**
The `signed_fields` array is now included in the typed envelope's `payload` object, meaning it is covered by the signature. A mandatory minimum field set is defined; consumers MUST reject events whose `signed_fields` omits required fields.

**SIG-03 (No domain separation) - FIXED.**
Section 7.3 now requires the 24-byte domain separator `ChangeSpec-Signature-1.0\n` prepended to every signature input. This prevents cross-protocol signature reuse.

**SIG-04 (No replay protection) - FIXED.**
`published_at` is now a required member of the mandatory signed-field minimum. Section 12.7 defines mandatory freshness enforcement: consumers MUST reject events more than 90 days old (recommended) or more than 5 minutes in the future.

**SIG-05 (No vendor_id to key_id binding) - FIXED.**
`vendor_id` is now part of the typed envelope. Section 7.3 and 7.4 now explicitly require key resolution to be scoped by `(vendor_id, key_id)`. A key registered for one vendor cannot be used to sign events claiming a different `vendor_id`.

**SIG-06 (Trust bootstrap under-specified) - PARTIALLY ADDRESSED.**
Section 12.5 now defines three acceptable trust bootstrap mechanisms (key pinning, transparency log, multi-party cosigning). Key pinning is the formally available mechanism for v1.0; a full key-transparency mechanism is planned for v1.1. This is a known gap documented in Section 12.20.

### Schema Hardening

**GEN-01 (Schema divergence between implementations) - FIXED.**
The Go reference implementation now embeds the canonical schema.json via `//go:embed` rather than a hand-maintained simplified inline schema. This eliminates drift between implementations.

**GEN-02 (URL scheme not restricted) - FIXED.**
`source_url` and `migration_url` now carry a `pattern: "^https://"` constraint in schema.json. `file://`, `gopher://`, `javascript:`, `data:`, and other non-HTTPS schemes are rejected at the schema level.

### Additional Schema and Spec Fixes

**TS-01 (TypeScript .passthrough() prototype pollution risk) - FIXED.**
The TypeScript reference's extension field handling now explicitly filters against the `__proto__`, `constructor`, and `prototype` key names before returning the extensions map.

**PY-01 (Python build-backend invalid) - FIXED.**
`pyproject.toml` `build-backend` corrected from the non-existent `setuptools.backends.legacy:build` to the correct `setuptools.build_meta`.

### Conformance Gaps Closed

All 10 conformance gaps identified in the audit are closed:

1. Go: canonical schema.json embedded via `//go:embed`
2. Go: `date-time` format enforced on `published_at`
3. Go: `date` format enforced on `effective_date` and `sunset_date`
4. Go: `uri` format enforced on `source_url` and `migration_url`
5. Go: `https://` scheme pattern enforced for URL fields
6. Go: `cvss_vector` pattern enforced
7. Go: `tags` item lowercase pattern enforced
8. TypeScript: prototype-pollution key names rejected from extensions map
9. Python: build-backend corrected
10. Python: Pydantic 2.x `Annotated[str, Field(...)]` syntax adopted for all constrained fields

---

## Appendix E: Retraction Event Example

The following example shows a ChangeSpec RETRACTION event for a supply-chain compromise where malicious versions were published by a compromised CI pipeline. The `provenance_invalidated` field is critical: SLSA attestations for the affected versions are cryptographically valid because they were generated by the project's legitimate CI infrastructure. The attacker ran code *inside* the build pipeline. Consumers that verify SLSA provenance and stop there will not detect the compromise - ChangeSpec's RETRACTION, signed by an out-of-band key the attacker did not hold, is the orthogonal signal.

```json
{
  "specversion": "1.1",
  "id": "cs_01HZRT8K2N5P9Q3T6V8W4Y2B1",
  "vendor_id": "npm:@tanstack/react-query",
  "category": "retraction",
  "severity": "critical",
  "title": "Retraction: versions 5.62.4-5.62.5 contain malicious payload",
  "summary": "Versions 5.62.4 and 5.62.5 were published by a compromised CI pipeline and contain a credential-harvesting payload. Do not install. Pin to 5.62.3. Rotate any secrets in environments that ran npm install between 2026-05-10T14:08Z and 14:28Z.",
  "published_at": "2026-05-10T14:47:00Z",
  "source_type": "publisher_verified",
  "affected_versions": "5.62.4 || 5.62.5",
  "action_required": true,
  "do_not_install": true,
  "last_known_good_version": "5.62.3",
  "provenance_invalidated": true,
  "retraction_reason": "supply_chain_compromise",
  "retraction_indicators": ["credential_exfiltration", "unauthorized_publish", "ci_pipeline_compromise"],
  "migration_hint": "Pin to 5.62.3. Rotate npm tokens, GitHub tokens, and cloud credentials from affected environments.",
  "source_url": "https://tanstack.com/incidents/2026-05-10",
  "recommended_reviewers": ["security", "engineering"],
  "confidence_score": 1.0,
  "signature": {
    "alg": "ed25519",
    "key_id": "tanstack-2026-q2-offline",
    "value": "<base64url-encoded signature>",
    "signed_fields": [
      "specversion", "id", "vendor_id", "category", "severity",
      "title", "summary", "published_at", "source_type",
      "affected_versions", "action_required", "do_not_install",
      "last_known_good_version", "provenance_invalidated",
      "retraction_reason", "retraction_indicators",
      "migration_hint", "source_url", "confidence_score",
      "signature.alg", "signature.key_id", "signature.signed_fields"
    ]
  }
}
```
