-- name: resources-by-service
-- description: Resource count per service and type
-- params: account, region
SELECT
    service, type, COUNT(*) AS count
FROM resources
WHERE {scan_filter}
GROUP BY service, type
ORDER BY count DESC
