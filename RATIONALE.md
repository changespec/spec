# ChangeSpec Design Rationale

This document explains the reasoning behind each significant design decision in ChangeSpec 1.0. It is written for readers who are evaluating the spec for adoption or implementation, who want to understand why we made particular choices, and who may want to propose changes in future versions.

---

## Why a new spec at all?

The obvious question. CloudEvents exists. AsyncAPI exists. OpenAPI exists. Why is another spec needed?

None of those address the specific problem ChangeSpec solves. CloudEvents is a format for event routing - it says how to describe an event generically, not what the event means. AsyncAPI describes the shape of an API's message types statically. OpenAPI describes what an API does today. None of them describe what changed, when, how severe it was, and what to do about it.

The closest analog is RSS, which solved a related problem (content publishing) in 2003 and became ubiquitous precisely because it was a boring, simple format that anyone could implement. RSS says nothing about software changes, severity, affected versions, or migration guidance. ChangeSpec fills that gap.

The spec also serves a dual audience that no existing format addresses: human readers (a compliance officer reviewing a TOS change) and machine consumers (a dependency management agent patching a CVE). This dual requirement shapes several decisions below.

---

## Why JSON, not YAML or Protobuf?

JSON is the lingua franca of web APIs. Every language has a JSON parser in its standard library or first-party ecosystem. YAML is a superset of JSON that adds complexity (multiple scalar types, anchors, the Norway problem) without adding value for a wire format. Protobuf is efficient but requires schema compilation and is opaque to humans without tooling.

ChangeSpec events are small (under 4 KB in practice). Wire efficiency is not a concern. Readability is. JSON.

---

## Why JSON Schema draft 2020-12?

Draft 2020-12 is the current stable draft. It adds `unevaluatedProperties`, better `$ref` semantics, and cleaner composition operators over draft 7. The major JSON Schema implementations (AJV, Python jsonschema, Go github.com/santhosh-tekuri/jsonschema) all support it.

We chose 2020-12 over the older draft 7 because we expect the spec to have a long life. Draft 7 is still functional but carries historical baggage and may be deprecated in implementations over the next few years.

---

## Why not build on CloudEvents directly?

ChangeSpec events CAN ride inside CloudEvents envelopes - this is explicitly specified in Section 8.2. CloudEvents is not replaced; it is an optional transport wrapper.

The reason ChangeSpec is not defined purely as a CloudEvents extension is that CloudEvents is optimized for event routing infrastructure (brokers, event buses, routing rules). It has very few opinions about event semantics. ChangeSpec is the opposite: it has strong opinions about what fields a change event must carry, what the category and severity values mean, and how attribution works.

Defining ChangeSpec as a CloudEvents extension would require consumers to understand both CloudEvents and ChangeSpec, and would force ChangeSpec into CloudEvents' extension field conventions, which are not designed for the richness required here. The CloudEvents binding is provided for interoperability, not as the primary format.

---

## Why a category taxonomy instead of free-form tags?

Consistency. If every producer invented their own category terms, consumers would need to normalize across "breaking-change", "breaking_change", "api_break", "incompatible" before they could route or filter. The taxonomy exists so that a consumer can write `if category == "api_breaking"` and know it fires for every producer.

The taxonomy is deliberately narrow (9 values). We considered a larger taxonomy with 20+ values but concluded that more values create more disagreement about edge cases and more burden on producers to choose correctly. Nine values cover the meaningful routing cases.

**On the `tos` vs. `liability` distinction:** these two categories overlap. The split reflects a practical routing difference: `liability` events route to legal counsel for review of indemnification, warranty, and limitation of liability terms. `tos` events are general policy changes that may only need awareness from compliance teams. Whether a given TOS change rises to `liability` requires human judgment; the taxonomy gives producers a way to signal that a change specifically affects legal liability, not just general policy.

---

## Why is the severity taxonomy independent of category?

Severity measures urgency and impact. Category measures type. They are orthogonal. A pricing change can be `informational` (minor restructuring) or `high` (30% price increase with two weeks' notice). A TOS change can be `low` (clarifying language) or `medium` (new arbitration clause). Conflating the two would force artificial severity assignments based on category alone.

The spec does include a recommended mapping in Section 5.1, but it is advisory. Producers know their changes better than a generic taxonomy does.

---

## Why semver ranges for `affected_versions`?

Semver is the closest thing to a universal version format across ecosystems. npm, Go, Rust, Python, Ruby all use semver or a close variant. npm's semver range syntax (`>=14.0.0 <15.0.0`) is the most widely implemented range language - it has libraries in every major language.

We do not define a new range syntax. We reference npm semver syntax because it is already implemented everywhere. The `semver` npm package, Go's `golang.org/x/mod/semver`, Python's `packaging` library, and Rust's `semver` crate all implement compatible range evaluation.

For non-versioned services (hosted APIs with date-based versioning like Stripe's `2026-05-01`), `affected_versions` is omitted and the `effective_date` carries the version information.

---

## Why is `vendor_id` namespaced?

Without namespaces, `requests` is ambiguous: is it the Python package or a vendor called "Requests"? `lodash` might refer to the npm package or a company. Namespaced IDs eliminate the ambiguity: `pypi:requests`, `npm:lodash`.

The no-namespace case is reserved for named services (companies, hosted products) that are globally unique by convention. `stripe`, `anthropic`, `github` are unambiguous. The registry of no-namespace vendor IDs is maintained to prevent conflicts.

The namespace list in the spec is not exhaustive. New namespaces can be added in minor releases. Producers using an unlisted namespace should register it to prevent future conflicts.

---

## Why three `source_type` values?

Because trust must be explicit. A `publisher_verified` event is authoritative - the vendor said this. A `crawled` event is an automated inference - a system detected a change and an AI classified it. A `community` event is a human submission that has not been independently verified.

Consumers that make automated decisions (CI gates, automated patch PRs) SHOULD filter on `source_type` and `confidence_score`. A consumer that automatically merges a patch based on a `community` event with `confidence_score: 0.6` is accepting a very different risk profile than one acting on a `publisher_verified` event with `confidence_score: 1.0`. Making this distinction explicit is not optional - it is a safety property.

---

## Why Ed25519 for signing?

Ed25519 is the right algorithm for this use case:

1. **Compact keys and signatures.** A 32-byte public key and 64-byte signature. Compare to RSA-2048's 256-byte signature or ECDSA P-256's 64-byte signature with a 64-byte public key.

2. **No weak-parameter risk.** ECDSA signatures can be broken if the same nonce is reused (the Sony PS3 signing failure used ECDSA with a static nonce). Ed25519 uses deterministic nonce derivation - there is no nonce to mismanage.

3. **Standard library support.** Go's `crypto/ed25519`, Node.js's `crypto.sign('ed25519', ...)`, Python's `cryptography.hazmat.primitives.asymmetric.ed25519`. No external crypto library needed in any reference language.

4. **NIST and RFC 8032 standardized.** Not an exotic curve. Widely reviewed.

RSA is not recommended. Its keys are 10x larger, its signatures are 4x larger, and it adds no security benefit for this use case.

Signing is optional. Most consumers will receive events through a trusted platform that has already verified signatures. Signing is primarily valuable for consumers that receive events directly from vendor-controlled endpoints and need to verify authenticity without trusting an intermediary.

---

## Why is signing field-based instead of signing the full JSON body?

JSON has no canonical serialization. Two JSON serializations of the same event may have different field ordering, different whitespace, or different Unicode normalization. Signing the raw JSON bytes means the signature breaks if any serialization detail changes, even without any semantic change.

The signed_fields approach signs a canonical byte string constructed from specific field values in a specified order. The construction is deterministic and independent of JSON serialization. This is the same approach used by HTTP Message Signatures (RFC 9421) and JWS compact serialization.

The producer specifies which fields are signed via `signed_fields`. At minimum, the required event fields should always be signed. Extension fields can be included but are not required.

---

## Why not HMAC for signing?

HMAC requires a shared secret between producer and consumer. Key distribution is then a problem: every consumer that wants to verify needs the secret, and the secret must be transmitted securely out-of-band. This does not scale.

Ed25519 is asymmetric: the vendor publishes a public key once (at a well-known URL) and every consumer can verify independently without any secret sharing.

HMAC (specifically Standard Webhooks' approach) is appropriate for webhook delivery verification between a platform and a consumer - it proves the platform sent this webhook, not a third party. That is a different problem from proving the vendor authored the event content. Both layers can coexist: Standard Webhooks HMAC verifies the delivery channel; Ed25519 verifies the event origin.

---

## Why the `ext:` prefix for extensions?

Namespaced extensions follow CloudEvents' convention. `ext:` is short, unambiguous, and clearly separates extension fields from core fields without requiring a separate JSON object layer.

Alternative considered: a nested `extensions` object (`{"extensions": {"compliance": {...}}}`). Rejected because it requires consumers to know whether to look in the top-level object or in `extensions`, and because it complicates JSON Schema validation (the schema would need to validate an arbitrary nested object).

Alternative considered: no formal extension mechanism (undocumented extra fields). Rejected because undocumented fields create silent schema conflicts when a future spec version adds a field with the same name.

The `ext:<namespace>.<fieldname>` pattern gives each organization a namespace to avoid conflicts. `ext:compliance.osfi_b10`, `ext:internal.ticket_id`, `ext:risk.vendor_tier` are all unambiguous and self-documenting.

---

## Why is `summary` plain text, not markdown?

Dual audience again. Compliance officers reading a TOS change summary in an email want readable English, not markdown syntax in their summary text. Machine consumers parsing the event do not need markdown. Rendering markdown correctly requires a renderer; not every consumer has one.

The `source_url` and `migration_url` fields point to richly formatted documents for consumers that want more detail. The `summary` field is the 150-word answer to "what changed and should I care?" - it should be readable in plain text in any context.

---

## Why no subscription or webhook registration in the spec?

Scope discipline. Subscription protocols involve authentication, authorization, retry negotiation, filter expressions, delivery guarantees, and backpressure. These are platform concerns. Different platforms will have different subscription models. Speccing out subscription would double the spec's scope and likely produce something no platform would implement exactly.

ChangeSpec is the event format. The platform that delivers events handles subscriptions. This is the same split CloudEvents makes: CloudEvents specifies the event envelope, not how events are subscribed to or routed.

---

## Why are `recommended_reviewers` values fixed to an enum?

To prevent the proliferation of synonyms. `engineering`, `security`, `legal`, `compliance`, `procurement`, `management` cover the teams that realistically route change events in the organizations that consume this spec. Freeform strings would result in `eng`, `engineering`, `Engineering`, `dev-team` being treated as different values by any consumer that pattern-matches on them.

The enum is advisory: consuming teams map these values to their own internal teams. The spec is not prescribing org structure; it is providing routing hints that map predictably to the most common structures.

---

## Why `published_at` as a required field and `effective_date` as optional?

`published_at` is the timestamp the event was created and published. It is always known. It is required because consumers need it for deduplication, time-ordering, and subscription filtering.

`effective_date` is when the change takes effect - the date a developer needs to care about for planning purposes. It is often known (the vendor announces "this change goes live on June 1") but not always (a TOS crawl detects a change that is already live). Making it optional accommodates the crawled case without forcing a bogus effective_date.

When `effective_date` is absent, consumers should treat the change as already effective as of `published_at`.

---

## Why is `id` stable?

A change event should be idempotent. If a platform re-delivers the same event (retry after timeout, dual-delivery from failover), the consumer should not process it twice. A stable `id` enables deduplication with a simple "have I seen this id before?" check.

The `cs_` prefix is a convention (not enforced by the schema beyond `minLength: 1`) that prevents collisions with other identifier schemes. ULID is recommended for the suffix because it is time-sortable and case-insensitive, but UUID v4 is equally valid.

---

## Why support both RSS/Atom and webhook?

Different consumers live in different ecosystems. A compliance team's workflow might be built around an RSS reader that already aggregates vendor communications. A CI/CD system needs a webhook. An AI coding assistant needs MCP. The event format is the same; the transport is an implementation choice.

Specifying all four bindings ensures that any platform can serve all these consumers without reformatting events.

---

## What the spec does not cover (and why)

**Subscription negotiation:** Platform concern, varies too widely between implementations.

**Delivery guarantees:** Platform concern. At-least-once delivery with idempotent consumers is the expected pattern, but enforcing this at the spec level is not appropriate.

**Filtering/routing rules:** Platform concern. How a consumer specifies "I want `api_breaking` events for `npm:express` at `severity >= high`" is implementation-specific.

**Event deletion/retraction:** Not specced in 1.0. If a vendor publishes an incorrect event, the practical mitigation is publishing a corrected event with the same `id` (producers may update events, consumers are expected to process the latest version of a given `id`). A formal retraction mechanism may be added in a future version.

**Pagination of historical events:** Platform concern. The polling binding specifies the cursor-based pagination envelope, but the pagination parameters themselves are platform-specific.

**Internationalization:** The spec does not specify multi-language `title` and `summary`. All string fields are assumed to be in English. Localization is a potential future extension via `ext:i18n.*` fields.
