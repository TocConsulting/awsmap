-- name: cross-account-roles
-- description: IAM roles with trust policies allowing external accounts
-- params: account
SELECT
    name,
    account_id,
    CASE
        WHEN json_extract(details, '$.trust_policy') LIKE '%"Federated"%' THEN 'Federated: ' || json_extract(json_extract(details, '$.trust_policy'), '$.Statement[0].Principal.Federated')
        WHEN json_extract(details, '$.trust_policy') LIKE '%"AWS"%' THEN 'AWS: ' || json_extract(json_extract(details, '$.trust_policy'), '$.Statement[0].Principal.AWS')
        WHEN json_extract(details, '$.trust_policy') LIKE '%"Service"%' THEN 'Service: ' || json_extract(json_extract(details, '$.trust_policy'), '$.Statement[0].Principal.Service')
        ELSE 'Unknown'
    END AS external_principal
FROM resources
WHERE {scan_filter}
AND service = 'iam' AND type = 'role'
AND json_extract(details, '$.trust_policy') LIKE '%arn:aws:iam::%'
ORDER BY account_id, name
