from __future__ import annotations

import re
from collections.abc import Callable
from typing import Final

TITLE_FAMILIES: Final[tuple[str, ...]] = (
    "data_analyst",
    "bi_analyst",
    "data_scientist",
    "ml_engineer",
    "data_engineer",
    "software_engineer",
    "research",
    "other",
)

_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ml_engineer", re.compile(r"\b(ml|mlops|llm|ai|machine learning)\b.{0,10}\bengineer\b|\bmlops\b|\bmle\b|מהנדס/?ת? (למידת מכונה|ml)")),
    ("data_engineer", re.compile(r"\bdata engineer\b|\betl\b|\bdata pipeline|מהנדס/?ת? (ה)?נתונים")),
    ("data_scientist", re.compile(r"\bdata scien(tist|ce)\b|מדע(ן|נית) נתונים")),
    ("bi_analyst", re.compile(r"\bbi\b|\bbusiness intelligence\b|\blooker\b|\btableau\b|\bpower bi\b")),
    ("data_analyst", re.compile(r"\banalyst\b|\banalytics\b|אנליסט")),
    ("research", re.compile(r"\bresearch(er)?\b|חוקר|מחקר")),
    ("software_engineer", re.compile(r"\bsoftware engineer\b|\bdeveloper\b|\bbackend\b|\bfrontend\b|\bfull ?stack\b|מפתח|מתכנת")),
)


def classify_title(title: str | None, fallback: Callable[[str], str] | None = None) -> str:
    raw = (title or "").strip().lower()
    if not raw:
        return "other"
    for family, pattern in _RULES:
        if pattern.search(raw):
            return family
    if fallback is not None:
        guess = (fallback(title) or "").strip().lower()
        if guess in TITLE_FAMILIES:
            return guess
    return "other"
