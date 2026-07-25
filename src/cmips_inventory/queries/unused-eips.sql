-- name: unused-eips
-- description: Elastic IPs not associated with any instance
-- params: account
SELECT
    name, region, account_id,
    json_extract(details, '$.public_ip') AS public_ip
FROM resources
WHERE {scan_filter}
AND service = 'ec2' AND type = 'elastic-ip'
AND (json_extract(details, '$.instance_id') IS NULL
     OR json_extract(details, '$.instance_id') = '')
ORDER BY account_id, region, name
