-- name: users-without-mfa
-- description: IAM users without MFA enabled
-- params: account
SELECT
    name, account_id,
    json_extract(details, '$.password_last_used') AS last_login,
    json_extract(details, '$.access_keys_count') AS access_keys
FROM resources
WHERE {scan_filter}
AND service = 'iam' AND type = 'user'
AND json_extract(details, '$.mfa_enabled') = 0
ORDER BY account_id, name
