# Conformance Runner Interface Specification

This document defines the interface a ChangeSpec library must expose to be testable by the conformance runners.

---

## Required Interface

A conforming library must provide a function with the following semantics:

### Input

- Accept a byte string (or language-equivalent) containing the JSON to validate.
- Must not require pre-parsed JSON. The runner passes raw bytes.

### Output

A result object with:

- `valid: bool` - whether the input is a conforming ChangeSpec 1.0 event.
- `error: string | null` - if `valid` is false, a human-readable description of the failure. May be null for valid inputs.
- `error_type: "json_parse_error" | "schema_error" | null` - the category of error, if applicable.

The function MUST NOT panic, crash, or raise an unhandled exception on any input. All errors must be returned via the result object.

### Language-specific signatures

**Go:**
```go
func Validate(data []byte) (*Event, error)
// Error types:
//   - *ValidationError for schema failures
//   - standard error for JSON parse failures
```

**TypeScript:**
```typescript
function validate(raw: unknown): ValidationResult
// ValidationResult = { success: true, data: ParsedEvent } | { success: false, error: ZodError }
// Caller parses JSON before calling validate()
```

**Python:**
```python
def validate(raw: Union[dict, str, bytes]) -> ChangeSpecEvent
# Raises pydantic.ValidationError for schema failures
# Raises json.JSONDecodeError for JSON parse failures
```

---

## Runner Responsibilities

Each runner:

1. Loads all `.yml` test vector files from the specified directory.
2. For each vector:
   a. Constructs the input JSON (from the `input` field or `input_json` or `generate` instructions).
   b. Calls the library's validate function.
   c. Compares the result to `expected.valid`.
   d. For security vectors with `max_memory_mb` or `max_time_ms`, enforces those limits.
3. Prints a report in the format described below.
4. Exits with code 0 if all vectors pass, non-zero if any fail.

---

## Report Format

```
ChangeSpec Conformance Runner v1.0
Testing: <library name> <library version>
Vectors: <directory>

PASS valid/valid-001.yml - Minimal valid event with only required fields
PASS valid/valid-002.yml - Full api_breaking event with all common fields populated
...
FAIL invalid/invalid-016.yml - title contains a newline character
     Expected: valid=false
     Got: valid=true (no error returned)
...
WARN security/security-007.yml - NUL byte in summary field
     Expected: valid=true, no_crash=true
     Got: valid=true (PASS), but no_crash could not be verified programmatically

Summary:
  Vectors run:  105
  Passed:       103
  Failed:       1
  Warnings:     1

  Level 1 (Syntactic):    PASS (70/70)
  Level 2 (Semantic):     PASS (85/85)
  Level 3 (Secure):       FAIL (17/20)

Exit code: 1
```

---

## Vector Input Construction

Most vectors specify `input:` as a YAML object that is serialized to JSON before passing to the library.

Some security vectors use alternative input specifications:

### `input_type: json_string` + `input_json:`

The `input_json` value is a JSON string passed directly to the library as bytes. This allows constructing inputs with features not representable in YAML (e.g., duplicate keys, certain escape sequences).

### `input_type: raw_bytes` + `raw_input:`

The `raw_input` string is passed as bytes with no JSON serialization. This tests non-JSON inputs.

### `input_type: generated` + `generate:` block

The runner generates the input using the `generate` instructions:

- `type: oversized_field` - generates a base_input with a specific field filled to `size_bytes` with repeated 'A' characters.
- `type: array_overflow` - generates a base_input with a specific field set to an array of `count` items.
- `type: deeply_nested_ext` - generates a base_input with an extension field containing a deeply nested object.
- `type: deeply_nested_field` - generates a base_input with an unknown field containing a deeply nested object.

Runners that cannot implement a generation type SHOULD skip the vector and report it as SKIP, not FAIL.

---

## Security Constraint Enforcement

For vectors with `max_memory_mb` or `max_time_ms`:

- **Timeout**: Run the validation call in a goroutine/thread/subprocess with a timer. If it does not return within `max_time_ms`, report FAIL with reason "timed out".
- **Memory**: Memory measurement is implementation-specific and optional. If a runner cannot measure memory, it SHOULD report the vector as WARN rather than FAIL for the memory constraint.

---

## Skipping Vectors

A runner MAY skip a vector by reporting it as SKIP with a reason. Skip reasons:

- `input_type: generated` with an unsupported `generate.type`.
- The vector's `level` is higher than the level being tested (e.g., running only Level 1 vectors and encountering a Level 3 vector).

Skipped vectors do not count toward pass or fail totals. They are listed in the report.
