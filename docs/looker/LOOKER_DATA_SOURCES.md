# Looker Studio — מקורות נתונים (P2-06)

פרויקט BigQuery: **noam-job-hub-123** · dataset **jobs**.

## חיבור

1. [Looker Studio](https://lookerstudio.google.com) → **יצירה → מקור נתונים → BigQuery**.
2. בחר `noam-job-hub-123` → `jobs`.
3. הוסף ארבעה מקורות (views):

| View | שימוש בדשבורד |
|------|----------------|
| `jobs_latest` | עמוד 1 — פאנל, פילטרים, סטטוס אחרון |
| `days_to_reply` | עמוד 2 — זמן לתשובה |
| `response_rate_by_title_family` | עמוד 3 — שיעור תשובה לפי משפחת תפקיד |
| `response_rate_by_cv_version` | עמוד 3 — לפי גרסת CV |

**אימות:** אחרי טעינת 111 משרות, `SELECT COUNT(DISTINCT job_id) FROM jobs.jobs_latest` ≈ 111.

## שאילתות בדיקה (Console / bq)

```sql
SELECT COUNT(*) AS rows_raw FROM `noam-job-hub-123.jobs.events`;
SELECT COUNT(DISTINCT event_id) AS events_dedup FROM `noam-job-hub-123.jobs.events_dedup`;
SELECT COUNT(DISTINCT job_id) AS jobs FROM `noam-job-hub-123.jobs.jobs_latest`;
```

## סנכרון שוטף

אחרי שינוי ב-ledger מקומי:

```powershell
.\local\windows\run_incremental_sync.ps1 -CheckBq   # ללא עלות load
.\local\windows\run_incremental_sync.ps1 -Apply     # WRITE_APPEND בלבד
```

פרטי עיצוב העמודים: `docs/looker_steps.md`.
