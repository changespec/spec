# ChangeSpec

ChangeSpec is an open specification for software change communication. It defines a standard event format that vendors use to publish changes - API updates, security advisories, terms of service edits, pricing adjustments - and that consumers use to receive and process them.

Version: **1.1**
License: Apache 2.0
Status: Stable

## The Problem

Every software vendor ships changes. Breaking API changes, security patches, deprecations, TOS updates, DPA modifications. These changes arrive through scattered channels - blog posts, GitHub releases, email blasts, Slack announcements - with no consistent structure, no standard severity taxonomy, and no machine-readable format. Downstream consumers miss changes, build integrations that silently break, and fail compliance audits because a vendor updated a subprocessor list with no formal notification.

ChangeSpec is the contract layer that fixes this. One format. Any vendor. Any consumer.

## What ChangeSpec Is Not

ChangeSpec specifies the **event format** only. It does not specify:

- How events are stored or indexed
- How subscriptions are negotiated
- How webhooks are registered or delivered
- Compliance workflow logic

Those concerns belong to platform implementations built on top of the spec.

## Elevator Pitch

ChangeSpec is to vendor change communication what CloudEvents is to event routing and what OpenAPI is to HTTP API description. It is a boring, stable, extensible format that anyone can implement in an afternoon and that becomes more valuable as adoption grows.

A ChangeSpec event looks like this:

```json
{
  "specversion": "1.0",
  "id": "cs_01HXYZ1234ABCD",
  "vendor_id": "stripe",
  "category": "api_breaking",
  "severity": "high",
  "title": "confirm() now requires return_url parameter",
  "summary": "The PaymentIntent confirm() method now requires the return_url parameter in all cases where a redirect may occur. Calls without return_url that previously succeeded will now return a 400 error.",
  "effective_date": "2026-05-01",
  "published_at": "2026-04-10T14:00:00Z",
  "source_url": "https://stripe.com/docs/upgrades#2026-05-01",
  "source_type": "publisher_verified",
  "affected_versions": ">=14.0.0 <15.0.0",
  "migration_hint": "Add return_url to all confirm() calls. See migration guide for redirect-less flows.",
  "migration_url": "https://stripe.com/docs/migration/v15"
}
```

## Quickstart

### Validate an event

**Go:**

```go
import "github.com/changespec/changespec-go"

event, err := changespec.Validate(jsonBytes)
if err != nil {
    // validation error with field-level detail
}
```

**TypeScript:**

```typescript
import { validate } from "@changespec/changespec";

const result = validate(rawObject);
if (!result.success) {
  // result.error contains Zod validation errors
}
const event = result.data;
```

**Python:**

```python
from changespec import validate

event = validate(raw_dict)  # raises ValidationError on invalid input
```

### Publish an event

Any HTTP client can POST a ChangeSpec event to a platform endpoint. The event body is a JSON object conforming to `schema.json`.

### Consume events

Events are delivered via:

- HTTPS POST webhook (body is a ChangeSpec event JSON object)
- MCP tool response
- RSS/Atom feed (event fields mapped to feed item elements)
- Polling API (returns arrays of ChangeSpec event objects)

## Repository Layout

```
README.md             - this file
spec.md               - the full specification
schema.json           - JSON Schema (draft 2020-12) for validation
CHANGELOG.md          - version history
RATIONALE.md          - design decision rationale
changespec.proto      - Protobuf wire format
integration-safety.md - integration security guidance
examples/             - example events for each category
conformance/          - conformance test suite
reference/
  go/                 - Go reference implementation
  typescript/         - TypeScript reference implementation
  python/             - Python reference implementation
governance/
  CHARTER.md
  CONTRIBUTING.md
  GOVERNANCE.md
  MAINTAINERS.md
```

## Versioning Policy

ChangeSpec uses calendar versioning for major releases. The current release is **1.1**.

**Backward compatibility guarantee:** A field added in a minor release (1.1, 1.2) is always optional. Required fields may only be added in a major release with a formal deprecation period. Unknown fields in a 1.x event must be ignored by 1.0 consumers (forward compatibility).

**Extension fields** are supported via the `ext:` prefix namespace (see spec.md). Extension fields never conflict with core spec fields.

**Version negotiation:** Events carry `"specversion": "1.0"`. Consumers that support only 1.0 should reject events with an incompatible major version.

## Governance

ChangeSpec is released under the Apache 2.0 license.

Spec evolution is community-driven:

- Proposals via GitHub Issues in this repository
- Discussion period of at least 30 days for any change to required fields
- Changes to the core taxonomy require a formal proposal and rough consensus among active contributors
- Roboticforce Inc. serves as steward but holds no veto over community proposals that achieve consensus

Contributions to the spec, schema, reference implementations, and examples are welcome. See [governance/CONTRIBUTING.md](governance/CONTRIBUTING.md).

## Related Standards

ChangeSpec is designed to complement, not replace, these existing standards:

- **CloudEvents** - ChangeSpec events can ride inside a CloudEvents envelope. See spec.md for the binding.
- **OpenAPI / AsyncAPI** - These describe API schemas. ChangeSpec describes changes to those schemas over time.
- **Standard Webhooks** - ChangeSpec is payload-agnostic about delivery. Standard Webhooks signing works with ChangeSpec payloads.
- **RSS / Atom** - ChangeSpec events map cleanly to feed items. See spec.md for the feed binding.
