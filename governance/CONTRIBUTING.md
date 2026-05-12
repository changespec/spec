# Contributing to ChangeSpec

**Version:** 1.0
**Effective:** 2026-04-16

---

Thank you for your interest in contributing to ChangeSpec. This document describes how to participate.

## What we accept

- Bug reports: unclear language, contradictions, or errors in the specification
- Clarification requests: questions about intended behavior belong in GitHub Discussions before becoming issues
- Editorial improvements: typos, grammatical errors, broken links, formatting inconsistencies
- Substantive changes: proposals to add informative notes, clarify ambiguous language, extend examples
- Significant changes: new fields, new enum values, changes to the signing scheme - these require a SEP

If you are unsure which category your contribution falls into, open a Discussion first.

## Filing issues

Use GitHub Issues at https://github.com/changespec/spec/issues.

A good issue:

- States the section number and quotes the relevant text
- Explains why the current text is incorrect, unclear, or incomplete
- Proposes the intended behavior (not necessarily the specific wording)
- Notes whether you are willing to draft the fix

Label your issue with one of: `editorial`, `clarification`, `substantive`, `bug`, `question`.

## Submitting pull requests

1. Fork the repository and create a branch from `main`.
2. Make your changes. For spec changes, edit `spec.md`. For schema changes, edit `schema.json`.
3. Update the reference implementations if your change affects conformance behavior.
4. Run the conformance test suite (`make test` in each reference implementation directory).
5. Open a pull request. Fill in the PR template completely.

All PRs require:

- A description of what changed and why
- The section number(s) affected
- Whether the change alters conformance requirements
- For conformance-affecting changes: a description of how implementations must change

## Specification Extension Proposals (SEPs)

Significant changes require a SEP. See GOVERNANCE.md for the SEP process.

Before opening a SEP pull request, open a GitHub Discussion to gauge interest and gather early feedback. This saves effort if the direction is fundamentally problematic.

The SEP template is at `governance/SEP-TEMPLATE.md` in the repository.

## Reference implementation contributions

The reference implementations live in separate repositories:

- Go: https://github.com/changespec/changespec-go
- TypeScript: https://github.com/changespec/changespec-ts
- Python: https://github.com/changespec/changespec-py

Each has its own CONTRIBUTING.md. All reference implementation contributions must pass the full conformance test suite before merge.

## Code of conduct

All contributors are expected to follow the Code of Conduct (CODE_OF_CONDUCT.md). Violations should be reported to conduct@changespec.org.

## Intellectual property

By contributing to ChangeSpec, you agree that your contributions are licensed under the Apache 2.0 license (for specification and schema content) or the MIT license (for reference implementation code). You represent that you have the right to make the contribution under these terms.

If your contribution includes material that is the property of your employer, you are responsible for ensuring you have authorization to contribute it.

## Contact

- GitHub Issues: https://github.com/changespec/spec/issues
- GitHub Discussions: https://github.com/changespec/spec/discussions
- General inquiries: standards@changespec.org
- Security issues: security@changespec.org (do not file security issues as public GitHub issues)
