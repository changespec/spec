# ChangeSpec Governance

**Version:** 1.0
**Effective:** 2026-04-16

---

## Decision-making

ChangeSpec uses an IETF-adjacent rough-consensus model. Decisions are made by the maintainer group with input from the contributor community. The goal is consensus, not unanimity. A rough consensus is reached when no substantive unresolved objections remain, even if not everyone agrees.

## Roles

### Contributor

Anyone who has submitted a pull request, filed an issue, or participated in a SEP discussion. No formal membership required.

### Maintainer

Maintainers merge pull requests, run the SEP process, and cut releases. Maintainers are listed in MAINTAINERS.md.

**Becoming a maintainer:** Any consistent contributor may be nominated by an existing maintainer. Nominations are accepted by rough consensus of the existing maintainer group. New maintainers are expected to have demonstrated understanding of the specification, good judgment in code review, and a commitment to the project's governance principles.

**Emeritus maintainers:** Maintainers who step back from active participation are moved to emeritus status. Emeritus maintainers retain recognition but do not participate in governance decisions.

### Working Group Chair

Leads a specific Working Group for the scope of the WG's charter. Appointed by the maintainer group. WG Chairs need not be existing maintainers.

## Change categories

### Routine changes

Typos, cross-references, clarifications that do not alter semantics, broken link fixes. These may merge on approval of one maintainer. They do not require a prior issue, though one is recommended for substantive clarifications.

### Substantive changes

Changes that add or clarify constraints, add informative notes, extend examples, or clarify ambiguous language without changing semantics. Require:

- An associated issue or discussion.
- Approval of two maintainers.
- No unresolved substantive objections after 7 days open.

### Significant changes (SEP required)

Any change that:

- Adds a required field.
- Removes any field.
- Changes the semantics of an existing field.
- Alters transport bindings in a breaking way.
- Changes the signature scheme or security model.
- Adds a new enum value to `category` or `severity`.
- Changes the versioning policy.

These require a Specification Extension Proposal (SEP).

## SEP process

1. **Draft.** Author opens a pull request against the `seps/` directory in the repository. The SEP file must follow the SEP template (SEP-TEMPLATE.md). The pull request is labeled `sep`.

2. **Discussion.** A 30-day public comment period begins when a maintainer labels the PR `sep-open`. Comments are in the PR thread and in the associated GitHub Discussion thread.

3. **Revision.** The author revises the proposal based on feedback. The PR description is updated with a summary of substantive changes and how objections were resolved.

4. **Decision.** After at least 30 days of open comment (extended if substantive objections arise in the final week), maintainers determine whether rough consensus has been reached. Outcomes:
   - **Accepted:** Merged. Implementation proceeds.
   - **Withdrawn:** Author decides not to proceed.
   - **Rejected:** Maintainers determine there is no rough consensus. The SEP is closed. The author may re-open with substantive changes.
   - **Returned for revision:** Specific issues must be resolved before re-evaluation.

5. **Implementation.** Accepted SEPs are implemented in the specification and reference implementations. The implementation may be developed before or after acceptance. A SEP is not merged until reference implementations pass the relevant conformance tests.

## Release process

**Patch releases (X.Y.Z):** Clarifications only. Maintainer decision, no SEP required. Release tag created from main after all relevant PRs are merged.

**Minor releases (X.Y):** May include accepted SEPs for optional field additions or enum extensions. Two-week stabilization period after final PR merge before tagging. Reference implementations must pass the full conformance suite before release.

**Major releases (X.0):** Require a formal deprecation period of at least 12 months for the prior major version. Major releases are treated as a new charter cycle and require maintainer consensus.

## Meetings

Meeting cadence is determined by the Working Groups, not the maintainer group. Maintainer decisions are made asynchronously via GitHub. If a synchronous discussion is needed (for example, to resolve a deadlocked SEP), any maintainer may request a meeting via GitHub Discussions. Meetings are open to observers and minutes are posted within 5 business days.

## Conflict resolution

Technical disputes are resolved through the SEP comment process. If a maintainer group cannot reach rough consensus, the steward (Roboticforce Inc.) makes a final determination. The steward has no vote in ordinary governance decisions; steward authority is reserved for deadlocks.

Conduct disputes are handled under the Code of Conduct.

Trademark disputes are handled under the Trademark Policy.

## Amendments

This document may be amended by rough consensus of the maintainer group after a 14-day public comment period. Material changes that affect contributor rights require a 30-day comment period.
