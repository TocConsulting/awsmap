-- name: rds-unencrypted
-- description: RDS instances without encryption
-- params: account
SELECT
    name, region, account_id,
    json_extract(details, '$.engine') AS engine,
    json_extract(details, '$.instance_class') AS instance_class,
    json_extract(details, '$.allocated_storage') AS storage_gb
FROM resources
WHERE {scan_filter}
AND service = 'rds' AND type = 'db-instance'
AND json_extract(details, '$.storage_encrypted') = 0
ORDER BY account_id, region, name
