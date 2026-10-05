#!/usr/bin/env bash
# e2-micro Telegram listener VM (Always Free in us-central1 when within free limits).
# Prerequisite: secret telegram-intake-token + /etc/jobhub/env on VM (see RUNBOOK_P1.md).
#
#   export PROJECT=noam-job-hub-123 ZONE=us-central1-a
#   DRY_RUN=1 bash scripts/deploy_watcher_vm.sh
#   DRY_RUN=0 bash scripts/deploy_watcher_vm.sh
set -euo pipefail

DRY_RUN="${DRY_RUN:-1}"
PROJECT="${PROJECT:-noam-job-hub-123}"
ZONE="${ZONE:-us-central1-a}"
REGION="${REGION:-us-central1}"
NAME="${NAME:-jobhub-telegram-listener}"
SA="sa-telegram-listener@${PROJECT}.iam.gserviceaccount.com"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STARTUP="${ROOT}/scripts/vm_startup_watcher.sh"

run() {
  echo "+ $*"
  if [[ "${DRY_RUN}" == "0" ]]; then
    "$@"
  fi
}

echo "=== Enable P1 APIs ==="
run env PROJECT="${PROJECT}" DRY_RUN="${DRY_RUN}" bash "${ROOT}/infra/01_apis.sh" p1
run env PROJECT="${PROJECT}" DRY_RUN="${DRY_RUN}" bash "${ROOT}/infra/30_pubsub.sh"

echo "=== Secret accessor for listener SA ==="
run gcloud secrets add-iam-policy-binding telegram-intake-token \
  --project="${PROJECT}" \
  --member="serviceAccount:${SA}" \
  --role=roles/secretmanager.secretAccessor || true

run gcloud compute instances create "${NAME}" \
  --project="${PROJECT}" \
  --zone="${ZONE}" \
  --machine-type=e2-micro \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-standard \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --service-account="${SA}" \
  --scopes=cloud-platform \
  --tags=jobhub-telegram \
  --network-tier=STANDARD \
  --metadata="PROJECT=${PROJECT},REF=main" \
  --metadata-from-file=startup-script="${STARTUP}"

echo "DRY_RUN=${DRY_RUN}"
echo "After VM boots: create /etc/jobhub/env with TELEGRAM_INTAKE_ALLOWED_CHAT_IDS=..."
echo "Token via Secret Manager (telegram-intake-token). See docs/gcp/RUNBOOK_P1.md"
