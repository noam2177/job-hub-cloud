import pytest
from pydantic import ValidationError

from jobs_pipeline.ad_schema import JobAd, json_schema


def test_blank_strings_become_none() -> None:
    ad = JobAd.model_validate({"title": "  ", "company": "", "requirements": [" SQL ", "", 3]})
    assert ad.title is None and ad.company is None
    assert ad.requirements == ["SQL"]


def test_requirements_capped() -> None:
    ad = JobAd.model_validate({"requirements": [f"r{i}" for i in range(30)]})
    assert len(ad.requirements) == 15


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("jobs@example.com", "jobs@example.com"),
        ("050-1234567", "050-1234567"),
        ("https://jobs.example.com/apply", "https://jobs.example.com/apply"),
        ("ישראל ישראלי jobs@example.com", "jobs@example.com"),
        ("לפרטים: 050-1234567.", "050-1234567"),
        ("שלחו קורות חיים", None),
    ],
)
def test_contact_is_salvaged_not_fatal(raw: str, want: str | None) -> None:
    assert JobAd.model_validate({"contact": raw}).contact == want


def test_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        JobAd.model_validate({"confidence": 1.5})
    ad = JobAd.model_validate({"field_confidence": {"title": 3, "bogus": 0.5}})
    assert ad.field_confidence == {"title": 1.0}


def test_schema_exports_fields() -> None:
    props = json_schema()["properties"]
    assert {"title", "company", "requirements", "location", "contact"} <= set(props)
