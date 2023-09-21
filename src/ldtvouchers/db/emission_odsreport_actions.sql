SELECT
    a.actionid AS action,
    datetime(a.timestamp_utc, "localtime") AS date,
    a.origin AS origin,
    u.label AS user,
    tv.token AS voucher,
    a.requestid AS request,
    a.responseid AS response
FROM actions a
LEFT JOIN users u USING(userid)
LEFT JOIN vouchers v USING(voucherid)
LEFT JOIN tokens tu ON a.userid = tu.idintable AND tu.tablename = "users"
LEFT JOIN tokens tv ON a.voucherid = tv.idintable AND tv.tablename = "vouchers"
LEFT JOIN emissions e ON v.emissionid = e.emissionid;