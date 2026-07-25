-- name: open-security-groups
-- description: Security groups with inbound rules open to 0.0.0.0/0
-- params: account
SELECT
    name, region, account_id,
    json_extract(details, '$.inbound_rules') AS inbound_rules
FROM resources
WHERE {scan_filter}
AND service = 'ec2' AND type = 'security-group'
AND json_extract(details, '$.inbound_rules') LIKE '%0.0.0.0/0%'
ORDER BY account_id, region, name
