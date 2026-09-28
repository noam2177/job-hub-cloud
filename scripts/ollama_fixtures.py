"""Dev tool: cheap steps on local Ollama via the Hub's sanctioned wrapper (zone checks + $0 spend row).

Usage (from this repo): python scripts/ollama_fixtures.py ads|families
Requires HUB_ROOT (default: ../../principal-architect-hub). Synthetic data only.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HUB = Path(os.environ.get("HUB_ROOT", REPO.parents[1] / "principal-architect-hub"))
sys.path.insert(0, str(HUB))

from hub.local_infer import local_chat  # noqa: E402

FAMILIES = ["data_analyst", "bi_analyst", "data_scientist", "ml_engineer", "data_engineer", "software_engineer", "research", "other"]
TITLES = [
    "Junior Data Analyst", "אנליסט/ית נתונים", "BI Developer", "Power BI Analyst", "Data Scientist - NLP",
    "Machine Learning Engineer", "MLOps Engineer", "Data Engineer (Spark, Airflow)", "Backend Developer Python",
    "Full Stack Developer", "Research Assistant - Computational Linguistics", "חוקר/ת אלגוריתמים", "Product Analyst",
    "מהנדס/ת נתונים", "LLM Engineer", "Customer Success Manager",
]

ADS_PROMPT = (
    "Create 6 SYNTHETIC Israeli job ads for testing. Use fake companies and the contact name ישראל ישראלי only. "
    "Mix: 4 in Hebrew, 2 in English. Return JSON {\"ads\":[{\"ad_id\":\"syn-01\",\"text\":\"full ad text 40-80 words\","
    "\"title\":\"...\",\"company\":\"...\",\"requirements\":[\"...\"],\"location\":\"...\",\"contact\":\"jobs@example.com\","
    "\"language\":\"he|en\"}]}. Contact must be an @example.com e-mail. The text must contain every field value verbatim."
)


def _json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.S)
    return json.loads(match.group(0)) if match else {}


def ads() -> int:
    out = local_chat(ADS_PROMPT, model="qwen2.5:7b", max_tokens=2600, timeout=300)
    if not out.get("ok"):
        print(json.dumps({"ok": False, "error": out.get("error")}))
        return 1
    data = _json(out["content"])
    rows = [a for a in data.get("ads", []) if isinstance(a, dict) and a.get("text") and a.get("title")]
    target = REPO / "tests" / "fixtures" / "ads_synthetic.json"
    target.write_text(json.dumps({"generator": out.get("model"), "ads": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "model": out.get("model"), "ads": len(rows), "path": str(target.relative_to(REPO))}))
    return 0


def families() -> int:
    prompt = (
        f"Classify each job title into exactly one family from {FAMILIES}. "
        f"Titles: {json.dumps(TITLES, ensure_ascii=False)}. Return JSON {{\"map\":{{\"<title>\":\"<family>\"}}}}."
    )
    out = local_chat(prompt, model="qwen2.5:7b", max_tokens=900, timeout=180)
    if not out.get("ok"):
        print(json.dumps({"ok": False, "error": out.get("error")}))
        return 1
    mapping = {k: v for k, v in (_json(out["content"]).get("map") or {}).items() if v in FAMILIES}
    target = REPO / "tests" / "fixtures" / "title_family_ollama.json"
    target.write_text(json.dumps({"generator": out.get("model"), "map": mapping}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "model": out.get("model"), "classified": len(mapping), "of": len(TITLES)}))
    return 0


if __name__ == "__main__":
    raise SystemExit({"ads": ads, "families": families}[sys.argv[1]]())
