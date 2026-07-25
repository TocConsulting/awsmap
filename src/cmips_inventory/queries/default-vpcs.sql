-- name: default-vpcs
-- description: Default VPCs across all regions
-- params: account
SELECT
    name, region, account_id,
    json_extract(details, '$.cidr_block') AS cidr
FROM resources
WHERE {scan_filter}
AND service = 'vpc' AND type = 'vpc'
AND is_default = 1
ORDER BY account_id, region
