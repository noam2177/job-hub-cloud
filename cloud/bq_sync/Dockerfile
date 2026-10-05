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

CMD ["python", "main.py"]
