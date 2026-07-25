-- name: resources-by-account
-- description: Resource count per account
-- params: service
SELECT
    account_id, COUNT(*) AS count
FROM resources
WHERE {scan_filter}
GROUP BY account_id
ORDER BY count DESC
