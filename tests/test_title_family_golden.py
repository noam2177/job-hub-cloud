import json
from pathlib import Path

from jobs_pipeline.title_family import TITLE_FAMILIES, classify_title

GOLDEN = Path(__file__).parent / "fixtures" / "title_family_ollama.json"


def test_rules_agree_with_local_llm_golden_set() -> None:
    mapping = json.loads(GOLDEN.read_text(encoding="utf-8"))["map"]
    misses = {title: (want, classify_title(title)) for title, want in mapping.items() if classify_title(title) != want}
    assert not misses, misses


def test_short_tokens_do_not_match_inside_words() -> None:
    assert classify_title("Simple Office Manager") == "other"
    assert classify_title("Ambient Designer") == "other"


def test_always_closed_list() -> None:
    assert classify_title("Chef", fallback=lambda _t: "astronaut") in TITLE_FAMILIES
