"""Cloud Run entry: incremental ledger snapshot → BigQuery (append only).

Expects ledger JSON at JOBHUB_LEDGER_GCS_URI (gs://bucket/path/jobs.json) downloaded to /tmp/jobs.json
before handler runs, or mounted via gcsfuse in the VM pattern. No WRITE_TRUNCATE.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from google.cloud import storage

from jobs_pipeline.backfill import _load_state, _save_state
from jobs_pipeline.incremental_sync import DEFAULT_PROJECT_ID, run_incremental_sync


def _download_gcs(uri: str, dest: Path) -> None:
    if not uri.startswith("gs://"):
        raise ValueError("JOBHUB_LEDGER_GCS_URI must be gs://...")
    parts = uri[5:].split("/", 1)
    bucket_name, blob_name = parts[0], parts[1]
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    bucket.blob(blob_name).download_to_filename(str(dest))


def handle(request=None) -> tuple[str, int]:
    project = os.environ.get("GCP_PROJECT_ID", DEFAULT_PROJECT_ID)
    ledger_uri = os.environ.get("JOBHUB_LEDGER_GCS_URI", "")
    state_path = Path(os.environ.get("JOBHUB_STATE_PATH", "/tmp/export_state.json"))

    with tempfile.TemporaryDirectory() as tmp:
        jobs_path = Path(tmp) / "jobs.json"
        if ledger_uri:
            _download_gcs(ledger_uri, jobs_path)
        else:
            local = os.environ.get("JOBHUB_LEDGER_PATH", "/ledger/jobs.json")
            jobs_path = Path(local)
        if not jobs_path.is_file():
            return json.dumps({"ok": False, "error": "ledger missing"}), 500

        from google.cloud import bigquery

        client = bigquery.Client(project=project)
        state = _load_state(state_path)
        report = run_incremental_sync(
            jobs_path,
            state,
            outcomes_path=None,
            project_id=project,
            client=client,
            apply=True,
            preview_bq=False,
        )
        new_state = report.pop("_state", None)
        if new_state is not None:
            _save_state(state_path, new_state)
        report["ok"] = True
        return json.dumps(report, ensure_ascii=False), 200


def main() -> None:
    body, code = handle()
    print(body)
    raise SystemExit(0 if code == 200 else 1)


if __name__ == "__main__":
    main()
