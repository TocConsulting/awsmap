-- name: rds-engines
-- description: RDS instances grouped by engine
-- params: account
SELECT
    json_extract(details, '$.engine') AS engine,
    json_extract(details, '$.engine_version') AS version,
    COUNT(*) AS count
FROM resources
WHERE {scan_filter}
AND service = 'rds' AND type = 'db-instance'
GROUP BY engine, version
ORDER BY count DESC
