#!/usr/bin/env python3
"""
ChangeSpec conformance runner for Python.

Loads YAML test vectors from the specified directory tree, runs each vector
against the changespec Python reference implementation, and prints a conformance
report.

Usage:
    python runner.py <vectors-directory> [--level 1|2|3]

Example:
    python runner.py ../../test-vectors
    python runner.py ../../test-vectors --level 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import ValidationError

# Add the parent reference implementation to the path so we can import it.
# In a real CI setup, the changespec package would be installed via pip.
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "reference" / "python"))

from changespec import validate, SPEC_VERSION

RUNNER_VERSION = "1.0.0"
DEFAULT_TIMEOUT_MS = 5000


@dataclass
class GenerateSpec:
    type: str
    field: str
    pattern: str = ""
    repeat: int = 0
    size_bytes: int = 0
    count: int = 0
    item_value: str = "item"
    depth: int = 10


@dataclass
class Expected:
    valid: bool
    reason: str = ""
    error_type: str = ""
    no_network_requests: bool = False
    no_file_access: bool = False
    no_crash: bool = False
    no_prototype_corruption: bool = False
    max_memory_mb: int = 0
    max_time_ms: int = 0


@dataclass
class TestVector:
    id: str
    description: str
    level: int
    spec_clause: str = ""
    input_type: str = "yaml"
    input: Optional[dict[str, Any]] = None
    input_json: str = ""
    raw_input: str = ""
    generate: Optional[GenerateSpec] = None
    base_input: Optional[dict[str, Any]] = None
    expected: Expected = field(default_factory=lambda: Expected(valid=True))
    notes: str = ""


@dataclass
class VectorResult:
    vector_id: str
    file_path: str
    description: str
    level: int
    status: str  # PASS, FAIL, SKIP, WARN
    reason: str = ""
    duration_ms: float = 0.0


def load_vectors(vectors_dir: Path) -> list[tuple[str, TestVector]]:
    """Load all .yml test vector files from the directory tree."""
    results = []

    for root, dirs, files in os.walk(vectors_dir):
        dirs.sort()
        for filename in sorted(files):
            if not filename.endswith(".yml"):
                continue
            full_path = Path(root) / filename
            relative_path = str(full_path.relative_to(vectors_dir))

            with open(full_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)

            if raw is None:
                continue

            expected_raw = raw.get("expected", {})
            expected = Expected(
                valid=expected_raw.get("valid", True),
                reason=expected_raw.get("reason", ""),
                error_type=expected_raw.get("error_type", ""),
                no_network_requests=expected_raw.get("no_network_requests", False),
                no_file_access=expected_raw.get("no_file_access", False),
                no_crash=expected_raw.get("no_crash", False),
                max_memory_mb=expected_raw.get("max_memory_mb", 0),
                max_time_ms=expected_raw.get("max_time_ms", 0),
            )

            gen_raw = raw.get("generate")
            generate = None
            if gen_raw:
                generate = GenerateSpec(
                    type=gen_raw.get("type", ""),
                    field=gen_raw.get("field", ""),
                    pattern=gen_raw.get("pattern", ""),
                    repeat=gen_raw.get("repeat", 0),
                    size_bytes=gen_raw.get("size_bytes", 0),
                    count=gen_raw.get("count", 0),
                    item_value=gen_raw.get("item_value", "item"),
                    depth=gen_raw.get("depth", 10),
                )

            vector = TestVector(
                id=raw.get("id", filename),
                description=raw.get("description", ""),
                level=raw.get("level", 1),
                spec_clause=raw.get("spec_clause", ""),
                input_type=raw.get("input_type", "yaml").strip(),
                input=raw.get("input"),
                input_json=raw.get("input_json", ""),
                raw_input=raw.get("raw_input", ""),
                generate=generate,
                base_input=raw.get("base_input"),
                expected=expected,
                notes=raw.get("notes", ""),
            )

            results.append((relative_path, vector))

    return results


def build_input(vector: TestVector) -> tuple[bytes, Optional[str]]:
    """
    Build the input bytes for a test vector.
    Returns (bytes, skip_reason). If skip_reason is set, the vector should be skipped.
    """
    input_type = (vector.input_type or "yaml").strip()

    if input_type in ("yaml", ""):
        data = vector.input or {}
        return json.dumps(data).encode(), None

    if input_type == "json_string":
        return (vector.input_json or "").encode(), None

    if input_type == "raw_bytes":
        return (vector.raw_input or "").encode(), None

    if input_type == "generated":
        g = vector.generate
        if g is None:
            return b"", "generate spec missing"

        base = dict(vector.base_input or {})

        if g.type == "oversized_field":
            size = g.size_bytes or 1000
            base[g.field] = "A" * size

        elif g.type == "array_overflow":
            count = g.count or 100
            base[g.field] = [g.item_value] * count

        elif g.type in ("deeply_nested_ext", "deeply_nested_field"):
            depth = g.depth or 10
            nested: Any = "leaf"
            for _ in range(depth):
                nested = {"child": nested}
            base[g.field] = nested

        else:
            return b"", f"unsupported generate type: {g.type}"

        return json.dumps(base).encode(), None

    return b"", f"unsupported input_type: {input_type}"


def run_single(input_bytes: bytes) -> tuple[bool, Optional[Exception]]:
    """Call the changespec validator and return (is_valid, error)."""
    try:
        validate(input_bytes)
        return True, None
    except (ValidationError, json.JSONDecodeError) as e:
        return False, e
    except Exception as e:
        return False, e


def run_vector(file_path: str, vector: TestVector, max_level: int) -> VectorResult:
    """Execute a single test vector and return the result."""
    base = VectorResult(
        vector_id=vector.id,
        file_path=file_path,
        description=vector.description,
        level=vector.level,
        status="PASS",
    )

    if vector.level > max_level:
        base.status = "SKIP"
        base.reason = f"level {vector.level} exceeds max level {max_level}"
        return base

    input_bytes, skip_reason = build_input(vector)
    if skip_reason:
        base.status = "SKIP"
        base.reason = skip_reason
        return base

    timeout_ms = vector.expected.max_time_ms or DEFAULT_TIMEOUT_MS
    timeout_s = timeout_ms / 1000.0

    start = time.monotonic()

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_single, input_bytes)
            try:
                is_valid, error = future.result(timeout=timeout_s)
            except FutureTimeoutError:
                base.status = "FAIL"
                base.reason = f"timed out after {timeout_ms}ms"
                base.duration_ms = (time.monotonic() - start) * 1000
                return base
    except Exception as e:
        base.status = "FAIL"
        base.reason = f"runner error: {e}"
        base.duration_ms = (time.monotonic() - start) * 1000
        return base

    base.duration_ms = (time.monotonic() - start) * 1000

    if is_valid == vector.expected.valid:
        base.status = "PASS"
        return base

    base.status = "FAIL"
    if vector.expected.valid:
        base.reason = f"expected valid=true but got error: {error}"
    else:
        base.reason = "expected valid=false but validation succeeded (no error raised)"

    return base


def print_report(results: list[VectorResult]) -> None:
    """Print the conformance report."""
    passed = failed = skipped = warned = 0
    level_pass: dict[int, int] = {}
    level_total: dict[int, int] = {}

    for r in results:
        if r.status == "PASS":
            passed += 1
            level_pass[r.level] = level_pass.get(r.level, 0) + 1
            level_total[r.level] = level_total.get(r.level, 0) + 1
        elif r.status == "FAIL":
            failed += 1
            level_total[r.level] = level_total.get(r.level, 0) + 1
        elif r.status == "SKIP":
            skipped += 1
        elif r.status == "WARN":
            warned += 1
            level_total[r.level] = level_total.get(r.level, 0) + 1

    for r in results:
        if r.status == "PASS":
            print(f"PASS  {r.file_path}")
        elif r.status == "SKIP":
            print(f"SKIP  {r.file_path} - {r.reason}")
        elif r.status == "WARN":
            print(f"WARN  {r.file_path}")
            print(f"      {r.reason}")
        elif r.status == "FAIL":
            print(f"FAIL  {r.file_path} - {r.description}")
            print(f"      {r.reason}")

    print("\nSummary:")
    print(f"  Vectors run:  {passed + failed + warned}")
    print(f"  Passed:       {passed}")
    print(f"  Failed:       {failed}")
    print(f"  Warnings:     {warned}")
    print(f"  Skipped:      {skipped}\n")

    level_names = {1: "Syntactic", 2: "Semantic", 3: "Secure"}
    for level in [1, 2, 3]:
        total = level_total.get(level, 0)
        if total == 0:
            continue
        p = level_pass.get(level, 0)
        status = "PASS" if p == total else "FAIL"
        print(f"  Level {level} ({level_names[level]}): {status} ({p}/{total})")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ChangeSpec conformance runner for Python"
    )
    parser.add_argument("vectors_dir", help="Path to the test-vectors directory")
    parser.add_argument(
        "--level",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="Maximum conformance level to test (default: 3)",
    )
    args = parser.parse_args()

    vectors_dir = Path(args.vectors_dir)
    if not vectors_dir.exists():
        print(f"Error: vectors directory not found: {vectors_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"ChangeSpec Conformance Runner v{RUNNER_VERSION}")
    print(f"Testing: changespec Python v{SPEC_VERSION}")
    print(f"Vectors: {vectors_dir}")
    print(f"Max level: {args.level}\n")

    vector_files = load_vectors(vectors_dir)
    results = []

    for file_path, vector in vector_files:
        result = run_vector(file_path, vector, args.level)
        results.append(result)

    print_report(results)

    any_fail = any(r.status == "FAIL" for r in results)
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
