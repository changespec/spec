"""
Tests that load and validate every example from spec/examples/ against
the ChangeSpec 1.0 Python reference implementation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from changespec import (
    SPEC_VERSION,
    Category,
    ChangeSpecEvent,
    Severity,
    SourceType,
    validate,
)

# Resolve the examples directory relative to this test file.
EXAMPLES_DIR = Path(__file__).parent.parent.parent.parent / "examples"


def example_files() -> list[Path]:
    """Return all .json files in the examples directory."""
    if not EXAMPLES_DIR.exists():
        pytest.fail(f"examples directory not found: {EXAMPLES_DIR}")
    files = sorted(EXAMPLES_DIR.glob("*.json"))
    if not files:
        pytest.fail(f"no .json files found in {EXAMPLES_DIR}")
    return files


@pytest.mark.parametrize("path", example_files(), ids=lambda p: p.name)
def test_example_file_validates(path: Path) -> None:
    """Each example file must parse and validate without errors."""
    data = json.loads(path.read_text())
    event = validate(data)

    assert event.specversion == SPEC_VERSION, f"{path.name}: unexpected specversion"
    assert event.id, f"{path.name}: id is empty"
    assert event.vendor_id, f"{path.name}: vendor_id is empty"
    assert event.category, f"{path.name}: category is empty"
    assert event.severity, f"{path.name}: severity is empty"
    assert event.title, f"{path.name}: title is empty"
    assert event.summary, f"{path.name}: summary is empty"
    assert event.published_at, f"{path.name}: published_at is empty"
    assert event.source_type, f"{path.name}: source_type is empty"


def test_all_required_examples_present() -> None:
    """Verify that the canonical set of example files exists."""
    required = [
        "security-cve.json",
        "api-breaking.json",
        "api-deprecation.json",
        "tos-update.json",
        "data-handling.json",
        "pricing.json",
        "cosmetic.json",
    ]
    for name in required:
        path = EXAMPLES_DIR / name
        assert path.exists(), f"required example missing: {name}"


def test_minimal_valid_event() -> None:
    """An event with only required fields must be accepted."""
    event = validate({
        "specversion": "1.0",
        "id": "cs_minimal001",
        "vendor_id": "acme",
        "category": "informational",
        "severity": "informational",
        "title": "Documentation typo fix",
        "summary": "Corrected a typo. No behavior change.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
    })

    assert event.id == "cs_minimal001"
    assert event.vendor_id == "acme"
    assert event.category == Category.INFORMATIONAL
    assert event.severity == Severity.INFORMATIONAL
    assert event.source_type == SourceType.CRAWLED
    assert event.extensions == {}


def test_extension_fields_collected() -> None:
    """Extension fields must be collected into event.extensions."""
    event = validate({
        "specversion": "1.0",
        "id": "cs_ext001",
        "vendor_id": "twilio",
        "category": "data_handling",
        "severity": "medium",
        "title": "DPA updated: new subprocessor",
        "summary": "A new subprocessor was added to the DPA.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
        "ext:compliance.gdpr_article": "28",
        "ext:compliance.requires_dpa_review": True,
        "ext:internal.ticket_id": "ENG-4521",
    })

    assert len(event.extensions) == 3
    assert event.extensions["ext:compliance.gdpr_article"] == "28"
    assert event.extensions["ext:compliance.requires_dpa_review"] is True
    assert event.extensions["ext:internal.ticket_id"] == "ENG-4521"


def test_unknown_non_extension_fields_rejected() -> None:
    """Unknown non-ext fields must be rejected. Extension fields must use the ext: prefix."""
    with pytest.raises(ValidationError) as exc_info:
        validate({
            "specversion": "1.0",
            "id": "cs_unknown001",
            "vendor_id": "acme",
            "category": "informational",
            "severity": "informational",
            "title": "Test",
            "summary": "Test summary.",
            "published_at": "2026-04-10T14:00:00Z",
            "source_type": "crawled",
            "future_field_added_in_v11": "some value",
        })
    assert "future_field_added_in_v11" in str(exc_info.value)


def test_invalid_specversion_rejected() -> None:
    """Events with specversion != '1.0' must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        validate({
            "specversion": "2.0",
            "id": "cs_bad001",
            "vendor_id": "acme",
            "category": "informational",
            "severity": "informational",
            "title": "Test",
            "summary": "Test summary.",
            "published_at": "2026-04-10T14:00:00Z",
            "source_type": "crawled",
        })
    errors = exc_info.value.errors()
    assert any("specversion" in str(e) or "1.0" in str(e) for e in errors)


def test_invalid_category_rejected() -> None:
    """Unknown category values must be rejected."""
    with pytest.raises(ValidationError):
        validate({
            "specversion": "1.0",
            "id": "cs_bad002",
            "vendor_id": "acme",
            "category": "unknown_category",
            "severity": "informational",
            "title": "Test",
            "summary": "Test summary.",
            "published_at": "2026-04-10T14:00:00Z",
            "source_type": "crawled",
        })


def test_invalid_severity_rejected() -> None:
    """Unknown severity values must be rejected."""
    with pytest.raises(ValidationError):
        validate({
            "specversion": "1.0",
            "id": "cs_bad003",
            "vendor_id": "acme",
            "category": "informational",
            "severity": "extreme",
            "title": "Test",
            "summary": "Test summary.",
            "published_at": "2026-04-10T14:00:00Z",
            "source_type": "crawled",
        })


def test_invalid_cve_id_rejected() -> None:
    """Malformed CVE IDs must be rejected."""
    with pytest.raises(ValidationError):
        validate({
            "specversion": "1.0",
            "id": "cs_bad004",
            "vendor_id": "npm:lodash",
            "category": "security",
            "severity": "critical",
            "title": "Security issue",
            "summary": "A security issue.",
            "published_at": "2026-04-10T14:00:00Z",
            "source_type": "crawled",
            "cve_id": "not-a-cve-id",
        })


def test_title_with_newline_rejected() -> None:
    """Titles containing newlines must be rejected."""
    with pytest.raises(ValidationError):
        validate({
            "specversion": "1.0",
            "id": "cs_bad005",
            "vendor_id": "acme",
            "category": "informational",
            "severity": "informational",
            "title": "Line one\nLine two",
            "summary": "Test summary.",
            "published_at": "2026-04-10T14:00:00Z",
            "source_type": "crawled",
        })


def test_json_string_input_accepted() -> None:
    """validate() must accept a JSON string as input."""
    raw_json = json.dumps({
        "specversion": "1.0",
        "id": "cs_json001",
        "vendor_id": "acme",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test summary.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
    })
    event = validate(raw_json)
    assert event.id == "cs_json001"


def test_json_bytes_input_accepted() -> None:
    """validate() must accept JSON bytes as input."""
    raw_bytes = json.dumps({
        "specversion": "1.0",
        "id": "cs_bytes001",
        "vendor_id": "acme",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test summary.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
    }).encode()
    event = validate(raw_bytes)
    assert event.id == "cs_bytes001"


def test_security_event_fields() -> None:
    """Security events with CVE fields must parse correctly."""
    event = validate({
        "specversion": "1.0",
        "id": "cs_sec001",
        "vendor_id": "npm:express",
        "category": "security",
        "severity": "critical",
        "title": "CVE-2025-29999: path traversal",
        "summary": "A path traversal vulnerability.",
        "published_at": "2026-04-10T09:00:00Z",
        "source_type": "crawled",
        "cve_id": "CVE-2025-29999",
        "cvss_score": 9.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "fixed_in_version": "4.21.3",
        "confidence_score": 0.97,
    })

    assert event.cve_id == "CVE-2025-29999"
    assert event.cvss_score == pytest.approx(9.1)
    assert event.fixed_in_version == "4.21.3"
    assert event.confidence_score == pytest.approx(0.97)


def test_confidence_score_bounds() -> None:
    """confidence_score must be in [0.0, 1.0]."""
    base = {
        "specversion": "1.0",
        "id": "cs_conf001",
        "vendor_id": "acme",
        "category": "informational",
        "severity": "informational",
        "title": "Test",
        "summary": "Test summary.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "crawled",
    }

    # 0.0 is valid
    event = validate({**base, "confidence_score": 0.0})
    assert event.confidence_score == pytest.approx(0.0)

    # 1.0 is valid
    event = validate({**base, "confidence_score": 1.0})
    assert event.confidence_score == pytest.approx(1.0)

    # > 1.0 is invalid
    with pytest.raises(ValidationError):
        validate({**base, "confidence_score": 1.1})

    # < 0.0 is invalid
    with pytest.raises(ValidationError):
        validate({**base, "confidence_score": -0.1})
