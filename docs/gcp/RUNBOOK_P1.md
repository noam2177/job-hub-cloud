# P1 runbook — Telegram intake + local puller

## Script order

1. `infra/20_vm.sh` — create e2-micro listener VM (`DRY_RUN=1` then `DRY_RUN=0 PROJECT=...`).
2. `infra/21_harden.sh` — IAP-only SSH firewall; run remote setup via `gcloud compute ssh --tunnel-through-iap`.
3. `infra/30_pubsub.sh` — topics `tasks`, `tasks-dlq`, `results`; subscription `tasks-local` (DLQ after 5 attempts).

## Bot token (Secret Manager)

Never pass the token on the command line.

```bash
gcloud secrets create telegram-intake-token --data-file=- --project="${PROJECT}"
# paste token, then Ctrl-D
```

VM: `TOKEN_FROM_SECRET_MANAGER=1`, SA needs `secretAccessor` on that secret.

## Deploy listener

```bash
gcloud compute scp --tunnel-through-iap --recurse cloud jobs_pipeline contracts \
  jobhub-telegram-listener:/opt/jobhub-cloud/ --zone=us-central1-a --project="${PROJECT}"
```

Install `cloud/telegram_listener/requirements.txt` in VM venv; enable `infra/systemd/jobhub-telegram.service` and `jobhub-healthcheck.timer`.

Set `TELEGRAM_ALLOWED_CHAT_IDS` (comma-separated). Optional `REPLY_ACK=1` for «התקבל».

## Hardening checklist

- [ ] IAP SSH only (`35.235.240.0/20`)
- [ ] `PasswordAuthentication no`
- [ ] Dedicated `jobhub` user, `/var/lib/jobhub` state
- [ ] Listener `MemoryMax=300M`, `ProtectSystem=strict`
- [ ] No inbound webhook; outbound long-poll only

## Windows local

- Task Scheduler at logon (no admin): `local\windows\run_puller.ps1`, `run_watcher.ps1`
- `CAREER_DRIVE_BUS_DIR` → synced `inbox_raw/`
- `JOBHUB_DRY_RUN=0` when ready; Hub at `http://127.0.0.1:8788`

## P1-08 soak (7 days)

| Drill | Expected |
|-------|----------|
| VM reboot | Listener resumes; offset monotonic |
| PC off 12h | Pub/Sub retains; catch-up on pull |
| Duplicate Telegram message | One Hub link / one dedupe row |
| Hub down | Nack + retry; no poison ack |

### Drill log

| Date | Drill | Result | Notes |
|------|-------|--------|-------|
| | | | |

## Cost

External IPv4 on the VM is **not** free tier (~$3.65/month — verify in billing). Consider `IPV6_ONLY=1` variant in `20_vm.sh` (UNVERIFIED).
