-- name: resources-per-account-service
-- description: Resource count per account per service
-- params: account
SELECT
    account_id, service, COUNT(*) AS count
FROM resources
WHERE {scan_filter}
GROUP BY account_id, service
ORDER BY account_id, count DESC
