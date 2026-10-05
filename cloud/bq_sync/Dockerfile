# Lightweight sync job (Cloud Run Job or manual docker run). Build from repo root:
#   docker build -f cloud/bq_sync/Dockerfile -t jobhub-bq-sync .
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt google-cloud-storage
COPY jobs_pipeline ./jobs_pipeline
COPY cloud/bq_sync/main.py ./main.py

ENV PYTHONUNBUFFERED=1
ENV JOBHUB_STATE_PATH=/tmp/export_state.json
ENV PORT=8080
# job = one-shot CLI (Cloud Run Job); http = Cloud Run Service
ENV JOBHUB_RUN_MODE=http

COPY cloud/bq_sync/http_server.py ./http_server.py

CMD ["sh", "-c", "if [ \"$JOBHUB_RUN_MODE\" = job ]; then python main.py; else python http_server.py; fi"]
