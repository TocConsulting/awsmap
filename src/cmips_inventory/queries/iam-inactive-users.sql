-- name: iam-inactive-users
-- description: IAM users who have never logged in or have no access keys
-- params: account
SELECT
    name, account_id,
    json_extract(details, '$.password_last_used') AS last_login,
    json_extract(details, '$.access_keys_count') AS access_keys,
    json_extract(details, '$.mfa_enabled') AS mfa
FROM resources
WHERE {scan_filter}
AND service = 'iam' AND type = 'user'
AND (json_extract(details, '$.password_last_used') IS NULL
     OR json_extract(details, '$.password_last_used') = 'N/A')
AND json_extract(details, '$.access_keys_count') = 0
ORDER BY account_id, name
