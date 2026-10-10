#!/usr/bin/env bash
# Cloud Run Job for incremental BQ sync (~$0 if run on schedule within free tier; image storage minimal).
set -euo pipefail
DRY_RUN="${DRY_RUN:-1}"
PROJECT="${PROJECT:-noam-job-hub-123}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-jobhub-bq-sync}"
IMAGE="gcr.io/${PROJECT}/${SERVICE_NAME}:latest"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run() {
  echo "+ $*"
  if [[ "${DRY_RUN}" == "0" ]]; then
    "$@"
  fi
}

run gcloud builds submit "${ROOT}" --config "${ROOT}/cloud/bq_sync/cloudbuild.yaml"
run gcloud run jobs deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --service-account "sa-bq-exporter@${PROJECT}.iam.gserviceaccount.com" \
  --set-env-vars "GCP_PROJECT_ID=${PROJECT},JOBHUB_LEDGER_GCS_URI=gs://${PROJECT}-ledger-backup/ledger/jobs.json,JOBHUB_RUN_MODE=job" \
  --max-retries 1 \
  --task-timeout 10m \
  --memory 512Mi

echo "DRY_RUN=${DRY_RUN} (set DRY_RUN=0 and approve billing before deploy)"
