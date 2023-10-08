SELECT
    a.timestamp_utc,
    u.label AS user_label,
    u.description AS user_description,
    a.requestid,
    a.responseid
FROM actions a, users u
ON a.userid = u.userid
WHERE a.voucherid = :voucherid
ORDER BY a.timestamp_utc ASC;