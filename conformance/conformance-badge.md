# ChangeSpec Conformance Badge

This document defines the conformance badge format, embed codes, and revocation mechanism.

---

## Badge Designs

### SVG Badges

Four badges correspond to the four certification levels.

**Level 1 - Syntactic**

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="190" height="20">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="190" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="120" height="20" fill="#555"/>
    <rect x="120" width="70" height="20" fill="#4c97d1"/>
    <rect width="190" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="110">
    <text x="610" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="1100" lengthAdjust="spacing">ChangeSpec Certified</text>
    <text x="610" y="140" transform="scale(.1)" textLength="1100" lengthAdjust="spacing">ChangeSpec Certified</text>
    <text x="1550" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="600" lengthAdjust="spacing">Level 1</text>
    <text x="1550" y="140" transform="scale(.1)" textLength="600" lengthAdjust="spacing">Level 1</text>
  </g>
</svg>
```

**Level 2 - Semantic** - same structure, `#4c97d1` replaced with `#4caf50`, label `Level 2`.

**Level 3 - Secure** - same structure, `#4c97d1` replaced with `#7c4dff`, label `Level 3`.

**Level 4 - Full Producer** - same structure, `#4c97d1` replaced with `#f57c00`, label `Level 4`.

### Color Codes

| Level | Name | Badge Color |
|---|---|---|
| 1 | Syntactic | `#4c97d1` (blue) |
| 2 | Semantic | `#4caf50` (green) |
| 3 | Secure | `#7c4dff` (purple) |
| 4 | Full Producer | `#f57c00` (orange) |

---

## Static Badge Embed Codes

Use these for self-certified implementations. Replace `LEVEL` with the achieved level (1, 2, 3, or 4):

**Markdown:**
```markdown
[![ChangeSpec Certified Level LEVEL](https://changespec.com/badges/certified-level-LEVEL.svg)](https://changespec.com/certified)
```

**HTML:**
```html
<a href="https://changespec.com/certified">
  <img src="https://changespec.com/badges/certified-level-LEVEL.svg"
       alt="ChangeSpec Certified Level LEVEL"
       height="20">
</a>
```

**reStructuredText:**
```rst
.. image:: https://changespec.com/badges/certified-level-LEVEL.svg
   :target: https://changespec.com/certified
   :alt: ChangeSpec Certified Level LEVEL
```

---

## Dynamic Badge Endpoint

For officially certified implementations, a dynamic badge endpoint verifies that the library is still passing the current test vectors:

```
https://changespec.com/badges/verify?library=<library-id>&level=<level>
```

This endpoint:

1. Looks up the library's CI integration webhook registered during official certification.
2. Checks the most recent conformance CI run for the library.
3. If the most recent run passes at the claimed level, returns the green badge.
4. If the most recent run fails, returns a red "Conformance Failed" badge.
5. If no run has been recorded in the last 30 days, returns a yellow "Unverified" badge.

### Registering a Dynamic Badge

During official certification, provide:

- The GitHub repository URL for the library.
- The name of the GitHub Actions workflow that runs the conformance suite.
- The branch to monitor (typically `main`).

The ChangeSpec certification service polls the GitHub Actions API to check the status of the latest conformance run.

### Dynamic Badge Markdown

```markdown
[![ChangeSpec Certified Level 3](https://changespec.com/badges/verify?library=myorg-mylibrary&level=3)](https://changespec.com/certified/myorg-mylibrary)
```

---

## Badge Usage Requirements

1. The badge must link to either `changespec.com/certified` (for self-certified) or the library's certification page (for officially certified).
2. The alt text must accurately state the level.
3. The badge must not be displayed if the library no longer passes the test suite at the claimed level.
4. The level number in the badge must match the level actually achieved.

---

## Revocation Mechanism

### Automatic Revocation (Dynamic Badges)

For libraries using the dynamic badge endpoint, revocation is automatic:

- If a CI run fails at the claimed level, the badge endpoint returns a red "Conformance Failed" badge within 24 hours.
- The library owner is notified by email that the badge status has changed.
- If the conformance issue is not resolved within 60 days, the library is removed from the certified registry.

### Manual Revocation (Self-Certified, Static Badges)

For self-certified libraries using static badges:

1. Roboticforce Inc. may file a GitHub issue on the library repository noting that recent conformance runs (if visible) show failures.
2. If the library does not respond or fix the issue within 60 days, Roboticforce Inc. sends a formal notice requesting removal of the badge.
3. If the badge is not removed, the certification is listed as "Revoked" in the public registry.

The public registry at `changespec.com/certified` reflects the current certification status of all registered implementations. Users who rely on the badge should verify the registry status for any implementation they depend on.

---

## Getting the Static Badge Files

The official SVG badge files are available at:

- `https://changespec.com/badges/certified-level-1.svg`
- `https://changespec.com/badges/certified-level-2.svg`
- `https://changespec.com/badges/certified-level-3.svg`
- `https://changespec.com/badges/certified-level-4.svg`

These files may be served from the library's own infrastructure (caching a copy of the badge is permitted) but must not be modified.
