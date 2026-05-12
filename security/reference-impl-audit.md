# Reference Implementation Security Audit

This document is a line-by-line security audit of the three reference implementations at `spec/reference/{go,typescript,python}`. Findings are grouped by implementation and prioritized.

---

## Snyk Scanning

**Status: NOT EXECUTED LOCALLY.** The CLAUDE.md instructs using Snyk MCP tools (`snyk_code_scan`, `snyk_sca_scan`, `snyk_iac_scan`) for security scanning. The current environment does not expose Snyk MCP tools (only `plugin:posthog:posthog` is listed in MCP server instructions), and the `snyk` CLI is not installed on the system. I documented this explicitly and used manual static analysis augmented by direct vulnerability database lookups.

Dependency vulnerability checks performed manually by consulting public databases (Snyk security advisories, GitHub Advisory Database, OSV):

| Dependency | Version | Language | Status (as of 2026-04-16) |
|---|---|---|---|
| `github.com/santhosh-tekuri/jsonschema/v6` | v6.0.1 | Go | No known CVEs. Actively maintained. |
| `golang.org/x/text` | v0.14.0 | Go (indirect) | No known CVEs at this version. |
| `zod` | 4.3.6 | npm | No known CVEs at this version. Earlier 3.x had CVE-2023-4316 (ReDoS) - not applicable. |
| `@types/node` | 25.6.0 | npm dev | Type definitions only. No runtime risk. |
| `typescript` | 6.0.2 | npm dev | No known CVEs. |
| `pydantic` | 2.13.1 | pip | No known CVEs. Historical CVEs (CVE-2021-29510, CVE-2020-10735) apply only to 1.x. |
| `setuptools` | 80.9.0 | pip build | No known CVEs at this version. |
| `wheel` | 0.45.1 | pip build | No known CVEs at this version. |
| `pytest` | 8.4.1 | pip dev | No known CVEs. |

**Recommendation:** Re-run Snyk MCP scans before v1.0 launch. If CLI is not available, enable the Snyk MCP server in the security-review environment and re-execute `snyk_sca_scan` and `snyk_code_scan` on each reference implementation.

---

## Cross-Cutting Findings (All Implementations)

### Finding X-01: No JSON parser hardening (High)

**OWASP:** A05 (Security Misconfiguration), A06 (Vulnerable Components).

All three reference implementations use language-default JSON parsers with no configuration for:

- Maximum payload size
- Maximum JSON nesting depth
- Rejection of duplicate keys
- Rejection of trailing data
- Rejection of BOM/NBSP prefixes
- Maximum object key count
- Maximum string length per field (beyond schema limits applied after parsing)

Any untrusted input can cause memory exhaustion or parser confusion before schema validation runs.

**Location:**

- `spec/reference/go/validate.go` line 112: `json.Unmarshal(data, &v)` - no limits.
- `spec/reference/typescript/src/validate.ts`: `EventSchema.safeParse(raw)` - the caller is responsible for JSON.parse, no limits.
- `spec/reference/python/changespec/validate.py` line 36: `json.loads(raw)` - no limits.

**Fix:** add a bounded-depth, bounded-size pre-validation pass. Reference code pattern:

```python
MAX_EVENT_BYTES = 65536
MAX_JSON_DEPTH = 32

def _check_bounds(raw: bytes | str) -> None:
    data = raw.encode() if isinstance(raw, str) else raw
    if len(data) > MAX_EVENT_BYTES:
        raise ValueError("event exceeds maximum size")
    # Scan depth without full parse
    depth = max_depth = 0
    for c in data:
        if c in b"[{":
            depth += 1
            max_depth = max(max_depth, depth)
        elif c in b"]}":
            depth -= 1
    if max_depth > MAX_JSON_DEPTH:
        raise ValueError("JSON too deeply nested")
```

### Finding X-02: No signature verification implementation (Critical)

**OWASP:** A02 (Cryptographic Failures).

All three reference implementations parse the `signature` block but NONE of them verify the Ed25519 signature. They accept `signature.alg`, `signature.key_id`, `signature.value`, `signature.signed_fields` as data and do nothing with them.

For a spec that centers cryptographic signing as a critical feature, the reference implementations must implement verification. Otherwise every downstream user implements it themselves, with varying correctness.

**Fix:** add a `verify(event, public_key)` function to each reference implementation that:

1. Reconstructs the signature input per revised Section 7.3 (JCS + envelope).
2. Verifies the Ed25519 signature in strict mode.
3. Returns a typed result (Verified, BadSignature, WrongAlg, etc.).

The reference implementation is not a trust-bootstrap implementation - that is a separate library. But signature-over-known-key verification belongs in the spec's reference code.

### Finding X-03: No fuzzing harness (Medium)

**OWASP:** A04 (Insecure Design).

A spec this security-critical must have fuzz testing for parser correctness. None of the three reference implementations ship with a fuzz harness.

**Fix:**

- Go: `FuzzValidate` target using Go 1.18+ native fuzzing.
- TypeScript: `jest-fuzz` or `@fast-check/fuzz`.
- Python: `hypothesis` or `atheris` (Google's Python coverage-guided fuzzer).

Run nightly with a 15-minute budget per implementation. Gate v1.0 release on zero panics/crashes after 100 million executions.

### Finding X-04: No tests for malicious input (High)

**OWASP:** A04 (Insecure Design).

The existing test suites validate positive cases (valid events) and a small set of negative cases (missing fields, wrong specversion). They do not test:

- Oversized payloads
- Deeply nested JSON
- Duplicate keys
- Non-HTTPS URLs
- URL schemes like `javascript:`, `data:`, `file:`
- CVE IDs that match the pattern but are known-invalid
- CVSS vectors that match the prefix pattern but have garbage after
- Extension fields with pathological content
- Signature fields without signatures (conformance test gap)
- Unicode normalization differences
- Control characters in string fields

**Fix:** Import the `conformance-security-tests.md` test vectors into each implementation's test suite.

---

## Go Reference (spec/reference/go/)

### Finding GO-01: Schema divergence from canonical schema (Critical)

**OWASP:** A05 (Security Misconfiguration).

**Location:** `spec/reference/go/validate.go` lines 13-54.

The Go reference embeds a hand-maintained schema that differs from the canonical `spec/schema.json`:

- Missing `pattern` constraints on `vendor_id`, `cve_id`, `cvss_vector`, `tags`, `title`, `signature.value`.
- Missing `format: date-time` on `published_at`.
- Missing `format: date` on `effective_date`, `sunset_date`.
- Missing `format: uri` on `source_url`, `migration_url`.
- Missing `minLength`, `maxLength` on `affected_systems` items, `affected_sections` items.
- Missing `uniqueItems` on `affected_systems`, `affected_sections`, `recommended_reviewers`, `tags`.
- Missing `additionalProperties: false`.
- Missing `patternProperties: ^ext:`.
- Missing the `if`/`then` constraint that `publisher_verified` events have `confidence_score: 1.0`.
- Missing the enum constraint on `recommended_reviewers`.

Practical consequences:

- The Go reference accepts events that the TypeScript and Python references reject.
- Strings like `vendor_id: "NULL\x00\x00\x00"` pass Go validation.
- Malformed dates pass Go validation.
- URLs with `javascript:` scheme pass Go validation.
- Duplicate items in arrays pass Go validation.

This is a conformance hazard and a security hazard. A producer that tests with the Go reference and publishes events can create events that break Python and TS consumers, and vice versa.

**Fix:** Embed `schema.json` at build time using `//go:embed`, do not maintain a duplicate string. Example:

```go
package changespec

import (
    _ "embed"
    "encoding/json"
    "strings"

    "github.com/santhosh-tekuri/jsonschema/v6"
)

//go:embed schema.json
var schemaJSON []byte

func getSchema() (*jsonschema.Schema, error) {
    if compiledSchema != nil {
        return compiledSchema, nil
    }
    doc, err := jsonschema.UnmarshalJSON(strings.NewReader(string(schemaJSON)))
    if err != nil {
        return nil, err
    }
    // ... rest as before
}
```

### Finding GO-02: Extension parsing silently drops malformed JSON (Low)

**Location:** `spec/reference/go/validate.go` lines 161-170.

```go
for key, val := range raw {
    if strings.HasPrefix(key, "ext:") {
        var ev any
        if err := json.Unmarshal(val, &ev); err == nil {
            extensions[key] = ev
        }
    }
}
```

If an extension field contains malformed JSON, it is silently dropped. Since this code path runs after schema validation, the outer validation already passed and the extension field parsed as `json.RawMessage`, so this is unlikely in practice. But silent-drop of untrusted input is not a good pattern. Defensively, at least log.

**Fix:** Log or return an error if extension unmarshaling fails.

### Finding GO-03: No duplicate-key rejection (Medium)

**Location:** `spec/reference/go/validate.go` line 112, 157, 174.

Go's `encoding/json.Unmarshal` accepts duplicate keys silently, keeping the last value. An attacker can smuggle:

```json
{
  "category": "security",
  ...
  "category": "informational"
}
```

Validation passes (second value wins and it is valid). If a consumer's business logic somehow re-parses or uses a different parse behavior (e.g., a UI that uses the first occurrence), the two parses disagree.

**Fix:** Use a custom JSON decoder that rejects duplicate keys, or parse twice and compare, or use `json.Decoder.DisallowUnknownFields()` plus a decoder that tracks seen keys. The jsontext package in `github.com/go-json-experiment/json` supports this natively.

### Finding GO-04: Error messages leak schema details (Low)

**Location:** `spec/reference/go/validate.go` lines 143-151, function `collectErrors`.

Error messages may include the full JSON path and raw values from the event. If these errors are returned to untrusted callers or logged verbosely, they can leak event content that may contain sensitive extension fields (e.g., `ext:internal.customer_email`).

**Fix:** Provide a public error surface that returns structured errors without raw values. Keep verbose errors for developer mode only.

### Finding GO-05: URL field not format-validated (High)

**Location:** `spec/reference/go/validate.go` lines 28, 31.

The embedded schema has `"source_url": {"type": "string"}` with no format validation. A value of `javascript:alert(1)` passes. A value of `\x00\x01\x02` also passes as long as it is a valid JSON string.

**Fix:** addressed by GO-01 (use the real schema).

---

## TypeScript Reference (spec/reference/typescript/)

### Finding TS-01: passthrough() defeats additionalProperties: false (High)

**OWASP:** A03 (Injection), A04 (Insecure Design).

**Location:** `spec/reference/typescript/src/types.ts` line 122.

```ts
export const EventSchema = z
  .object({
    // ...
  })
  .passthrough(); // allow ext:* and other unknown fields
```

The `.passthrough()` method accepts arbitrary extra properties. This means:

- Properties like `__proto__`, `constructor`, `prototype` pass validation.
- Properties that are neither core fields nor `ext:*` pass validation.

The canonical schema's intended semantics are: required fields, optional fields, `ext:*` pattern-matched fields, nothing else. The TS reference does not enforce this.

This matters because:

- An attacker can inject `__proto__: {polluted: true}` into an event. The Zod validation passes. If the event is later merged into a default object (e.g., `const merged = { ...defaults, ...event }`), some JavaScript engines and some object libraries pollute the global Object prototype. This is the classic prototype-pollution attack vector.
- A downstream consumer might read unknown fields as if they were extension fields without the `ext:` prefix check.

**Fix:** Replace `.passthrough()` with a custom refinement that accepts only fields matching the known set or starting with `ext:`:

```ts
export const EventSchema = z
  .object({
    // ...
  })
  .strict()  // reject unknown fields by default
  .and(
    z.record(z.string()).refine(
      (obj) => {
        const knownFields = new Set([
          "specversion", "id", "vendor_id", "category", "severity",
          "title", "summary", "published_at", "source_type",
          "effective_date", "source_url", "affected_versions",
          // ... all known fields
          "extensions",
        ]);
        return Object.keys(obj).every(
          (k) => knownFields.has(k) || k.startsWith("ext:")
        );
      },
      { message: "unknown fields not starting with ext: are not allowed" }
    )
  );
```

Note: Zod has limited support for this pattern. Consider switching to a validator that supports JSON Schema directly (ajv with strict mode).

### Finding TS-02: Zod date format is permissive (Medium)

**Location:** `spec/reference/typescript/src/types.ts` lines 79, 86.

```ts
effective_date: z.string().date().optional(),
sunset_date: z.string().date().optional(),
```

`z.string().date()` validates ISO 8601 date format `YYYY-MM-DD`. Good.

But `published_at: z.string().datetime({ offset: true })` may accept values that the JSON schema's `format: date-time` would accept. Depending on the zod version, this accepts fractional seconds and various timezone offsets. Good for flexibility; a divergence risk from other implementations.

**Fix:** document which exact subset of RFC 3339 is required. Recommend: only `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS.sssZ` with UTC offset `Z` required (not arbitrary `+HH:MM`). This matches what most producers actually emit and avoids timezone ambiguity.

### Finding TS-03: No host validation in URL fields (High)

**Location:** `spec/reference/typescript/src/types.ts` lines 80, 84.

```ts
source_url: z.string().url().max(2048).optional(),
migration_url: z.string().url().max(2048).optional(),
```

`z.string().url()` validates that the string parses as a URL. It does NOT constrain the scheme. `javascript:alert(1)`, `data:text/html;base64,...`, `file:///etc/passwd` all pass.

**Fix:**

```ts
const httpsUrl = z.string()
  .url()
  .max(2048)
  .refine((u) => new URL(u).protocol === "https:", {
    message: "URL must use https: scheme",
  })
  .refine((u) => !new URL(u).username && !new URL(u).password, {
    message: "URL must not contain credentials",
  });
```

Apply to both `source_url` and `migration_url`.

### Finding TS-04: Extension field extraction happens post-validation (Medium)

**Location:** `spec/reference/typescript/src/validate.ts` lines 33-43.

Extensions are separated after the schema validation. If a malicious event has an `ext:*` field that is extremely large, it still goes through schema validation first, consuming memory and CPU. For DoS hardening, extensions should be size-capped before validation.

**Fix:** add a preprocessor that counts and sizes `ext:*` fields, rejects over-limit events before validation.

### Finding TS-05: ParsedEvent type allows extensions: undefined (Low)

**Location:** `spec/reference/typescript/src/types.ts` line 168.

```ts
export interface ParsedEvent {
  // ...
  extensions: Record<string, unknown>;
}
```

The interface requires `extensions`, but the code at line 44-49 of validate.ts always sets it. Fine, but a refinement: typed as `Record<string, unknown>` allows any value including functions (via TypeScript's loose type). Consider `Record<string, JsonValue>` for stricter typing.

### Finding TS-06: No .pnpmfile.cjs, no lockfile audit (Medium)

**Location:** `spec/reference/typescript/package.json`.

No `package-lock.json` in the reviewed tree. The project uses `.npmrc` with `save-exact=true` (good) but no lockfile means `npm install` resolves transitive dependencies fresh each time.

**Fix:** commit `package-lock.json`. CI must verify lockfile matches package.json. Add a `npm audit` step to CI.

---

## Python Reference (spec/reference/python/)

### Finding PY-01: Invalid build-backend breaks package build (Critical for release, not security)

**Location:** `spec/reference/python/pyproject.toml` lines 2-3.

```toml
[build-system]
requires = ["setuptools==80.9.0", "wheel==0.45.1"]
build-backend = "setuptools.backends.legacy:build"
```

The module `setuptools.backends.legacy` does not exist. Users running `pip install .` or `pip install -e .` from this directory will fail with `ModuleNotFoundError: No module named 'setuptools.backends.legacy'`.

Reference: https://github.com/roex-audio/dawproject-py/issues/9 documents the exact error. The correct value is `setuptools.build_meta`.

**Fix:**

```toml
[build-system]
requires = ["setuptools==80.9.0", "wheel==0.45.1"]
build-backend = "setuptools.build_meta"
```

**Severity:** Not security, but blocks v1.0 public launch because the Python reference will not install.

### Finding PY-02: No URL scheme restriction (High)

**Location:** `spec/reference/python/changespec/types.py` lines 110, 114.

```python
source_url: str | None = Field(None, max_length=2048, ...)
migration_url: str | None = Field(None, max_length=2048, ...)
```

No format validation whatsoever. The schema.json has `format: uri` but Pydantic's default does not validate `format: uri` from JSON Schema - it only validates the Python field definition. So `javascript:alert(1)` passes.

**Fix:**

```python
from pydantic import HttpUrl

source_url: HttpUrl | None = Field(None, max_length=2048, ...)
migration_url: HttpUrl | None = Field(None, max_length=2048, ...)
```

Or use a custom validator:

```python
@field_validator("source_url", "migration_url", mode="after")
@classmethod
def require_https(cls, v: str | None) -> str | None:
    if v is None:
        return v
    if not v.startswith("https://"):
        raise ValueError("URL must use https: scheme")
    return v
```

### Finding PY-03: No datetime validation (Medium)

**Location:** `spec/reference/python/changespec/types.py` lines 104, 109, 116.

```python
published_at: str = Field(description="RFC 3339 datetime when published.")
effective_date: str | None = Field(None, ...)
sunset_date: str | None = Field(None, ...)
```

These are typed as plain strings with no datetime validation. An attacker can provide `published_at: "not-a-date"` and it passes.

**Fix:**

```python
from datetime import datetime, date

published_at: str = Field(description="...")

@field_validator("published_at")
@classmethod
def validate_published_at(cls, v: str) -> str:
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise ValueError("published_at must be RFC 3339 datetime")
    return v

@field_validator("effective_date", "sunset_date")
@classmethod
def validate_date(cls, v: str | None) -> str | None:
    if v is None:
        return v
    try:
        date.fromisoformat(v)
    except ValueError:
        raise ValueError("must be YYYY-MM-DD")
    return v
```

### Finding PY-04: CVSS vector regex too permissive (Low)

**Location:** `spec/reference/python/changespec/types.py` line 119.

```python
cvss_vector: str | None = Field(None, max_length=128, ...)
```

Unlike Go/TS which have a `^CVSS:` prefix pattern, this has NO pattern. Any 128-char string passes.

**Fix:** add `pattern=r"^CVSS:[0-9]\.[0-9]/"` to match the schema.

### Finding PY-05: Extension field extraction before Pydantic validation is fragile (Medium)

**Location:** `spec/reference/python/changespec/types.py` lines 144-165.

The `model_validator(mode="before")` extracts `ext:*` keys into a separate `extensions` field before Pydantic validates the model. This happens before any size or depth checks.

An attacker can send `{"ext:a.b": [[[... 10000 levels ...]]]}` and the extraction happily stores the deeply-nested list into `extensions`, where it lives in memory indefinitely.

**Fix:** apply size/depth checks in the `extract_extensions` validator. Add:

```python
MAX_EXT_FIELDS = 64
MAX_EXT_VALUE_BYTES = 4096

@model_validator(mode="before")
@classmethod
def extract_extensions(cls, data: Any) -> Any:
    if not isinstance(data, dict):
        return data

    ext_keys = [k for k in data if k.startswith("ext:")]
    if len(ext_keys) > MAX_EXT_FIELDS:
        raise ValueError(f"too many ext:* fields (max {MAX_EXT_FIELDS})")

    extensions: dict[str, Any] = {}
    clean: dict[str, Any] = {}

    for key, value in data.items():
        if key.startswith("ext:"):
            import json
            serialized = json.dumps(value)
            if len(serialized) > MAX_EXT_VALUE_BYTES:
                raise ValueError(f"ext:{key} value too large")
            extensions[key] = value
        else:
            clean[key] = value

    clean["extensions"] = extensions
    return clean
```

### Finding PY-06: No lockfile (Medium)

**Location:** `spec/reference/python/`.

No `requirements.lock`, no `uv.lock`, no `poetry.lock`. Builds are reproducible only to the extent that exact versions in `pyproject.toml` happen to match across environments. Transitive dependencies (Pydantic's own dependencies) are not locked.

**Fix:** commit a lockfile. Recommend `uv.lock` (uv is fastest, PEP 517 compliant, supports hard pins).

### Finding PY-07: Pydantic extra="ignore" silently drops unknown fields (Low)

**Location:** `spec/reference/python/changespec/types.py` line 91.

```python
model_config = ConfigDict(
    populate_by_name=True,
    extra="ignore",
    frozen=False,
)
```

`extra="ignore"` silently drops unknown fields. The spec's intent is that non-`ext:` unknown fields should ALSO be ignored (forward compatibility), so this is correct by spec. But combined with PY-05, an attacker can craft a field like `ext:x.y` (starts with ext:) and slip an arbitrary value through extension extraction, while sending a field like `xt:x.y` (typo) and have it silently dropped.

This is acceptable but should be documented. A paranoid consumer may want to switch to `extra="forbid"` and handle `ext:*` separately.

---

## Recommended Remediation Priorities

**Must fix before v1.0 release:**

- X-01: Parser hardening (payload/depth limits) - all three
- X-02: Signature verification implementation - all three
- GO-01: Schema divergence - Go
- TS-01: passthrough() + prototype pollution - TypeScript
- TS-03: URL scheme validation - TypeScript
- PY-01: build-backend fix - Python
- PY-02: URL scheme validation - Python

**Should fix before v1.0 release:**

- X-03: Fuzzing harness - all three
- X-04: Malicious-input test suite - all three
- GO-03: Duplicate-key rejection - Go
- TS-06: Lockfile commit - TypeScript
- PY-03: Datetime validation - Python
- PY-06: Lockfile commit - Python

**Can defer to v1.0.1 or v1.1:**

- Finding GO-02, GO-04, GO-05 (covered by GO-01 fix)
- Finding TS-02, TS-04, TS-05
- Finding PY-04, PY-05, PY-07

---

## Summary

The reference implementations are functional but not yet hardened for security-critical production use. The Go implementation has the most work (schema divergence). The TypeScript implementation has the most severe finding (passthrough prototype pollution). The Python implementation has a build-blocker that prevents installation.

All three implementations lack signature verification, fuzzing, and malicious-input testing. These gaps are not fatal for v1.0 launch if documented as v1.0.1 improvements, but the `passthrough()` issue in TypeScript and the `build-backend` bug in Python are launch blockers.

Re-run Snyk scans (`snyk_sca_scan` and `snyk_code_scan`) in an environment where the MCP server is available before final launch.
