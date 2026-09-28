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
ZONE="${ZONE:-us-central1-a}"
NAME="${NAME:-jobhub-telegram-listener}"

run gcloud compute firewall-rules create jobhub-deny-ingress \
  --project="${PROJECT}" \
  --direction=INGRESS \
  --priority=1000 \
  --network=default \
  --action=DENY \
  --rules=all \
  --source-ranges=0.0.0.0/0

run gcloud compute firewall-rules create jobhub-iap-ssh \
  --project="${PROJECT}" \
  --direction=INGRESS \
  --priority=100 \
  --network=default \
  --action=ALLOW \
  --rules=tcp:22 \
  --source-ranges=35.235.240.0/20 \
  --target-tags=jobhub-telegram

cat <<'REMOTE'
#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y unattended-upgrades python3-venv
fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl reload sshd || systemctl reload ssh
id -u jobhub &>/dev/null || useradd --system --home /var/lib/jobhub --create-home jobhub
install -d -o jobhub -g jobhub /var/lib/jobhub
REMOTE

echo "Run on VM via IAP:"
echo "  gcloud compute ssh --tunnel-through-iap ${NAME} --project=${PROJECT} --zone=${ZONE} -- bash -s < remote-setup.sh"
