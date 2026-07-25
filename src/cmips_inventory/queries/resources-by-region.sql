-- name: resources-by-region
-- description: Resource count per region
-- params: account, service
SELECT
    region, COUNT(*) AS count
FROM resources
WHERE {scan_filter}
GROUP BY region
ORDER BY count DESC
