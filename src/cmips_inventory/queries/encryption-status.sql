-- name: encryption-status
-- description: S3 buckets and their encryption configuration
-- params: account
SELECT
    name, region, account_id,
    json_extract(details, '$.encryption') AS encryption
FROM resources
WHERE {scan_filter}
AND service = 's3' AND type = 'bucket'
ORDER BY encryption, account_id, name
