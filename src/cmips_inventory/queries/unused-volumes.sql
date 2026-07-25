-- name: unused-volumes
-- description: EBS volumes not attached to any instance
-- params: account
SELECT
    name, region, account_id,
    json_extract(details, '$.size_gb') AS size_gb,
    json_extract(details, '$.volume_type') AS type,
    json_extract(details, '$.state') AS state
FROM resources
WHERE {scan_filter}
AND service = 'ec2' AND type = 'volume'
AND json_extract(details, '$.state') = 'available'
ORDER BY account_id, region, name
