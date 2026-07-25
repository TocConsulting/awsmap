-- name: lambda-high-memory
-- description: Lambda functions with memory greater than 512 MB
-- params: account
SELECT
    name, region, account_id,
    json_extract(details, '$.runtime') AS runtime,
    json_extract(details, '$.memory_size') AS memory_mb,
    json_extract(details, '$.timeout') AS timeout
FROM resources
WHERE {scan_filter}
AND service = 'lambda' AND type = 'function'
AND CAST(json_extract(details, '$.memory_size') AS INTEGER) > 512
ORDER BY CAST(json_extract(details, '$.memory_size') AS INTEGER) DESC
