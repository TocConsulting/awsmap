-- name: rds-no-multi-az
-- description: RDS instances without Multi-AZ enabled
-- params: account
SELECT
    name, region, account_id,
    json_extract(details, '$.engine') AS engine,
    json_extract(details, '$.instance_class') AS instance_class
FROM resources
WHERE {scan_filter}
AND service = 'rds' AND type = 'db-instance'
AND json_extract(details, '$.multi_az') = 0
ORDER BY account_id, region, name
