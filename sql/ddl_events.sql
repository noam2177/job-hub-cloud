CREATE TABLE IF NOT EXISTS `${PROJECT}.jobs.events` (
  event_id STRING NOT NULL,
  job_id STRING,
  event_type STRING,
  ts TIMESTAMP,
  cv_version STRING,
  title_family STRING,
  keywords ARRAY<STRING>,
  source_type STRING,
  payload JSON,
  exported_at TIMESTAMP
)
PARTITION BY DATE(ts)
CLUSTER BY event_type, title_family;
