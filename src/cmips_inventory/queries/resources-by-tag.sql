-- name: resources-by-tag
-- description: Resources that have a specific tag (default: Owner)
-- params: account, tag=Owner
SELECT
    name, service, type, region, account_id,
    json_extract(tags, '$.{tag}') AS tag_value
FROM resources
WHERE {scan_filter}
AND json_extract(tags, '$.{tag}') IS NOT NULL
ORDER BY account_id, service, type, name
