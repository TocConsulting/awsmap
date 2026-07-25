-- name: rds-public
-- description: RDS instances with public access enabled
-- params: account
SELECT
    name, region, account_id,
    json_extract(details, '$.engine') AS engine,
    json_extract(details, '$.instance_class') AS instance_class
FROM resources
WHERE {scan_filter}
AND service = 'rds' AND type = 'db-instance'
AND json_extract(details, '$.publicly_accessible') = 1
ORDER BY account_id, region, name
