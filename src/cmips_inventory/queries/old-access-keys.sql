-- name: old-access-keys
-- description: IAM users with access keys (check create_date for age)
-- params: account
SELECT
    name, account_id,
    json_extract(details, '$.access_keys_count') AS keys,
    json_extract(details, '$.create_date') AS user_created,
    json_extract(details, '$.mfa_enabled') AS mfa
FROM resources
WHERE {scan_filter}
AND service = 'iam' AND type = 'user'
AND json_extract(details, '$.access_keys_count') > 0
ORDER BY account_id, name
