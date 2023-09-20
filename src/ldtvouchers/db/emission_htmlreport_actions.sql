SELECT a.actionid, datetime(a.timestamp_utc, "localtime") AS timestamp_localtime, a.origin, u.label as user, tv.token as voucher, a.requestid, a.responseid
FROM actions a
LEFT JOIN users u USING(userid)
LEFT JOIN vouchers v USING(voucherid)
LEFT JOIN tokens tu ON a.userid = tu.idintable AND tu.tablename = "users"
LEFT JOIN tokens tv ON a.voucherid = tv.idintable AND tv.tablename = "vouchers"
LEFT JOIN emissions e ON v.emissionid = e.emissionid
WHERE e.emissionid = :emissionid OR e.emissionid IS NULL;