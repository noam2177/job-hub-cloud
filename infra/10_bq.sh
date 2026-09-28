#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${DRY_RUN:-1}"

if [[ -z "${PROJECT:-}" ]]; then
  echo "PROJECT env var is required" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run() {
  echo "+ $*"
  if [[ "${DRY_RUN}" == "0" ]]; then
    "$@"
  fi
}

run bq mk --dataset --location=US "${PROJECT}:jobs" || true

apply_sql() {
  local sql_file="$1"
  echo "+ sed '${sql_file}' | bq query --use_legacy_sql=false"
  if [[ "${DRY_RUN}" == "0" ]]; then
    sed "s/\${PROJECT}/${PROJECT}/g" "${sql_file}" | bq query --use_legacy_sql=false
  fi
}

apply_sql "${ROOT}/sql/ddl_events.sql"
apply_sql "${ROOT}/sql/views.sql"

echo "DRY_RUN=${DRY_RUN} (set DRY_RUN=0 to execute)"
