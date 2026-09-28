#!/usr/bin/env bash
set -euo pipefail
DRY_RUN=${DRY_RUN:-1}

run() {
  echo "+ $*"
  if [[ "${DRY_RUN}" == "0" ]]; then
    "$@"
  fi
}

: "${PROJECT:?set PROJECT}"

for topic in tasks tasks-dlq results; do
  run gcloud pubsub topics create "${topic}" --project="${PROJECT}" || true
done

run gcloud pubsub subscriptions create tasks-local \
  --project="${PROJECT}" \
  --topic=tasks \
  --ack-deadline=60 \
  --message-retention-duration=7d \
  --min-retry-delay=10s \
  --max-retry-delay=600s \
  --dead-letter-topic=tasks-dlq \
  --max-delivery-attempts=5

run gcloud pubsub subscriptions create tasks-dlq-hold \
  --project="${PROJECT}" \
  --topic=tasks-dlq

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT}" --format='value(projectNumber)')"
PSA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

run gcloud pubsub topics add-iam-policy-binding tasks-dlq \
  --project="${PROJECT}" \
  --member="serviceAccount:${PSA}" \
  --role=roles/pubsub.publisher

run gcloud pubsub subscriptions add-iam-policy-binding tasks-local \
  --project="${PROJECT}" \
  --member="serviceAccount:${PSA}" \
  --role=roles/pubsub.subscriber

run gcloud pubsub topics add-iam-policy-binding tasks \
  --project="${PROJECT}" \
  --member="serviceAccount:sa-telegram-listener@${PROJECT}.iam.gserviceaccount.com" \
  --role=roles/pubsub.publisher

run gcloud pubsub subscriptions add-iam-policy-binding tasks-local \
  --project="${PROJECT}" \
  --member="serviceAccount:sa-local-puller@${PROJECT}.iam.gserviceaccount.com" \
  --role=roles/pubsub.subscriber
