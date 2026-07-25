-- name: admin-roles
-- description: IAM roles with admin policies attached
-- params: account
SELECT
    name,
    account_id,
    json_extract(details, '$.attached_policies') AS policies
FROM resources
WHERE {scan_filter}
AND service = 'iam' AND type = 'role'
AND json_extract(details, '$.attached_policies') LIKE '%AdministratorAccess%'
ORDER BY account_id, name
