-- name: public-s3-buckets
-- description: S3 buckets with public access enabled
-- params: account
SELECT
    name, region, account_id,
    json_extract(details, '$.public_access') AS public_access
FROM resources
WHERE {scan_filter}
AND service = 's3' AND type = 'bucket'
AND json_extract(details, '$.public_access') = 1
ORDER BY account_id, name
