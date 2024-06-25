SELECT
	v.sortnumber AS sortnumber,
	t.token AS token,
	v.value_CAN AS value_CAN,
	COALESCE(ud.label, "") AS distributed_by,
	COALESCE(uc.label, "") AS cashedin_by,
	datetime(v.cashedin_utc, "localtime") AS cashedin_localtime,
	datetime(e.expiration_utc, "localtime") AS expiration_localtime
FROM vouchers v
LEFT JOIN tokens t ON v.voucherid = t.idintable AND t.tablename = "vouchers"
LEFT JOIN users ud ON v.distributed_by = ud.userid
LEFT JOIN users uc ON v.cashedin_by = uc.userid
LEFT JOIN emissions e USING(emissionid)
WHERE v.emissionid = :emissionid
ORDER BY v.sortnumber ASC;