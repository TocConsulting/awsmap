-- name: secrets-no-rotation
-- description: Secrets Manager secrets without automatic rotation
-- params: account
SELECT
    name, region, account_id
FROM resources
WHERE {scan_filter}
AND service = 'secretsmanager' AND type = 'secret'
AND (json_extract(details, '$.rotation_enabled') IS NULL
     OR json_extract(details, '$.rotation_enabled') = 0)
ORDER BY account_id, region, name
