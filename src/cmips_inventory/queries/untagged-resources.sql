-- name: untagged-resources
-- description: Resources without any tags
-- params: account, service
SELECT
    name, service, type, region, account_id
FROM resources
WHERE {scan_filter}
AND (tags IS NULL OR tags = '{}')
ORDER BY account_id, service, type, region
