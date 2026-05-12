# ChangeSpec Conformance Program

This directory contains the official conformance test suite and certification program for ChangeSpec 1.0.

## What "ChangeSpec Certified" Means

A "ChangeSpec Certified" mark on a library or vendor means that an independent test suite has verified that the implementation correctly handles the ChangeSpec 1.0 event format. It is a verifiable claim, not marketing copy. The mark is backed by test vectors that any engineer can read, run, and audit.

Certification is distinguished from compatibility claims. "ChangeSpec Compatible" can be claimed by any implementation the author believes works. "ChangeSpec Certified" requires passing the published test suite at a defined level.

## Two Certification Tracks

### Consumer Track (libraries and tools)

For libraries that parse, validate, or route ChangeSpec events. This is the primary certification path for open source packages, SDK authors, and platform integrators.

Examples: a Go validation library, a Python SDK, a Kafka consumer that filters by severity, a Slack bot that routes events to channels.

### Producer Track (vendors publishing events)

For vendors that publish ChangeSpec-formatted change events to consumers. This track validates that the events a vendor produces meet all MUST requirements from the spec.

Examples: a SaaS company's changelog API, a package registry's deprecation feed, a platform's breaking-change webhook stream.

## Certification Levels

Full level definitions are in [certification-levels.md](certification-levels.md). Summary:

| Level | Name | What It Proves | Who It's For |
|---|---|---|---|
| 1 | Syntactic | Accepts valid events, rejects invalid events | Any consumer library |
| 2 | Semantic | Also handles edge cases, boundary conditions | Production consumer libraries |
| 3 | Secure | Also handles adversarial inputs safely | Security-sensitive deployments |
| 4 | Full Producer | Implements all MUST producer requirements | Vendors publishing events |

Each level strictly includes all requirements of all lower levels.

## Self-Certification Path

Any implementation can self-certify by:

1. Running the test runner for your language against the published test vectors.
2. Achieving 100% pass rate at the desired level.
3. Adding the appropriate badge to your README (see [conformance-badge.md](conformance-badge.md)).
4. Filing a self-certification report as a GitHub issue on the conformance repository using the provided template.

Self-certification is accepted and sufficient for most use cases. It carries the label "Self-Certified."

## Official Certification Path

Official certification (without the "Self-" qualifier) is available for implementations that have:

1. Passed all test vectors at the desired level on a clean, reproducible test run.
2. Submitted a certification request with a link to a public CI run showing results.
3. Had the submission reviewed by a maintainer of the ChangeSpec conformance program.
4. Been listed in the certified implementations registry at `changespec.com/certified`.

Official certification is renewed annually or upon release of a new spec minor version, whichever comes first. Implementations that regress (fail vectors on a subsequent run) have their certification suspended until the regression is fixed.

## Trademark Policy

See [trademark-policy.md](trademark-policy.md) for the full policy. Short version:

- Certified implementations may display the "ChangeSpec Certified: Level N" badge.
- Uncertified implementations may claim "ChangeSpec Compatible" but not "ChangeSpec Certified."
- No implementation may claim a certification level it has not achieved.
- The "ChangeSpec" wordmark belongs to Roboticforce Inc. The conformance program is a service of Roboticforce Inc.

## Test Suite Structure

```
conformance/
  README.md                  - This file
  certification-levels.md    - Level definitions and criteria
  producer-tests.md          - Producer conformance requirements
  consumer-tests.md          - Consumer conformance requirements
  trademark-policy.md        - Mark usage policy
  conformance-badge.md       - Badge format and embed codes
  ci-integration.md          - CI/CD integration guide
  run-against-references.md  - Results of running against reference implementations

  test-vectors/
    valid/                   - Events that must validate successfully (~30 vectors)
    invalid/                 - Events that must be rejected (~40 vectors)
    security/                - Adversarial inputs that must not cause parser problems (~20 vectors)
    edge-cases/              - Boundary conditions (~15 vectors)

  runner/
    spec.md                  - Interface a testable library must expose
    go/runner.go             - Go conformance runner
    typescript/runner.ts     - TypeScript conformance runner
    python/runner.py         - Python conformance runner
```

## Test Vector Format

Each test vector is a YAML file with the following structure:

```yaml
id: valid-001
description: Minimal valid event with only required fields
level: 1
spec_clause: "Section 2"
input:
  specversion: "1.0"
  id: "cs_01HXYZ1234ABCD"
  vendor_id: "acme"
  category: "informational"
  severity: "informational"
  title: "Documentation typo fix"
  summary: "Corrected a typo. No behavior change."
  published_at: "2026-04-10T14:00:00Z"
  source_type: "crawled"
expected:
  valid: true
```

For invalid vectors:

```yaml
id: invalid-001
description: Missing required field id
level: 1
spec_clause: "Section 1.1"
input:
  specversion: "1.0"
  vendor_id: "acme"
  category: "informational"
  severity: "informational"
  title: "Test"
  summary: "Test summary."
  published_at: "2026-04-10T14:00:00Z"
  source_type: "crawled"
expected:
  valid: false
  reason: "Missing required field: id"
```

## Running the Suite

See [runner/spec.md](runner/spec.md) for the interface a library must expose, and the language-specific runners in `runner/go/`, `runner/typescript/`, and `runner/python/`.

Quick start for each language:

```bash
# Go
cd runner/go && go run runner.go ../../test-vectors

# TypeScript
cd runner/typescript && npx ts-node runner.ts ../../test-vectors

# Python
cd runner/python && python runner.py ../../test-vectors
```

## Versioning

This test suite is versioned to match the ChangeSpec spec:

- `conformance-1.0/` - test suite for ChangeSpec 1.0
- Future minor versions add test vectors without removing or modifying existing ones.
- A library certified at Level 2 against conformance-1.0 retains that certification until conformance-1.1 is released, at which point it must re-run to maintain certification.

The current version is **conformance-1.0**.
