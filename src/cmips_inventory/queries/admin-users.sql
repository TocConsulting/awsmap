-- name: admin-users
-- description: IAM users with admin permissions (direct or via group membership)
-- params: account
SELECT
    u.name,
    u.account_id,
    json_extract(u.details, '$.mfa_enabled') AS mfa,
    json_extract(u.details, '$.groups') AS groups,
    CASE
        WHEN json_extract(u.details, '$.attached_policies') LIKE '%AdministratorAccess%' THEN 'DIRECT'
        WHEN EXISTS (
            SELECT 1 FROM resources g
            WHERE g.service = 'iam' AND g.type = 'group'
            AND g.account_id = u.account_id
            AND json_extract(u.details, '$.groups') LIKE '%' || g.name || '%'
            AND json_extract(g.details, '$.attached_policies') LIKE '%AdministratorAccess%'
            AND {scan_filter_g}
        ) THEN 'VIA GROUP'
        ELSE 'NONE'
    END AS admin_source
FROM resources u
WHERE {scan_filter_u}
AND u.service = 'iam' AND u.type = 'user'
AND (
    json_extract(u.details, '$.attached_policies') LIKE '%AdministratorAccess%'
    OR EXISTS (
        SELECT 1 FROM resources g
        WHERE g.service = 'iam' AND g.type = 'group'
        AND g.account_id = u.account_id
        AND json_extract(u.details, '$.groups') LIKE '%' || g.name || '%'
        AND json_extract(g.details, '$.attached_policies') LIKE '%AdministratorAccess%'
        AND {scan_filter_g}
    )
)
ORDER BY u.account_id, admin_source, u.name
