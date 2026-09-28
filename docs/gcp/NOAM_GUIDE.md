# NOAM GUIDE — what only you can do, in order

Each step says where, what to run/click, what you should see, and what to send back. Run every script with
`DRY_RUN=1` first, read the printed commands, then `DRY_RUN=0`. Use Cloud Shell (browser) or Git Bash with gcloud.

## Step 0 — local, 2 minutes (unblocks P2)

In PowerShell, from `principal-architect-hub`:

```powershell
.\.venv\Scripts\python.exe -c "import os,json,pathlib;from dotenv import load_dotenv;load_dotenv();p=pathlib.Path(os.environ['CAREER_DRIVE_BUS_DIR'])/'ledger'/'jobs.json';r=json.loads(p.read_text(encoding='utf-8'))['jobs'];print(len(r));print(sorted({k for x in r for k in x}));print(sorted({str(x.get('status')) for x in r}))"
```

Send back: the three printed lines (count, field names, statuses). No row content is printed.

Then a local dry-run backfill (no cloud, prints a reconciliation report only):

```powershell
cd C:\Users\noam1\Documents\GitHub\job-hub-cloud
.\.venv\Scripts\python.exe -m jobs_pipeline.backfill --jobs "<CAREER_DRIVE_BUS_DIR>\ledger\jobs.json"
```

Send back: the JSON report (counts and reason codes only).

## Step 1 — decisions (reply in chat)

- D-1 taxonomy and D-2 export allow-list in `P2_TAXONOMY.md`: approve or edit.
- Title families: confirm or rename `data_analyst, bi_analyst, data_scientist, ml_engineer, data_engineer, software_engineer, research, other`.
- D-6: OK to drop Tailscale (IAP SSH instead)? D-7: CV stays local? D-9: P3 verifies Spark output instead of writing CVs?

## Step 2 — G0-1 trial and budget (Console, you only)

1. Console → note the trial credit amount and **expiry date** → write both into `COST_LEDGER.md`.
2. Create a budget for the project with alerts at 50 / 90 / 100 % of $10. Screenshot → note the file name in `COST_LEDGER.md`.
3. Put a calendar reminder on day 80: upgrade or tear down (R12).

## Step 3 — G0-2 / G0-3 project, service accounts, APIs

```bash
export PROJECT=<your-project-id>
DRY_RUN=1 bash infra/00_project.sh     # read the output
DRY_RUN=0 bash infra/00_project.sh
DRY_RUN=0 bash infra/01_apis.sh g0
```

Expected: three service accounts listed by `gcloud iam service-accounts list`. Send back that list (emails only).

## Step 4 — P2 BigQuery

Follow `RUNBOOK_P2.md` (`infra/10_bq.sh`, then backfill `--apply`). Then build the dashboard with `docs/looker_steps.md`.
Send back: the backfill report and a screenshot of dashboard page 1.

## Step 5 — P1 intake bot and VM

1. Telegram → @BotFather → `/newbot` → name it e.g. `NoamJobIntakeBot`. Keep the token **only** for the next command.
2. Send any message to the new bot, then get your chat id from @userinfobot. Send back the numeric chat id (not a secret).
3. `DRY_RUN=0 bash infra/01_apis.sh p1`, then store the token without it touching shell history:
   `gcloud secrets create telegram-intake-token --replication-policy=automatic --data-file=-` → paste token → Enter → Ctrl-D.
4. Follow `RUNBOOK_P1.md`: `30_pubsub.sh`, `20_vm.sh`, `21_harden.sh`, deploy, systemd.
5. On the PC: `gcloud auth application-default login --impersonate-service-account=sa-local-puller@<PROJECT>.iam.gserviceaccount.com`,
   then `local\windows\run_puller.ps1` (dry-run first).

Send back: `systemctl status jobhub-telegram` first 5 lines, and whether a test link appeared in the Hub career window.

## Step 6 — P4 local watcher

Create the folder `inbox_raw` inside the Drive bus folder. Run `local\windows\run_watcher.ps1` with `JOBHUB_WATCHER=1`.
Drop one screenshot of a job ad. Send back: the watcher's printed line and whether `state\ocr_queue\` got one file.

## Step 7 — P5 labels

Collect 20 public job-ad images into `data\ads\` (gitignored) and fill `data\ads_gt.csv` from `data\ads_gt_template.csv`
(see `data\README.md`). Send back: "labels ready" (not the files).

## Housekeeping

- GLM review is blocked by the Hub session call cap (`GLM_MAX_CALLS_SESSION`, default 24). When you want the review:
  reset the Hub GLM session ledger the way you normally do, then run
  `..\..\principal-architect-hub\.venv\Scripts\python.exe scripts\glm_review.py` from this repo.
- The Hub has no git history. Before any future Hub code change for this project, run `git init` + first commit there.
