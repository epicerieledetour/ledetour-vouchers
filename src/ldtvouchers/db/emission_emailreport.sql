SELECT
    u.description AS user, 
    time(cashedin_utc, "localtime") AS localtime,
    tv.token AS token
FROM vouchers v
JOIN tokens tv ON v.voucherid = tv.idintable AND tv.tablename = "vouchers"
JOIN users u ON v.cashedin_by = u.userid
WHERE cashedin_utc >= date(:date_utc) AND cashedin_utc < date(:date_utc, "+1 day")
ORDER BY u.label ASC, v.cashedin_utc ASC;