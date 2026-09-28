# P2-06 — Looker Studio dashboard (Noam, ~20 min)

Prerequisite: `infra/10_bq.sh` applied and a backfill loaded (`RUNBOOK_P2.md`).

1. Open https://lookerstudio.google.com → **Create → Data source → BigQuery**. Pick project → dataset `jobs`.
   Add four data sources: `jobs_latest`, `days_to_reply`, `response_rate_by_title_family`, `response_rate_by_cv_version`.
   Credentials: **Owner's credentials** (your user). Do not share the dashboard publicly.
2. **Create → Report**, add `jobs_latest` first.

## Page 1 — Funnel
- Scorecards: `COUNT_DISTINCT(job_id)` (found), `COUNT(applied_ts)`, `COUNT(reply_ts)`.
- Bar chart: dimension `last_event`, metric record count.
- Time series: dimension `DATE(found_ts)` (week granularity), metric record count.
- Filter control: `title_family`.

## Page 2 — Time to reply (`days_to_reply`)
- Histogram-style bar chart: dimension `days_to_reply` (bucketed: use a calculated field
  `CASE WHEN days_to_reply<=3 THEN '0-3' WHEN days_to_reply<=7 THEN '4-7' WHEN days_to_reply<=14 THEN '8-14' ELSE '15+' END`).
- Scorecard: median `days_to_reply` (aggregation **Median**).

## Page 3 — Breakdowns
- Table from `response_rate_by_title_family`: `title_family, n_applied, n_replied, rate, wilson_low, wilson_high, flag`.
- Same table from `response_rate_by_cv_version`.
- Conditional formatting: grey out rows where `flag = insufficient_n`. Add a text box:
  «אין מסקנות כש-n קטן מ-30».

3. Share → **Restrict to you**. Send back: the report URL (it stays private) and a screenshot of page 1.
