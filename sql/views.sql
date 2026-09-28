CREATE OR REPLACE VIEW `${PROJECT}.jobs.events_dedup` AS
SELECT *
FROM `${PROJECT}.jobs.events`
QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY exported_at DESC) = 1;

CREATE OR REPLACE VIEW `${PROJECT}.jobs.jobs_latest` AS
WITH dedup AS (
  SELECT * FROM `${PROJECT}.jobs.events_dedup`
),
per_job AS (
  SELECT
    job_id,
    MIN(IF(event_type = 'found', ts, NULL)) AS first_found_ts,
    MIN(IF(event_type = 'applied', ts, NULL)) AS applied_ts,
    MIN(IF(event_type = 'reply', ts, NULL)) AS reply_ts,
    MAX(ts) AS last_event_ts,
    ARRAY_AGG(
      STRUCT(event_type, title_family, cv_version, payload)
      ORDER BY ts DESC
      LIMIT 1
    )[OFFSET(0)] AS latest
  FROM dedup
  GROUP BY job_id
)
SELECT
  job_id,
  first_found_ts,
  applied_ts,
  reply_ts,
  last_event_ts,
  latest.event_type AS last_event_type,
  latest.title_family AS title_family,
  latest.cv_version AS cv_version,
  JSON_VALUE(latest.payload, '$.company') AS company,
  JSON_VALUE(latest.payload, '$.title') AS title
FROM per_job;

CREATE OR REPLACE VIEW `${PROJECT}.jobs.days_to_reply` AS
SELECT
  job_id,
  first_found_ts,
  applied_ts,
  reply_ts,
  TIMESTAMP_DIFF(reply_ts, applied_ts, DAY) AS days_to_reply
FROM `${PROJECT}.jobs.jobs_latest`
WHERE applied_ts IS NOT NULL AND reply_ts IS NOT NULL;

CREATE OR REPLACE VIEW `${PROJECT}.jobs.response_rate_by_title_family` AS
WITH applied AS (
  SELECT job_id, title_family
  FROM `${PROJECT}.jobs.events_dedup`
  WHERE event_type = 'applied'
),
replied AS (
  SELECT DISTINCT job_id FROM `${PROJECT}.jobs.events_dedup` WHERE event_type = 'reply'
),
base AS (
  SELECT
    a.title_family,
    COUNT(DISTINCT a.job_id) AS n_applied,
    COUNT(DISTINCT IF(r.job_id IS NOT NULL, a.job_id, NULL)) AS n_replied
  FROM applied a
  LEFT JOIN replied r USING (job_id)
  GROUP BY a.title_family
)
SELECT
  title_family,
  n_applied,
  n_replied,
  SAFE_DIVIDE(n_replied, n_applied) AS rate,
  GREATEST(
    0.0,
    SAFE_DIVIDE(
      n_replied + 3.8416 / 2,
      n_applied + 3.8416
    ) - 1.96 / (n_applied + 3.8416) * SQRT(
      SAFE_DIVIDE(n_replied * (n_applied - n_replied), n_applied) + 3.8416 / 4
    )
  ) AS wilson_low,
  LEAST(
    1.0,
    SAFE_DIVIDE(
      n_replied + 3.8416 / 2,
      n_applied + 3.8416
    ) + 1.96 / (n_applied + 3.8416) * SQRT(
      SAFE_DIVIDE(n_replied * (n_applied - n_replied), n_applied) + 3.8416 / 4
    )
  ) AS wilson_high,
  IF(n_applied < 30, 'insufficient_n', 'ok') AS flag
FROM base;

CREATE OR REPLACE VIEW `${PROJECT}.jobs.response_rate_by_cv_version` AS
WITH applied AS (
  SELECT job_id, cv_version
  FROM `${PROJECT}.jobs.events_dedup`
  WHERE event_type = 'applied'
),
replied AS (
  SELECT DISTINCT job_id FROM `${PROJECT}.jobs.events_dedup` WHERE event_type = 'reply'
),
base AS (
  SELECT
    a.cv_version,
    COUNT(DISTINCT a.job_id) AS n_applied,
    COUNT(DISTINCT IF(r.job_id IS NOT NULL, a.job_id, NULL)) AS n_replied
  FROM applied a
  LEFT JOIN replied r USING (job_id)
  GROUP BY a.cv_version
)
SELECT
  cv_version,
  n_applied,
  n_replied,
  SAFE_DIVIDE(n_replied, n_applied) AS rate,
  GREATEST(
    0.0,
    SAFE_DIVIDE(
      n_replied + 3.8416 / 2,
      n_applied + 3.8416
    ) - 1.96 / (n_applied + 3.8416) * SQRT(
      SAFE_DIVIDE(n_replied * (n_applied - n_replied), n_applied) + 3.8416 / 4
    )
  ) AS wilson_low,
  LEAST(
    1.0,
    SAFE_DIVIDE(
      n_replied + 3.8416 / 2,
      n_applied + 3.8416
    ) + 1.96 / (n_applied + 3.8416) * SQRT(
      SAFE_DIVIDE(n_replied * (n_applied - n_replied), n_applied) + 3.8416 / 4
    )
  ) AS wilson_high,
  IF(n_applied < 30, 'insufficient_n', 'ok') AS flag
FROM base;
