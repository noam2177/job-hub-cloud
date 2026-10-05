#!/usr/bin/env bash
# Deploy BQ sync as Cloud Run Service (free-tier friendly: scale to zero, low caps).
# Build context: repo root. Requires: gcloud auth, Cloud Build API, Run API.
#
#   export PROJECT=noam-job-hub-123 REGION=us-central1
#   DRY_RUN=1 bash scripts/deploy_cloud_run.sh
#   DRY_RUN=0 bash scripts/deploy_cloud_run.sh
set -euo pipefail

DRY_RUN="${DRY_RUN:-1}"
PROJECT="${PROJECT:-noam-job-hub-123}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-jobhub-bq-sync}"
IMAGE="${IMAGE:-gcr.io/${PROJECT}/${SERVICE_NAME}:latest}"
SA_EMAIL="${SA_EMAIL:-sa-bq-exporter@${PROJECT}.iam.gserviceaccount.com}"
LEDGER_URI="${JOBHUB_LEDGER_GCS_URI:-gs://${PROJECT}-ledger-backup/ledger/jobs.json}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run() {
  echo "+ $*"
  if [[ "${DRY_RUN}" == "0" ]]; then
    "$@"
  fi
}

echo "=== Enable APIs (g0 + cloud run) ==="
run gcloud services enable \
  iam.googleapis.com bigquery.googleapis.com \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  storage.googleapis.com \
  --project="${PROJECT}"

echo "=== Build image ==="
run gcloud builds submit "${ROOT}" \
  --project="${PROJECT}" \
  --tag "${IMAGE}" \
  --file "${ROOT}/cloud/bq_sync/Dockerfile"

echo "=== Deploy Cloud Run Service (free-tier caps) ==="
run gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT}" \
  --region="${REGION}" \
  --image="${IMAGE}" \
  --service-account="${SA_EMAIL}" \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=2 \
  --concurrency=1 \
  --timeout=600 \
  --no-allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT},JOBHUB_LEDGER_GCS_URI=${LEDGER_URI},JOBHUB_RUN_MODE=http"

echo ""
echo "DRY_RUN=${DRY_RUN}"
echo "Invoke sync (authenticated):"
echo "  gcloud run services proxy ${SERVICE_NAME} --region=${REGION} --project=${PROJECT}"
echo "  curl -X POST http://127.0.0.1:8080/sync"
echo "Or Scheduler OIDC → POST /sync on the service URL."
