SELECT
  'duplicate_event_id' AS check_name,
  COUNT(*) - COUNT(DISTINCT event_id) AS value,
  0 AS threshold,
  IF(COUNT(*) - COUNT(DISTINCT event_id) > 0, 'fail', 'ok') AS status
FROM `${PROJECT}.jobs.events`;

SELECT
  CONCAT('null_rate_', col) AS check_name,
  SAFE_DIVIDE(nulls, total) AS value,
  0.5 AS threshold,
  IF(SAFE_DIVIDE(nulls, total) > 0.5, 'fail', 'ok') AS status
FROM (
  SELECT 'event_id' AS col, COUNTIF(event_id IS NULL) AS nulls, COUNT(*) AS total
  FROM `${PROJECT}.jobs.events`
  WHERE ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  UNION ALL
  SELECT 'job_id', COUNTIF(job_id IS NULL), COUNT(*)
  FROM `${PROJECT}.jobs.events`
  WHERE ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  UNION ALL
  SELECT 'event_type', COUNTIF(event_type IS NULL), COUNT(*)
  FROM `${PROJECT}.jobs.events`
  WHERE ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  UNION ALL
  SELECT 'ts', COUNTIF(ts IS NULL), COUNT(*)
  FROM `${PROJECT}.jobs.events`
  WHERE ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  UNION ALL
  SELECT 'exported_at', COUNTIF(exported_at IS NULL), COUNT(*)
  FROM `${PROJECT}.jobs.events`
  WHERE ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
);

SELECT
  'freshness_hours_since_export' AS check_name,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(exported_at), HOUR) AS value,
  48 AS threshold,
  IF(
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(exported_at), HOUR) > 48,
    'fail',
    'ok'
  ) AS status
FROM `${PROJECT}.jobs.events`;

SELECT
  'unknown_event_type_count' AS check_name,
  COUNTIF(
    event_type NOT IN (
      'found',
      'draft_created',
      'applied',
      'reply',
      'interview',
      'reject',
      'offer',
      'withdrawn',
      'closed'
    )
  ) AS value,
  0 AS threshold,
  IF(
    COUNTIF(
      event_type NOT IN (
        'found',
        'draft_created',
        'applied',
        'reply',
        'interview',
        'reject',
        'offer',
        'withdrawn',
        'closed'
      )
    ) > 0,
    'fail',
    'ok'
  ) AS status
FROM `${PROJECT}.jobs.events`;
