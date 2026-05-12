"""
changespec - ChangeSpec 1.0 types and validator for Python.

This package provides:
  - ChangeSpecEvent: Pydantic 2.x model for a ChangeSpec 1.0 event
  - validate(): parse and validate a dict or JSON input into a ChangeSpecEvent
  - Category, Severity, SourceType, ReviewerRole: typed enums matching the spec
  - Signature: typed model for the Ed25519 signature block
  - SPEC_VERSION: the spec version this package implements ("1.0")

Specification: https://github.com/changespec/changespec/blob/main/spec/spec.md

Example usage::

    from changespec import validate

    event = validate({
        "specversion": "1.0",
        "id": "cs_01HXYZ1234ABCD",
        "vendor_id": "stripe",
        "category": "api_breaking",
        "severity": "high",
        "title": "confirm() now requires return_url",
        "summary": "The confirm() method now requires return_url.",
        "published_at": "2026-04-10T14:00:00Z",
        "source_type": "publisher_verified",
    })

    print(event.vendor_id)   # "stripe"
    print(event.category)    # Category.API_BREAKING
    print(event.severity)    # Severity.HIGH
"""

from .types import (
    SPEC_VERSION,
    Category,
    ChangeSpecEvent,
    ReviewerRole,
    Severity,
    Signature,
    SourceType,
)
from .validate import validate

__all__ = [
    "SPEC_VERSION",
    "Category",
    "ChangeSpecEvent",
    "ReviewerRole",
    "Severity",
    "Signature",
    "SourceType",
    "validate",
]

__version__ = "1.0.0"
