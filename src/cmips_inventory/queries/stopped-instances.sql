-- name: stopped-instances
-- description: EC2 instances in stopped state
-- params: account
SELECT
    name, region, account_id,
    json_extract(details, '$.instance_type') AS instance_type,
    json_extract(details, '$.state') AS state
FROM resources
WHERE {scan_filter}
AND service = 'ec2' AND type = 'instance'
AND json_extract(details, '$.state') = 'stopped'
ORDER BY account_id, region, name
