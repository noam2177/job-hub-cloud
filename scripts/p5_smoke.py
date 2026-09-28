"""P5 local smoke: render a synthetic English ad, run LocalVlmDirect, print fields + latency. No cloud.

Usage: python scripts/p5_smoke.py render OUT.png   (needs Pillow)
       python scripts/p5_smoke.py run OUT.png
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

AD_LINES = [
    "WE ARE HIRING",
    "Junior Data Analyst",
    "Example Analytics Ltd",
    "Location: Haifa",
    "Requirements:",
    "- SQL",
    "- Python",
    "- Power BI",
    "Send CV: jobs@example.com",
]


def render(out: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (640, 520), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    for i, line in enumerate(AD_LINES):
        draw.text((40, 30 + i * 52), line, fill="black", font=font)
    img.save(out)


def run(image: Path) -> int:
    from jobs_pipeline.ad_direct import LocalVlmDirect

    t0 = time.perf_counter()
    result = LocalVlmDirect().extract(image.read_bytes(), "image/png")
    seconds = time.perf_counter() - t0
    ad = result.job_ad.model_dump() if result.job_ad else None
    print(json.dumps({"seconds": round(seconds, 1), "error": result.error, "job_ad": ad}, ensure_ascii=False, indent=2))
    return 0 if ad else 1


if __name__ == "__main__":
    mode, path = sys.argv[1], Path(sys.argv[2])
    raise SystemExit(render(path) if mode == "render" else run(path))
