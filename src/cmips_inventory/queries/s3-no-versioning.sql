-- name: s3-no-versioning
-- description: S3 buckets without versioning enabled
-- params: account
SELECT
    name, region, account_id,
    json_extract(details, '$.versioning') AS versioning
FROM resources
WHERE {scan_filter}
AND service = 's3' AND type = 'bucket'
AND (json_extract(details, '$.versioning') IS NULL
     OR json_extract(details, '$.versioning') != 'Enabled')
ORDER BY account_id, name
