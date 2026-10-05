#!/usr/bin/env bash
# GCE startup: Telegram listener (Pub/Sub) + optional local watcher deps.
# Rendered into instance metadata by scripts/deploy_watcher_vm.sh — not run on dev PC.
set -euo pipefail

PROJECT="${PROJECT:-noam-job-hub-123}"
REPO_URL="${REPO_URL:-https://github.com/noam2177/job-hub-cloud.git}"
REF="${REF:-main}"
APP_USER="${APP_USER:-jobhub}"
APP_HOME="/var/lib/jobhub"
STATE_DIR="${APP_HOME}/state"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git python3-venv python3-pip ca-certificates

id -u "${APP_USER}" &>/dev/null || useradd --system --home "${APP_HOME}" --create-home "${APP_USER}"
install -d -o "${APP_USER}" -g "${APP_USER}" "${STATE_DIR}"

APP_DIR="${APP_HOME}/app"
if [[ ! -d "${APP_DIR}/.git" ]]; then
  git clone --depth 1 --branch "${REF}" "${REPO_URL}" "${APP_DIR}"
fi
cd "${APP_DIR}"
git fetch --depth 1 origin "${REF}" || true
git checkout "${REF}" || true

python3 -m venv "${APP_HOME}/venv"
"${APP_HOME}/venv/bin/pip" install -q -r requirements.txt

cat >/etc/systemd/system/jobhub-telegram.service <<UNIT
[Unit]
Description=Job Hub Telegram intake → Pub/Sub
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=JOBHUB_STATE_DIR=${STATE_DIR}
Environment=GOOGLE_CLOUD_PROJECT=${PROJECT}
Environment=GCP_PROJECT=${PROJECT}
Environment=JOBHUB_PUBSUB_TOPIC=tasks
EnvironmentFile=-/etc/jobhub/env
ExecStart=${APP_HOME}/venv/bin/python -m cloud.telegram_listener
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable jobhub-telegram.service
systemctl restart jobhub-telegram.service || true
