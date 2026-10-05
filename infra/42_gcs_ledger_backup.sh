#!/usr/bin/env bash
# Upload local ledger snapshot to GCS (backup for Cloud Run sync). No PII beyond career ledger.
set -euo pipefail
DRY_RUN="${DRY_RUN:-1}"
PROJECT="${PROJECT:-noam-job-hub-123}"
BUCKET="${BUCKET:-${PROJECT}-ledger-backup}"
LEDGER_PATH="${LEDGER_PATH:-}"

run() {
  echo "+ $*"
  if [[ "${DRY_RUN}" == "0" ]]; then
    "$@"
  fi
}

run gsutil mb -p "${PROJECT}" -l US "gs://${BUCKET}" || true
if [[ -z "${LEDGER_PATH}" ]]; then
  echo "Set LEDGER_PATH to local jobs.json before DRY_RUN=0" >&2
  exit 1
fi
run gsutil cp "${LEDGER_PATH}" "gs://${BUCKET}/ledger/jobs.json"
run gsutil versioning set on "gs://${BUCKET}"

echo "DRY_RUN=${DRY_RUN} (GCS storage ~\\$0.02/GB/mo; lifecycle rules recommended)"
