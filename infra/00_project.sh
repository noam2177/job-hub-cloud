#!/usr/bin/env bash
# G0-2: select project and create one service account per component. No key files.
# Usage: PROJECT=<id> DRY_RUN=1 bash infra/00_project.sh
set -euo pipefail
: "${PROJECT:?set PROJECT}"
DRY_RUN="${DRY_RUN:-1}"

run() {
  echo "+ $*"
  if [[ "$DRY_RUN" == "0" ]]; then "$@"; fi
}

run gcloud config set project "$PROJECT"

declare -A SAS=(
  [sa-telegram-listener]="Telegram intake on the bridge VM"
  [sa-local-puller]="Local PC Pub/Sub pull consumer"
  [sa-bq-exporter]="Single BigQuery writer"
)
for sa in "${!SAS[@]}"; do
  run gcloud iam service-accounts create "$sa" --display-name="${SAS[$sa]}"
done

# Resource-level grants (topic, subscription, secret) live in 30_pubsub.sh and RUNBOOK_P1.md.
# Project-level only where BigQuery requires it (job creation is a project permission).
run gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:sa-bq-exporter@${PROJECT}.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser" --condition=None

echo "Dataset-level roles/bigquery.dataEditor for sa-bq-exporter is granted in infra/10_bq.sh."
echo "Local auth: gcloud auth application-default login with impersonation, never a JSON key:"
echo "  gcloud auth application-default login --impersonate-service-account=sa-local-puller@${PROJECT}.iam.gserviceaccount.com"
