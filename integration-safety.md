# ChangeSpec Integration Safety

**Status:** Released
**Version:** 1.0.0
**Date:** 2026-04-16
**Companion to:** spec.md (see Section 13)

---

## Abstract

This document specifies non-blocking safety requirements for all ChangeSpec client integrations: the CLI, MCP server, webhook consumers, and any third-party tooling that calls the ChangeSpec API. The core invariant is:

> ChangeSpec MUST NEVER be the reason a developer's build, deploy, test run, or IDE session fails.

ChangeSpec is an advisory intelligence layer. It surfaces information. It does not own the gate. All client implementations MUST be engineered with this constraint as a load-bearing requirement, not a nice-to-have.

---

## Conformance

The key words "MUST", "MUST NOT", "REQUIRED", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are interpreted as described in RFC 2119.

A **conforming integration** is any ChangeSpec client (CLI, MCP server, webhook consumer, SDK) that satisfies every MUST requirement in this document.

A **non-conforming integration** that blocks user workflows on ChangeSpec infrastructure failures MUST NOT claim ChangeSpec client conformance.

---

## 1. Non-Blocking Requirements

### 1.1 Fail-Open Mandate

**MUST.** When a ChangeSpec integration cannot reach the API - whether due to network failure, DNS resolution failure, TLS error, server error (5xx), or any other condition outside the user's control - the integration MUST return a non-error result from the perspective of the calling process.

For the purposes of this requirement, "non-error result" means:

- CLI tools MUST exit 0 in advisory mode (the default). Exit codes are specified in Section 4.
- MCP tools MUST return a structured response, not throw or return `isError: true`, unless the error is user-supplied bad input. Infrastructure failures MUST return a degraded response per Section 5.
- Webhook consumers MUST NOT gate a deploy or build on successful delivery acknowledgment from ChangeSpec. Consumers drive their own retry logic.

**MUST NOT.** A conforming integration MUST NOT propagate a ChangeSpec infrastructure failure as an error to the calling process in advisory mode. The infrastructure failure MAY be surfaced as a warning on stderr or in a `warnings` field of the response, but MUST NOT change the exit code or error state of the host process.

### 1.2 Advisory by Default

**MUST.** The default operating mode of any ChangeSpec integration is advisory. An advisory integration:

- Returns results (cached or live) that describe change events
- Surfaces degradation warnings to the user
- Does not block, halt, or fail the host workflow

**MUST.** Blocking behavior - where a non-zero exit code or thrown exception is returned based on ChangeSpec findings - MUST require explicit opt-in by the user. The opt-in mechanism MUST be documented prominently and MUST NOT be enabled by default.

### 1.3 Always Bypassable

**MUST.** Every integration point MUST support a complete bypass that disables all ChangeSpec network activity and returns immediately with an empty or no-op result.

Required bypass mechanisms:

| Mechanism | Value | Scope |
|---|---|---|
| Environment variable | `CHANGESPEC_SKIP=1` | All integration types |
| CLI flag | `--no-changespec` | CLI only |
| Config file key | `changespec: disabled` | Config-file-based integrations |
| MCP env var | `CHANGESPEC_SKIP=1` | MCP server |

When bypass is active, the integration MUST:

- Make zero network calls to any ChangeSpec endpoint
- Return immediately with an empty result set and a flag or warning indicating bypass is active
- Log the bypass activation to stderr (not stdout) at debug level
- Exit 0 (CLI) or return a non-error response (MCP)

The bypass MUST be documented in the first screen of every integration's documentation. The 30-second bypass path (set env var, restart tool) MUST be tested in conformance.

---

## 2. Timeout Budgets

### 2.1 Required Timeout Enforcement

**MUST.** Every synchronous outbound network call from a ChangeSpec integration MUST have a hard wall-clock timeout. No integration MAY hang indefinitely on a network call.

**MUST.** Timeout enforcement is at the transport layer, not the application layer. A TCP connection that accepts the connection but then stalls MUST be terminated by the timeout, not by waiting for an application-level response.

### 2.2 Default Timeout Budgets by Consumer Type

| Consumer type | Default timeout | Notes |
|---|---|---|
| MCP server (per tool call) | 2,000 ms | User is waiting synchronously in IDE |
| CLI, interactive mode | 2,000 ms | User invoked command manually |
| CLI, CI/batch mode | 5,000 ms | Machine-driven, more tolerance |
| Webhook consumer (outbound fetch) | 5,000 ms | Background check-in |
| Dashboard (API queries) | 10,000 ms | User-initiated via browser |
| Background feed refresh | 30,000 ms | Non-interactive, best-effort |

### 2.3 Configurable Timeout Override

**MUST.** Integrations that make network calls MUST expose a timeout configuration mechanism.

- Environment variable: `CHANGESPEC_TIMEOUT_MS` (integer, milliseconds)
- Config file: `timeout_ms: <integer>` where config files are supported

**MUST.** If `CHANGESPEC_TIMEOUT_MS` is set to `0`, the integration MUST treat this as "use the default timeout", not "no timeout". Removing all timeout protection is not a valid configuration.

**SHOULD.** Integrations SHOULD log the timeout value being used at startup in debug mode, so users can diagnose slow-network false timeouts.

### 2.4 Timeout Handling

When a timeout fires, the integration MUST:

1. Cancel the in-flight request
2. Record the failure for circuit breaker accounting (Section 3)
3. Attempt to serve from local cache (Section 4)
4. If no cache is available, return a degraded response (Section 5)
5. Surface a warning to the user on stderr
6. NOT propagate the timeout as an exception or non-zero exit in advisory mode

---

## 3. Circuit Breaker

### 3.1 Requirement

**MUST.** Conforming integrations that make outbound API calls MUST implement a circuit breaker to prevent retry storms and to protect the user's workflow from repeated slow/hanging calls after the ChangeSpec API becomes unavailable.

### 3.2 Circuit Breaker States

The circuit breaker has three states:

```
CLOSED (normal operation)
  |
  | N consecutive failures within window W
  v
OPEN (degraded mode, no outbound calls)
  |
  | Cooldown period elapsed
  v
HALF-OPEN (probe with single call)
  |
  | Success -> CLOSED
  | Failure -> OPEN (reset cooldown)
```

### 3.3 Default Parameters

| Parameter | Default | Override env var |
|---|---|---|
| Failure threshold N | 3 consecutive failures | `CHANGESPEC_CB_THRESHOLD` |
| Failure window W | 60 seconds | `CHANGESPEC_CB_WINDOW_S` |
| Cooldown period | 120 seconds | `CHANGESPEC_CB_COOLDOWN_S` |

A "failure" for circuit breaker purposes is any of:
- Timeout (per Section 2)
- HTTP 5xx response
- Connection refused / DNS failure
- TLS handshake failure

HTTP 4xx responses (except 429 rate-limiting) are NOT failures for circuit breaker purposes - they indicate successful communication with a valid negative response.

### 3.4 Reference Implementation Pseudocode

```
class CircuitBreaker:
  state = CLOSED
  failure_count = 0
  last_failure_time = null
  cooldown_until = null

  def call(fn, fallback):
    now = current_time()

    if state == OPEN:
      if now >= cooldown_until:
        state = HALF_OPEN
      else:
        warn_user("ChangeSpec unavailable, using cached data")
        return fallback()

    try:
      result = fn()  # with timeout enforcement
      on_success()
      return result
    except TimeoutError, NetworkError, ServerError as err:
      on_failure(now)
      warn_user("ChangeSpec call failed: " + err.message)
      return fallback()

  def on_success():
    failure_count = 0
    state = CLOSED

  def on_failure(now):
    failure_count += 1
    last_failure_time = now
    if failure_count >= THRESHOLD:
      state = OPEN
      cooldown_until = now + COOLDOWN
      log_stderr("ChangeSpec circuit open. Degraded mode for " + COOLDOWN + "s")

  def fallback():
    cached = cache.read()
    if cached:
      return DegradedResult(data=cached, reason="circuit_open")
    return DegradedResult(data=empty, reason="circuit_open_no_cache")
```

### 3.5 Circuit State Persistence

**SHOULD.** Integrations SHOULD persist circuit state across process restarts for long-running contexts (e.g., an IDE with the MCP server running persistently). Persisting state prevents a restarted process from immediately hammering an unavailable API.

For short-lived processes (CLI invocations), in-process state is sufficient.

---

## 4. Cache-First Semantics

### 4.1 Requirement

**MUST.** Conforming integrations that query the ChangeSpec API MUST maintain a local cache of the last successful response. When the API is unavailable (network failure, timeout, circuit open), the integration MUST serve from cache rather than failing.

### 4.2 Cache Location

Default cache locations by consumer type:

| Consumer | Default path |
|---|---|
| CLI | `~/.changespec/cache/` |
| MCP server | OS temp dir + `changespec/cache/` |
| SDK (Node.js) | OS temp dir + `changespec/cache/` |
| SDK (Python) | OS temp dir + `changespec/cache/` |

**SHOULD.** Cache paths SHOULD be configurable via `CHANGESPEC_CACHE_DIR`.

### 4.3 Cache TTL and Staleness

| Data type | Default TTL | Override env var |
|---|---|---|
| General change feed | 7 days | `CHANGESPEC_CACHE_TTL_DAYS` |
| Security advisories | 24 hours | `CHANGESPEC_SECURITY_CACHE_TTL_HOURS` |
| Vendor grade scores | 30 days | - |

**MUST.** When serving from a stale cache (beyond TTL but within stale-tolerance window), the integration MUST emit a staleness warning on stderr. The staleness warning MUST include the cache age and the last-updated timestamp.

**MUST NOT.** Staleness warnings MUST NOT be emitted on stdout (which may be consumed by scripts) and MUST NOT change the exit code or error state of the host process.

Example staleness warning format (stderr):
```
[changespec] Warning: using cached data from 2026-04-09T12:00:00Z (48h old). API unreachable.
```

### 4.4 Cache File Structure

Cache files MUST include metadata sufficient to compute staleness:

```json
{
  "cached_at": "2026-04-09T12:00:00Z",
  "expires_at": "2026-04-16T12:00:00Z",
  "source": "api.changespec.com",
  "etag": "\"abc123\"",
  "events": [ ... ]
}
```

### 4.5 Cold Start (No Cache)

When the integration is running for the first time and has no local cache, and the API is unavailable:

- **MUST** return an empty result set (not an error)
- **MUST** emit a warning on stderr explaining no data is available
- **MUST** exit 0 (CLI advisory mode)
- **SHOULD** suggest the user run `changespec refresh` when connectivity is restored

---

## 5. Graceful Degradation by Consumer Type

### 5.1 MCP Server

When the ChangeSpec API is unavailable and the MCP server is operating in degraded mode:

**MUST.** Every tool call MUST return a structured result, never `isError: true` for infrastructure failures.

Degraded response envelope:

```json
{
  "status": "degraded",
  "reason": "api_unavailable",
  "cached_at": "2026-04-09T12:00:00Z",
  "cache_age_hours": 48,
  "events": [ ... ],
  "note": "ChangeSpec API unreachable. Results from local cache. Set CHANGESPEC_SKIP=1 to silence."
}
```

When `CHANGESPEC_SKIP=1` is set:

```json
{
  "status": "skipped",
  "reason": "CHANGESPEC_SKIP env var set",
  "events": [],
  "note": "ChangeSpec is disabled via CHANGESPEC_SKIP. No network calls made."
}
```

**MUST.** The MCP server MUST NOT throw an unhandled exception for any infrastructure failure. All tool handlers MUST have a catch-all that returns a degraded response per this section.

### 5.2 CLI

Operating modes:

| Mode | Exit code on findings | Exit code on infra failure |
|---|---|---|
| Advisory (default) | 0 | 0 |
| Blocking (`--fail-on` set) | 2 | 0 |
| User error (bad args) | 3 | - |

**MUST.** Exit code 1 MUST NOT be used for ChangeSpec infrastructure failures. Exit code 1 is reserved for hard errors in the user's own toolchain. Using it for our availability problems would break `set -e` pipelines.

Degraded CLI output (stderr):
```
Warning: ChangeSpec API unavailable (timeout after 2s). Showing cached data from 48h ago.
To bypass entirely: export CHANGESPEC_SKIP=1
```

### 5.3 Webhooks

**MUST.** Webhook delivery failures (ChangeSpec cannot deliver to a consumer endpoint) MUST use exponential backoff with jitter.

Backoff schedule (minimum):

| Attempt | Delay |
|---|---|
| 1 (initial) | Immediate |
| 2 | 30 seconds |
| 3 | 5 minutes |
| 4 | 30 minutes |
| 5 | 2 hours |
| 6+ | 6 hours (cap) |

**MUST.** After 24 hours of failed delivery, the webhook event MUST be dropped. An event that could not be delivered in 24 hours is no longer timely.

**MUST NOT.** The drop MUST be logged server-side. Consumers SHOULD poll the API to recover missed events after an outage.

**SHOULD.** ChangeSpec SHOULD expose a `GET /v1/subscriptions/{id}/missed` endpoint that returns events that could not be delivered during an outage window.

### 5.4 Dashboard

**MUST.** The ChangeSpec dashboard MUST display cached or last-known data when the backend is in a degraded state, rather than showing an error page.

**MUST.** A visible "last updated" timestamp MUST be displayed whenever cached data is being served.

**SHOULD.** The dashboard SHOULD link to status.changespec.com when degraded data is being displayed.

---

## 6. Status and Health Discovery

### 6.1 Well-Known Health Endpoint

**MUST.** The ChangeSpec platform MUST expose a machine-readable health endpoint at:

```
https://api.changespec.com/.well-known/changespec-health
```

Response schema:

```json
{
  "status": "ok",
  "components": {
    "api": "ok",
    "feed": "ok",
    "webhooks": "ok",
    "mcp": "ok"
  },
  "feed_freshness": {
    "last_event_at": "2026-04-16T10:00:00Z",
    "lag_minutes": 12
  },
  "incidents": [],
  "checked_at": "2026-04-16T14:00:00Z"
}
```

`status` values: `ok`, `degraded`, `outage`

**MUST.** The endpoint MUST respond within 1,000 ms under normal conditions.

**MUST.** The endpoint MUST return HTTP 200 even when `status` is `degraded`. HTTP error codes from this endpoint indicate the status service itself has failed, not merely that ChangeSpec is degraded. Client tooling MUST treat a non-200 from this endpoint as "status unknown, assume degraded".

**MUST.** The endpoint MUST be served with `Cache-Control: no-cache` so clients always get fresh data.

### 6.2 Status Page

**MUST.** A human-readable status page MUST be available at `status.changespec.com`.

**MUST.** The status page MUST be hosted independently from the main ChangeSpec infrastructure so it remains available when the API is down.

### 6.3 RSS Incident Feed

**MUST.** An RSS feed of incidents MUST be available at:

```
https://status.changespec.com/incidents.rss
```

Feed schema per item:

```xml
<item>
  <title>API Degradation - Elevated latency on /v1/changes</title>
  <description>Status: investigating. Impact: response times 3-8s. No data loss.</description>
  <pubDate>Wed, 16 Apr 2026 10:30:00 +0000</pubDate>
  <guid>https://status.changespec.com/incidents/2026-04-16-latency</guid>
  <link>https://status.changespec.com/incidents/2026-04-16-latency</link>
  <changespec:status>investigating</changespec:status>
  <changespec:severity>degraded</changespec:severity>
  <changespec:components>api,feed</changespec:components>
</item>
```

Client tooling MAY subscribe to this feed to drive local degradation UI without polling the health endpoint.

### 6.4 Version Negotiation

**MUST.** The ChangeSpec API MUST advertise its current and minimum supported client versions at:

```
https://api.changespec.com/.well-known/changespec-api
```

Response:

```json
{
  "api_version": "1",
  "min_client_version": "0.1.0",
  "deprecated_client_versions": [],
  "spec_version": "1.0.0"
}
```

Client integrations SHOULD check this endpoint on startup (with caching) and emit a warning when running a deprecated version.

---

## 7. Versioning and Forward Compatibility

### 7.1 Client Stability Guarantee

**MUST.** Old MCP server versions MUST continue to function against the current API indefinitely, subject only to explicit deprecation notices with a minimum 12-month lead time.

**MUST NOT.** The ChangeSpec API MUST NOT make a breaking change to any response field consumed by existing client versions without going through the deprecation process in Section 7.2.

### 7.2 Deprecation Process

1. The deprecated field or behavior is announced in the API changelog and on status.changespec.com
2. The minimum 12-month deprecation window begins
3. The API returns a `Deprecation` header on responses that include deprecated fields
4. Client integrations emit a deprecation warning on stderr when they detect the header
5. At the end of the window, the field or behavior is removed in a new API version
6. Old API versions remain available for an additional 6 months after the new version ships

### 7.3 Version Pinning in MCP Configuration

**SHOULD.** MCP server configurations SHOULD allow pinning to a specific API version:

```json
{
  "mcpServers": {
    "changespec": {
      "command": "changespec-mcp",
      "env": {
        "CHANGESPEC_API_VERSION": "1"
      }
    }
  }
}
```

### 7.4 No Forced Upgrades

**MUST NOT.** The ChangeSpec platform MUST NOT force-upgrade client software by breaking compatibility with older versions outside the deprecation window.

**MUST.** When a version is deprecated, clients running that version MUST receive a clear warning in their output, not a broken experience.

---

## 8. Conformance Tests for Non-Blocking Behavior

These test definitions live in `spec/conformance/test-vectors/safety/`. A conforming integration MUST pass all tests in this directory. Test format follows the same YAML schema as other conformance test vectors.

See `spec/conformance/test-vectors/safety/` for the full set. The 10 mandatory scenarios are:

| ID | Scenario |
|---|---|
| safety-001 | Client handles HTTP 500 gracefully |
| safety-002 | Client handles connection timeout gracefully |
| safety-003 | Client handles malformed JSON response gracefully |
| safety-004 | Client caches a successful response to disk |
| safety-005 | Client returns cached data when API is offline |
| safety-006 | Client respects CHANGESPEC_SKIP=1 bypass |
| safety-007 | Client circuit-breaks after repeated failures |
| safety-008 | CLI exits 0 in advisory mode despite findings |
| safety-009 | Client respects timeout budget |
| safety-010 | Client surfaces degradation warning without crashing |

---

## Appendix A: Exit Code Reference

| Code | Meaning |
|---|---|
| 0 | Success (advisory mode findings, cache served, bypass active) |
| 2 | Blocking finding (only when `--fail-on` is explicitly set) |
| 3 | User error (bad arguments, missing required input) |
| 1 | RESERVED - MUST NOT be used for ChangeSpec infrastructure failures |

Note: Exit code 1 is conventionally used by shells and scripts to indicate "general error". Using it for ChangeSpec infrastructure failures would break `|| true` guards and `set -e` pipelines in unexpected ways. ChangeSpec infrastructure problems are never the user's fault and MUST NOT produce exit 1.

---

## Appendix B: SLO Reference

ChangeSpec targets the following service-level objectives. These are targets, not guarantees, and are published so client implementations can set appropriate expectations.

| Metric | Target |
|---|---|
| API availability (monthly) | 99% |
| API p95 response time | < 500 ms |
| Feed freshness (general) | Events published within 1 hour of source |
| Feed freshness (security) | Events published within 15 minutes of source |
| Health endpoint availability | 99.5% |
| Status page availability | 99.9% (independently hosted) |

99% monthly availability corresponds to approximately 7.3 hours of downtime per month. Client integrations MUST be designed to function through that level of unavailability via the cache-first and circuit-breaker mechanisms in this document.

We do not promise 99.9% or higher at this stage. Any integration that would break under 99% availability is not conforming.

---

## Appendix C: Normative References

- RFC 2119: Key words for use in RFCs to Indicate Requirement Levels
- ChangeSpec 1.0 Specification, spec.md
- Integration Safety Conformance Tests, spec/conformance/test-vectors/safety/
