#!/usr/bin/env bash
# Cloud Scheduler → Cloud Run Job (hourly incremental sync). ~$0.10/mo per job within trial.
set -euo pipefail
DRY_RUN="${DRY_RUN:-1}"
PROJECT="${PROJECT:-noam-job-hub-123}"
REGION="${REGION:-us-central1}"
JOB_NAME="${JOB_NAME:-jobhub-bq-sync}"
SCHEDULER_NAME="${SCHEDULER_NAME:-jobhub-hourly-bq-sync}"

run() {
  echo "+ $*"
  if [[ "${DRY_RUN}" == "0" ]]; then
    "$@"
  fi
}

RUN_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB_NAME}:run"

run gcloud scheduler jobs create http "${SCHEDULER_NAME}" \
  --location "${REGION}" \
  --schedule "0 * * * *" \
  --uri "${RUN_URI}" \
  --http-method POST \
  --oauth-service-account-email "sa-bq-exporter@${PROJECT}.iam.gserviceaccount.com" \
  --description "Hourly incremental ledger → BigQuery append"

echo "DRY_RUN=${DRY_RUN} (requires Cloud Run Job from infra/40_cloud_run_sync.sh)"
