#!/usr/bin/env bash
# P1-01: one e2-micro bridge VM (Always Free: us-central1, 30 GB pd-standard). Creates exactly one VM.
# Usage: PROJECT=<id> DRY_RUN=1 [IPV6_ONLY=1] bash infra/20_vm.sh
# Prerequisite: secret telegram-intake-token exists (NOAM_GUIDE step 5).
set -euo pipefail
DRY_RUN=${DRY_RUN:-1}

run() {
  echo "+ $*"
  if [[ "${DRY_RUN}" == "0" ]]; then
    "$@"
  fi
}

: "${PROJECT:?set PROJECT}"

ZONE="${ZONE:-us-central1-a}"
NAME="${NAME:-jobhub-telegram-listener}"
SA="sa-telegram-listener@${PROJECT}.iam.gserviceaccount.com"

run gcloud secrets add-iam-policy-binding telegram-intake-token \
  --project="${PROJECT}" \
  --member="serviceAccount:${SA}" \
  --role=roles/secretmanager.secretAccessor

COMMON=(
  --project="${PROJECT}"
  --zone="${ZONE}"
  --machine-type=e2-micro
  --boot-disk-size=30GB
  --boot-disk-type=pd-standard
  --image-family=debian-12
  --image-project=debian-cloud
  --service-account="${SA}"
  --scopes=cloud-platform
  --shielded-secure-boot
  --metadata=enable-oslogin=TRUE
  --tags=jobhub-telegram
)

if [[ "${IPV6_ONLY:-0}" == "1" ]]; then
  # UNVERIFIED (CLAUDE_HANDOFF Q1): needs an IPv6-capable subnet; avoids the billed external IPv4.
  run gcloud compute instances create "${NAME}" "${COMMON[@]}" \
    --stack-type=IPV6_ONLY \
    --ipv6-network-tier=PREMIUM
else
  # External IPv4 is billed separately from Always Free (~$3.65/month; see COST_LEDGER.md).
  run gcloud compute instances create "${NAME}" "${COMMON[@]}" \
    --network-tier=STANDARD
fi
