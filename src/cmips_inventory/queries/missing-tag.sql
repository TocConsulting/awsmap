-- name: missing-tag
-- description: Resources missing a required tag (default: Owner)
-- params: account, service, tag=Owner
SELECT
    name, service, type, region, account_id
FROM resources
WHERE {scan_filter}
AND (tags IS NULL OR json_extract(tags, '$.{tag}') IS NULL)
ORDER BY account_id, service, type, region
