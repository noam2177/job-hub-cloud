from pathlib import Path

import pytest

from jobs_pipeline.ad_schema import JobAd
from jobs_pipeline.stats import wilson as stats_wilson
from scripts.p5_eval import field_correct, main, normalize, percentile, self_test, token_f1, wilson


def test_hebrew_final_letters_and_punctuation() -> None:
    assert normalize("תל-אביב!") == normalize("תל אביב")
    assert normalize("מנהלת שיווק ומכירות") == normalize("מנהלת שיווק ומכירות")
    assert normalize("ך ם ן ף ץ") == "כ מ נ פ צ"
    assert normalize("  Example Ltd. ") == "example ltd"


def test_requirements_f1_threshold() -> None:
    assert token_f1(["SQL", "Python"], ["SQL", "Python"]) == 1.0
    assert token_f1([], []) == 1.0
    assert token_f1(["SQL"], []) == 0.0
    assert field_correct("requirements", JobAd(requirements=["SQL", "Python", "AWS"]), {"requirements": "SQL|Python"})
    assert not field_correct("requirements", JobAd(requirements=["Excel"]), {"requirements": "SQL|Python"})


def test_missing_prediction_matches_empty_gold() -> None:
    assert field_correct("contact", JobAd(), {"contact": ""})
    assert not field_correct("contact", None, {"contact": "jobs@example.com"})


def test_local_wilson_matches_shared_stats() -> None:
    for k, n in [(10, 20), (0, 40), (35, 35), (7, 29)]:
        low, high = stats_wilson(k, n)
        assert wilson(k, n) == pytest.approx((max(0.0, low), min(1.0, high)))


def test_percentile() -> None:
    assert percentile([5, 1, 3, 2, 4], 0.5) == 3
    assert percentile([1, 2, 3, 4, 100], 0.95) == 100


def test_self_test_writes_table(tmp_path: Path) -> None:
    out = tmp_path / "P5_EVAL.md"
    scores = {s.name: s.overall for s in self_test(out)}
    assert scores["fake_perfect"] == (10, 10)
    assert scores["fake_empty"][0] < 10
    assert "| fake_perfect | 2 | 100.0% |" in out.read_text(encoding="utf-8")


def test_gcp_paths_skipped_without_flag(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.p5_eval import build_extractors

    monkeypatch.delenv("JOBHUB_ALLOW_GCP_EVAL", raising=False)
    assert build_extractors(["direct_gcp", "ocr_llm_gcp"]) == {}
    assert "skip direct_gcp" in capsys.readouterr().out


def test_cli_requires_inputs() -> None:
    with pytest.raises(SystemExit):
        main([])
