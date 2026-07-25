-- name: s3-no-logging
-- description: S3 buckets without access logging enabled
-- params: account
SELECT
    name, region, account_id
FROM resources
WHERE {scan_filter}
AND service = 's3' AND type = 'bucket'
AND (json_extract(details, '$.logging') IS NULL
     OR json_extract(details, '$.logging') = 0)
ORDER BY account_id, name
