"""
ChangeSpec 1.0 type definitions using Pydantic 2.x.

All types mirror the ChangeSpec JSON Schema exactly. Optional fields use
Python's Optional type and default to None when absent.

Extension fields (ext:*) are captured in the `extensions` dict on ChangeSpecEvent.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

SPEC_VERSION = "1.0"

# Regex patterns matching the canonical schema.json constraints.
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HTTPS_PATTERN = re.compile(r"^https://")


class Category(str, Enum):
    """Classifies the type of change in an event."""

    API_BREAKING = "api_breaking"
    API_DEPRECATION = "api_deprecation"
    SECURITY = "security"
    DATA_HANDLING = "data_handling"
    LIABILITY = "liability"
    PRICING = "pricing"
    TOS = "tos"
    COSMETIC = "cosmetic"
    INFORMATIONAL = "informational"


class Severity(str, Enum):
    """Communicates urgency and potential impact."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class SourceType(str, Enum):
    """Indicates how the event was produced."""

    PUBLISHER_VERIFIED = "publisher_verified"
    CRAWLED = "crawled"
    COMMUNITY = "community"


class ReviewerRole(str, Enum):
    """Advisory routing hint for which team should review an event."""

    ENGINEERING = "engineering"
    SECURITY = "security"
    LEGAL = "legal"
    COMPLIANCE = "compliance"
    PROCUREMENT = "procurement"
    MANAGEMENT = "management"


class Signature(BaseModel):
    """Ed25519 signature block for publisher_verified events."""

    model_config = ConfigDict(frozen=True)

    alg: str = Field(pattern=r"^ed25519$", description="Signature algorithm. Must be 'ed25519'.")
    key_id: str = Field(
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$",
        description="Signing key identifier. Scoped by vendor_id at resolution time.",
    )
    value: str = Field(
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Base64url-encoded Ed25519 signature (no padding).",
    )
    signed_fields: Annotated[list[str], Field(min_length=9)] = Field(
        description="Ordered field names in signature input. Must include all required event fields plus signature metadata."
    )
    key_fingerprint: str | None = Field(
        None,
        pattern=r"^[A-Za-z0-9_-]{43}$",
        description="Optional SHA-256 fingerprint of the public key, base64url-encoded (43 chars).",
    )


class ChangeSpecEvent(BaseModel):
    """
    A ChangeSpec 1.0 event.

    Required fields are defined without defaults. Optional fields default to None.
    Extension fields (keys starting with 'ext:') are collected into `extensions`.
    Unknown non-extension fields are silently ignored.
    """

    model_config = ConfigDict(
        # Allow population by field name.
        populate_by_name=True,
        # extra="forbid" rejects unknown non-extension fields at the model level.
        # Extension fields (ext:*) are extracted before Pydantic sees them via
        # the model_validator below, so they do not trigger this restriction.
        # This matches the schema's additionalProperties: false enforcement.
        extra="forbid",
        frozen=False,
    )

    # --- Required fields ---

    specversion: str = Field(description="Must be '1.0'.")
    id: Annotated[str, Field(min_length=1, max_length=128)] = Field(
        description="Globally unique event identifier."
    )
    vendor_id: Annotated[str, Field(min_length=1, max_length=256)] = Field(
        description="Vendor or package identifier."
    )
    category: Category = Field(description="Change category.")
    severity: Severity = Field(description="Change severity.")
    title: Annotated[str, Field(min_length=1, max_length=200)] = Field(
        description="Short change title. No newlines."
    )
    summary: Annotated[str, Field(min_length=1, max_length=2000)] = Field(
        description="1-5 sentence plain-text description."
    )
    published_at: datetime = Field(description="RFC 3339 datetime when published.")
    source_type: SourceType = Field(description="How this event was produced.")

    # --- Optional fields ---

    effective_date: (
        Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] | None
    ) = Field(None, description="YYYY-MM-DD when the change takes effect.")
    source_url: str | None = Field(
        None, max_length=2048, description="URL of the primary source document. Must be https://."
    )
    affected_versions: (
        Annotated[str, Field(max_length=256)] | None
    ) = Field(None, description="Semver range of affected versions.")
    fixed_in_version: (
        Annotated[str, Field(max_length=64)] | None
    ) = Field(None, description="Semver version where issue is resolved.")
    migration_hint: (
        Annotated[str, Field(max_length=500)] | None
    ) = Field(None, description="Short plain-text action for consumers.")
    migration_url: str | None = Field(
        None, max_length=2048, description="URL of migration guide. Must be https://."
    )
    confidence_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Classification confidence [0.0, 1.0]."
    )
    sunset_date: (
        Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] | None
    ) = Field(None, description="YYYY-MM-DD when deprecated feature is removed.")
    cve_id: (
        Annotated[str, Field(pattern=r"^CVE-[0-9]{4}-[0-9]{4,}$")] | None
    ) = Field(None, description="CVE identifier.")
    cvss_score: float | None = Field(
        None, ge=0.0, le=10.0, description="CVSS base score."
    )
    cvss_vector: (
        Annotated[str, Field(pattern=r"^CVSS:[0-9]\.[0-9]/", max_length=128)] | None
    ) = Field(None, description="CVSS vector string.")
    affected_systems: (
        Annotated[list[Annotated[str, Field(min_length=1, max_length=200)]], Field(max_length=50)] | None
    ) = Field(None, description="Named affected systems.")
    affected_sections: (
        Annotated[list[Annotated[str, Field(min_length=1, max_length=200)]], Field(max_length=50)] | None
    ) = Field(None, description="Affected document sections.")
    action_required: bool | None = Field(
        None, description="Whether consumers must take action."
    )
    recommended_reviewers: (
        Annotated[list[ReviewerRole], Field(max_length=6)] | None
    ) = Field(None, description="Routing hints.")
    tags: (
        Annotated[
            list[Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=50)]],
            Field(max_length=20),
        ] | None
    ) = Field(None, description="Freeform lowercase tags.")
    signature: Signature | None = Field(None, description="Ed25519 signature block.")

    # Extension fields collected by the model_validator below.
    extensions: dict[str, Any] = Field(default_factory=dict, exclude=True)

    @field_validator("published_at", mode="before")
    @classmethod
    def published_at_must_be_datetime(cls, v: Any) -> Any:
        """Reject date-only strings and free-form text. Must be RFC 3339 datetime."""
        if not isinstance(v, str):
            return v
        # Reject date-only strings (YYYY-MM-DD without a time component).
        # A valid RFC 3339 datetime always contains a 'T' separator.
        if "T" not in v and "t" not in v:
            raise ValueError(
                f"published_at must be a RFC 3339 datetime (e.g. 2026-04-10T14:00:00Z), "
                f"date-only strings like {v!r} are not valid"
            )
        return v

    @field_validator("specversion")
    @classmethod
    def specversion_must_be_10(cls, v: str) -> str:
        if v != "1.0":
            raise ValueError(f"specversion must be '1.0', got '{v}'")
        return v

    @field_validator("title")
    @classmethod
    def title_no_newlines(cls, v: str) -> str:
        if "\n" in v or "\r" in v:
            raise ValueError("title must not contain newlines")
        return v

    @field_validator("source_url", "migration_url", mode="before")
    @classmethod
    def url_must_be_https(cls, v: Any) -> Any:
        if v is None:
            return v
        if not isinstance(v, str):
            return v
        if not v.startswith("https://"):
            raise ValueError(
                f"URL must use the https:// scheme, got: {v!r}"
            )
        return v

    @model_validator(mode="before")
    @classmethod
    def extract_extensions(cls, data: Any) -> Any:
        """
        Extract ext:* fields from the raw input dict before Pydantic processes
        the remaining fields. Extension fields are stored under the 'extensions'
        key and will not cause 'extra fields not permitted' errors.
        """
        if not isinstance(data, dict):
            return data

        extensions: dict[str, Any] = {}
        clean: dict[str, Any] = {}

        for key, value in data.items():
            if key.startswith("ext:"):
                extensions[key] = value
            else:
                clean[key] = value

        clean["extensions"] = extensions
        return clean

    def model_post_init(self, __context: Any) -> None:
        """Ensure extensions is always a dict even if not provided."""
        if self.extensions is None:
            object.__setattr__(self, "extensions", {})
