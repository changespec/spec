# CI Integration Guide

This document describes how to wire the ChangeSpec conformance test suite into a library's continuous integration pipeline using GitHub Actions.

---

## Quick Start

Add this file to your repository at `.github/workflows/changespec-conformance.yml`:

```yaml
name: ChangeSpec Conformance

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  # Run weekly to catch spec test vector updates.
  schedule:
    - cron: "0 9 * * 1"

jobs:
  conformance:
    uses: changespec/conformance/.github/workflows/reusable-runner.yml@v1
    with:
      level: 3
      language: go
      library_module: github.com/myorg/my-changespec-lib
```

---

## Reusable Workflow

The reusable workflow is published at `changespec/conformance/.github/workflows/reusable-runner.yml`.

### Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `level` | no | `3` | Maximum conformance level to test (1, 2, or 3) |
| `language` | yes | - | Language runtime to use: `go`, `typescript`, or `python` |
| `library_module` | no | - | For Go: the module path of the library under test |
| `vectors_ref` | no | `v1` | Git ref of the conformance repo to use for test vectors |
| `runner_timeout_minutes` | no | `10` | Maximum runtime for the full conformance job |

### Workflow Definition

```yaml
# .github/workflows/reusable-runner.yml in changespec/conformance repo

name: Reusable ChangeSpec Conformance Runner

on:
  workflow_call:
    inputs:
      level:
        type: number
        default: 3
      language:
        type: string
        required: true
      library_module:
        type: string
        default: ""
      vectors_ref:
        type: string
        default: v1
      runner_timeout_minutes:
        type: number
        default: 10
    outputs:
      passed:
        description: "Number of vectors passed"
        value: ${{ jobs.run.outputs.passed }}
      failed:
        description: "Number of vectors failed"
        value: ${{ jobs.run.outputs.failed }}
      certified_level:
        description: "Highest level achieved (0 if any failures)"
        value: ${{ jobs.run.outputs.certified_level }}

jobs:
  run:
    runs-on: ubuntu-24.04
    timeout-minutes: ${{ inputs.runner_timeout_minutes }}
    outputs:
      passed: ${{ steps.report.outputs.passed }}
      failed: ${{ steps.report.outputs.failed }}
      certified_level: ${{ steps.report.outputs.certified_level }}

    steps:
      - name: Checkout conformance suite
        uses: actions/checkout@v4
        with:
          repository: changespec/conformance
          ref: ${{ inputs.vectors_ref }}
          path: conformance-suite

      - name: Checkout library under test
        uses: actions/checkout@v4
        with:
          path: library

      - name: Run Go conformance
        if: inputs.language == 'go'
        working-directory: conformance-suite/runner/go
        run: |
          go mod tidy
          go run runner.go \
            ../../test-vectors \
            --level ${{ inputs.level }} \
            2>&1 | tee /tmp/conformance-output.txt
          echo "exit_code=${PIPESTATUS[0]}" >> $GITHUB_ENV

      - name: Run TypeScript conformance
        if: inputs.language == 'typescript'
        working-directory: conformance-suite/runner/typescript
        run: |
          npm ci
          npx ts-node runner.ts \
            ../../test-vectors \
            --level ${{ inputs.level }} \
            2>&1 | tee /tmp/conformance-output.txt
          echo "exit_code=${PIPESTATUS[0]}" >> $GITHUB_ENV

      - name: Run Python conformance
        if: inputs.language == 'python'
        working-directory: conformance-suite/runner/python
        run: |
          pip install pyyaml
          pip install -e ../../library
          python runner.py \
            ../../test-vectors \
            --level ${{ inputs.level }} \
            2>&1 | tee /tmp/conformance-output.txt
          echo "exit_code=${PIPESTATUS[0]}" >> $GITHUB_ENV

      - name: Parse report
        id: report
        run: |
          OUTPUT=$(cat /tmp/conformance-output.txt)
          PASSED=$(echo "$OUTPUT" | grep "Passed:" | awk '{print $2}')
          FAILED=$(echo "$OUTPUT" | grep "Failed:" | awk '{print $2}')

          echo "passed=${PASSED}" >> $GITHUB_OUTPUT
          echo "failed=${FAILED}" >> $GITHUB_OUTPUT

          if [ "$FAILED" = "0" ]; then
            echo "certified_level=${{ inputs.level }}" >> $GITHUB_OUTPUT
          else
            echo "certified_level=0" >> $GITHUB_OUTPUT
          fi

      - name: Upload conformance report
        uses: actions/upload-artifact@v4
        with:
          name: conformance-report
          path: /tmp/conformance-output.txt
          retention-days: 90

      - name: Fail if conformance failed
        if: env.exit_code != '0'
        run: exit 1
```

---

## Self-Managed Integration (No Reusable Workflow)

If you prefer to manage the CI yourself without the reusable workflow:

### Go Example

```yaml
name: ChangeSpec Conformance

on:
  push:
    branches: [main]
  pull_request:

jobs:
  conformance:
    runs-on: ubuntu-24.04

    steps:
      - uses: actions/checkout@v4
        with:
          path: library

      - name: Checkout conformance vectors
        uses: actions/checkout@v4
        with:
          repository: changespec/conformance
          ref: v1
          path: conformance

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: "1.22"

      - name: Run conformance
        working-directory: conformance/runner/go
        run: |
          # Point the runner at the library under test.
          # Modify go.mod to use the local library if needed:
          # go mod edit -replace github.com/changespec/changespec-go=../../library
          go run runner.go ../../test-vectors --level 3
```

### TypeScript Example

```yaml
name: ChangeSpec Conformance

on:
  push:
    branches: [main]
  pull_request:

jobs:
  conformance:
    runs-on: ubuntu-24.04

    steps:
      - uses: actions/checkout@v4
        with:
          path: library

      - name: Checkout conformance vectors
        uses: actions/checkout@v4
        with:
          repository: changespec/conformance
          ref: v1
          path: conformance

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "22"

      - name: Install runner dependencies
        working-directory: conformance/runner/typescript
        run: |
          npm install
          # Link the local library:
          cd ../../library && npm link
          cd ../conformance/runner/typescript && npm link @changespec/changespec

      - name: Run conformance
        working-directory: conformance/runner/typescript
        run: npx ts-node runner.ts ../../test-vectors --level 3
```

### Python Example

```yaml
name: ChangeSpec Conformance

on:
  push:
    branches: [main]
  pull_request:

jobs:
  conformance:
    runs-on: ubuntu-24.04

    steps:
      - uses: actions/checkout@v4
        with:
          path: library

      - name: Checkout conformance vectors
        uses: actions/checkout@v4
        with:
          repository: changespec/conformance
          ref: v1
          path: conformance

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install pyyaml
          pip install -e ./library

      - name: Run conformance
        working-directory: conformance/runner/python
        run: python runner.py ../../test-vectors --level 3
```

---

## Adding a Conformance Badge

After a successful run, add the badge to your README. See [conformance-badge.md](conformance-badge.md) for the full badge specification.

The simplest approach is to use the static badge with a link to your latest CI run:

```markdown
[![ChangeSpec Certified Level 3](https://changespec.com/badges/certified-level-3.svg)](https://github.com/myorg/my-library/actions)
```

---

## Conformance Job as a Required Check

To prevent regressions, configure the conformance job as a required status check on protected branches:

1. Go to repository Settings > Branches > Branch protection rules.
2. Edit the rule for your main branch.
3. Under "Require status checks to pass before merging", add the `conformance` job.

This ensures that a PR which breaks conformance cannot be merged.

---

## Keeping Vectors Up to Date

The conformance suite uses tagged releases (`v1`, `v1.1`, etc.) that correspond to spec versions. When a new minor version of the spec is released:

1. The `v1` tag is updated to point to the latest 1.x vectors.
2. New vectors are added; existing vectors are never modified or removed.
3. Your CI will automatically pick up new vectors on the next run if you use `vectors_ref: v1`.

To pin to a specific vector set (for reproducibility):

```yaml
vectors_ref: v1.0.0  # exact tag, never changes
```

To always use the latest 1.x vectors:

```yaml
vectors_ref: v1  # floating tag, picks up new vectors automatically
```

---

## Reporting Conformance Results

When submitting for official certification, link to a GitHub Actions run that shows all vectors passing. The URL format is:

```
https://github.com/<org>/<repo>/actions/runs/<run-id>
```

The run must show the conformance job passing with 0 failures at the desired level.
