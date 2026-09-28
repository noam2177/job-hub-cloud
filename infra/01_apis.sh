#!/usr/bin/env bash
# G0-3: enable APIs one phase at a time (smallest surface).
# Usage: PROJECT=<id> DRY_RUN=1 bash infra/01_apis.sh <g0|p1|p5>
# No p3 phase: D-7 keeps the CV local, so Vertex AI Search is never enabled.
set -euo pipefail
: "${PROJECT:?set PROJECT}"
DRY_RUN="${DRY_RUN:-1}"
PHASE="${1:?phase: g0|p1|p5}"

run() {
  echo "+ $*"
  if [[ "$DRY_RUN" == "0" ]]; then "$@"; fi
}

case "$PHASE" in
  g0) APIS=(iam.googleapis.com bigquery.googleapis.com) ;;
  p1) APIS=(compute.googleapis.com iap.googleapis.com pubsub.googleapis.com secretmanager.googleapis.com) ;;
  p5) APIS=(documentai.googleapis.com aiplatform.googleapis.com) ;;
  *) echo "unknown phase: $PHASE" >&2; exit 2 ;;
esac

run gcloud services enable "${APIS[@]}" --project="$PROJECT"
