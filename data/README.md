# data/ — local only

Everything in this folder except this README and `*_template.csv` is gitignored.

## P5-01 labeling (Noam, ~40 min for 20 ads)

1. Put 20 **public** job-ad images in `data/ads/` (screenshots from LinkedIn/Facebook groups/job boards). Mix: at least 12 Hebrew, some English, some mixed.
2. Copy `ads_gt_template.csv` to `ads_gt.csv`, delete the two example rows, add one row per image.
3. Label exactly what is **visible in the image**:
   - `title`, `company`, `location`: as written (spelling differences, punctuation and ך/כ final letters are normalized by the scorer).
   - `requirements`: the listed requirements, separated by `|`. Scored by token F1 ≥ 0.6, so order and small wording differences do not matter.
   - `contact`: the e-mail / phone / URL exactly as it appears; empty if none. Do not add a contact that is not in the image.
   - Leave a field empty when the ad does not state it (the model is expected to return null).
4. Start with 2–3 ads to check Hebrew quality before labeling all 20:

```powershell
.\.venv\Scripts\python.exe scripts\p5_eval.py --gt data\ads_gt.csv --images data\ads --paths direct_local,ocr_llm_local
```

GCP paths run only with `$env:JOBHUB_ALLOW_GCP_EVAL="1"` after P5-03 (processor created) and cost approval.
