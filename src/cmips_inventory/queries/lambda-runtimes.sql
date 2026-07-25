-- name: lambda-runtimes
-- description: Lambda functions grouped by runtime
-- params: account
SELECT
    json_extract(details, '$.runtime') AS runtime,
    COUNT(*) AS count
FROM resources
WHERE {scan_filter}
AND service = 'lambda' AND type = 'function'
GROUP BY runtime
ORDER BY count DESC
