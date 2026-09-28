"""P5-06: compare ad-extraction paths on labeled ads; writes docs/gcp/P5_EVAL.md.

Usage:
  python scripts/p5_eval.py --self-test
  python scripts/p5_eval.py --gt data/ads_gt.csv --images data/ads [--paths ocr_llm_local,direct_local]
GCP paths (ocr_llm_gcp, direct_gcp) run only with JOBHUB_ALLOW_GCP_EVAL=1 (they cost money; see COST_LEDGER.md).
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import re
import statistics
import sys
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from jobs_pipeline.ad_schema import JobAd  # noqa: E402

SCALAR_FIELDS = ("title", "company", "location", "contact")
FIELDS = (*SCALAR_FIELDS, "requirements")
GCP_PATHS = frozenset({"ocr_llm_gcp", "direct_gcp"})
_FINALS = str.maketrans({"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"})
_PUNCT = re.compile(r"[^\w\s@.+]|_", re.UNICODE)

Extractor = Callable[[bytes, str], tuple[JobAd | None, float]]


def normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold().translate(_FINALS)
    text = _PUNCT.sub(" ", text)
    return " ".join(text.split()).strip(" .")


def token_f1(pred: list[str], gold: list[str]) -> float:
    p = set(normalize(" ".join(pred)).split())
    g = set(normalize(" ".join(gold)).split())
    if not p and not g:
        return 1.0
    if not p or not g:
        return 0.0
    tp = len(p & g)
    if tp == 0:
        return 0.0
    precision, recall = tp / len(p), tp / len(g)
    return 2 * precision * recall / (precision + recall)


def field_correct(field: str, pred: JobAd | None, gold: dict[str, str]) -> bool:
    if field == "requirements":
        gold_reqs = [r for r in (gold.get("requirements") or "").split("|") if r.strip()]
        return token_f1(pred.requirements if pred else [], gold_reqs) >= 0.6
    return normalize(getattr(pred, field, None) if pred else None) == normalize(gold.get(field))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    z2 = z * z
    center = (k + z2 / 2) / (n + z2)
    margin = z / (n + z2) * math.sqrt(k * (n - k) / n + z2 / 4)
    return (max(0.0, center - margin), min(1.0, center + margin))


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))]


@dataclass
class PathScore:
    name: str
    n: int
    correct: dict[str, int]
    costs: list[float]
    latencies_ms: list[float]
    failures: int

    @property
    def overall(self) -> tuple[int, int]:
        return sum(self.correct.values()), self.n * len(FIELDS)


def evaluate(name: str, extractor: Extractor, rows: list[dict[str, str]], images: Path) -> PathScore:
    correct = {f: 0 for f in FIELDS}
    costs: list[float] = []
    latencies: list[float] = []
    failures = 0
    for row in rows:
        data = (images / row["image_file"]).read_bytes()
        mime = "image/png" if row["image_file"].lower().endswith(".png") else "image/jpeg"
        t0 = time.perf_counter()
        try:
            ad, cost = extractor(data, mime)
        except Exception:  # noqa: BLE001 - a failed ad scores zero, the run continues
            ad, cost = None, 0.0
            failures += 1
        latencies.append((time.perf_counter() - t0) * 1000)
        costs.append(cost)
        for f in FIELDS:
            correct[f] += int(field_correct(f, ad, row))
    return PathScore(name, len(rows), correct, costs, latencies, failures)


def render(scores: list[PathScore], note: str) -> str:
    head = "| path | n | overall acc | Wilson 95% | " + " | ".join(FIELDS) + " | mean $/ad | p50 ms | p95 ms | failures |"
    lines = ["# P5_EVAL — ad extraction comparison", "", note, "", head, "|" + "---|" * (9 + len(FIELDS) - 1)]
    for s in scores:
        k, n = s.overall
        low, high = wilson(k, n)
        per_field = " | ".join(f"{s.correct[f] / s.n:.0%}" if s.n else "-" for f in FIELDS)
        lines.append(
            f"| {s.name} | {s.n} | {k / n:.1%} | {low:.1%}–{high:.1%} | {per_field} | "
            f"{statistics.fmean(s.costs) if s.costs else 0:.4f} | {percentile(s.latencies_ms, 0.5):.0f} | "
            f"{percentile(s.latencies_ms, 0.95):.0f} | {s.failures} |"
        )
    lines += ["", "Adopt the cheapest path with overall ≥ 90% and Wilson low ≥ 80% (P5_PLAN.md)."]
    return "\n".join(lines) + "\n"


def build_extractors(names: list[str]) -> dict[str, Extractor]:
    from jobs_pipeline.ad_direct import GeminiVision, LocalVlmDirect
    from jobs_pipeline.ad_structure import GeminiLlm, OllamaLlm, structure
    from jobs_pipeline.ocr_extract import DocumentAiOcr, LocalVlmOcr

    def ocr_then_llm(ocr, llm) -> Extractor:  # noqa: ANN001
        def run(data: bytes, mime: str) -> tuple[JobAd | None, float]:
            text = ocr.run(data, mime)
            return structure(text.text, llm).job_ad, text.cost_usd
        return run

    def direct(engine) -> Extractor:  # noqa: ANN001
        def run(data: bytes, mime: str) -> tuple[JobAd | None, float]:
            out = engine.extract(data, mime)
            return out.job_ad, out.cost_usd
        return run

    factories = {
        "ocr_llm_local": lambda: ocr_then_llm(LocalVlmOcr(), OllamaLlm()),
        "direct_local": lambda: direct(LocalVlmDirect()),
        "ocr_llm_gcp": lambda: ocr_then_llm(DocumentAiOcr(), GeminiLlm()),
        "direct_gcp": lambda: direct(GeminiVision()),
    }
    allow_gcp = os.environ.get("JOBHUB_ALLOW_GCP_EVAL") == "1"
    out: dict[str, Extractor] = {}
    for name in names:
        if name in GCP_PATHS and not allow_gcp:
            print(f"skip {name}: set JOBHUB_ALLOW_GCP_EVAL=1 to spend on GCP")
            continue
        out[name] = factories[name]()
    return out


def self_test(out_path: Path) -> list[PathScore]:
    import tempfile

    rows = [
        {"ad_id": "s1", "image_file": "s1.png", "title": "אנליסט נתונים", "company": "דוגמה בע\"מ",
         "requirements": "SQL|Python", "location": "תל אביב", "contact": "jobs@example.com"},
        {"ad_id": "s2", "image_file": "s2.png", "title": "Data Engineer", "company": "Example Ltd",
         "requirements": "Spark|Airflow", "location": "Haifa", "contact": ""},
    ]
    perfect = {
        b"s1": JobAd(title="אנליסט נתונים", company='דוגמה בע"מ', requirements=["SQL", "Python"], location="תל-אביב", contact="jobs@example.com"),
        b"s2": JobAd(title="data engineer", company="Example Ltd.", requirements=["Spark", "Airflow", "AWS"], location="Haifa"),
    }
    with tempfile.TemporaryDirectory() as tmp:
        images = Path(tmp)
        for r in rows:
            (images / r["image_file"]).write_bytes(r["ad_id"].encode())
        scores = [
            evaluate("fake_perfect", lambda d, _m: (perfect[d], 0.0), rows, images),
            evaluate("fake_empty", lambda _d, _m: (None, 0.0), rows, images),
        ]
    out_path.write_text(render(scores, "Self-test on synthetic fixtures (no model calls)."), encoding="utf-8")
    return scores


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gt", type=Path)
    parser.add_argument("--images", type=Path)
    parser.add_argument("--paths", default="ocr_llm_local,direct_local")
    parser.add_argument("--out", type=Path, default=REPO / "docs" / "gcp" / "P5_EVAL.md")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        scores = self_test(args.out)
        print({s.name: f"{s.overall[0]}/{s.overall[1]}" for s in scores})
        return 0
    if not args.gt or not args.images:
        parser.error("--gt and --images are required unless --self-test")
    with args.gt.open(encoding="utf-8-sig", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r.get("image_file")]
    extractors = build_extractors([p.strip() for p in args.paths.split(",") if p.strip()])
    scores = [evaluate(name, fn, rows, args.images) for name, fn in extractors.items()]
    args.out.write_text(render(scores, f"{len(rows)} labeled ads from `{args.gt.name}`."), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
