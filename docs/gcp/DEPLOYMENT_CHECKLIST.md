# רשימת פריסה (לפני חיוב מכוון)

## עלות משוערת (תוך trial ₪891)

| רכיב | סקריפט | הערה |
|------|--------|------|
| BigQuery load jobs | מקומי / Cloud Run Job | סנטים ל-GB |
| GCS ledger backup | `infra/42_gcs_ledger_backup.sh` | ~$0.02/GB |
| Cloud Run Job (sync) | `infra/40_cloud_run_sync.sh` | מינימלי אם לא always-on |
| Cloud Scheduler | `infra/41_scheduler_sync.sh` | ~$0.10/חודש |
| e2-micro VM (P1) | `infra/20_vm.sh` | ~$3.65 IPv4 — כבר בתקציב |

**אין הרצה אוטומטית:** כל `infra/*.sh` ברירת מחדל `DRY_RUN=1`.

## סכמה ב-BigQuery

אם `check-bq` מחזיר `bq_schema_note` (טעינה ישנה בלי `event_type`), הרץ `infra/10_bq.sh` עם `DRY_RUN=0` ואז backfill מחדש **רק** אחרי אישור (ייתכן מיגרציה / טבלה חדשה). עד אז incremental מדלג על 111 `found` לוגיים ומציע append רק ל־`applied`/`closed` (35 שורות במצב הנוכחי).

## סדר מומלץ

1. **אימות מקומי:** `pytest` · `scripts\incremental_sync_to_bq.py --check-bq`
2. **גיבוי ledger:** `LEDGER_PATH=... DRY_RUN=0 bash infra/42_gcs_ledger_backup.sh`
3. **Cloud Run Job:** `DRY_RUN=0 bash infra/40_cloud_run_sync.sh` (אישור מפעיל)
4. **תזמון:** `DRY_RUN=0 bash infra/41_scheduler_sync.sh`
5. **Looker:** `docs/looker/LOOKER_DATA_SOURCES.md`
6. **P1 VM + Telegram:** `RUNBOOK_P1.md`

## דרישות IAM

- `sa-bq-exporter`: `bigquery.dataEditor` על `jobs.events`, `bigquery.jobUser`
- Cloud Run Job: אותו SA + `storage.objectViewer` על bucket הגיבוי
