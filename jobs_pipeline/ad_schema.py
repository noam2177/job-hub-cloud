"""Structured job-ad record for image extraction (P5)."""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

FIELDS = ("title", "company", "requirements", "location", "contact")

_CONTACT_EMAIL = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$", re.I)
_CONTACT_PHONE = re.compile(
    r"^(?:\+?\d{1,3}[-\s]?)?(?:\(?\d{2,4}\)?[-\s]?)?\d{3}[-\s]?\d{4,6}$"
)
_CONTACT_URL = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.I)


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    return s if s else None


_CONTACT_SEARCH = (
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    re.compile(r"https?://\S+", re.I),
    re.compile(r"(?:\+?\d{1,3}[-\s]?)?\(?\d{2,4}\)?[-\s]?\d{3}[-\s]?\d{4,6}"),
)


def _valid_contact(value: str | None) -> str | None:
    """A bad contact must not sink the whole ad: keep the first e-mail/URL/phone found, else None."""
    s = _blank_to_none(value)
    if s is None:
        return None
    if _CONTACT_EMAIL.match(s) or _CONTACT_PHONE.match(s) or _CONTACT_URL.match(s):
        return s
    for pattern in _CONTACT_SEARCH:
        found = pattern.search(s)
        if found:
            return found.group(0).rstrip(".,;)")
    return None


class JobAd(BaseModel):
    title: str | None = None
    company: str | None = None
    requirements: list[str] = Field(default_factory=list, max_length=15)
    location: str | None = None
    contact: str | None = None
    language: Literal["he", "en", "mixed"] | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    field_confidence: dict[str, float] = Field(default_factory=dict)

    @field_validator("title", "company", "location", mode="before")
    @classmethod
    def strip_optional_str(cls, value: Any) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        return _blank_to_none(value)

    @field_validator("contact", mode="before")
    @classmethod
    def normalize_contact(cls, value: Any) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        return _valid_contact(value)

    @field_validator("requirements", mode="before")
    @classmethod
    def normalize_requirements(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("requirements must be a list")
        out: list[str] = []
        for item in value[:15]:
            if not isinstance(item, str):
                continue
            s = item.strip()
            if not s:
                continue
            out.append(s[:200])
        return out

    @model_validator(mode="after")
    def clamp_field_confidence(self) -> JobAd:
        cleaned: dict[str, float] = {}
        for key, val in self.field_confidence.items():
            if key in FIELDS or key == "language":
                cleaned[key] = max(0.0, min(1.0, float(val)))
        object.__setattr__(self, "field_confidence", cleaned)
        return self


def json_schema() -> dict[str, Any]:
    """JSON Schema for LLM schema-bound output."""
    return JobAd.model_json_schema()
